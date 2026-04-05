using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;

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
    public UpdateParkingLotCommandValidator()
    {
        RuleFor(x => x.LotId)
            .GreaterThan(0);

        RuleFor(x => x.Name)
            .NotEmpty()
            .MaximumLength(128);

        RuleFor(x => x.City)
            .NotEmpty()
            .MaximumLength(128);

        RuleFor(x => x.Address)
            .NotEmpty()
            .MaximumLength(256);

        RuleFor(x => x.Latitude)
            .InclusiveBetween(-90d, 90d);

        RuleFor(x => x.Longitude)
            .InclusiveBetween(-180d, 180d);
    }
}

public sealed class UpdateParkingLotCommandHandler : IRequestHandler<UpdateParkingLotCommand>
{
    private readonly IApplicationDbContext _dbContext;

    public UpdateParkingLotCommandHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task Handle(UpdateParkingLotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingLots
            .SingleOrDefaultAsync(x => x.Id == request.LotId, cancellationToken);

        if (entity is null)
        {
            throw new Masters.Api.Application.Common.Exceptions.NotFoundException($"Parking lot with id '{request.LotId}' was not found.");
        }

        entity.Name = request.Name.Trim();
        entity.City = request.City.Trim();
        entity.Address = request.Address.Trim();
        entity.Latitude = request.Latitude;
        entity.Longitude = request.Longitude;

        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
