using Masters.Api.Application.Admin.Models;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Application.Common.Models;
using Microsoft.Extensions.Options;

namespace Masters.Api.Application.Admin.Queries.GetAdminParkingLots;

[Authorize(Roles = Roles.Admin)]
public sealed record GetAdminParkingLotsQuery : IRequest<List<AdminParkingLotListItemDto>>;

public sealed class GetAdminParkingLotsQueryHandler : IRequestHandler<GetAdminParkingLotsQuery, List<AdminParkingLotListItemDto>>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly TimeProvider _clock;
    private readonly int _maxAgeSeconds;

    public GetAdminParkingLotsQueryHandler(IApplicationDbContext dbContext, TimeProvider clock, IOptions<TelemetryFreshnessOptions> freshness)
    {
        _dbContext = dbContext;
        _clock = clock;
        _maxAgeSeconds = freshness.Value.MaxAgeSeconds;
    }

    public async Task<List<AdminParkingLotListItemDto>> Handle(GetAdminParkingLotsQuery request, CancellationToken cancellationToken)
    {
        var now = _clock.GetUtcNow();
        var lots = await _dbContext.ParkingLots
            .AsNoTracking()
            .OrderBy(x => x.City)
            .ThenBy(x => x.Name)
            .Select(x => new
            {
                x.Id,
                x.Name,
                x.City,
                x.Address,
                x.Latitude,
                x.Longitude,
                Spots = x.Spots
                    .OrderBy(spot => spot.DisplayName)
                    .Select(spot => new AdminParkingSpotDto(
                        spot.Id,
                        spot.DisplayName,
                        spot.DeviceId,
                        spot.SourceKind,
                        spot.IsOccupied,
                        spot.LastDistanceCm,
                        spot.LastLatitude,
                        spot.LastLongitude,
                        spot.LastTelemetryAtUtc,
                        TelemetryFreshnessOptions.Status(spot.LastTelemetryAtUtc, now, _maxAgeSeconds)))
                    .ToList()
            })
            .ToListAsync(cancellationToken);

        return lots
            .Select(x =>
            {
                var totalSpots = x.Spots.Count;
                var occupiedSpots = x.Spots.Count(spot => spot.DataStatus == "current" && spot.Occupied);
                var freeSpots = x.Spots.Count(spot => spot.DataStatus == "current" && !spot.Occupied);

                return new AdminParkingLotListItemDto(
                    x.Id,
                    x.Name,
                    x.City,
                    x.Address,
                    x.Latitude,
                    x.Longitude,
                    totalSpots,
                    occupiedSpots,
                    freeSpots,
                    x.Spots,
                    totalSpots - occupiedSpots - freeSpots);
            })
            .ToList();
    }
}
