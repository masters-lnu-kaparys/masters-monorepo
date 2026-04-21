using Masters.Api.Application.Admin.Models;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;

namespace Masters.Api.Application.Admin.Queries.GetAdminDetectedDevices;

[Authorize(Roles = Roles.Admin)]
public sealed record GetAdminDetectedDevicesQuery : IRequest<List<AdminDetectedDeviceDto>>;

public sealed class GetAdminDetectedDevicesQueryHandler : IRequestHandler<GetAdminDetectedDevicesQuery, List<AdminDetectedDeviceDto>>
{
    private readonly IApplicationDbContext _dbContext;

    public GetAdminDetectedDevicesQueryHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<List<AdminDetectedDeviceDto>> Handle(GetAdminDetectedDevicesQuery request, CancellationToken cancellationToken)
    {
        return await _dbContext.DetectedDevices
            .AsNoTracking()
            .OrderByDescending(x => x.LastSeenAtUtc)
            .Select(x => new AdminDetectedDeviceDto(
                x.DeviceId,
                x.FirstSeenAtUtc,
                x.LastSeenAtUtc,
                x.LastMeasuredAtUtc,
                x.LastDistanceCm,
                x.LastOccupied))
            .ToListAsync(cancellationToken);
    }
}
