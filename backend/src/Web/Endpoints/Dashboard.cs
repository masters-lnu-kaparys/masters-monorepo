using Masters.Api.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Web.Endpoints;

public sealed class Dashboard : EndpointGroupBase
{
    public override string GroupName => "dashboard";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.MapGet(GetSummary, "summary");
    }

    private static async Task<DashboardSummaryDto> GetSummary(
        ApplicationDbContext dbContext,
        CancellationToken cancellationToken)
    {
        var totalSpots = await dbContext.ParkingSpots.CountAsync(cancellationToken);
        var occupiedSpots = await dbContext.ParkingSpots.CountAsync(x => x.IsOccupied, cancellationToken);
        var freeSpots = totalSpots - occupiedSpots;

        var lastTelemetryAtUtc = await dbContext.ParkingTelemetries
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

    private sealed record DashboardSummaryDto(
        int TotalSpots,
        int OccupiedSpots,
        int FreeSpots,
        double OccupancyRate,
        DateTimeOffset? LastTelemetryAtUtc);
}
