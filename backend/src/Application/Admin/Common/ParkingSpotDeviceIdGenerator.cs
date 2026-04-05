using FluentValidation.Results;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Domain.Enums;

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
        CancellationToken cancellationToken)
    {
        var normalizedDeviceId = requestedDeviceId?.Trim();

        if (!string.IsNullOrWhiteSpace(normalizedDeviceId))
        {
            await EnsureUniqueAsync(dbContext, normalizedDeviceId, currentSpotId, cancellationToken);
            return normalizedDeviceId;
        }

        if (sourceKind == SpotSourceKind.Real)
        {
            throw new Masters.Api.Application.Common.Exceptions.ValidationException(
            [
                new ValidationFailure(nameof(requestedDeviceId), "Device ID is required for real parking spots.")
            ]);
        }

        if (currentSpotId.HasValue
            && currentSourceKind == SpotSourceKind.Simulated
            && !string.IsNullOrWhiteSpace(currentDeviceId))
        {
            return currentDeviceId;
        }

        return await GenerateSimulatedDeviceIdAsync(dbContext, lotId, currentSpotId, cancellationToken);
    }

    private static async Task<string> GenerateSimulatedDeviceIdAsync(
        IApplicationDbContext dbContext,
        long lotId,
        long? currentSpotId,
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

        throw new Masters.Api.Application.Common.Exceptions.ValidationException(
        [
            new ValidationFailure("DeviceId", "Unable to generate a unique device ID for the simulated parking spot.")
        ]);
    }

    private static async Task EnsureUniqueAsync(
        IApplicationDbContext dbContext,
        string deviceId,
        long? currentSpotId,
        CancellationToken cancellationToken)
    {
        var duplicateExists = await dbContext.ParkingSpots.AnyAsync(
            x => x.DeviceId == deviceId && (!currentSpotId.HasValue || x.Id != currentSpotId.Value),
            cancellationToken);

        if (duplicateExists)
        {
            throw new Masters.Api.Application.Common.Exceptions.ValidationException(
            [
                new ValidationFailure("DeviceId", "A parking spot with the same device ID already exists.")
            ]);
        }
    }
}
