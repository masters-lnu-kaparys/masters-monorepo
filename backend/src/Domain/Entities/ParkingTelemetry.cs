namespace Masters.Api.Domain.Entities;

public sealed class ParkingTelemetry : BaseEntity
{
    public long ParkingSpotId { get; set; }

    public ParkingSpot ParkingSpot { get; set; } = null!;

    public DateTimeOffset MeasuredAtUtc { get; set; }

    public DateTimeOffset ReceivedAtUtc { get; set; }

    public double DistanceCm { get; set; }

    public bool Occupied { get; set; }
}
