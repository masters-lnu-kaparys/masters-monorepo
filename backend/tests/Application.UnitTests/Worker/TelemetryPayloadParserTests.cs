using Masters.Api.Worker.Services;

namespace Masters.Api.Application.UnitTests.Worker;

public class TelemetryPayloadParserTests
{
    private readonly TelemetryPayloadParser _parser = new();

    [Test]
    public void ShouldParseValidPayload()
    {
        const string payload = "{\"deviceId\":\"ps-uzh-lot1-spot001\",\"ts\":1735689600,\"distanceCm\":37.4,\"occupied\":true,\"latitude\":49.8387,\"longitude\":23.9944}";

        var parsed = _parser.TryParse(payload, out var message);

        parsed.ShouldBeTrue();
        message.ShouldNotBeNull();
        message!.DeviceId.ShouldBe("ps-uzh-lot1-spot001");
        message.DistanceCm.ShouldBe(37.4d);
        message.Occupied.ShouldBeTrue();
        message.MeasuredAtUtc.ShouldBe(DateTimeOffset.FromUnixTimeSeconds(1735689600));
        message.Latitude.ShouldBe(49.8387d);
        message.Longitude.ShouldBe(23.9944d);
    }

    [Test]
    public void ShouldRejectPayloadWithMissingFields()
    {
        const string payload = "{\"deviceId\":\"spot\",\"distanceCm\":24.1}";

        var parsed = _parser.TryParse(payload, out var message);

        parsed.ShouldBeFalse();
        message.ShouldBeNull();
    }
}
