using System.Reflection;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;

namespace Masters.Api.Application.Common.Behaviours;

public class AuthorizationBehaviour<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse> 
    where TRequest : notnull
{
    private readonly IUser _user;
    private readonly IUserAuthorizationService _authorizationService;

    public AuthorizationBehaviour(IUser user, IUserAuthorizationService authorizationService)
    {
        _user = user;
        _authorizationService = authorizationService;
    }

    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken cancellationToken)
    {
        var authorizeAttributes = request.GetType().GetCustomAttributes<AuthorizeAttribute>();

        if (authorizeAttributes.Any())
        {
            // Must be authenticated user
            if (_user.Id == null)
            {
                throw new UnauthorizedAccessException();
            }

            foreach (var authorizeAttribute in authorizeAttributes)
            {
                if (!string.IsNullOrWhiteSpace(authorizeAttribute.Roles))
                {
                    var authorizedRoles = authorizeAttribute.Roles
                        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

                    if (!authorizedRoles.Any(_authorizationService.IsInRole))
                    {
                        throw new ForbiddenAccessException();
                    }
                }

                if (!string.IsNullOrWhiteSpace(authorizeAttribute.Policy))
                {
                    var authorized = await _authorizationService.AuthorizeAsync(authorizeAttribute.Policy);

                    if (!authorized)
                    {
                        throw new ForbiddenAccessException();
                    }
                }
            }
        }

        // User is authorized / authorization not required
        return await next();
    }
}
