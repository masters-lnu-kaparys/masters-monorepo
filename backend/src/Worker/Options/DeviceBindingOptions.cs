namespace Masters.Api.Worker.Options;

public sealed class DeviceBindingOptions
{
    public const string SectionName = "DeviceBinding";

    public double MaxParkingLotDistanceKm { get; set; } = 0.2d;
}
