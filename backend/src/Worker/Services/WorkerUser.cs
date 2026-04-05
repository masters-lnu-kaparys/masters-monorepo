using Masters.Api.Application.Common.Interfaces;

namespace Masters.Api.Worker.Services;

public sealed class WorkerUser : IUser
{
    public string? Id => "worker";

    public List<string>? Roles => [];
}
