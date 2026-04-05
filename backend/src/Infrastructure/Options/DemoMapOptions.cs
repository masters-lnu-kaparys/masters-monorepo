namespace Masters.Api.Infrastructure.Options;

public sealed class DemoMapOptions
{
    public const string SectionName = "DemoMap";

    public string FallbackCity { get; set; } = "Львів";

    public double FallbackLatitude { get; set; } = 49.8419d;

    public double FallbackLongitude { get; set; } = 24.0315d;

    public int FallbackZoom { get; set; } = 13;

    public double MaxUserDistanceKm { get; set; } = 50d;
}
