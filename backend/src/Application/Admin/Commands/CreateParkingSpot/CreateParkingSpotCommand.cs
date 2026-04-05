using Masters.Api.Application.Admin.Common;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;

namespace Masters.Api.Application.Admin.Commands.CreateParkingSpot;

[Authorize(Roles = Roles.Admin)]
public sealed record CreateParkingSpotCommand(
    long LotId,
    string DisplayName,
    SpotSourceKind SourceKind,
    string? DeviceId) : IRequest<long>;

public sealed class CreateParkingSpotCommandValidator : AbstractValidator<CreateParkingSpotCommand>
{
    public CreateParkingSpotCommandValidator()
    {
        RuleFor(x => x.LotId)
            .GreaterThan(0);

        RuleFor(x => x.DisplayName)
            .NotEmpty()
            .MaximumLength(128);

        RuleFor(x => x.SourceKind)
            .IsInEnum();

        RuleFor(x => x.DeviceId)
            .MaximumLength(128)
            .When(x => !string.IsNullOrWhiteSpace(x.DeviceId));

        RuleFor(x => x.DeviceId)
            .NotEmpty()
            .When(x => x.SourceKind == SpotSourceKind.Real)
            .WithMessage("Device ID is required for real parking spots.");
    }
}

public sealed class CreateParkingSpotCommandHandler : IRequestHandler<CreateParkingSpotCommand, long>
{
    private readonly IApplicationDbContext _dbContext;

    public CreateParkingSpotCommandHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<long> Handle(CreateParkingSpotCommand request, CancellationToken cancellationToken)
    {
        var lotExists = await _dbContext.ParkingLots
            .AnyAsync(x => x.Id == request.LotId, cancellationToken);

        if (!lotExists)
        {
            throw new Masters.Api.Application.Common.Exceptions.NotFoundException($"Parking lot with id '{request.LotId}' was not found.");
        }

        var deviceId = await ParkingSpotDeviceIdGenerator.ResolveAsync(
            _dbContext,
            request.LotId,
            request.SourceKind,
            request.DeviceId,
            currentSpotId: null,
            currentDeviceId: null,
            currentSourceKind: null,
            cancellationToken);

        var entity = new ParkingSpot
        {
            ParkingLotId = request.LotId,
            DisplayName = request.DisplayName.Trim(),
            SourceKind = request.SourceKind,
            DeviceId = deviceId
        };

        _dbContext.ParkingSpots.Add(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);

        return entity.Id;
    }
}
