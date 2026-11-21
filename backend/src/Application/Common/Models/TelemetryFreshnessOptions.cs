namespace Masters.Api.Application.Common.Models;

public sealed class TelemetryFreshnessOptions
{
    public const string SectionName = "TelemetryFreshness";
    // Operational timeout for the prototype, separate from the research policy.
    public int MaxAgeSeconds { get; set; } = 120;

    public static string Status(DateTimeOffset? measuredAt, DateTimeOffset now, int maxAgeSeconds) =>
        measuredAt is null ? "missing" :
        measuredAt <= now && measuredAt >= now.AddSeconds(-maxAgeSeconds) ? "current" : "stale";
}
