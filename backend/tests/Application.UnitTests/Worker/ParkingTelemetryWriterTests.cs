using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Worker.Models;
using Masters.Api.Worker.Options;
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
            Options.Create(new DemoTopologyOptions()),
            Options.Create(new DeviceBindingOptions()));

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

        var writer = new ParkingTelemetryWriter(
            dbContext,
            TimeProvider.System,
            options,
            Options.Create(new DeviceBindingOptions()));

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

    [Test]
    public async Task ShouldTrackUnknownRealDeviceUntilItIsAssigned()
    {
        await using var dbContext = CreateDbContext();
        dbContext.ParkingLots.Add(new ParkingLot
        {
            Name = "Центральна парковка",
            City = "Львів",
            Address = "пл. Ринок, 1",
            Latitude = 49.8418d,
            Longitude = 24.0316d
        });
        await dbContext.SaveChangesAsync();

        var writer = new ParkingTelemetryWriter(
            dbContext,
            TimeProvider.System,
            Options.Create(new DemoTopologyOptions()),
            Options.Create(new DeviceBindingOptions()));

        var measuredAtUtc = DateTimeOffset.UtcNow;
        var result = await writer.WriteAsync(
            new DeviceTelemetryMessage("ps-lviv-001", measuredAtUtc, 31.2d, true),
            SpotSourceKind.Real,
            CancellationToken.None);

        result.Outcome.ShouldBe(TelemetryWriteOutcome.UnknownSpot);
        dbContext.ParkingSpots.Count().ShouldBe(0);

        var detectedDevice = await dbContext.DetectedDevices.SingleAsync();
        detectedDevice.DeviceId.ShouldBe("ps-lviv-001");
        detectedDevice.LastMeasuredAtUtc.ShouldBe(measuredAtUtc);
        detectedDevice.LastDistanceCm.ShouldBe(31.2d);
        detectedDevice.LastOccupied.ShouldBeTrue();
    }

    [Test]
    public async Task ShouldAssignRealDeviceToNearestLotWhenCoordinatesAreProvided()
    {
        await using var dbContext = CreateDbContext();
        dbContext.ParkingLots.AddRange(
            new ParkingLot
            {
                Name = "Вокзальна стоянка",
                City = "Львів",
                Address = "пл. Двірцева, 1",
                Latitude = 49.8387d,
                Longitude = 23.9944d
            },
            new ParkingLot
            {
                Name = "Центральна парковка",
                City = "Львів",
                Address = "пл. Ринок, 1",
                Latitude = 49.8418d,
                Longitude = 24.0316d
            });
        await dbContext.SaveChangesAsync();

        var writer = new ParkingTelemetryWriter(
            dbContext,
            TimeProvider.System,
            Options.Create(new DemoTopologyOptions()),
            Options.Create(new DeviceBindingOptions
            {
                MaxParkingLotDistanceKm = 0.4d
            }));

        var result = await writer.WriteAsync(
            new DeviceTelemetryMessage("ps-lviv-station-01", DateTimeOffset.UtcNow, 22.7d, true, 49.83872d, 23.99445d),
            SpotSourceKind.Real,
            CancellationToken.None);

        result.Outcome.ShouldBe(TelemetryWriteOutcome.Saved);

        var savedSpot = await dbContext.ParkingSpots
            .Include(x => x.ParkingLot)
            .SingleAsync();

        savedSpot.ParkingLot.Name.ShouldBe("Вокзальна стоянка");
        dbContext.DetectedDevices.Count().ShouldBe(0);
    }

    private static ApplicationDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApplicationDbContext(options);
    }
}
