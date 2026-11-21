using Azure.Messaging.EventHubs.Consumer;
using Masters.Api.Domain.Enums;
using Masters.Api.Worker.Models;
using Masters.Api.Worker.Options;
using Masters.Api.Worker.Services;
using Microsoft.Extensions.Options;
using Microsoft.EntityFrameworkCore;
using Microsoft.Data.SqlClient;

namespace Masters.Api.Worker;

public sealed class Worker : BackgroundService
{
    private static readonly TimeSpan RetryDelay = TimeSpan.FromSeconds(5);

    private readonly ILogger<Worker> _logger;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly TelemetryPayloadParser _payloadParser;
    private readonly RealtimeEventHubOptions _options;

    public Worker(
        ILogger<Worker> logger,
        IServiceScopeFactory scopeFactory,
        TelemetryPayloadParser payloadParser,
        IOptions<RealtimeEventHubOptions> options)
    {
        _logger = logger;
        _scopeFactory = scopeFactory;
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

            partitionEvent.Data.SystemProperties.TryGetValue("iothub-connection-device-id", out var authenticatedId);
            if (!_payloadParser.TryParseFromDevice(rawPayload, authenticatedId as string, out var message) || message is null)
            {
                _logger.LogWarning("Skipped invalid telemetry or mismatched device identity.");
                continue;
            }

            try
            {
                await PersistTelemetryAsync(message, stoppingToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                _logger.LogDebug("Skipped telemetry for {DeviceId} after a concurrent change.", message.DeviceId);
            }
            catch (DbUpdateException ex) when (ex.InnerException is SqlException { Number: 8152 or 2628 or 8114 or 8115 or 547 })
            {
                // A bad record must not poison or restart the entire partition stream.
                // Connectivity and other infrastructure errors still reach the retry loop.
                _logger.LogError(ex, "Rejected telemetry record for device {DeviceId}.", message.DeviceId);
            }
        }
    }

    private async Task PersistTelemetryAsync(DeviceTelemetryMessage message, CancellationToken stoppingToken)
    {
        using var scope = _scopeFactory.CreateScope();
        var telemetryWriter = scope.ServiceProvider.GetRequiredService<IParkingTelemetryWriter>();
        var result = await telemetryWriter.WriteAsync(message, SpotSourceKind.Real, stoppingToken);

        switch (result.Outcome)
        {
            case TelemetryWriteOutcome.Duplicate:
                _logger.LogDebug(
                    "Skipped duplicate reading for device {DeviceId} at {MeasuredAtUtc}.",
                    message.DeviceId,
                    message.MeasuredAtUtc);
                break;

            case TelemetryWriteOutcome.SourceMismatch:
                _logger.LogWarning(
                    "Rejected Event Hub update for device {DeviceId} because the spot belongs to another source.",
                    message.DeviceId);
                break;

            case TelemetryWriteOutcome.UnknownSpot:
                _logger.LogWarning(
                    "Rejected Event Hub update for device {DeviceId} because no mapped spot or lot is available.",
                    message.DeviceId);
                break;

            case TelemetryWriteOutcome.FutureMeasurement:
                _logger.LogWarning("Skipped telemetry for {DeviceId} with a measurement time in the future.", message.DeviceId);
                break;

            case TelemetryWriteOutcome.ConcurrentChange:
                _logger.LogDebug("Skipped telemetry for {DeviceId} after a concurrent change.", message.DeviceId);
                break;
        }
    }
}
