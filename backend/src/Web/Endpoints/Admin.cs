using Masters.Api.Application.Admin.Commands.CreateParkingLot;
using Masters.Api.Application.Admin.Commands.CreateParkingSpot;
using Masters.Api.Application.Admin.Commands.DeleteParkingLot;
using Masters.Api.Application.Admin.Commands.DeleteParkingSpot;
using Masters.Api.Application.Admin.Queries.GetAdminDetectedDevices;
using Masters.Api.Application.Admin.Queries.GetAdminParkingLots;
using Masters.Api.Application.Admin.Commands.UpdateParkingLot;
using Masters.Api.Application.Admin.Commands.UpdateParkingSpot;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Enums;
using Microsoft.AspNetCore.Http.HttpResults;

namespace Masters.Api.Web.Endpoints;

public sealed class Admin : EndpointGroupBase
{
    public override string GroupName => "admin";

    public override void Map(RouteGroupBuilder groupBuilder)
    {
        groupBuilder.RequireAuthorization(Policies.AdminAccess);
        groupBuilder.MapGet(GetLots, "lots");
        groupBuilder.MapGet(GetDetectedDevices, "devices/unassigned");
        groupBuilder.MapPost(CreateLot, "lots");
        groupBuilder.MapPut(UpdateLot, "lots/{lotId:long}");
        groupBuilder.MapDelete(DeleteLot, "lots/{lotId:long}");
        groupBuilder.MapPost(CreateSpot, "lots/{lotId:long}/spots");
        groupBuilder.MapPut(UpdateSpot, "spots/{spotId:long}");
        groupBuilder.MapDelete(DeleteSpot, "spots/{spotId:long}");
    }

    private static Task<List<Application.Admin.Models.AdminParkingLotListItemDto>> GetLots(
        ISender sender,
        CancellationToken cancellationToken)
    {
        return sender.Send(new GetAdminParkingLotsQuery(), cancellationToken);
    }

    private static Task<List<Application.Admin.Models.AdminDetectedDeviceDto>> GetDetectedDevices(
        ISender sender,
        CancellationToken cancellationToken)
    {
        return sender.Send(new GetAdminDetectedDevicesQuery(), cancellationToken);
    }

    private static async Task<Created<long>> CreateLot(
        CreateParkingLotRequest request,
        ISender sender,
        CancellationToken cancellationToken)
    {
        var lotId = await sender.Send(
            new CreateParkingLotCommand(
                request.Name,
                request.City,
                request.Address,
                request.Latitude,
                request.Longitude),
            cancellationToken);

        return TypedResults.Created($"/api/admin/lots/{lotId}", lotId);
    }

    private static async Task<NoContent> UpdateLot(
        long lotId,
        UpdateParkingLotRequest request,
        ISender sender,
        CancellationToken cancellationToken)
    {
        await sender.Send(
            new UpdateParkingLotCommand(
                lotId,
                request.Name,
                request.City,
                request.Address,
                request.Latitude,
                request.Longitude),
            cancellationToken);

        return TypedResults.NoContent();
    }

    private static async Task<NoContent> DeleteLot(
        long lotId,
        ISender sender,
        CancellationToken cancellationToken)
    {
        await sender.Send(new DeleteParkingLotCommand(lotId), cancellationToken);
        return TypedResults.NoContent();
    }

    private static async Task<Created<long>> CreateSpot(
        long lotId,
        UpsertParkingSpotRequest request,
        ISender sender,
        CancellationToken cancellationToken)
    {
        var spotId = await sender.Send(
            new CreateParkingSpotCommand(
                lotId,
                request.DisplayName,
                request.SourceKind,
                request.DeviceId),
            cancellationToken);

        return TypedResults.Created($"/api/admin/spots/{spotId}", spotId);
    }

    private static async Task<NoContent> UpdateSpot(
        long spotId,
        UpsertParkingSpotRequest request,
        ISender sender,
        CancellationToken cancellationToken)
    {
        await sender.Send(
            new UpdateParkingSpotCommand(
                spotId,
                request.DisplayName,
                request.SourceKind,
                request.DeviceId),
            cancellationToken);

        return TypedResults.NoContent();
    }

    private static async Task<NoContent> DeleteSpot(
        long spotId,
        ISender sender,
        CancellationToken cancellationToken)
    {
        await sender.Send(new DeleteParkingSpotCommand(spotId), cancellationToken);
        return TypedResults.NoContent();
    }

    private sealed record CreateParkingLotRequest(
        string Name,
        string City,
        string Address,
        double Latitude,
        double Longitude);

    private sealed record UpdateParkingLotRequest(
        string Name,
        string City,
        string Address,
        double Latitude,
        double Longitude);

    private sealed record UpsertParkingSpotRequest(
        string DisplayName,
        SpotSourceKind SourceKind,
        string? DeviceId);
}
