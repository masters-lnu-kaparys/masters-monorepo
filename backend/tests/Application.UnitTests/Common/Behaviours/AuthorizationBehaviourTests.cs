using Masters.Api.Application.Common.Behaviours;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using MediatR;
using Moq;

namespace Masters.Api.Application.UnitTests.Common.Behaviours;

public class AuthorizationBehaviourTests
{
    [Test]
    public async Task ShouldThrowUnauthorizedWhenRequestRequiresAuthentication()
    {
        var user = new Mock<IUser>();
        user.SetupGet(x => x.Id).Returns((string?)null);

        var authorizationService = new Mock<IUserAuthorizationService>();
        var behaviour = new AuthorizationBehaviour<AdminOnlyRequest, Unit>(user.Object, authorizationService.Object);

        await Should.ThrowAsync<UnauthorizedAccessException>(() =>
            behaviour.Handle(new AdminOnlyRequest(), () => Task.FromResult(Unit.Value), CancellationToken.None));
    }

    [Test]
    public async Task ShouldThrowForbiddenWhenRoleIsMissing()
    {
        var user = new Mock<IUser>();
        user.SetupGet(x => x.Id).Returns("auth0|user-1");

        var authorizationService = new Mock<IUserAuthorizationService>();
        authorizationService.Setup(x => x.IsInRole(Roles.Admin)).Returns(false);

        var behaviour = new AuthorizationBehaviour<AdminOnlyRequest, Unit>(user.Object, authorizationService.Object);

        await Should.ThrowAsync<ForbiddenAccessException>(() =>
            behaviour.Handle(new AdminOnlyRequest(), () => Task.FromResult(Unit.Value), CancellationToken.None));
    }

    [Test]
    public async Task ShouldAllowRequestWhenPolicySucceeds()
    {
        var user = new Mock<IUser>();
        user.SetupGet(x => x.Id).Returns("auth0|user-1");

        var authorizationService = new Mock<IUserAuthorizationService>();
        authorizationService.Setup(x => x.AuthorizeAsync(Policies.UserAccess)).ReturnsAsync(true);

        var behaviour = new AuthorizationBehaviour<UserPolicyRequest, string>(user.Object, authorizationService.Object);

        var result = await behaviour.Handle(
            new UserPolicyRequest(),
            () => Task.FromResult("ok"),
            CancellationToken.None);

        result.ShouldBe("ok");
    }

    [Authorize(Roles = Roles.Admin)]
    private sealed record AdminOnlyRequest : IRequest<Unit>;

    [Authorize(Policy = Policies.UserAccess)]
    private sealed record UserPolicyRequest : IRequest<string>;
}
