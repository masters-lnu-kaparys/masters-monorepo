namespace Masters.Api.Infrastructure.Options;

public class ClientSideOptions
{
    public const string SectionName = "ClientSide";

    public string WebsiteUrl { get; set; } = string.Empty;

    public string[] AllowedOrigins { get; set; } = Array.Empty<string>();
}
