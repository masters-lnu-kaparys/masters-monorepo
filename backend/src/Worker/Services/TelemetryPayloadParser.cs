using System.Globalization;
using System.Text.Json;
using Masters.Api.Worker.Models;

namespace Masters.Api.Worker.Services;

public sealed class TelemetryPayloadParser
{
    public bool TryParse(string payload, out DeviceTelemetryMessage? message)
    {
        message = null;

        if (string.IsNullOrWhiteSpace(payload))
        {
            return false;
        }

        try
        {
            using var document = JsonDocument.Parse(payload);
            var root = document.RootElement;

            if (!TryReadDeviceId(root, out var deviceId) ||
                !TryReadTimestamp(root, out var measuredAtUtc) ||
                !TryReadDistance(root, out var distanceCm) ||
                !TryReadOccupied(root, out var occupied))
            {
                return false;
            }

            message = new DeviceTelemetryMessage(deviceId, measuredAtUtc, distanceCm, occupied);
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static bool TryReadDeviceId(JsonElement root, out string deviceId)
    {
        deviceId = string.Empty;

        if (!root.TryGetProperty("deviceId", out var property) || property.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        deviceId = property.GetString()?.Trim() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(deviceId);
    }

    private static bool TryReadTimestamp(JsonElement root, out DateTimeOffset measuredAtUtc)
    {
        measuredAtUtc = default;

        if (!root.TryGetProperty("ts", out var property) || property.ValueKind != JsonValueKind.Number)
        {
            return false;
        }

        if (!property.TryGetInt64(out var unixSeconds) || unixSeconds <= 0)
        {
            return false;
        }

        measuredAtUtc = DateTimeOffset.FromUnixTimeSeconds(unixSeconds).ToUniversalTime();
        return true;
    }

    private static bool TryReadDistance(JsonElement root, out double distanceCm)
    {
        distanceCm = default;

        if (!root.TryGetProperty("distanceCm", out var property))
        {
            return false;
        }

        if (property.ValueKind == JsonValueKind.Number)
        {
            return property.TryGetDouble(out distanceCm);
        }

        if (property.ValueKind == JsonValueKind.String)
        {
            var raw = property.GetString();
            return double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out distanceCm);
        }

        return false;
    }

    private static bool TryReadOccupied(JsonElement root, out bool occupied)
    {
        occupied = false;

        if (!root.TryGetProperty("occupied", out var property))
        {
            return false;
        }

        if (property.ValueKind == JsonValueKind.True || property.ValueKind == JsonValueKind.False)
        {
            occupied = property.GetBoolean();
            return true;
        }

        if (property.ValueKind == JsonValueKind.String)
        {
            return bool.TryParse(property.GetString(), out occupied);
        }

        return false;
    }
}
