using Masters.Api.Application.Common.Security;
using Masters.Api.Web.Services;

namespace Masters.Api.Web.Endpoints;

public sealed class Dashboard : EndpointGroupBase
{
    public override string GroupName => "dashboard";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.RequireAuthorization(Policies.UserAccess);
        groupBuilder.MapGet(GetSummary, "summary");
    }

    private static Task<Models.DashboardSummaryDto> GetSummary(
        IParkingReadService parkingReadService,
        CancellationToken cancellationToken)
    {
        return parkingReadService.GetSummaryAsync(cancellationToken);
    }
}
