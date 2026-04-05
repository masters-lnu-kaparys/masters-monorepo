using Microsoft.AspNetCore.SignalR;

namespace Masters.Api.Web.Hubs;

[Microsoft.AspNetCore.Authorization.Authorize(Policy = Masters.Api.Application.Common.Security.Policies.UserAccess)]
public sealed class ParkingHub : Hub
{
}
