namespace Masters.Api.Infrastructure.Options;

public sealed class IoTHubDeviceCommandsOptions
{
    public const string SectionName = "IoTHubDeviceCommands";

    public bool Enabled { get; set; }

    public string ConnectionString { get; set; } = string.Empty;
}
