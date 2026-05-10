using Masters.Api.Application.Admin.Commands.SendDeviceCommand;
using Masters.Api.Application.Admin.Models;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;
using Moq;

namespace Masters.Api.Application.UnitTests.Admin;

public class SendDeviceCommandTests
{
    [Test]
    public async Task ShouldDispatchMeasureNowCommandForRealSpot()
    {
        using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext);
        dbContext.ParkingSpots.Add(new ParkingSpot
        {
            ParkingLotId = lot.Id,
            DeviceId = "ps-lviv-001",
            DisplayName = "Lviv-R01",
            SourceKind = SpotSourceKind.Real
        });
        await dbContext.SaveChangesAsync(CancellationToken.None);
        var spotId = await dbContext.ParkingSpots.Select(x => x.Id).SingleAsync();

        var dispatcher = new Mock<IDeviceCommandDispatcher>();
        dispatcher
            .Setup(x => x.SendAsync(
                "ps-lviv-001",
                It.Is<DeviceCommandDispatchRequest>(r => r.MethodName == "measureNow"),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new DeviceCommandDispatchResult(200, "{\"ok\":true}"));

        var handler = new SendDeviceCommandCommandHandler(dbContext, dispatcher.Object, Text, TimeProvider.System);

        var result = await handler.Handle(
            new SendDeviceCommandCommand(spotId, DeviceCommandType.MeasureNow, null, null),
            CancellationToken.None);

        result.StatusCode.ShouldBe(200);
        result.DeviceId.ShouldBe("ps-lviv-001");
        result.ResponsePayload.ShouldBe("{\"ok\":true}");
    }

    [Test]
    public async Task ShouldRejectCommandsForSimulatedSpot()
    {
        using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext);
        dbContext.ParkingSpots.Add(new ParkingSpot
        {
            ParkingLotId = lot.Id,
            DeviceId = "sim-lviv-001",
            DisplayName = "Lviv-S01",
            SourceKind = SpotSourceKind.Simulated
        });
        await dbContext.SaveChangesAsync(CancellationToken.None);
        var spotId = await dbContext.ParkingSpots.Select(x => x.Id).SingleAsync();

        var dispatcher = new Mock<IDeviceCommandDispatcher>();
        var handler = new SendDeviceCommandCommandHandler(dbContext, dispatcher.Object, Text, TimeProvider.System);

        var exception = await Should.ThrowAsync<ValidationException>(() => handler.Handle(
            new SendDeviceCommandCommand(spotId, DeviceCommandType.Ping, null, null),
            CancellationToken.None));

        exception.Errors.ShouldContainKey(nameof(SendDeviceCommandCommand.SpotId));
    }

    private static async Task<ParkingLot> SeedLotAsync(ApplicationDbContext dbContext)
    {
        var lot = new ParkingLot
        {
            Name = "Центральна парковка",
            City = "Львів",
            Address = "пл. Ринок, 1",
            Latitude = 49.8419d,
            Longitude = 24.0315d
        };

        dbContext.ParkingLots.Add(lot);
        await dbContext.SaveChangesAsync(CancellationToken.None);

        return lot;
    }

    private static ApplicationDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApplicationDbContext(options);
    }

    private static IApplicationText Text => new Masters.Api.Infrastructure.Localization.ApplicationText();
}
