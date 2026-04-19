using Masters.Api.Domain.Enums;

namespace Masters.Api.Infrastructure.Data;

public static class ParkingSpotDisplayNameGenerator
{
    public static string Build(string lotKey, SpotSourceKind sourceKind, int ordinal)
    {
        var normalizedLotKey = NormalizeLotKey(lotKey);
        var sourceMarker = sourceKind == SpotSourceKind.Real ? "R" : "S";

        return $"{normalizedLotKey}-{sourceMarker}{ordinal:00}";
    }

    private static string NormalizeLotKey(string lotKey)
    {
        var normalized = new string(lotKey
            .Where(char.IsLetterOrDigit)
            .Select(char.ToUpperInvariant)
            .ToArray());

        return string.IsNullOrWhiteSpace(normalized)
            ? "LOT"
            : normalized;
    }
}
