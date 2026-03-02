namespace Masters.Api.Web.Models;

public sealed record DashboardSummaryDto(
    int TotalSpots,
    int OccupiedSpots,
    int FreeSpots,
    double OccupancyRate,
    DateTimeOffset? LastTelemetryAtUtc);

public sealed record SpotStateDto(
    long Id,
    string DeviceId,
    string DisplayName,
    bool Occupied,
    double? DistanceCm,
    DateTimeOffset? LastTelemetryAtUtc);

public sealed record SpotHistoryPointDto(
    DateTimeOffset MeasuredAtUtc,
    double DistanceCm,
    bool Occupied);

public sealed record SpotHistoryDto(
    long SpotId,
    DateTimeOffset FromUtc,
    DateTimeOffset ToUtc,
    IReadOnlyList<SpotHistoryPointDto> Points);

public sealed record DashboardSnapshotDto(
    DateTimeOffset GeneratedAtUtc,
    DashboardSummaryDto Summary,
    IReadOnlyList<SpotStateDto> Spots);
