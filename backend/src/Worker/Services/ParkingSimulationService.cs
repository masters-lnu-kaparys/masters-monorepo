using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Worker.Models;
using Masters.Api.Worker.Options;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Worker.Services;

public sealed class ParkingSimulationService : BackgroundService
{
    private readonly ILogger<ParkingSimulationService> _logger;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly TimeProvider _timeProvider;
    private readonly SimulationOptions _options;

    public ParkingSimulationService(
        ILogger<ParkingSimulationService> logger,
        IServiceScopeFactory scopeFactory,
        TimeProvider timeProvider,
        IOptions<SimulationOptions> options)
    {
        _logger = logger;
        _scopeFactory = scopeFactory;
        _timeProvider = timeProvider;
        _options = options.Value;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (!_options.Enabled)
        {
            _logger.LogInformation("Parking simulation is disabled in configuration.");
            return;
        }

        try
        {
            await WarmupAsync(stoppingToken);
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
        {
            return;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create warmup history for simulated parking spots.");
        }

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await GenerateCycleAsync(stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to generate simulated parking data.");
            }

            await Task.Delay(TimeSpan.FromSeconds(_options.UpdateIntervalSeconds), stoppingToken);
        }
    }

    private async Task WarmupAsync(CancellationToken cancellationToken)
    {
        using var scope = _scopeFactory.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        var simulatedSpots = await dbContext.ParkingSpots
            .AsNoTracking()
            .Where(x => x.SourceKind == SpotSourceKind.Simulated)
            .OrderBy(x => x.Id)
            .Select(x => new SimulationSpotState(
                x.Id,
                x.DeviceId,
                x.ParkingLotId,
                x.IsOccupied))
            .ToListAsync(cancellationToken);

        if (simulatedSpots.Count == 0)
        {
            return;
        }

        var simulatedSpotIds = simulatedSpots.Select(x => x.Id).ToList();
        var existingTelemetryCount = await dbContext.ParkingTelemetries
            .Where(x => simulatedSpotIds.Contains(x.ParkingSpotId))
            .CountAsync(cancellationToken);

        if (existingTelemetryCount > 0)
        {
            return;
        }

        var writer = scope.ServiceProvider.GetRequiredService<IParkingTelemetryWriter>();
        var now = _timeProvider.GetUtcNow();
        var occupiedStates = simulatedSpots.ToDictionary(x => x.Id, x => x.IsOccupied);

        for (var minutesAgo = _options.WarmupHistoryMinutes; minutesAgo >= 0; minutesAgo -= _options.WarmupStepMinutes)
        {
            var measuredAtUtc = now.AddMinutes(-minutesAgo);

            foreach (var spot in simulatedSpots)
            {
                var currentSpotState = spot with { IsOccupied = occupiedStates[spot.Id] };
                var occupied = ResolveOccupied(currentSpotState, measuredAtUtc);
                var distanceCm = ResolveDistanceCm(spot, measuredAtUtc, occupied);
                occupiedStates[spot.Id] = occupied;

                await writer.WriteAsync(
                    new DeviceTelemetryMessage(
                        spot.DeviceId,
                        measuredAtUtc,
                        distanceCm,
                        occupied),
                    SpotSourceKind.Simulated,
                    cancellationToken);
            }
        }
    }

    private async Task GenerateCycleAsync(CancellationToken cancellationToken)
    {
        using var scope = _scopeFactory.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var writer = scope.ServiceProvider.GetRequiredService<IParkingTelemetryWriter>();

        var simulatedSpots = await dbContext.ParkingSpots
            .AsNoTracking()
            .Where(x => x.SourceKind == SpotSourceKind.Simulated)
            .OrderBy(x => x.Id)
            .Select(x => new SimulationSpotState(
                x.Id,
                x.DeviceId,
                x.ParkingLotId,
                x.IsOccupied))
            .ToListAsync(cancellationToken);

        if (simulatedSpots.Count == 0)
        {
            return;
        }

        var now = _timeProvider.GetUtcNow();

        foreach (var spot in simulatedSpots)
        {
            var occupied = ResolveOccupied(spot, now);
            var distanceCm = ResolveDistanceCm(spot, now, occupied);

            await writer.WriteAsync(
                new DeviceTelemetryMessage(
                    spot.DeviceId,
                    now,
                    distanceCm,
                    occupied),
                SpotSourceKind.Simulated,
                cancellationToken);
        }
    }

    private static bool ResolveOccupied(SimulationSpotState spot, DateTimeOffset measuredAtUtc)
    {
        var targetOccupancy = ResolveTargetOccupancy(spot.ParkingLotId, measuredAtUtc);
        var drift = ResolveStableFraction(spot.Id, measuredAtUtc, 11) - 0.5d;

        if (spot.IsOccupied)
        {
            var releaseChance = Math.Clamp(0.07d + (0.55d - targetOccupancy) * 0.35d + drift * 0.1d, 0.02d, 0.35d);
            return Random.Shared.NextDouble() >= releaseChance;
        }

        var occupyChance = Math.Clamp(0.06d + targetOccupancy * 0.32d + drift * 0.08d, 0.03d, 0.42d);
        return Random.Shared.NextDouble() < occupyChance;
    }

    private static double ResolveDistanceCm(SimulationSpotState spot, DateTimeOffset measuredAtUtc, bool occupied)
    {
        var waveform = ResolveStableFraction(spot.Id, measuredAtUtc, 7);

        if (occupied)
        {
            return 18d + waveform * 22d;
        }

        return 92d + waveform * 62d;
    }

    private static double ResolveTargetOccupancy(long parkingLotId, DateTimeOffset measuredAtUtc)
    {
        var hour = measuredAtUtc.Hour;
        var baseOccupancy = hour switch
        {
            >= 7 and < 10 => 0.42d,
            >= 10 and < 13 => 0.63d,
            >= 13 and < 18 => 0.76d,
            >= 18 and < 21 => 0.58d,
            _ => 0.18d
        };

        var lotBias = ((parkingLotId % 5) - 2) * 0.05d;
        return Math.Clamp(baseOccupancy + lotBias, 0.08d, 0.92d);
    }

    private static double ResolveStableFraction(long seed, DateTimeOffset measuredAtUtc, int cadenceMinutes)
    {
        var window = measuredAtUtc.ToUnixTimeSeconds() / (cadenceMinutes * 60L);
        var value = HashCode.Combine(seed, window);
        return (Math.Abs(value) % 1000) / 1000d;
    }

    private sealed record SimulationSpotState(
        long Id,
        string DeviceId,
        long ParkingLotId,
        bool IsOccupied);
}
