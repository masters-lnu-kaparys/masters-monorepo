using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Web.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Web.Services;

public interface IParkingReadService
{
    Task<DashboardSummaryDto> GetSummaryAsync(CancellationToken cancellationToken);

    Task<List<SpotStateDto>> GetSpotsAsync(CancellationToken cancellationToken);

    Task<MapOverviewDto> GetMapOverviewAsync(CancellationToken cancellationToken);

    Task<LotDetailsDto?> GetLotDetailsAsync(long lotId, CancellationToken cancellationToken);

    Task<SpotHistoryDto?> GetSpotHistoryAsync(
        long spotId,
        DateTimeOffset? fromUtc,
        DateTimeOffset? toUtc,
        int? maxPoints,
        CancellationToken cancellationToken);

    Task<DashboardSnapshotDto> GetSnapshotAsync(CancellationToken cancellationToken);

    Task<MapSnapshotDto> GetMapSnapshotAsync(CancellationToken cancellationToken);
}

public sealed class ParkingReadService : IParkingReadService
{
    private const int DefaultMaxPoints = 1000;
    private const int AbsoluteMaxPoints = 10000;

    private readonly ApplicationDbContext _dbContext;
    private readonly TimeProvider _timeProvider;
    private readonly DemoMapOptions _demoMapOptions;

    public ParkingReadService(
        ApplicationDbContext dbContext,
        TimeProvider timeProvider,
        IOptions<DemoMapOptions> demoMapOptions)
    {
        _dbContext = dbContext;
        _timeProvider = timeProvider;
        _demoMapOptions = demoMapOptions.Value;
    }

    public async Task<DashboardSummaryDto> GetSummaryAsync(CancellationToken cancellationToken)
    {
        var mapOverview = await GetMapOverviewAsync(cancellationToken);

        return new DashboardSummaryDto(
            mapOverview.Summary.TotalSpots,
            mapOverview.Summary.OccupiedSpots,
            mapOverview.Summary.FreeSpots,
            mapOverview.Summary.OccupancyRate,
            mapOverview.Summary.LastUpdatedAtUtc);
    }

    public async Task<List<SpotStateDto>> GetSpotsAsync(CancellationToken cancellationToken)
    {
        return await _dbContext.ParkingSpots
            .AsNoTracking()
            .OrderBy(x => x.ParkingLot.City)
            .ThenBy(x => x.ParkingLot.Name)
            .ThenBy(x => x.DisplayName)
            .Select(x => new SpotStateDto(
                x.Id,
                x.DeviceId,
                x.DisplayName,
                x.IsOccupied,
                x.LastDistanceCm,
                x.LastTelemetryAtUtc))
            .ToListAsync(cancellationToken);
    }

    public async Task<MapOverviewDto> GetMapOverviewAsync(CancellationToken cancellationToken)
    {
        var lots = await GetLotMapDtosAsync(cancellationToken);
        var summary = BuildMapSummary(lots);

        return new MapOverviewDto(
            new MapCenterDto(_demoMapOptions.FallbackLatitude, _demoMapOptions.FallbackLongitude),
            _demoMapOptions.FallbackZoom,
            _demoMapOptions.FallbackCity,
            _demoMapOptions.MaxUserDistanceKm,
            summary,
            lots);
    }

