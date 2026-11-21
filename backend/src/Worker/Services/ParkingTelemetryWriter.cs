using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Worker.Models;
using Masters.Api.Worker.Options;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Worker.Services;

public enum TelemetryWriteOutcome
{
    Saved = 1,
    Duplicate = 2,
    UnknownSpot = 3,
    SourceMismatch = 4,
    FutureMeasurement = 5,
    ConcurrentChange = 6
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
    private readonly DeviceBindingOptions _deviceBindingOptions;

    public ParkingTelemetryWriter(
        ApplicationDbContext dbContext,
        TimeProvider timeProvider,
        IOptions<DemoTopologyOptions> demoTopologyOptions,
        IOptions<DeviceBindingOptions> deviceBindingOptions)
    {
        _dbContext = dbContext;
        _timeProvider = timeProvider;
        _demoTopologyOptions = demoTopologyOptions.Value;
        _deviceBindingOptions = deviceBindingOptions.Value;
    }

    public async Task<TelemetryWriteResult> WriteAsync(
        DeviceTelemetryMessage message,
        SpotSourceKind sourceKind,
        CancellationToken cancellationToken)
    {
        var receivedAtUtc = _timeProvider.GetUtcNow();
        if (message.MeasuredAtUtc > receivedAtUtc)
        {
            return new TelemetryWriteResult(TelemetryWriteOutcome.FutureMeasurement);
        }

        var spot = await _dbContext.ParkingSpots
            .Include(x => x.ParkingLot)
            .SingleOrDefaultAsync(x => x.DeviceId == message.DeviceId, cancellationToken);

        if (spot is null)
        {
            if (sourceKind != SpotSourceKind.Real)
            {
                return new TelemetryWriteResult(TelemetryWriteOutcome.UnknownSpot);
            }

            var lot = await ResolveParkingLotForRealDeviceAsync(message, cancellationToken);
            if (lot is null)
            {
                await UpsertDetectedDeviceAsync(message, receivedAtUtc, cancellationToken);
                return new TelemetryWriteResult(TelemetryWriteOutcome.UnknownSpot);
            }

            var displayOrder = await _dbContext.ParkingSpots
                .Where(x => x.ParkingLotId == lot.Id && x.SourceKind == SpotSourceKind.Real)
                .CountAsync(cancellationToken);

            spot = new ParkingSpot
            {
                ParkingLotId = lot.Id,
                DeviceId = message.DeviceId,
                DisplayName = ParkingSpotDisplayNameGenerator.Build(
                    ResolveLotKey(lot),
                    SpotSourceKind.Real,
                    displayOrder + 1),
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

        var detectedDevice = await _dbContext.DetectedDevices
            .SingleOrDefaultAsync(x => x.DeviceId == message.DeviceId, cancellationToken);

        if (detectedDevice is not null)
        {
            _dbContext.DetectedDevices.Remove(detectedDevice);
        }

        // Late records belong in history, but must not roll the live map backwards.
        if (spot.LastTelemetryAtUtc is null
            || spot.LastTelemetryAtUtc > receivedAtUtc
            || message.MeasuredAtUtc > spot.LastTelemetryAtUtc)
        {
            spot.IsOccupied = message.Occupied;
            spot.LastDistanceCm = message.DistanceCm;
            if (message.Latitude is not null && message.Longitude is not null)
            {
                spot.LastLatitude = message.Latitude;
                spot.LastLongitude = message.Longitude;
            }
            spot.LastTelemetryAtUtc = message.MeasuredAtUtc;
        }

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
        catch (DbUpdateConcurrencyException)
        {
            // A measurement read before a rebind must not update the new device's state.
            _dbContext.ChangeTracker.Clear();
            return new TelemetryWriteResult(TelemetryWriteOutcome.ConcurrentChange, spot.Id, spot.DisplayName);
        }
        catch (DbUpdateException ex) when (IsUniqueConstraintViolation(ex))
        {
            _dbContext.ChangeTracker.Clear();
            return new TelemetryWriteResult(TelemetryWriteOutcome.Duplicate, spot.Id, spot.DisplayName);
        }
    }

    private async Task UpsertDetectedDeviceAsync(
        DeviceTelemetryMessage message,
        DateTimeOffset receivedAtUtc,
        CancellationToken cancellationToken)
    {
        var entity = await _dbContext.DetectedDevices
            .SingleOrDefaultAsync(x => x.DeviceId == message.DeviceId, cancellationToken);

        if (entity is null)
        {
            entity = new DetectedDevice
            {
                DeviceId = message.DeviceId,
                FirstSeenAtUtc = receivedAtUtc
            };

            _dbContext.DetectedDevices.Add(entity);
        }

        entity.LastSeenAtUtc = receivedAtUtc;
        if (entity.LastMeasuredAtUtc > receivedAtUtc || message.MeasuredAtUtc > entity.LastMeasuredAtUtc)
        {
            entity.LastMeasuredAtUtc = message.MeasuredAtUtc;
            entity.LastDistanceCm = message.DistanceCm;
            entity.LastOccupied = message.Occupied;
            entity.LastLatitude = message.Latitude;
            entity.LastLongitude = message.Longitude;
        }

        await _dbContext.SaveChangesAsync(cancellationToken);
    }

    private async Task<ParkingLot?> ResolveParkingLotForRealDeviceAsync(
        DeviceTelemetryMessage message,
        CancellationToken cancellationToken)
    {
        var configuredLot = _demoTopologyOptions.Lots
            .FirstOrDefault(x => x.RealSpotDeviceIds.Contains(message.DeviceId, StringComparer.OrdinalIgnoreCase));

        if (configuredLot is not null)
        {
            return await ResolveConfiguredLotAsync(configuredLot, cancellationToken);
        }

        if (message.Latitude is not null && message.Longitude is not null)
        {
            var nearestLotId = await ResolveNearestLotIdAsync(
                message.Latitude.Value,
                message.Longitude.Value,
                cancellationToken);

            if (nearestLotId.HasValue)
            {
                return await _dbContext.ParkingLots
                    .SingleAsync(x => x.Id == nearestLotId.Value, cancellationToken);
            }
        }

        return null;
    }

    private async Task<ParkingLot> ResolveConfiguredLotAsync(
        DemoLotOptions configuredLot,
        CancellationToken cancellationToken)
    {
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

    private async Task<long?> ResolveNearestLotIdAsync(
        double latitude,
        double longitude,
        CancellationToken cancellationToken)
    {
        var lots = await _dbContext.ParkingLots
            .AsNoTracking()
            .Select(x => new
            {
                x.Id,
                x.Latitude,
                x.Longitude
            })
            .ToListAsync(cancellationToken);

        var nearestLot = lots
            .Select(x => new
            {
                x.Id,
                DistanceKm = CalculateDistanceKm(latitude, longitude, x.Latitude, x.Longitude)
            })
            .OrderBy(x => x.DistanceKm)
            .FirstOrDefault();

        if (nearestLot is null || nearestLot.DistanceKm > _deviceBindingOptions.MaxParkingLotDistanceKm)
        {
            return null;
        }

        return nearestLot.Id;
    }

    private string ResolveLotKey(ParkingLot lot)
    {
        var configuredLot = _demoTopologyOptions.Lots
            .FirstOrDefault(x =>
                x.City.Equals(lot.City, StringComparison.OrdinalIgnoreCase)
                && x.Name.Equals(lot.Name, StringComparison.OrdinalIgnoreCase));

        return configuredLot?.Key ?? $"lot{lot.Id}";
    }

    private static bool IsUniqueConstraintViolation(DbUpdateException ex)
    {
        return ex.InnerException is SqlException sqlException
            && (sqlException.Number == 2601 || sqlException.Number == 2627);
    }

    private static double CalculateDistanceKm(
        double latitudeA,
        double longitudeA,
        double latitudeB,
        double longitudeB)
    {
        const double earthRadiusKm = 6371d;

        var deltaLatitude = DegreesToRadians(latitudeB - latitudeA);
        var deltaLongitude = DegreesToRadians(longitudeB - longitudeA);
        var latitudeARadians = DegreesToRadians(latitudeA);
        var latitudeBRadians = DegreesToRadians(latitudeB);

        var haversine = Math.Sin(deltaLatitude / 2) * Math.Sin(deltaLatitude / 2)
            + Math.Cos(latitudeARadians) * Math.Cos(latitudeBRadians)
            * Math.Sin(deltaLongitude / 2) * Math.Sin(deltaLongitude / 2);

        var arc = 2 * Math.Atan2(Math.Sqrt(haversine), Math.Sqrt(1 - haversine));
        return earthRadiusKm * arc;
    }

    private static double DegreesToRadians(double degrees) => degrees * (Math.PI / 180d);
}
