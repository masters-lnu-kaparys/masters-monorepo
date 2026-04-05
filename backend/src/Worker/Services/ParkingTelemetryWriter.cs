using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Worker.Models;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Worker.Services;

public enum TelemetryWriteOutcome
{
    Saved = 1,
    Duplicate = 2,
    UnknownSpot = 3,
    SourceMismatch = 4
}

public sealed record TelemetryWriteResult(
    TelemetryWriteOutcome Outcome,
    long? SpotId = null,
    string? SpotName = null);

public interface IParkingTelemetryWriter
{
    Task<TelemetryWriteResult> WriteAsync(
        DeviceTelemetryMessage message,
        SpotSourceKind sourceKind,
        CancellationToken cancellationToken);
}

public sealed class ParkingTelemetryWriter : IParkingTelemetryWriter
{
    private readonly ApplicationDbContext _dbContext;
    private readonly TimeProvider _timeProvider;
    private readonly DemoTopologyOptions _demoTopologyOptions;

    public ParkingTelemetryWriter(
        ApplicationDbContext dbContext,
        TimeProvider timeProvider,
        IOptions<DemoTopologyOptions> demoTopologyOptions)
    {
        _dbContext = dbContext;
        _timeProvider = timeProvider;
        _demoTopologyOptions = demoTopologyOptions.Value;
    }

    public async Task<TelemetryWriteResult> WriteAsync(
        DeviceTelemetryMessage message,
        SpotSourceKind sourceKind,
        CancellationToken cancellationToken)
    {
        var spot = await _dbContext.ParkingSpots
            .Include(x => x.ParkingLot)
            .SingleOrDefaultAsync(x => x.DeviceId == message.DeviceId, cancellationToken);

        if (spot is null)
        {
            if (sourceKind != SpotSourceKind.Real)
            {
                return new TelemetryWriteResult(TelemetryWriteOutcome.UnknownSpot);
            }

            var lot = await ResolveLotForRealDeviceAsync(message.DeviceId, cancellationToken);
            if (lot is null)
            {
                return new TelemetryWriteResult(TelemetryWriteOutcome.UnknownSpot);
            }

            var displayOrder = await _dbContext.ParkingSpots
                .Where(x => x.ParkingLotId == lot.Id)
                .CountAsync(cancellationToken);

            spot = new ParkingSpot
            {
                ParkingLotId = lot.Id,
                DeviceId = message.DeviceId,
                DisplayName = $"Місце {displayOrder + 1:00}",
                SourceKind = SpotSourceKind.Real
            };

            _dbContext.ParkingSpots.Add(spot);
        }

        if (spot.SourceKind != sourceKind)
        {
            return new TelemetryWriteResult(
                TelemetryWriteOutcome.SourceMismatch,
                spot.Id,
                spot.DisplayName);
        }

        var receivedAtUtc = _timeProvider.GetUtcNow();

        spot.IsOccupied = message.Occupied;
        spot.LastDistanceCm = message.DistanceCm;
        spot.LastTelemetryAtUtc = message.MeasuredAtUtc;

        _dbContext.ParkingTelemetries.Add(new ParkingTelemetry
        {
            ParkingSpot = spot,
            MeasuredAtUtc = message.MeasuredAtUtc,
            ReceivedAtUtc = receivedAtUtc,
            DistanceCm = message.DistanceCm,
            Occupied = message.Occupied
        });

        try
        {
            await _dbContext.SaveChangesAsync(cancellationToken);
            return new TelemetryWriteResult(TelemetryWriteOutcome.Saved, spot.Id, spot.DisplayName);
        }
        catch (DbUpdateException ex) when (IsUniqueConstraintViolation(ex))
        {
            _dbContext.ChangeTracker.Clear();
            return new TelemetryWriteResult(TelemetryWriteOutcome.Duplicate, spot.Id, spot.DisplayName);
        }
    }

    private async Task<ParkingLot?> ResolveLotForRealDeviceAsync(string deviceId, CancellationToken cancellationToken)
    {
        var configuredLot = _demoTopologyOptions.Lots
            .FirstOrDefault(x => x.RealSpotDeviceIds.Contains(deviceId, StringComparer.OrdinalIgnoreCase))
            ?? _demoTopologyOptions.Lots.FirstOrDefault();

        if (configuredLot is null)
        {
            return await _dbContext.ParkingLots
                .OrderBy(x => x.Id)
                .FirstOrDefaultAsync(cancellationToken);
        }

        var lot = await _dbContext.ParkingLots
            .SingleOrDefaultAsync(
                x => x.City == configuredLot.City && x.Name == configuredLot.Name,
                cancellationToken);

        if (lot is not null)
        {
            return lot;
        }

        lot = new ParkingLot
        {
            Name = configuredLot.Name,
            City = configuredLot.City,
            Address = configuredLot.Address,
            Latitude = configuredLot.Latitude,
            Longitude = configuredLot.Longitude
        };

        _dbContext.ParkingLots.Add(lot);
        await _dbContext.SaveChangesAsync(cancellationToken);

        return lot;
    }

    private static bool IsUniqueConstraintViolation(DbUpdateException ex)
    {
        return ex.InnerException is SqlException sqlException
            && (sqlException.Number == 2601 || sqlException.Number == 2627);
    }
}
