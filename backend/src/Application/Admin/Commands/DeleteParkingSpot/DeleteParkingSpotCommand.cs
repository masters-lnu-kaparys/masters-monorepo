using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using AppNotFoundException = Masters.Api.Application.Common.Exceptions.NotFoundException;

namespace Masters.Api.Application.Admin.Commands.DeleteParkingSpot;

[Authorize(Roles = Roles.Admin)]
public sealed record DeleteParkingSpotCommand(long SpotId) : IRequest;

public sealed class DeleteParkingSpotCommandValidator : AbstractValidator<DeleteParkingSpotCommand>
{
    public DeleteParkingSpotCommandValidator(IApplicationText text)
    {
        RuleFor(x => x.SpotId)
            .GreaterThan(0)
            .WithMessage(text["validation.spotId.required"]);
    }
}

public sealed class DeleteParkingSpotCommandHandler : IRequestHandler<DeleteParkingSpotCommand>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly IApplicationText _text;

    public DeleteParkingSpotCommandHandler(IApplicationDbContext dbContext, IApplicationText text)
    {
        _dbContext = dbContext;
        _text = text;
    }

    public async Task Handle(DeleteParkingSpotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingSpots
            .SingleOrDefaultAsync(x => x.Id == request.SpotId, cancellationToken);

        if (entity is null)
        {
            throw new AppNotFoundException(_text.Format("errors.parkingSpot.notFound", request.SpotId));
        }

        _dbContext.ParkingSpots.Remove(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
