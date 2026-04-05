using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;

namespace Masters.Api.Application.Admin.Commands.DeleteParkingLot;

[Authorize(Roles = Roles.Admin)]
public sealed record DeleteParkingLotCommand(long LotId) : IRequest;

public sealed class DeleteParkingLotCommandValidator : AbstractValidator<DeleteParkingLotCommand>
{
    public DeleteParkingLotCommandValidator()
    {
        RuleFor(x => x.LotId)
            .GreaterThan(0);
    }
}

public sealed class DeleteParkingLotCommandHandler : IRequestHandler<DeleteParkingLotCommand>
{
    private readonly IApplicationDbContext _dbContext;

    public DeleteParkingLotCommandHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task Handle(DeleteParkingLotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingLots
            .SingleOrDefaultAsync(x => x.Id == request.LotId, cancellationToken);

        if (entity is null)
        {
            throw new Masters.Api.Application.Common.Exceptions.NotFoundException($"Parking lot with id '{request.LotId}' was not found.");
        }

        _dbContext.ParkingLots.Remove(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
