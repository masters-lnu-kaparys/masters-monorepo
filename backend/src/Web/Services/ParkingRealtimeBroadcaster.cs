using System.Text.Json;
using Masters.Api.Web.Hubs;
using Microsoft.AspNetCore.SignalR;

namespace Masters.Api.Web.Services;

public sealed class ParkingRealtimeBroadcaster : BackgroundService
{
    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(2);

    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IHubContext<ParkingHub> _hubContext;
    private readonly ILogger<ParkingRealtimeBroadcaster> _logger;

    private string? _lastSnapshotSignature;

    public ParkingRealtimeBroadcaster(
        IServiceScopeFactory scopeFactory,
        IHubContext<ParkingHub> hubContext,
        ILogger<ParkingRealtimeBroadcaster> logger)
    {
        _scopeFactory = scopeFactory;
        _hubContext = hubContext;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await BroadcastIfChangedAsync(stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to broadcast parking snapshot.");
            }

            await Task.Delay(PollInterval, stoppingToken);
        }
    }

    private async Task BroadcastIfChangedAsync(CancellationToken cancellationToken)
    {
        using var scope = _scopeFactory.CreateScope();
        var readService = scope.ServiceProvider.GetRequiredService<IParkingReadService>();

        var snapshot = await readService.GetMapSnapshotAsync(cancellationToken);
        var signature = JsonSerializer.Serialize(new
        {
            snapshot.Summary,
            snapshot.Lots
        });

        if (signature == _lastSnapshotSignature)
        {
            return;
        }

        _lastSnapshotSignature = signature;

        await _hubContext.Clients.All.SendAsync("mapSnapshot", snapshot, cancellationToken);
    }
}
