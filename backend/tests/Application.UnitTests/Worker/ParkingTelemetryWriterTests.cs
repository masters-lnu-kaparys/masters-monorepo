using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Worker.Models;
using Masters.Api.Worker.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Application.UnitTests.Worker;

public class ParkingTelemetryWriterTests
{
    [Test]
    public async Task ShouldRejectSimulatedWriteForRealSpot()
    {
        await using var dbContext = CreateDbContext();
        var lot = new ParkingLot
        {
            Name = "Центральна парковка",
            City = "Ужгород",
            Address = "пл. Поштова, 1",
            Latitude = 48.6208d,
            Longitude = 22.2879d
        };

        dbContext.ParkingLots.Add(lot);
        await dbContext.SaveChangesAsync();

        dbContext.ParkingSpots.Add(new ParkingSpot
        {
            ParkingLotId = lot.Id,
            DeviceId = "ps-real-001",
            DisplayName = "Місце 01",
            SourceKind = SpotSourceKind.Real,
            IsOccupied = false
        });

        await dbContext.SaveChangesAsync();

        var writer = new ParkingTelemetryWriter(
            dbContext,
            TimeProvider.System,
            Options.Create(new DemoTopologyOptions()));

        var result = await writer.WriteAsync(
            new DeviceTelemetryMessage("ps-real-001", DateTimeOffset.UtcNow, 21.5d, true),
            SpotSourceKind.Simulated,
            CancellationToken.None);

        result.Outcome.ShouldBe(TelemetryWriteOutcome.SourceMismatch);
        dbContext.ParkingTelemetries.Count().ShouldBe(0);
    }

    [Test]
    public async Task ShouldCreateKnownRealSpotInConfiguredLot()
    {
        await using var dbContext = CreateDbContext();
        var options = Options.Create(new DemoTopologyOptions
        {
            Lots =
            [
                new DemoLotOptions
                {
                    Key = "central",
                    Name = "Центральна парковка",
                    City = "Ужгород",
                    Address = "пл. Поштова, 1",
                    Latitude = 48.6208d,
                    Longitude = 22.2879d,
                    RealSpotDeviceIds = ["ps-real-001"]
                }
            ]
        });

        var writer = new ParkingTelemetryWriter(dbContext, TimeProvider.System, options);

        var result = await writer.WriteAsync(
            new DeviceTelemetryMessage("ps-real-001", DateTimeOffset.UtcNow, 24.3d, true),
            SpotSourceKind.Real,
            CancellationToken.None);

        var savedSpot = await dbContext.ParkingSpots
            .Include(x => x.ParkingLot)
            .SingleAsync();

        result.Outcome.ShouldBe(TelemetryWriteOutcome.Saved);
        savedSpot.SourceKind.ShouldBe(SpotSourceKind.Real);
        savedSpot.ParkingLot.Name.ShouldBe("Центральна парковка");
        dbContext.ParkingTelemetries.Count().ShouldBe(1);
    }

    private static ApplicationDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApplicationDbContext(options);
    }
}
