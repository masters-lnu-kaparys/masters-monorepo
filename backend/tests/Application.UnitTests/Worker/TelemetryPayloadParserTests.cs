using Masters.Api.Worker.Services;

namespace Masters.Api.Application.UnitTests.Worker;

public class TelemetryPayloadParserTests
{
    private readonly TelemetryPayloadParser _parser = new();

    [TestCase("[]")]
    [TestCase("42")]
    [TestCase("null")]
    [TestCase("{\"deviceId\":\"spot\",\"ts\":9223372036854775807,\"distanceCm\":20,\"occupied\":true}")]
    [TestCase("{\"deviceId\":\"spot\",\"ts\":1735689600,\"distanceCm\":\"NaN\",\"occupied\":true}")]
    [TestCase("{\"deviceId\":\"spot\",\"ts\":1735689600,\"distanceCm\":\"Infinity\",\"occupied\":true}")]
    [TestCase("{\"deviceId\":\"spot\",\"ts\":1735689600,\"distanceCm\":-10,\"occupied\":true}")]
    [TestCase("{\"deviceId\":\"spot\",\"ts\":1735689600,\"distanceCm\":401,\"occupied\":true}")]
    public void ShouldRejectInvalidRecordsWithoutThrowing(string payload)
    {
        _parser.TryParse(payload, out var message).ShouldBeFalse();
        message.ShouldBeNull();
    }

    [TestCase(null, false)]
    [TestCase("other-device", false)]
    [TestCase("spot", true)]
    public void ShouldRequireAuthenticatedDeviceIdentity(string? authenticatedId, bool expected)
    {
        const string payload = "{\"deviceId\":\"spot\",\"ts\":1735689600,\"distanceCm\":20,\"occupied\":true}";
        _parser.TryParseFromDevice(payload, authenticatedId, out _).ShouldBe(expected);
    }

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
