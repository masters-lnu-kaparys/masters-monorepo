using Masters.Api.Application.Admin.Commands.CreateParkingSpot;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Application.UnitTests.Admin;

public class CreateParkingSpotCommandTests
{
    [Test]
    public async Task ShouldGenerateDeviceIdForSimulatedSpotWhenMissing()
    {
        await using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext);
        var handler = new CreateParkingSpotCommandHandler(dbContext);

        var spotId = await handler.Handle(
            new CreateParkingSpotCommand(lot.Id, "Місце 01", SpotSourceKind.Simulated, null),
            CancellationToken.None);

        var createdSpot = await dbContext.ParkingSpots.SingleAsync(x => x.Id == spotId);

        createdSpot.DeviceId.ShouldBe($"sim-{lot.Id}-001");
        createdSpot.SourceKind.ShouldBe(SpotSourceKind.Simulated);
    }

    [Test]
    public async Task ShouldRejectDuplicateDeviceId()
    {
        await using var dbContext = CreateDbContext();
        var lot = await SeedLotAsync(dbContext);

        dbContext.ParkingSpots.Add(new ParkingSpot
        {
            ParkingLotId = lot.Id,
            DisplayName = "Місце 01",
            DeviceId = "ps-lviv-001",
            SourceKind = SpotSourceKind.Real,
        });

        await dbContext.SaveChangesAsync();

        var handler = new CreateParkingSpotCommandHandler(dbContext);

        var exception = await Should.ThrowAsync<ValidationException>(async () =>
            await handler.Handle(
                new CreateParkingSpotCommand(lot.Id, "Місце 02", SpotSourceKind.Real, "ps-lviv-001"),
                CancellationToken.None));

        exception.Errors.ShouldContainKey("DeviceId");
    }

    private static async Task<ParkingLot> SeedLotAsync(ApplicationDbContext dbContext)
    {
        var lot = new ParkingLot
        {
            Name = "Центральна парковка",
            City = "Львів",
            Address = "пл. Ринок, 1",
            Latitude = 49.8419d,
            Longitude = 24.0315d,
        };

        dbContext.ParkingLots.Add(lot);
        await dbContext.SaveChangesAsync();
        return lot;
    }

    private static ApplicationDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApplicationDbContext(options);
    }
}
