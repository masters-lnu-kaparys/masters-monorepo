namespace Masters.Api.Worker.Options;

public sealed class RealtimeEventHubOptions
{
    public const string SectionName = "RealtimeEventHub";

    public bool Enabled { get; set; }

    public string ConnectionString { get; set; } = string.Empty;

    public string EventHubName { get; set; } = string.Empty;

    public string ConsumerGroup { get; set; } = string.Empty;

    public bool StartFromEarliest { get; set; }
}

