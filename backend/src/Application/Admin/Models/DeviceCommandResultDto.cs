namespace Masters.Api.Application.Admin.Models;

public sealed record DeviceCommandResultDto(
    string DeviceId,
    int StatusCode,
    string ResponsePayload,
    DateTimeOffset ProcessedAtUtc);
