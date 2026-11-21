using System.Net;
using System.Net.Http.Json;
using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Application.UnitTests.Web.Infrastructure;
using Masters.Api.Web.Models;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace Masters.Api.Application.UnitTests.Web;

public class AuthEndpointTests
{
    [TestCase(SpotSourceKind.Real, "new-clock")]
    [TestCase(SpotSourceKind.Simulated, "previous-clock")]
    public async Task SqlRebindingMustClearAvailabilityAndKeepHistory(SpotSourceKind source, string deviceId)
    {
        await using var factory = new TestWebApplicationFactory();
        var measured = DateTimeOffset.UtcNow.AddSeconds(-5);
        var lot = new ParkingLot { Name = "Rebinding API", City = "Test", Address = "Test" };
        var spot = new ParkingSpot
        {
            ParkingLot = lot,
            DeviceId = "previous-clock",
            DisplayName = "Before rebind",
            SourceKind = SpotSourceKind.Real,
            LastDistanceCm = 100,
            LastTelemetryAtUtc = measured,
            LastLatitude = 49,
            LastLongitude = 24
        };
        await factory.SeedAsync(new ParkingTelemetry
        {
            ParkingSpot = spot,
            MeasuredAtUtc = measured,
            ReceivedAtUtc = measured,
            DistanceCm = 100
        });

        var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserHeader, "test-admin");
        client.DefaultRequestHeaders.Add(TestAuthHandler.RolesHeader, "Admin");
        var url = $"/api/admin/spots/{spot.Id}";

        var rename = await client.PutAsJsonAsync(url, new
        {
            displayName = "Renamed",
            sourceKind = (int)SpotSourceKind.Real,
            deviceId = "previous-clock"
        });
        rename.StatusCode.ShouldBe(HttpStatusCode.NoContent);
        var renamed = await client.GetFromJsonAsync<LotDetailsDto>($"/api/lots/{lot.Id}");
        renamed!.Spots.Single().DataStatus.ShouldBe("current");

        // Keep a separate context at the old binding to model overlapping ingestion.
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var oldBinding = await db.ParkingSpots.SingleAsync();

        var rebind = await client.PutAsJsonAsync(url, new
        {
            displayName = "After rebind",
            sourceKind = (int)source,
            deviceId
        });
        rebind.StatusCode.ShouldBe(HttpStatusCode.NoContent);
        var details = await client.GetFromJsonAsync<LotDetailsDto>($"/api/lots/{lot.Id}");
        details!.Spots.Single().DeviceId.ShouldBe(deviceId);
        details.Spots.Single().DataStatus.ShouldBe("missing");
        details.Spots.Single().DistanceCm.ShouldBeNull();
        details.FreeSpots.ShouldBe(0);
        details.UnknownSpots.ShouldBe(1);

