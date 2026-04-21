using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Application.Common.Interfaces;

public interface IApplicationDbContext
{
    DbSet<DetectedDevice> DetectedDevices { get; }

    DbSet<ParkingLot> ParkingLots { get; }

    DbSet<ParkingSpot> ParkingSpots { get; }

    DbSet<ParkingTelemetry> ParkingTelemetries { get; }

    Task<int> SaveChangesAsync(CancellationToken cancellationToken);
}
