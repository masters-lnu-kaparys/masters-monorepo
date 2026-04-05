using System.Security.Claims;
using Masters.Api.Web.Options;
using Masters.Api.Web.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace Masters.Api.Application.UnitTests.Web;

public class CurrentUserTests
{
    [Test]
    public void ShouldReadSubAndRolesFromAuth0Claims()
    {
        var httpContext = new DefaultHttpContext();
        httpContext.User = new ClaimsPrincipal(
            new ClaimsIdentity(
            [
                new Claim("sub", "auth0|abc123"),
                new Claim("https://masters.api/roles", "Admin"),
                new Claim("https://masters.api/roles", "User"),
            ],
            authenticationType: "Test"));

        var currentUser = new CurrentUser(
            new HttpContextAccessor { HttpContext = httpContext },
            Options.Create(new Auth0Options()));

        currentUser.Id.ShouldBe("auth0|abc123");
        currentUser.Roles.ShouldBe(["Admin", "User"]);
    }
}
