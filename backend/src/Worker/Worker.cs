using Azure.Messaging.EventHubs.Consumer;
using Masters.Api.Domain.Entities;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Worker.Models;
using Masters.Api.Worker.Options;
using Masters.Api.Worker.Services;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Masters.Api.Worker;

public sealed class Worker : BackgroundService
{
    private static readonly TimeSpan RetryDelay = TimeSpan.FromSeconds(5);

    private readonly ILogger<Worker> _logger;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly TimeProvider _timeProvider;
    private readonly TelemetryPayloadParser _payloadParser;
    private readonly RealtimeEventHubOptions _options;

    public Worker(
        ILogger<Worker> logger,
        IServiceScopeFactory scopeFactory,
        TimeProvider timeProvider,
        TelemetryPayloadParser payloadParser,
        IOptions<RealtimeEventHubOptions> options)
    {
        _logger = logger;
        _scopeFactory = scopeFactory;
        _timeProvider = timeProvider;
        _payloadParser = payloadParser;
        _options = options.Value;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (!_options.Enabled)
        {
            _logger.LogInformation("RealtimeEventHub ingestion is disabled in configuration.");
            return;
        }

        if (string.IsNullOrWhiteSpace(_options.ConnectionString) || string.IsNullOrWhiteSpace(_options.EventHubName))
        {
            _logger.LogError("RealtimeEventHub options are invalid. Configure both ConnectionString and EventHubName.");
            return;
        }

        var readOptions = new ReadEventOptions();

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await ConsumeAsync(readOptions, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to consume Event Hub telemetry. Retrying in {DelaySeconds}s.", RetryDelay.TotalSeconds);
                await Task.Delay(RetryDelay, stoppingToken);
            }
        }
    }

    private async Task ConsumeAsync(ReadEventOptions readOptions, CancellationToken stoppingToken)
    {
        await using var consumer = new EventHubConsumerClient(
            _options.ConsumerGroup,
            _options.ConnectionString,
            _options.EventHubName);

        _logger.LogInformation(
            "Listening Event Hub '{EventHubName}' in consumer group '{ConsumerGroup}' (start: {StartPosition}).",
            _options.EventHubName,
            _options.ConsumerGroup,
            _options.StartFromEarliest ? "earliest" : "latest");

        await foreach (var partitionEvent in consumer.ReadEventsAsync(_options.StartFromEarliest, readOptions, stoppingToken))
        {
            var rawPayload = partitionEvent.Data.EventBody.ToString();

            if (!_payloadParser.TryParse(rawPayload, out var message) || message is null)
            {
                _logger.LogWarning("Skipped malformed telemetry payload: {Payload}", rawPayload);
                continue;
            }

            await PersistTelemetryAsync(message, stoppingToken);
        }
    }

    private async Task PersistTelemetryAsync(DeviceTelemetryMessage message, CancellationToken stoppingToken)
    {
        using var scope = _scopeFactory.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        var spot = await dbContext.ParkingSpots
            .SingleOrDefaultAsync(x => x.DeviceId == message.DeviceId, stoppingToken);

        if (spot is null)
        {
            spot = new ParkingSpot
            {
                DeviceId = message.DeviceId,
                DisplayName = message.DeviceId
            };

            dbContext.ParkingSpots.Add(spot);
        }

        var receivedAtUtc = _timeProvider.GetUtcNow();

        spot.IsOccupied = message.Occupied;
        spot.LastDistanceCm = message.DistanceCm;
        spot.LastTelemetryAtUtc = message.MeasuredAtUtc;

        dbContext.ParkingTelemetries.Add(new ParkingTelemetry
        {
            ParkingSpot = spot,
            MeasuredAtUtc = message.MeasuredAtUtc,
            ReceivedAtUtc = receivedAtUtc,
            DistanceCm = message.DistanceCm,
            Occupied = message.Occupied
        });

        try
        {
            await dbContext.SaveChangesAsync(stoppingToken);
        }
        catch (DbUpdateException ex) when (IsUniqueConstraintViolation(ex))
        {
            dbContext.ChangeTracker.Clear();
            _logger.LogDebug(
                "Skipped duplicate telemetry for device {DeviceId} at {MeasuredAtUtc}.",
                message.DeviceId,
                message.MeasuredAtUtc);
        }
    }

    private static bool IsUniqueConstraintViolation(DbUpdateException ex)
    {
        return ex.InnerException is SqlException sqlException
            && (sqlException.Number == 2601 || sqlException.Number == 2627);
    }
}
