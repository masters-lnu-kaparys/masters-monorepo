namespace Masters.Api.Infrastructure.Options;

public sealed class DemoTopologyOptions
{
    public const string SectionName = "DemoTopology";

    public bool SeedOnStartup { get; set; } = true;

    public List<DemoLotOptions> Lots { get; set; } =
    [
        new DemoLotOptions
        {
            Key = "central",
            Name = "Центральна парковка",
            City = "Львів",
            Address = "пл. Ринок, 1",
            Latitude = 49.8418d,
            Longitude = 24.0316d,
            RealSpotDeviceIds = ["ps-uzh-lot1-spot001"],
            SimulatedSpotCount = 5
        },
        new DemoLotOptions
        {
            Key = "opera",
            Name = "Паркінг біля Оперного",
            City = "Львів",
            Address = "просп. Свободи, 28",
            Latitude = 49.8442d,
            Longitude = 24.0269d,
            SimulatedSpotCount = 7
        },
        new DemoLotOptions
        {
            Key = "station",
            Name = "Вокзальна стоянка",
            City = "Львів",
            Address = "пл. Двірцева, 1",
            Latitude = 49.8387d,
            Longitude = 23.9944d,
            SimulatedSpotCount = 8
        }
    ];
}

public sealed class DemoLotOptions
{
    public string Key { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public string City { get; set; } = string.Empty;

    public string Address { get; set; } = string.Empty;

    public double Latitude { get; set; }

    public double Longitude { get; set; }

    public int SimulatedSpotCount { get; set; }

    public string[] RealSpotDeviceIds { get; set; } = [];
}
