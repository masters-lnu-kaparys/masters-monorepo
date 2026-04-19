using Masters.Api.Application.Admin.Common;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Enums;
using AppNotFoundException = Masters.Api.Application.Common.Exceptions.NotFoundException;

namespace Masters.Api.Application.Admin.Commands.UpdateParkingSpot;

[Authorize(Roles = Roles.Admin)]
public sealed record UpdateParkingSpotCommand(
    long SpotId,
    string DisplayName,
    SpotSourceKind SourceKind,
    string? DeviceId) : IRequest;

public sealed class UpdateParkingSpotCommandValidator : AbstractValidator<UpdateParkingSpotCommand>
{
    public UpdateParkingSpotCommandValidator(IApplicationText text)
    {
        RuleFor(x => x.SpotId)
            .GreaterThan(0)
            .WithMessage(text["validation.spotId.required"]);

        RuleFor(x => x.DisplayName)
            .NotEmpty()
            .WithMessage(text["validation.spot.displayName.required"])
            .MaximumLength(128)
            .WithMessage(text["validation.spot.displayName.max"]);

        RuleFor(x => x.SourceKind)
            .IsInEnum()
            .WithMessage(text["validation.spot.sourceKind.invalid"]);

        RuleFor(x => x.DeviceId)
            .MaximumLength(128)
            .WithMessage(text["validation.spot.deviceId.max"])
            .When(x => !string.IsNullOrWhiteSpace(x.DeviceId));

        RuleFor(x => x.DeviceId)
            .NotEmpty()
            .When(x => x.SourceKind == SpotSourceKind.Real)
            .WithMessage(text["validation.spot.deviceId.requiredForReal"]);
    }
}

public sealed class UpdateParkingSpotCommandHandler : IRequestHandler<UpdateParkingSpotCommand>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly IApplicationText _text;

    public UpdateParkingSpotCommandHandler(IApplicationDbContext dbContext, IApplicationText text)
    {
        _dbContext = dbContext;
        _text = text;
    }

    public async Task Handle(UpdateParkingSpotCommand request, CancellationToken cancellationToken)
    {
        var entity = await _dbContext.ParkingSpots
            .SingleOrDefaultAsync(x => x.Id == request.SpotId, cancellationToken);

        if (entity is null)
        {
            throw new AppNotFoundException(_text.Format("errors.parkingSpot.notFound", request.SpotId));
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
            _text,
            cancellationToken);

        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
