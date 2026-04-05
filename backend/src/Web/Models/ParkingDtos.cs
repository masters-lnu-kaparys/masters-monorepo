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

public sealed record MapCenterDto(
    double Latitude,
    double Longitude);

public sealed record MapSummaryDto(
    int TotalLots,
    int TotalSpots,
    int OccupiedSpots,
    int FreeSpots,
    double OccupancyRate,
    DateTimeOffset? LastUpdatedAtUtc);

public sealed record ParkingLotMapDto(
    long Id,
    string Name,
    string City,
    string Address,
    double Latitude,
    double Longitude,
    int TotalSpots,
    int OccupiedSpots,
    int FreeSpots,
    double OccupancyRate,
    DateTimeOffset? LastUpdatedAtUtc);

public sealed record MapOverviewDto(
    MapCenterDto MapCenter,
    int Zoom,
    string City,
    double UserLocationMaxDistanceKm,
    MapSummaryDto Summary,
    IReadOnlyList<ParkingLotMapDto> Lots);

public sealed record LotSpotStateDto(
    long Id,
    string DeviceId,
    string DisplayName,
    bool Occupied,
    double? DistanceCm,
    DateTimeOffset? LastUpdatedAtUtc);

public sealed record LotActivityDto(
    long SpotId,
    string SpotName,
    bool Occupied,
    double DistanceCm,
    DateTimeOffset MeasuredAtUtc);

public sealed record LotDetailsDto(
    long Id,
    string Name,
    string City,
    string Address,
    double Latitude,
    double Longitude,
    int TotalSpots,
    int OccupiedSpots,
    int FreeSpots,
    double OccupancyRate,
    DateTimeOffset? LastUpdatedAtUtc,
    IReadOnlyList<LotSpotStateDto> Spots,
    IReadOnlyList<LotActivityDto> RecentActivity);

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

public sealed record MapSnapshotDto(
    DateTimeOffset GeneratedAtUtc,
    MapSummaryDto Summary,
    IReadOnlyList<ParkingLotMapDto> Lots);
