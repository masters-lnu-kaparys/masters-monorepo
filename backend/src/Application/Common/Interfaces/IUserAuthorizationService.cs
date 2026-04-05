namespace Masters.Api.Application.Common.Interfaces;

public interface IUserAuthorizationService
{
    bool IsInRole(string role);

    Task<bool> AuthorizeAsync(string policyName);
}
