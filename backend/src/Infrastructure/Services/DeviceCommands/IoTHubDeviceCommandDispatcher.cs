using Masters.Api.Application.Common.Exceptions;
using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Infrastructure.Options;
using Microsoft.Azure.Devices;
using Microsoft.Extensions.Options;

namespace Masters.Api.Infrastructure.Services.DeviceCommands;

public sealed class IoTHubDeviceCommandDispatcher : IDeviceCommandDispatcher
{
    private readonly IoTHubDeviceCommandsOptions _options;
    private readonly IApplicationText _text;

    public IoTHubDeviceCommandDispatcher(
        IOptions<IoTHubDeviceCommandsOptions> options,
        IApplicationText text)
    {
        _options = options.Value;
        _text = text;
    }

    public async Task<DeviceCommandDispatchResult> SendAsync(
        string deviceId,
        DeviceCommandDispatchRequest request,
        CancellationToken cancellationToken)
    {
        if (!_options.Enabled || string.IsNullOrWhiteSpace(_options.ConnectionString))
        {
            throw new ValidationException(
            [
                new FluentValidation.Results.ValidationFailure(nameof(_options.ConnectionString), _text["errors.deviceCommands.notConfigured"])
            ]);
        }

        using var serviceClient = ServiceClient.CreateFromConnectionString(
            _options.ConnectionString,
            TransportType.Amqp_WebSocket_Only);

        var method = new CloudToDeviceMethod(request.MethodName, TimeSpan.FromSeconds(request.ResponseTimeoutSeconds));
        method.SetPayloadJson(request.PayloadJson);

        var response = await serviceClient.InvokeDeviceMethodAsync(deviceId, method, cancellationToken);

        return new DeviceCommandDispatchResult(
            response.Status,
            response.GetPayloadAsJson() ?? "{}");
    }
}
