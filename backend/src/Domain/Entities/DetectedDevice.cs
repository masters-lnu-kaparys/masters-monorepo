namespace Masters.Api.Domain.Entities;

public sealed class DetectedDevice : BaseAuditableEntity
{
    public string DeviceId { get; set; } = string.Empty;

    public DateTimeOffset FirstSeenAtUtc { get; set; }

    public DateTimeOffset LastSeenAtUtc { get; set; }

    public DateTimeOffset LastMeasuredAtUtc { get; set; }

    public double LastDistanceCm { get; set; }

    public bool LastOccupied { get; set; }

    public double? LastLatitude { get; set; }

    public double? LastLongitude { get; set; }
}
