using Masters.Api.Web.Services;

namespace Masters.Api.Web.Endpoints;

public sealed class Spots : EndpointGroupBase
{
    public override string GroupName => "spots";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.MapGet(GetSpots);
        groupBuilder.MapGet(GetSpotHistory, "{spotId:long}/history");
    }

    private static Task<List<Models.SpotStateDto>> GetSpots(
        IParkingReadService parkingReadService,
        CancellationToken cancellationToken)
    {
        return parkingReadService.GetSpotsAsync(cancellationToken);
    }

    private static async Task<IResult> GetSpotHistory(
        long spotId,
        DateTimeOffset? fromUtc,
        DateTimeOffset? toUtc,
        int? maxPoints,
        IParkingReadService parkingReadService,
        CancellationToken cancellationToken)
    {
        var history = await parkingReadService.GetSpotHistoryAsync(
            spotId,
            fromUtc,
            toUtc,
            maxPoints,
            cancellationToken);

        return history is null
            ? TypedResults.NotFound()
            : TypedResults.Ok(history);
    }
}
