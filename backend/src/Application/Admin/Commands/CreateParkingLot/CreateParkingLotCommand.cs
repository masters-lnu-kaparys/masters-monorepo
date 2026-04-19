using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Entities;

namespace Masters.Api.Application.Admin.Commands.CreateParkingLot;

[Authorize(Roles = Roles.Admin)]
public sealed record CreateParkingLotCommand(
    string Name,
    string City,
    string Address,
    double Latitude,
    double Longitude) : IRequest<long>;

public sealed class CreateParkingLotCommandValidator : AbstractValidator<CreateParkingLotCommand>
{
    public CreateParkingLotCommandValidator(IApplicationText text)
    {
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

public sealed class CreateParkingLotCommandHandler : IRequestHandler<CreateParkingLotCommand, long>
{
    private readonly IApplicationDbContext _dbContext;

    public CreateParkingLotCommandHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<long> Handle(CreateParkingLotCommand request, CancellationToken cancellationToken)
    {
        var entity = new ParkingLot
        {
            Name = request.Name.Trim(),
            City = request.City.Trim(),
            Address = request.Address.Trim(),
            Latitude = request.Latitude,
            Longitude = request.Longitude
        };

        _dbContext.ParkingLots.Add(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);

        return entity.Id;
    }
}
