using FluentValidation.Results;
using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Domain.Enums;
using AppValidationException = Masters.Api.Application.Common.Exceptions.ValidationException;

namespace Masters.Api.Application.Admin.Common;

internal static class ParkingSpotDeviceIdGenerator
{
    public static async Task<string> ResolveAsync(
        IApplicationDbContext dbContext,
        long lotId,
        SpotSourceKind sourceKind,
        string? requestedDeviceId,
        long? currentSpotId,
        string? currentDeviceId,
        SpotSourceKind? currentSourceKind,
        IApplicationText text,
        CancellationToken cancellationToken)
    {
        var normalizedDeviceId = requestedDeviceId?.Trim();

        if (!string.IsNullOrWhiteSpace(normalizedDeviceId))
        {
            await EnsureUniqueAsync(dbContext, normalizedDeviceId, currentSpotId, text, cancellationToken);
            return normalizedDeviceId;
        }

        if (sourceKind == SpotSourceKind.Real)
        {
            throw new AppValidationException(
            [
                new ValidationFailure(nameof(requestedDeviceId), text["validation.spot.deviceId.requiredForReal"])
            ]);
        }

        if (currentSpotId.HasValue
            && currentSourceKind == SpotSourceKind.Simulated
            && !string.IsNullOrWhiteSpace(currentDeviceId))
        {
            return currentDeviceId;
        }

        return await GenerateSimulatedDeviceIdAsync(dbContext, lotId, currentSpotId, text, cancellationToken);
    }

    private static async Task<string> GenerateSimulatedDeviceIdAsync(
        IApplicationDbContext dbContext,
        long lotId,
        long? currentSpotId,
        IApplicationText text,
        CancellationToken cancellationToken)
    {
        for (var index = 1; index <= 10_000; index++)
        {
            var candidate = $"sim-{lotId}-{index:000}";
            var exists = await dbContext.ParkingSpots.AnyAsync(
                x => x.DeviceId == candidate && (!currentSpotId.HasValue || x.Id != currentSpotId.Value),
                cancellationToken);

            if (!exists)
            {
                return candidate;
            }
        }

        throw new AppValidationException(
        [
            new ValidationFailure("DeviceId", text["validation.spot.deviceId.generateFailed"])
        ]);
    }

    private static async Task EnsureUniqueAsync(
        IApplicationDbContext dbContext,
        string deviceId,
        long? currentSpotId,
        IApplicationText text,
        CancellationToken cancellationToken)
    {
        var duplicateExists = await dbContext.ParkingSpots.AnyAsync(
            x => x.DeviceId == deviceId && (!currentSpotId.HasValue || x.Id != currentSpotId.Value),
            cancellationToken);

        if (duplicateExists)
        {
            throw new AppValidationException(
            [
                new ValidationFailure("DeviceId", text["validation.spot.deviceId.duplicate"])
            ]);
        }
    }
}
