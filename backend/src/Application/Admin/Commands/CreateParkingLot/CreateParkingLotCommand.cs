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
    public CreateParkingLotCommandValidator()
    {
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
