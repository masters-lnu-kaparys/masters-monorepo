using Masters.Api.Application.Admin.Common;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Enums;

namespace Masters.Api.Application.Admin.Commands.UpdateParkingSpot;

[Authorize(Roles = Roles.Admin)]
public sealed record UpdateParkingSpotCommand(
    long SpotId,
    string DisplayName,
    SpotSourceKind SourceKind,
    string? DeviceId) : IRequest;

public sealed class UpdateParkingSpotCommandValidator : AbstractValidator<UpdateParkingSpotCommand>
{
    public UpdateParkingSpotCommandValidator()
    {
        RuleFor(x => x.SpotId)
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

public sealed class UpdateParkingSpotCommandHandler : IRequestHandler<UpdateParkingSpotCommand>
{
    private readonly IApplicationDbContext _dbContext;

    public UpdateParkingSpotCommandHandler(IApplicationDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task Handle(UpdateParkingSpotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingSpots
            .SingleOrDefaultAsync(x => x.Id == request.SpotId, cancellationToken);

        if (entity is null)
        {
            throw new Masters.Api.Application.Common.Exceptions.NotFoundException($"Parking spot with id '{request.SpotId}' was not found.");
        }

        var previousSourceKind = entity.SourceKind;
        var previousDeviceId = entity.DeviceId;

        entity.DisplayName = request.DisplayName.Trim();
        entity.SourceKind = request.SourceKind;
        entity.DeviceId = await ParkingSpotDeviceIdGenerator.ResolveAsync(
            _dbContext,
            entity.ParkingLotId,
            request.SourceKind,
            request.DeviceId,
            currentSpotId: entity.Id,
            currentDeviceId: previousDeviceId,
            currentSourceKind: previousSourceKind,
            cancellationToken);

        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
