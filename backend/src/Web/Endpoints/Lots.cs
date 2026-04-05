using Masters.Api.Application.Common.Security;
using Masters.Api.Web.Services;
using Microsoft.AspNetCore.Http.HttpResults;

namespace Masters.Api.Web.Endpoints;

public sealed class Lots : EndpointGroupBase
{
    public override string GroupName => "lots";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.RequireAuthorization(Policies.UserAccess);
        groupBuilder.MapGet(GetLotById, "{lotId:long}");
    }

    private static async Task<Results<Ok<Models.LotDetailsDto>, NotFound>> GetLotById(
        long lotId,
        IParkingReadService parkingReadService,
        CancellationToken cancellationToken)
    {
        var lot = await parkingReadService.GetLotDetailsAsync(lotId, cancellationToken);

        return lot is null
            ? TypedResults.NotFound()
            : TypedResults.Ok(lot);
    }
}
