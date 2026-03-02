using Masters.Api.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Web.Endpoints;

public sealed class Spots : EndpointGroupBase
{
    private const int DefaultMaxPoints = 1000;
    private const int AbsoluteMaxPoints = 10000;

    public override string GroupName => "spots";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.MapGet(GetSpots);
        groupBuilder.MapGet(GetSpotHistory, "{spotId:long}/history");
    }

    private static async Task<List<SpotStateDto>> GetSpots(
        ApplicationDbContext dbContext,
        CancellationToken cancellationToken)
    {
        return await dbContext.ParkingSpots
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

    private static async Task<IResult> GetSpotHistory(
        long spotId,
        DateTimeOffset? fromUtc,
        DateTimeOffset? toUtc,
        int? maxPoints,
        TimeProvider timeProvider,
        ApplicationDbContext dbContext,
        CancellationToken cancellationToken)
    {
        var spotExists = await dbContext.ParkingSpots
            .AnyAsync(x => x.Id == spotId, cancellationToken);

        if (!spotExists)
        {
            return TypedResults.NotFound();
        }

        var resolvedToUtc = toUtc?.ToUniversalTime() ?? timeProvider.GetUtcNow();
        var resolvedFromUtc = fromUtc?.ToUniversalTime() ?? resolvedToUtc.AddHours(-24);

        if (resolvedFromUtc > resolvedToUtc)
        {
            (resolvedFromUtc, resolvedToUtc) = (resolvedToUtc, resolvedFromUtc);
        }

        var resolvedMaxPoints = maxPoints.GetValueOrDefault(DefaultMaxPoints);
        resolvedMaxPoints = Math.Clamp(resolvedMaxPoints, 1, AbsoluteMaxPoints);

        var points = await dbContext.ParkingTelemetries
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

        return TypedResults.Ok(new SpotHistoryDto(
            spotId,
            resolvedFromUtc,
            resolvedToUtc,
            points));
    }

    private sealed record SpotStateDto(
        long Id,
        string DeviceId,
        string DisplayName,
        bool Occupied,
        double? DistanceCm,
        DateTimeOffset? LastTelemetryAtUtc);

    private sealed record SpotHistoryDto(
        long SpotId,
        DateTimeOffset FromUtc,
        DateTimeOffset ToUtc,
        IReadOnlyList<SpotHistoryPointDto> Points);

    private sealed record SpotHistoryPointDto(
        DateTimeOffset MeasuredAtUtc,
        double DistanceCm,
        bool Occupied);
}