        oldBinding.LastTelemetryAtUtc = measured.AddSeconds(2);
        await Should.ThrowAsync<DbUpdateConcurrencyException>(() => db.SaveChangesAsync());
        db.ChangeTracker.Clear();
        (await db.ParkingTelemetries.SingleAsync()).MeasuredAtUtc.ShouldBe(measured);
        var rebound = await db.ParkingSpots.SingleAsync();
        rebound.LastLatitude.ShouldBeNull();
        rebound.LastLongitude.ShouldBeNull();
        rebound.LastTelemetryAtUtc.ShouldBeNull();
    }

    [Test]
    public async Task SqlApiMustKeepMissingAndStaleSpotsOutOfAvailability()
    {
        await using var factory = new TestWebApplicationFactory();
        var lot = new ParkingLot { Name = "Freshness API", City = "Test", Address = "Test",
            Spots = {
                new ParkingSpot { DeviceId = "api-missing", DisplayName = "Missing", SourceKind = SpotSourceKind.Real },
                new ParkingSpot { DeviceId = "api-stale", DisplayName = "Stale", SourceKind = SpotSourceKind.Real, LastDistanceCm = 100, LastTelemetryAtUtc = DateTimeOffset.UtcNow.AddDays(-1) },
                new ParkingSpot { DeviceId = "api-current", DisplayName = "Current", SourceKind = SpotSourceKind.Real, LastDistanceCm = 100, LastTelemetryAtUtc = DateTimeOffset.UtcNow.AddSeconds(-5) }
            }};
        await factory.SeedAsync(lot);
        var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserHeader, "test-admin");
        client.DefaultRequestHeaders.Add(TestAuthHandler.RolesHeader, "Admin");
        var overview = await client.GetFromJsonAsync<MapOverviewDto>("/api/map/overview");
        overview!.Summary.FreeSpots.ShouldBe(1);
        overview.Summary.UnknownSpots.ShouldBe(2);
        var details = await client.GetFromJsonAsync<LotDetailsDto>($"/api/lots/{lot.Id}");
        details!.Spots.Single(x => x.DeviceId == "api-missing").DataStatus.ShouldBe("missing");
        details.Spots.Single(x => x.DeviceId == "api-stale").DataStatus.ShouldBe("stale");
        var admin = await client.GetFromJsonAsync<List<Application.Admin.Models.AdminParkingLotListItemDto>>("/api/admin/lots");
        admin![0].FreeSpots.ShouldBe(1);
        admin[0].UnknownSpots.ShouldBe(2);
        admin[0].Spots.Single(x => x.DeviceId == "api-missing").DataStatus.ShouldBe("missing");
    }

    [Test]
    public async Task ShouldReturnUnauthorizedForAnonymousMapRequest()
    {
        await using var factory = new TestWebApplicationFactory();
        var client = factory.CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });

        var response = await client.GetAsync("/api/map/overview");

        response.StatusCode.ShouldBe(HttpStatusCode.Unauthorized);
    }

    [Test]
    public async Task ShouldAllowUserToReadProtectedMapOverview()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedAsync(
            new ParkingLot
            {
                Name = "Центральна парковка",
                City = "Львів",
                Address = "пл. Ринок, 1",
                Latitude = 49.8419d,
                Longitude = 24.0315d,
                Spots =
                {
                    new ParkingSpot
                    {
                        DeviceId = "ps-lviv-001",
                        DisplayName = "Місце 01",
                        SourceKind = SpotSourceKind.Real,
                        IsOccupied = false,
                    }
                }
            });

        var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserHeader, "auth0|user-1");
        client.DefaultRequestHeaders.Add(TestAuthHandler.RolesHeader, "User");

        var response = await client.GetAsync("/api/map/overview");

        response.StatusCode.ShouldBe(HttpStatusCode.OK);
        var payload = await response.Content.ReadFromJsonAsync<MapOverviewDto>();
        payload.ShouldNotBeNull();
        payload!.Lots.Count.ShouldBe(1);
    }

    [Test]
    public async Task ShouldAllowAuthenticatedUserWithoutExplicitRoleToReadProtectedMapOverview()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedAsync(
            new ParkingLot
            {
                Name = "Підзамче",
                City = "Львів",
                Address = "вул. Богдана Хмельницького, 124",
                Latitude = 49.8501d,
                Longitude = 24.0376d,
                Spots =
                {
                    new ParkingSpot
                    {
                        DeviceId = "ps-lviv-002",
                        DisplayName = "Місце 02",
                        SourceKind = SpotSourceKind.Real,
                        IsOccupied = true,
                    }
                }
            });

        var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserHeader, "auth0|user-2");

        var response = await client.GetAsync("/api/map/overview");

        response.StatusCode.ShouldBe(HttpStatusCode.OK);
    }

    [Test]
    public async Task ShouldReturnForbiddenForUserOnAdminEndpoint()
    {
        await using var factory = new TestWebApplicationFactory();
        var client = factory.CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserHeader, "auth0|user-1");
        client.DefaultRequestHeaders.Add(TestAuthHandler.RolesHeader, "User");

        var response = await client.GetAsync("/api/admin/lots");

        response.StatusCode.ShouldBe(HttpStatusCode.Forbidden);
    }

    [Test]
    public async Task ShouldAllowAdminToCreateParkingLotAndSpot()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedAsync();

        var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserHeader, "auth0|admin-1");
        client.DefaultRequestHeaders.Add(TestAuthHandler.RolesHeader, "Admin");

        var createLotResponse = await client.PostAsJsonAsync("/api/admin/lots", new
        {
            name = "Паркінг біля опери",
            city = "Львів",
            address = "просп. Свободи, 28",
            latitude = 49.8442d,
            longitude = 24.0269d,
        });

        createLotResponse.StatusCode.ShouldBe(HttpStatusCode.Created);
        var lotId = await createLotResponse.Content.ReadFromJsonAsync<long>();

        var createSpotResponse = await client.PostAsJsonAsync($"/api/admin/lots/{lotId}/spots", new
        {
            displayName = "Місце 01",
            sourceKind = (int)SpotSourceKind.Simulated,
            deviceId = (string?)null,
        });

        createSpotResponse.StatusCode.ShouldBe(HttpStatusCode.Created);

        var lotsResponse = await client.GetFromJsonAsync<List<Application.Admin.Models.AdminParkingLotListItemDto>>("/api/admin/lots");
        lotsResponse.ShouldNotBeNull();
        lotsResponse!.Count.ShouldBe(1);
        lotsResponse[0].Spots.Count.ShouldBe(1);
        lotsResponse[0].Spots[0].DeviceId.ShouldStartWith($"sim-{lotId}-");
    }
}
