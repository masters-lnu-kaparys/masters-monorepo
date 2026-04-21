using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Masters.Api.Infrastructure.Data.Configurations;

public sealed class DetectedDeviceConfiguration : IEntityTypeConfiguration<DetectedDevice>
{
    public void Configure(EntityTypeBuilder<DetectedDevice> builder)
    {
        builder.ToTable("DetectedDevices");

        builder.Property(x => x.DeviceId)
            .HasMaxLength(128)
            .IsRequired();

        builder.HasIndex(x => x.DeviceId)
            .IsUnique();

        builder.HasIndex(x => x.LastSeenAtUtc);
    }
}
