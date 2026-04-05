using Masters.Api.Web.Services;

namespace Masters.Api.Web.Endpoints;

public sealed class Maps : EndpointGroupBase
{
    public override string GroupName => "map";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.MapGet(GetOverview, "overview");
    }

    private static Task<Models.MapOverviewDto> GetOverview(
        IParkingReadService parkingReadService,
        CancellationToken cancellationToken)
    {
        return parkingReadService.GetMapOverviewAsync(cancellationToken);
    }
}
