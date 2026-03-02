using System.Reflection;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace Masters.Api.Infrastructure.Data;

public class ApplicationDbContext : DbContext, IApplicationDbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options) { }

    public DbSet<ParkingSpot> ParkingSpots => Set<ParkingSpot>();

    public DbSet<ParkingTelemetry> ParkingTelemetries => Set<ParkingTelemetry>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);
        builder.ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly());
    }
}
