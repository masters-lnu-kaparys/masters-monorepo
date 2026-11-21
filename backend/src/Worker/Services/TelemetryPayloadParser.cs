using System.Globalization;
using System.Text.Json;
using Masters.Api.Worker.Models;

namespace Masters.Api.Worker.Services;

public sealed class TelemetryPayloadParser
{
    public bool TryParseFromDevice(string payload, string? authenticatedDeviceId, out DeviceTelemetryMessage? message)
    {
        message = null;
        if (string.IsNullOrWhiteSpace(authenticatedDeviceId) || !TryParse(payload, out var parsed)
            || parsed is null || !string.Equals(parsed.DeviceId, authenticatedDeviceId, StringComparison.Ordinal))
            return false;
        message = parsed;
        return true;
    }

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

            if (root.ValueKind != JsonValueKind.Object ||
                !TryReadDeviceId(root, out var deviceId) ||
                !TryReadTimestamp(root, out var measuredAtUtc) ||
                !TryReadDistance(root, out var distanceCm) ||
                !TryReadOccupied(root, out var occupied))
            {
                return false;
            }

            double latitude = default;
            double longitude = default;
            var hasCoordinates = TryReadCoordinate(root, "latitude", -90d, 90d, out latitude)
                && TryReadCoordinate(root, "longitude", -180d, 180d, out longitude);

            message = new DeviceTelemetryMessage(
                deviceId,
                measuredAtUtc,
                distanceCm,
                occupied,
                hasCoordinates ? latitude : null,
                hasCoordinates ? longitude : null);
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
        return !string.IsNullOrWhiteSpace(deviceId) && deviceId.Length <= 128;
    }

    private static bool TryReadTimestamp(JsonElement root, out DateTimeOffset measuredAtUtc)
    {
        measuredAtUtc = default;

        if (!root.TryGetProperty("ts", out var property) || property.ValueKind != JsonValueKind.Number)
        {
            return false;
        }

        if (!property.TryGetInt64(out var unixSeconds) || unixSeconds <= 0
            || unixSeconds > DateTimeOffset.MaxValue.ToUnixTimeSeconds())
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
            return property.TryGetDouble(out distanceCm) && IsValidDistance(distanceCm);
        }

        if (property.ValueKind == JsonValueKind.String)
        {
            var raw = property.GetString();
            return double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out distanceCm)
                && IsValidDistance(distanceCm);
        }

        return false;
    }

    private static bool IsValidDistance(double distanceCm) =>
        double.IsFinite(distanceCm) && distanceCm >= 2 && distanceCm <= 400;

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

    private static bool TryReadCoordinate(
        JsonElement root,
        string propertyName,
        double minValue,
        double maxValue,
        out double value)
    {
        value = default;

        if (!root.TryGetProperty(propertyName, out var property))
        {
            return false;
        }

        var parsed = property.ValueKind switch
        {
            JsonValueKind.Number => property.TryGetDouble(out value),
            JsonValueKind.String => double.TryParse(
                property.GetString(),
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out value),
            _ => false
        };

        return parsed && value >= minValue && value <= maxValue;
    }
}
