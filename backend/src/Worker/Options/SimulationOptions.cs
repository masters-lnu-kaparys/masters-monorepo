namespace Masters.Api.Worker.Options;

public sealed class SimulationOptions
{
    public const string SectionName = "Simulation";

    public bool Enabled { get; set; } = true;

    public int UpdateIntervalSeconds { get; set; } = 20;

    public int WarmupHistoryMinutes { get; set; } = 90;

    public int WarmupStepMinutes { get; set; } = 5;
}
