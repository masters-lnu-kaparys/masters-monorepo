using Masters.Api.Domain.Enums;

namespace Masters.Api.Application.Admin.Models;

public sealed record AdminParkingSpotDto(
    long Id,
    string DisplayName,
    string DeviceId,
    SpotSourceKind SourceKind,
    bool Occupied,
    double? DistanceCm,
    double? LastLatitude,
    double? LastLongitude,
    DateTimeOffset? LastTelemetryAtUtc,
    string DataStatus = "missing");

public sealed record AdminParkingLotListItemDto(
    long Id,
    string Name,
    string City,
    string Address,
    double Latitude,
    double Longitude,
    int TotalSpots,
    int OccupiedSpots,
    int FreeSpots,
    IReadOnlyList<AdminParkingSpotDto> Spots,
    int UnknownSpots = 0);

public sealed record AdminDetectedDeviceDto(
    string DeviceId,
    DateTimeOffset FirstSeenAtUtc,
    DateTimeOffset LastSeenAtUtc,
    DateTimeOffset LastMeasuredAtUtc,
    double LastDistanceCm,
    bool LastOccupied,
    double? LastLatitude,
    double? LastLongitude,
    string DataStatus = "missing");
