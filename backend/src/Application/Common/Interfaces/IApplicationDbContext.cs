using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Application.Common.Interfaces;

public interface IApplicationDbContext
{
    DbSet<ParkingSpot> ParkingSpots { get; }

    DbSet<ParkingTelemetry> ParkingTelemetries { get; }

    Task<int> SaveChangesAsync(CancellationToken cancellationToken);
}
