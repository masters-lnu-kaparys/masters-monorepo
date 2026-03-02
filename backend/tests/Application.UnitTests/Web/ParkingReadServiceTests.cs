using Masters.Api.Domain.Entities;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Web.Services;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Application.UnitTests.Web;

public class ParkingReadServiceTests
{
    [Test]
    public async Task ShouldCalculateDashboardSummary()
    {
        await using var dbContext = CreateDbContext();

        var spotA = new ParkingSpot { DeviceId = "spot-a", DisplayName = "spot-a", IsOccupied = true, LastDistanceCm = 22.1d, LastTelemetryAtUtc = DateTimeOffset.UtcNow.AddMinutes(-1) };
        var spotB = new ParkingSpot { DeviceId = "spot-b", DisplayName = "spot-b", IsOccupied = false, LastDistanceCm = 75.4d, LastTelemetryAtUtc = DateTimeOffset.UtcNow.AddMinutes(-2) };
        var spotC = new ParkingSpot { DeviceId = "spot-c", DisplayName = "spot-c", IsOccupied = true, LastDistanceCm = 30.0d, LastTelemetryAtUtc = DateTimeOffset.UtcNow.AddMinutes(-3) };

        dbContext.ParkingSpots.AddRange(spotA, spotB, spotC);
        await dbContext.SaveChangesAsync();

        var telemetryA = new ParkingTelemetry { ParkingSpotId = spotA.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-3), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-3), DistanceCm = 22.1d, Occupied = true };
        var telemetryB = new ParkingTelemetry { ParkingSpotId = spotB.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-2), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-2), DistanceCm = 75.4d, Occupied = false };
        var telemetryC = new ParkingTelemetry { ParkingSpotId = spotC.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-1), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-1), DistanceCm = 30.0d, Occupied = true };

        dbContext.ParkingTelemetries.AddRange(telemetryA, telemetryB, telemetryC);
        await dbContext.SaveChangesAsync();

        var service = new ParkingReadService(dbContext, TimeProvider.System);

        var summary = await service.GetSummaryAsync(CancellationToken.None);

        summary.TotalSpots.ShouldBe(3);
        summary.OccupiedSpots.ShouldBe(2);
        summary.FreeSpots.ShouldBe(1);
        summary.OccupancyRate.ShouldBe(2d / 3d, 0.0001);
        summary.LastTelemetryAtUtc.ShouldNotBeNull();
        summary.LastTelemetryAtUtc!.Value.ShouldBe(telemetryC.MeasuredAtUtc);
    }

    [Test]
    public async Task ShouldFilterHistoryByRangeAndLimit()
    {
        await using var dbContext = CreateDbContext();

        var now = DateTimeOffset.UtcNow;
        var spot = new ParkingSpot { DeviceId = "spot-history", DisplayName = "spot-history" };

        dbContext.ParkingSpots.Add(spot);
        await dbContext.SaveChangesAsync();

        dbContext.ParkingTelemetries.AddRange(
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-120), ReceivedAtUtc = now.AddMinutes(-120), DistanceCm = 100, Occupied = false },
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-60), ReceivedAtUtc = now.AddMinutes(-60), DistanceCm = 80, Occupied = false },
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-40), ReceivedAtUtc = now.AddMinutes(-40), DistanceCm = 52, Occupied = true },
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-20), ReceivedAtUtc = now.AddMinutes(-20), DistanceCm = 34, Occupied = true });

        await dbContext.SaveChangesAsync();

        var service = new ParkingReadService(dbContext, TimeProvider.System);

        var history = await service.GetSpotHistoryAsync(
            spot.Id,
            now.AddMinutes(-90),
            now.AddMinutes(-10),
            maxPoints: 2,
            CancellationToken.None);

        history.ShouldNotBeNull();
        history!.Points.Count.ShouldBe(2);
        history.Points[0].MeasuredAtUtc.ShouldBe(now.AddMinutes(-40), TimeSpan.FromSeconds(1));
        history.Points[1].MeasuredAtUtc.ShouldBe(now.AddMinutes(-20), TimeSpan.FromSeconds(1));
    }

    [Test]
    public async Task ShouldReturnNullHistoryForUnknownSpot()
    {
        await using var dbContext = CreateDbContext();
        var service = new ParkingReadService(dbContext, TimeProvider.System);

        var history = await service.GetSpotHistoryAsync(404, null, null, null, CancellationToken.None);

        history.ShouldBeNull();
    }

    private static ApplicationDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApplicationDbContext(options);
    }
}
