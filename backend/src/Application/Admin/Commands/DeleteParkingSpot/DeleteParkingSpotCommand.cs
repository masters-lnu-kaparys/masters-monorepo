using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;

namespace Masters.Api.Application.Admin.Commands.DeleteParkingSpot;

[Authorize(Roles = Roles.Admin)]
public sealed record DeleteParkingSpotCommand(long SpotId) : IRequest;

public sealed class DeleteParkingSpotCommandValidator : AbstractValidator<DeleteParkingSpotCommand>
{
    public DeleteParkingSpotCommandValidator()
    {
        RuleFor(x => x.SpotId)
            .GreaterThan(0);
    }
}

public sealed class DeleteParkingSpotCommandHandler : IRequestHandler<DeleteParkingSpotCommand>
{
    private readonly IApplicationDbContext _dbContext;

    public DeleteParkingSpotCommandHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task Handle(DeleteParkingSpotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingSpots
            .SingleOrDefaultAsync(x => x.Id == request.SpotId, cancellationToken);

        if (entity is null)
        {
            throw new Masters.Api.Application.Common.Exceptions.NotFoundException($"Parking spot with id '{request.SpotId}' was not found.");
        }

        _dbContext.ParkingSpots.Remove(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
