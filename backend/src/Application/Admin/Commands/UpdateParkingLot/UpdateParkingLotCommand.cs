using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using AppNotFoundException = Masters.Api.Application.Common.Exceptions.NotFoundException;

namespace Masters.Api.Application.Admin.Commands.UpdateParkingLot;

[Authorize(Roles = Roles.Admin)]
public sealed record UpdateParkingLotCommand(
    long LotId,
    string Name,
    string City,
    string Address,
    double Latitude,
    double Longitude) : IRequest;

public sealed class UpdateParkingLotCommandValidator : AbstractValidator<UpdateParkingLotCommand>
{
    public UpdateParkingLotCommandValidator(IApplicationText text)
    {
        RuleFor(x => x.LotId)
            .GreaterThan(0)
            .WithMessage(text["validation.lotId.required"]);

        RuleFor(x => x.Name)
            .NotEmpty()
            .WithMessage(text["validation.lot.name.required"])
            .MaximumLength(128)
            .WithMessage(text["validation.lot.name.max"]);

        RuleFor(x => x.City)
            .NotEmpty()
            .WithMessage(text["validation.lot.city.required"])
            .MaximumLength(128)
            .WithMessage(text["validation.lot.city.max"]);

        RuleFor(x => x.Address)
            .NotEmpty()
            .WithMessage(text["validation.lot.address.required"])
            .MaximumLength(256)
            .WithMessage(text["validation.lot.address.max"]);

        RuleFor(x => x.Latitude)
            .InclusiveBetween(-90d, 90d)
            .WithMessage(text["validation.lot.latitude.range"]);

        RuleFor(x => x.Longitude)
            .InclusiveBetween(-180d, 180d)
            .WithMessage(text["validation.lot.longitude.range"]);
    }
}

public sealed class UpdateParkingLotCommandHandler : IRequestHandler<UpdateParkingLotCommand>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly IApplicationText _text;

    public UpdateParkingLotCommandHandler(IApplicationDbContext dbContext, IApplicationText text)
    {
        _dbContext = dbContext;
        _text = text;
    }

    public async Task Handle(UpdateParkingLotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingLots
            .SingleOrDefaultAsync(x => x.Id == request.LotId, cancellationToken);

        if (entity is null)
        {
            throw new AppNotFoundException(_text.Format("errors.parkingLot.notFound", request.LotId));
        }

        entity.Name = request.Name.Trim();
        entity.City = request.City.Trim();
        entity.Address = request.Address.Trim();
        entity.Latitude = request.Latitude;
        entity.Longitude = request.Longitude;

        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
