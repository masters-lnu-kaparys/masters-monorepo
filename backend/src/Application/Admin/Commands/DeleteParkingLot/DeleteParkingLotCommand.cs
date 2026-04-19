using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using AppNotFoundException = Masters.Api.Application.Common.Exceptions.NotFoundException;

namespace Masters.Api.Application.Admin.Commands.DeleteParkingLot;

[Authorize(Roles = Roles.Admin)]
public sealed record DeleteParkingLotCommand(long LotId) : IRequest;

public sealed class DeleteParkingLotCommandValidator : AbstractValidator<DeleteParkingLotCommand>
{
    public DeleteParkingLotCommandValidator(IApplicationText text)
    {
        RuleFor(x => x.LotId)
            .GreaterThan(0)
            .WithMessage(text["validation.lotId.required"]);
    }
}

public sealed class DeleteParkingLotCommandHandler : IRequestHandler<DeleteParkingLotCommand>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly IApplicationText _text;

    public DeleteParkingLotCommandHandler(IApplicationDbContext dbContext, IApplicationText text)
    {
        _dbContext = dbContext;
        _text = text;
    }

    public async Task Handle(DeleteParkingLotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingLots
            .SingleOrDefaultAsync(x => x.Id == request.LotId, cancellationToken);

        if (entity is null)
        {
            throw new AppNotFoundException(_text.Format("errors.parkingLot.notFound", request.LotId));
        }

        _dbContext.ParkingLots.Remove(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
