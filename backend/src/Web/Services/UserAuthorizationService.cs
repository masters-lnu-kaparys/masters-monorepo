using Masters.Api.Application.Common.Interfaces;
using Microsoft.AspNetCore.Authorization;

namespace Masters.Api.Web.Services;

public sealed class UserAuthorizationService : IUserAuthorizationService
{
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly IAuthorizationService _authorizationService;

    public UserAuthorizationService(
        IHttpContextAccessor httpContextAccessor,
        IAuthorizationService authorizationService)
    {
        _httpContextAccessor = httpContextAccessor;
        _authorizationService = authorizationService;
    }

    public bool IsInRole(string role)
    {
        return _httpContextAccessor.HttpContext?.User?.IsInRole(role) ?? false;
    }

    public async Task<bool> AuthorizeAsync(string policyName)
    {
        var user = _httpContextAccessor.HttpContext?.User;

        if (user is null)
        {
            return false;
        }

        var result = await _authorizationService.AuthorizeAsync(user, policyName);
        return result.Succeeded;
    }
}
