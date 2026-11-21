using System.Text.Json;
using FluentValidation.Results;
using Masters.Api.Application.Admin.Models;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Domain.Enums;
using Microsoft.EntityFrameworkCore;
using AppNotFoundException = Masters.Api.Application.Common.Exceptions.NotFoundException;

namespace Masters.Api.Application.Admin.Commands.SendDeviceCommand;

[Authorize(Roles = Roles.Admin)]
public sealed record SendDeviceCommandCommand(
    long SpotId,
    DeviceCommandType CommandType,
    double? OccupiedBelowCm,
    double? FreeAboveCm) : IRequest<DeviceCommandResultDto>;

public sealed class SendDeviceCommandCommandValidator : AbstractValidator<SendDeviceCommandCommand>
{
    public SendDeviceCommandCommandValidator(IApplicationText text)
    {
        RuleFor(x => x.SpotId)
            .GreaterThan(0)
            .WithMessage(text["validation.spotId.required"]);

        RuleFor(x => x.CommandType)
            .IsInEnum()
            .WithMessage(text["validation.command.type.invalid"]);

        When(x => x.CommandType == DeviceCommandType.SetThresholds, () =>
        {
            RuleFor(x => x.OccupiedBelowCm)
                .NotNull()
                .WithMessage(text["validation.command.thresholds.required"])
                .InclusiveBetween(2, 400)
                .WithMessage(text["validation.command.thresholds.positive"]);

            RuleFor(x => x.FreeAboveCm)
                .NotNull()
                .WithMessage(text["validation.command.thresholds.required"])
                .InclusiveBetween(2, 400)
                .WithMessage(text["validation.command.thresholds.positive"]);

            RuleFor(x => x)
                .Must(x => x.OccupiedBelowCm is not null && x.FreeAboveCm is not null && x.FreeAboveCm > x.OccupiedBelowCm)
                .WithMessage(text["validation.command.thresholds.order"]);
        });
    }
}

public sealed class SendDeviceCommandCommandHandler : IRequestHandler<SendDeviceCommandCommand, DeviceCommandResultDto>
{
    private readonly IApplicationDbContext _dbContext;
    private readonly IDeviceCommandDispatcher _deviceCommandDispatcher;
    private readonly IApplicationText _text;
    private readonly TimeProvider _timeProvider;

    public SendDeviceCommandCommandHandler(
        IApplicationDbContext dbContext,
        IDeviceCommandDispatcher deviceCommandDispatcher,
        IApplicationText text,
        TimeProvider timeProvider)
    {
        _dbContext = dbContext;
        _deviceCommandDispatcher = deviceCommandDispatcher;
        _text = text;
        _timeProvider = timeProvider;
    }

    public async Task<DeviceCommandResultDto> Handle(SendDeviceCommandCommand request, CancellationToken cancellationToken)
    {
        var spot = await _dbContext.ParkingSpots
            .SingleOrDefaultAsync(x => x.Id == request.SpotId, cancellationToken);

        if (spot is null)
        {
            throw new AppNotFoundException(_text.Format("errors.parkingSpot.notFound", request.SpotId));
        }

        if (spot.SourceKind != SpotSourceKind.Real || string.IsNullOrWhiteSpace(spot.DeviceId))
        {
            throw new Masters.Api.Application.Common.Exceptions.ValidationException(
            [
                new ValidationFailure(nameof(request.SpotId), _text["validation.command.realSpotRequired"])
            ]);
        }

        var dispatchRequest = new DeviceCommandDispatchRequest(
            ResolveMethodName(request.CommandType),
            BuildPayloadJson(request),
            ResponseTimeoutSeconds: 15);

        var result = await _deviceCommandDispatcher.SendAsync(
            spot.DeviceId,
            dispatchRequest,
            cancellationToken);

        return new DeviceCommandResultDto(
            spot.DeviceId,
            result.Status,
            result.PayloadJson,
            _timeProvider.GetUtcNow());
    }

    private static string ResolveMethodName(DeviceCommandType commandType)
    {
        return commandType switch
        {
            DeviceCommandType.Ping => "ping",
            DeviceCommandType.MeasureNow => "measureNow",
            DeviceCommandType.SetThresholds => "setThresholds",
            DeviceCommandType.Reboot => "reboot",
            _ => throw new ArgumentOutOfRangeException(nameof(commandType), commandType, null)
        };
    }

    private static string BuildPayloadJson(SendDeviceCommandCommand request)
    {
        return request.CommandType switch
        {
            DeviceCommandType.SetThresholds => JsonSerializer.Serialize(new
            {
                occupiedBelowCm = request.OccupiedBelowCm,
                freeAboveCm = request.FreeAboveCm
            }),
            _ => "{}"
        };
    }
}
