namespace Masters.Api.Domain.Entities;

public sealed class ParkingSpot : BaseAuditableEntity
{
    public string DeviceId { get; set; } = string.Empty;

    public string DisplayName { get; set; } = string.Empty;

    public bool IsOccupied { get; set; }

    public double? LastDistanceCm { get; set; }

    public DateTimeOffset? LastTelemetryAtUtc { get; set; }

    public ICollection<ParkingTelemetry> TelemetryEntries { get; } = new List<ParkingTelemetry>();
}
