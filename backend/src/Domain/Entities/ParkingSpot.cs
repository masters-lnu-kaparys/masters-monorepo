using Masters.Api.Domain.Enums;

namespace Masters.Api.Domain.Entities;

public sealed class ParkingSpot : BaseAuditableEntity
{
    public long ParkingLotId { get; set; }

    public ParkingLot ParkingLot { get; set; } = null!;

    public string DeviceId { get; set; } = string.Empty;

    public string DisplayName { get; set; } = string.Empty;

    public SpotSourceKind SourceKind { get; set; }

    public bool IsOccupied { get; set; }

    public double? LastDistanceCm { get; set; }

    public double? LastLatitude { get; set; }

    public double? LastLongitude { get; set; }

    public DateTimeOffset? LastTelemetryAtUtc { get; set; }

    public ICollection<ParkingTelemetry> TelemetryEntries { get; } = new List<ParkingTelemetry>();
}
