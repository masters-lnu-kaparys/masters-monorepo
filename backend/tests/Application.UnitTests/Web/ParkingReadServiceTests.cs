using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Web.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Application.UnitTests.Web;

public class ParkingReadServiceTests
{
    [Test]
    public async Task ShouldCalculateDashboardSummary()
    {
        await using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext, "Центральна парковка", "Ужгород");

        var spotA = CreateSpot(lot, "spot-a", "Місце 01", true, 22.1d, DateTimeOffset.UtcNow.AddMinutes(-1), SpotSourceKind.Real);
        var spotB = CreateSpot(lot, "spot-b", "Місце 02", false, 75.4d, DateTimeOffset.UtcNow.AddMinutes(-2), SpotSourceKind.Simulated);
        var spotC = CreateSpot(lot, "spot-c", "Місце 03", true, 30.0d, DateTimeOffset.UtcNow.AddMinutes(-3), SpotSourceKind.Simulated);

        dbContext.ParkingSpots.AddRange(spotA, spotB, spotC);
        await dbContext.SaveChangesAsync();

        var telemetryA = new ParkingTelemetry { ParkingSpotId = spotA.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-3), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-3), DistanceCm = 22.1d, Occupied = true };
        var telemetryB = new ParkingTelemetry { ParkingSpotId = spotB.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-2), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-2), DistanceCm = 75.4d, Occupied = false };
        var telemetryC = new ParkingTelemetry { ParkingSpotId = spotC.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-1), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-1), DistanceCm = 30.0d, Occupied = true };

        dbContext.ParkingTelemetries.AddRange(telemetryA, telemetryB, telemetryC);
        await dbContext.SaveChangesAsync();

        var service = CreateService(dbContext);

        var summary = await service.GetSummaryAsync(CancellationToken.None);

        summary.TotalSpots.ShouldBe(3);
        summary.OccupiedSpots.ShouldBe(2);
        summary.FreeSpots.ShouldBe(1);
        summary.OccupancyRate.ShouldBe(2d / 3d, 0.0001);
        summary.LastTelemetryAtUtc.ShouldNotBeNull();
        summary.LastTelemetryAtUtc!.Value.ShouldBe(telemetryC.MeasuredAtUtc, TimeSpan.FromSeconds(1));
    }

    [Test]
    public async Task ShouldBuildMapOverviewGroupedByParkingLots()
    {
        await using var dbContext = CreateDbContext();
        var lotA = await SeedLotAsync(dbContext, "Центральна парковка", "Ужгород");
        var lotB = await SeedLotAsync(dbContext, "Вокзальна стоянка", "Ужгород");

        dbContext.ParkingSpots.AddRange(
            CreateSpot(lotA, "spot-a", "Місце 01", true, 24d, DateTimeOffset.UtcNow.AddMinutes(-5), SpotSourceKind.Real),
            CreateSpot(lotA, "spot-b", "Місце 02", false, 108d, DateTimeOffset.UtcNow.AddMinutes(-3), SpotSourceKind.Simulated),
            CreateSpot(lotB, "spot-c", "Місце 01", true, 28d, DateTimeOffset.UtcNow.AddMinutes(-1), SpotSourceKind.Simulated));

        await dbContext.SaveChangesAsync();

        var service = CreateService(dbContext);

        var overview = await service.GetMapOverviewAsync(CancellationToken.None);

        overview.City.ShouldBe("Львів");
        overview.Lots.Count.ShouldBe(2);
        overview.Summary.TotalLots.ShouldBe(2);
        overview.Summary.TotalSpots.ShouldBe(3);
        overview.Summary.OccupiedSpots.ShouldBe(2);
        overview.Summary.FreeSpots.ShouldBe(1);
    }

    [Test]
    public async Task ShouldReturnLotDetailsWithRecentActivity()
    {
        await using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext, "Паркінг біля набережної", "Ужгород");

        var spotA = CreateSpot(lot, "spot-a", "Місце 01", false, 105d, DateTimeOffset.UtcNow.AddMinutes(-10), SpotSourceKind.Real);
        var spotB = CreateSpot(lot, "spot-b", "Місце 02", true, 26d, DateTimeOffset.UtcNow.AddMinutes(-4), SpotSourceKind.Simulated);

        dbContext.ParkingSpots.AddRange(spotA, spotB);
        await dbContext.SaveChangesAsync();

        dbContext.ParkingTelemetries.AddRange(
            new ParkingTelemetry { ParkingSpotId = spotA.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10), DistanceCm = 105d, Occupied = false },
            new ParkingTelemetry { ParkingSpotId = spotB.Id, MeasuredAtUtc = DateTimeOffset.UtcNow.AddMinutes(-4), ReceivedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-4), DistanceCm = 26d, Occupied = true });

        await dbContext.SaveChangesAsync();

        var service = CreateService(dbContext);

        var details = await service.GetLotDetailsAsync(lot.Id, CancellationToken.None);

        details.ShouldNotBeNull();
        details!.Spots.Count.ShouldBe(2);
        details.RecentActivity.Count.ShouldBe(2);
        details.FreeSpots.ShouldBe(1);
        details.OccupiedSpots.ShouldBe(1);
    }

    [Test]
    public async Task ShouldFilterHistoryByRangeAndLimit()
    {
        await using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext, "Центральна парковка", "Ужгород");

        var now = DateTimeOffset.UtcNow;
        var spot = CreateSpot(lot, "spot-history", "Місце 01", false, null, null, SpotSourceKind.Real);

        dbContext.ParkingSpots.Add(spot);
        await dbContext.SaveChangesAsync();

        dbContext.ParkingTelemetries.AddRange(
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-120), ReceivedAtUtc = now.AddMinutes(-120), DistanceCm = 100, Occupied = false },
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-60), ReceivedAtUtc = now.AddMinutes(-60), DistanceCm = 80, Occupied = false },
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-40), ReceivedAtUtc = now.AddMinutes(-40), DistanceCm = 52, Occupied = true },
            new ParkingTelemetry { ParkingSpotId = spot.Id, MeasuredAtUtc = now.AddMinutes(-20), ReceivedAtUtc = now.AddMinutes(-20), DistanceCm = 34, Occupied = true });

        await dbContext.SaveChangesAsync();

        var service = CreateService(dbContext);

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
        var service = CreateService(dbContext);

        var history = await service.GetSpotHistoryAsync(404, null, null, null, CancellationToken.None);

        history.ShouldBeNull();
    }

    private static ParkingReadService CreateService(ApplicationDbContext dbContext)
    {
        return new ParkingReadService(
            dbContext,
            TimeProvider.System,
            Options.Create(new DemoMapOptions()));
    }

    private static async Task<ParkingLot> SeedLotAsync(ApplicationDbContext dbContext, string name, string city)
    {
        var lot = new ParkingLot
        {
            Name = name,
            City = city,
            Address = $"{name}, {city}",
            Latitude = 48.6208d,
            Longitude = 22.2879d
        };

        dbContext.ParkingLots.Add(lot);
        await dbContext.SaveChangesAsync();

        return lot;
    }

    private static ParkingSpot CreateSpot(
        ParkingLot lot,
        string deviceId,
        string displayName,
        bool occupied,
        double? distanceCm,
        DateTimeOffset? lastTelemetryAtUtc,
        SpotSourceKind sourceKind)
    {
        return new ParkingSpot
        {
            ParkingLotId = lot.Id,
            DeviceId = deviceId,
            DisplayName = displayName,
            SourceKind = sourceKind,
            IsOccupied = occupied,
            LastDistanceCm = distanceCm,
            LastTelemetryAtUtc = lastTelemetryAtUtc
        };
    }

    private static ApplicationDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApplicationDbContext(options);
    }
}
