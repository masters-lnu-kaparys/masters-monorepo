using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Web.Options;
using Microsoft.Extensions.Options;

namespace Masters.Api.Web.Services;

public class CurrentUser : IUser
{
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly Auth0Options _auth0Options;

    public CurrentUser(
        IHttpContextAccessor httpContextAccessor,
        IOptions<Auth0Options> auth0Options)
    {
        _httpContextAccessor = httpContextAccessor;
        _auth0Options = auth0Options.Value;
    }

    public string? Id => _httpContextAccessor.HttpContext?.User?.FindFirst("sub")?.Value
        ?? _httpContextAccessor.HttpContext?.User?.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;

    public List<string>? Roles => _httpContextAccessor.HttpContext?.User?
        .FindAll(_auth0Options.RolesClaimType)
        .Select(x => x.Value)
        .ToList();
}
