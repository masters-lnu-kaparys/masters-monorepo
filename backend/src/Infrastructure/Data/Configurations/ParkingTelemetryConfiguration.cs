using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Masters.Api.Infrastructure.Data.Configurations;

public sealed class ParkingTelemetryConfiguration : IEntityTypeConfiguration<ParkingTelemetry>
{
    public void Configure(EntityTypeBuilder<ParkingTelemetry> builder)
    {
        builder.ToTable("ParkingTelemetry");

        builder.HasIndex(x => x.MeasuredAtUtc);

        builder.HasIndex(x => new { x.ParkingSpotId, x.MeasuredAtUtc })
            .IsUnique();
    }
}
