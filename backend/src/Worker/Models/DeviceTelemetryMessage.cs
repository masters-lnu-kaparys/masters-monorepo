namespace Masters.Api.Worker.Models;

public sealed record DeviceTelemetryMessage(
    string DeviceId,
    DateTimeOffset MeasuredAtUtc,
    double DistanceCm,
    bool Occupied,
    double? Latitude = null,
    double? Longitude = null);
