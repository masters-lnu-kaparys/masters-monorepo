using System.Net;
using System.Net.Http.Json;
using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Application.UnitTests.Web.Infrastructure;
using Masters.Api.Web.Models;
using Microsoft.AspNetCore.Mvc.Testing;

namespace Masters.Api.Application.UnitTests.Web;

public class AuthEndpointTests
{
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
