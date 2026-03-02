using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Masters.Api.Infrastructure.Data.Configurations;

public sealed class ParkingSpotConfiguration : IEntityTypeConfiguration<ParkingSpot>
{
    public void Configure(EntityTypeBuilder<ParkingSpot> builder)
    {
        builder.ToTable("ParkingSpots");

        builder.Property(x => x.DeviceId)
            .HasMaxLength(128)
            .IsRequired();

        builder.Property(x => x.DisplayName)
            .HasMaxLength(128)
            .IsRequired();

        builder.HasIndex(x => x.DeviceId)
            .IsUnique();

        builder.HasMany(x => x.TelemetryEntries)
            .WithOne(x => x.ParkingSpot)
            .HasForeignKey(x => x.ParkingSpotId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
