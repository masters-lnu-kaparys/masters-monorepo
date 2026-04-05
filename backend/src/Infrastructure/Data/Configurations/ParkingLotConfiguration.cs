using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Masters.Api.Infrastructure.Data.Configurations;

public sealed class ParkingLotConfiguration : IEntityTypeConfiguration<ParkingLot>
{
    public void Configure(EntityTypeBuilder<ParkingLot> builder)
    {
        builder.ToTable("ParkingLots");

        builder.Property(x => x.Name)
            .HasMaxLength(128)
            .IsRequired();

        builder.Property(x => x.City)
            .HasMaxLength(128)
            .IsRequired();

        builder.Property(x => x.Address)
            .HasMaxLength(256)
            .IsRequired();

        builder.HasIndex(x => new { x.City, x.Name })
            .IsUnique();

        builder.HasMany(x => x.Spots)
            .WithOne(x => x.ParkingLot)
            .HasForeignKey(x => x.ParkingLotId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