    public async Task<LotDetailsDto?> GetLotDetailsAsync(long lotId, CancellationToken cancellationToken)
    {
        var lot = await _dbContext.ParkingLots
            .AsNoTracking()
            .Where(x => x.Id == lotId)
            .Select(x => new
            {
                x.Id,
                x.Name,
                x.City,
                x.Address,
                x.Latitude,
                x.Longitude,
                TotalSpots = x.Spots.Count(),
                OccupiedSpots = x.Spots.Count(spot => spot.IsOccupied),
                LastUpdatedAtUtc = x.Spots.Max(spot => (DateTimeOffset?)spot.LastTelemetryAtUtc)
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (lot is null)
        {
            return null;
        }

        var spots = await _dbContext.ParkingSpots
            .AsNoTracking()
            .Where(x => x.ParkingLotId == lotId)
            .OrderBy(x => x.DisplayName)
            .Select(x => new LotSpotStateDto(
                x.Id,
                x.DeviceId,
                x.DisplayName,
                x.IsOccupied,
                x.LastDistanceCm,
                x.LastTelemetryAtUtc))
            .ToListAsync(cancellationToken);

        var recentActivity = await _dbContext.ParkingTelemetries
            .AsNoTracking()
            .Where(x => x.ParkingSpot.ParkingLotId == lotId)
            .OrderByDescending(x => x.MeasuredAtUtc)
            .Take(12)
            .Select(x => new LotActivityDto(
                x.ParkingSpotId,
                x.ParkingSpot.DisplayName,
                x.Occupied,
                x.DistanceCm,
                x.MeasuredAtUtc))
            .ToListAsync(cancellationToken);

        var freeSpots = lot.TotalSpots - lot.OccupiedSpots;
        var occupancyRate = lot.TotalSpots == 0
            ? 0
            : (double)lot.OccupiedSpots / lot.TotalSpots;

        return new LotDetailsDto(
            lot.Id,
            lot.Name,
            lot.City,
            lot.Address,
            lot.Latitude,
            lot.Longitude,
            lot.TotalSpots,
            lot.OccupiedSpots,
            freeSpots,
            occupancyRate,
            lot.LastUpdatedAtUtc,
            spots,
            recentActivity);
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
            .AsNoTracking()
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

    public async Task<MapSnapshotDto> GetMapSnapshotAsync(CancellationToken cancellationToken)
    {
        var lots = await GetLotMapDtosAsync(cancellationToken);
        var summary = BuildMapSummary(lots);

        return new MapSnapshotDto(
            _timeProvider.GetUtcNow(),
            summary,
            lots);
    }

    private async Task<List<ParkingLotMapDto>> GetLotMapDtosAsync(CancellationToken cancellationToken)
    {
        var lots = await _dbContext.ParkingLots
            .AsNoTracking()
            .OrderBy(x => x.City)
            .ThenBy(x => x.Name)
            .Select(x => new
            {
                x.Id,
                x.Name,
                x.City,
                x.Address,
                x.Latitude,
                x.Longitude,
                TotalSpots = x.Spots.Count(),
                OccupiedSpots = x.Spots.Count(spot => spot.IsOccupied),
                LastUpdatedAtUtc = x.Spots.Max(spot => (DateTimeOffset?)spot.LastTelemetryAtUtc)
            })
            .ToListAsync(cancellationToken);

        return lots
            .Select(x =>
            {
                var freeSpots = x.TotalSpots - x.OccupiedSpots;
                var occupancyRate = x.TotalSpots == 0
                    ? 0
                    : (double)x.OccupiedSpots / x.TotalSpots;

                return new ParkingLotMapDto(
                    x.Id,
                    x.Name,
                    x.City,
                    x.Address,
                    x.Latitude,
                    x.Longitude,
                    x.TotalSpots,
                    x.OccupiedSpots,
                    freeSpots,
                    occupancyRate,
                    x.LastUpdatedAtUtc);
            })
            .ToList();
    }

    private static MapSummaryDto BuildMapSummary(IReadOnlyCollection<ParkingLotMapDto> lots)
    {
        var totalLots = lots.Count;
        var totalSpots = lots.Sum(x => x.TotalSpots);
        var occupiedSpots = lots.Sum(x => x.OccupiedSpots);
        var freeSpots = totalSpots - occupiedSpots;
        var occupancyRate = totalSpots == 0
            ? 0
            : (double)occupiedSpots / totalSpots;
        var lastUpdatedAtUtc = lots
            .Select(x => x.LastUpdatedAtUtc)
            .OrderByDescending(x => x)
            .FirstOrDefault();

        return new MapSummaryDto(
            totalLots,
            totalSpots,
            occupiedSpots,
            freeSpots,
            occupancyRate,
            lastUpdatedAtUtc);
    }
}
