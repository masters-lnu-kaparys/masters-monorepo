using Masters.Api.Infrastructure.Data;
using Masters.Api.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Web.Services;

public interface IParkingReadService
{
    Task<DashboardSummaryDto> GetSummaryAsync(CancellationToken cancellationToken);

    Task<List<SpotStateDto>> GetSpotsAsync(CancellationToken cancellationToken);

    Task<SpotHistoryDto?> GetSpotHistoryAsync(
        long spotId,
        DateTimeOffset? fromUtc,
        DateTimeOffset? toUtc,
        int? maxPoints,
        CancellationToken cancellationToken);

    Task<DashboardSnapshotDto> GetSnapshotAsync(CancellationToken cancellationToken);
}

public sealed class ParkingReadService : IParkingReadService
{
    private const int DefaultMaxPoints = 1000;
    private const int AbsoluteMaxPoints = 10000;

    private readonly ApplicationDbContext _dbContext;
    private readonly TimeProvider _timeProvider;

    public ParkingReadService(ApplicationDbContext dbContext, TimeProvider timeProvider)
    {
        _dbContext = dbContext;
        _timeProvider = timeProvider;
    }

    public async Task<DashboardSummaryDto> GetSummaryAsync(CancellationToken cancellationToken)
    {
        var totalSpots = await _dbContext.ParkingSpots.CountAsync(cancellationToken);
        var occupiedSpots = await _dbContext.ParkingSpots.CountAsync(x => x.IsOccupied, cancellationToken);
        var freeSpots = totalSpots - occupiedSpots;

        var lastTelemetryAtUtc = await _dbContext.ParkingTelemetries
            .Select(x => (DateTimeOffset?)x.MeasuredAtUtc)
            .MaxAsync(cancellationToken);

        var occupancyRate = totalSpots == 0
            ? 0
            : (double)occupiedSpots / totalSpots;

        return new DashboardSummaryDto(
            totalSpots,
            occupiedSpots,
            freeSpots,
            occupancyRate,
            lastTelemetryAtUtc);
    }

    public async Task<List<SpotStateDto>> GetSpotsAsync(CancellationToken cancellationToken)
    {
        return await _dbContext.ParkingSpots
            .OrderBy(x => x.DeviceId)
            .Select(x => new SpotStateDto(
                x.Id,
                x.DeviceId,
                x.DisplayName,
                x.IsOccupied,
                x.LastDistanceCm,
                x.LastTelemetryAtUtc))
            .ToListAsync(cancellationToken);
    }

    public async Task<SpotHistoryDto?> GetSpotHistoryAsync(
        long spotId,
        DateTimeOffset? fromUtc,
        DateTimeOffset? toUtc,
        int? maxPoints,
        CancellationToken cancellationToken)
    {
        var spotExists = await _dbContext.ParkingSpots
            .AnyAsync(x => x.Id == spotId, cancellationToken);

        if (!spotExists)
        {
            return null;
        }

        var resolvedToUtc = toUtc?.ToUniversalTime() ?? _timeProvider.GetUtcNow();
        var resolvedFromUtc = fromUtc?.ToUniversalTime() ?? resolvedToUtc.AddHours(-24);

        if (resolvedFromUtc > resolvedToUtc)
        {
            (resolvedFromUtc, resolvedToUtc) = (resolvedToUtc, resolvedFromUtc);
        }

        var resolvedMaxPoints = Math.Clamp(maxPoints.GetValueOrDefault(DefaultMaxPoints), 1, AbsoluteMaxPoints);

        var points = await _dbContext.ParkingTelemetries
            .Where(x => x.ParkingSpotId == spotId)
            .Where(x => x.MeasuredAtUtc >= resolvedFromUtc && x.MeasuredAtUtc <= resolvedToUtc)
            .OrderByDescending(x => x.MeasuredAtUtc)
            .Take(resolvedMaxPoints)
            .Select(x => new SpotHistoryPointDto(
                x.MeasuredAtUtc,
                x.DistanceCm,
                x.Occupied))
            .ToListAsync(cancellationToken);

        points.Reverse();

        return new SpotHistoryDto(
            spotId,
            resolvedFromUtc,
            resolvedToUtc,
            points);
    }

    public async Task<DashboardSnapshotDto> GetSnapshotAsync(CancellationToken cancellationToken)
    {
        var summary = await GetSummaryAsync(cancellationToken);
        var spots = await GetSpotsAsync(cancellationToken);

        return new DashboardSnapshotDto(
            _timeProvider.GetUtcNow(),
            summary,
            spots);
    }
}
