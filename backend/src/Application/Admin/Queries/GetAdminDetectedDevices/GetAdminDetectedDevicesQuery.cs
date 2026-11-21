using Masters.Api.Application.Admin.Models;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Application.Common.Models;
using Microsoft.Extensions.Options;

namespace Masters.Api.Application.Admin.Queries.GetAdminDetectedDevices;

[Authorize(Roles = Roles.Admin)]
public sealed record GetAdminDetectedDevicesQuery : IRequest<List<AdminDetectedDeviceDto>>;

public sealed class GetAdminDetectedDevicesQueryHandler : IRequestHandler<GetAdminDetectedDevicesQuery, List<AdminDetectedDeviceDto>>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly TimeProvider _clock;
    private readonly int _maxAgeSeconds;

    public GetAdminDetectedDevicesQueryHandler(IApplicationDbContext dbContext, TimeProvider clock, IOptions<TelemetryFreshnessOptions> freshness)
    {
        _dbContext = dbContext;
        _clock = clock;
        _maxAgeSeconds = freshness.Value.MaxAgeSeconds;
    }

    public async Task<List<AdminDetectedDeviceDto>> Handle(GetAdminDetectedDevicesQuery request, CancellationToken cancellationToken)
    {
        var now = _clock.GetUtcNow();
        return await _dbContext.DetectedDevices
            .AsNoTracking()
            .OrderByDescending(x => x.LastSeenAtUtc)
            .Select(x => new AdminDetectedDeviceDto(
                x.DeviceId,
                x.FirstSeenAtUtc,
                x.LastSeenAtUtc,
                x.LastMeasuredAtUtc,
                x.LastDistanceCm,
                x.LastOccupied,
                x.LastLatitude,
                x.LastLongitude,
                TelemetryFreshnessOptions.Status(x.LastMeasuredAtUtc, now, _maxAgeSeconds)))
            .ToListAsync(cancellationToken);
    }
}
