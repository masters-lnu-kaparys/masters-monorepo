namespace Masters.Api.Application.Common.Interfaces;

public interface IDeviceCommandDispatcher
{
    Task<DeviceCommandDispatchResult> SendAsync(
        string deviceId,
        DeviceCommandDispatchRequest request,
        CancellationToken cancellationToken);
}

public sealed record DeviceCommandDispatchRequest(
    string MethodName,
    string PayloadJson,
    int ResponseTimeoutSeconds);

public sealed record DeviceCommandDispatchResult(
    int Status,
    string PayloadJson);
