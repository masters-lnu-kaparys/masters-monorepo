using Masters.Api.Application.Admin.Common;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using AppNotFoundException = Masters.Api.Application.Common.Exceptions.NotFoundException;

namespace Masters.Api.Application.Admin.Commands.CreateParkingSpot;

[Authorize(Roles = Roles.Admin)]
public sealed record CreateParkingSpotCommand(
    long LotId,
    string DisplayName,
    SpotSourceKind SourceKind,
    string? DeviceId) : IRequest<long>;

public sealed class CreateParkingSpotCommandValidator : AbstractValidator<CreateParkingSpotCommand>
{
    public CreateParkingSpotCommandValidator(IApplicationText text)
    {
        RuleFor(x => x.LotId)
            .GreaterThan(0)
            .WithMessage(text["validation.lotId.required"]);

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

public sealed class CreateParkingSpotCommandHandler : IRequestHandler<CreateParkingSpotCommand, long>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly IApplicationText _text;

    public CreateParkingSpotCommandHandler(IApplicationDbContext dbContext, IApplicationText text)
    {
        _dbContext = dbContext;
        _text = text;
    }

    public async Task<long> Handle(CreateParkingSpotCommand request, CancellationToken cancellationToken)
    {
        var lotExists = await _dbContext.ParkingLots
            .AnyAsync(x => x.Id == request.LotId, cancellationToken);

        if (!lotExists)
        {
            throw new AppNotFoundException(_text.Format("errors.parkingLot.notFound", request.LotId));
        }

        var deviceId = await ParkingSpotDeviceIdGenerator.ResolveAsync(
            _dbContext,
            request.LotId,
            request.SourceKind,
            request.DeviceId,
            currentSpotId: null,
            currentDeviceId: null,
            currentSourceKind: null,
            _text,
            cancellationToken);

        var entity = new ParkingSpot
        {
            ParkingLotId = request.LotId,
            DisplayName = request.DisplayName.Trim(),
            SourceKind = request.SourceKind,
            DeviceId = deviceId
        };

        var detectedDevice = await _dbContext.DetectedDevices
            .SingleOrDefaultAsync(x => x.DeviceId == deviceId, cancellationToken);

        if (detectedDevice is not null)
        {
            _dbContext.DetectedDevices.Remove(detectedDevice);
        }

        _dbContext.ParkingSpots.Add(entity);
        await _dbContext.SaveChangesAsync(cancellationToken);

        return entity.Id;
    }
}
