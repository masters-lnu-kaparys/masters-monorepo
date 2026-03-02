using Masters.Api.Domain.Entities;
using Masters.Api.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Application.UnitTests.Infrastructure;

public class ParkingModelConfigurationTests
{
    [Test]
    public void ShouldConfigureUniqueIndexForSpotAndMeasuredTimestamp()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        using var dbContext = new ApplicationDbContext(options);

        var telemetryEntity = dbContext.Model.FindEntityType(typeof(ParkingTelemetry));

        telemetryEntity.ShouldNotBeNull();

        var uniqueIndex = telemetryEntity!
            .GetIndexes()
            .SingleOrDefault(index =>
                index.IsUnique &&
                index.Properties.Select(property => property.Name)
                    .SequenceEqual([nameof(ParkingTelemetry.ParkingSpotId), nameof(ParkingTelemetry.MeasuredAtUtc)]));

        uniqueIndex.ShouldNotBeNull();
    }
}
