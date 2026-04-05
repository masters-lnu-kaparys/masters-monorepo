using Masters.Api.Infrastructure.Data;
using Masters.Api.Web.Options;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace Masters.Api.Application.UnitTests.Web.Infrastructure;

internal sealed class TestWebApplicationFactory : WebApplicationFactory<Program>
{
    private readonly string _connectionString =
        $"Server=(localdb)\\mssqllocaldb;Database=Masters.ApiDb.Testing.{Guid.NewGuid():N};Trusted_Connection=True;MultipleActiveResultSets=true";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.ConfigureAppConfiguration((_, configurationBuilder) =>
        {
            configurationBuilder.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ConnectionStrings:Masters.ApiDb"] = _connectionString,
                [$"{Auth0Options.SectionName}:Domain"] = "parking-demo.eu.auth0.com",
                [$"{Auth0Options.SectionName}:Audience"] = "https://parking-api",
                [$"{Auth0Options.SectionName}:RolesClaimType"] = "https://masters.api/roles",
                ["ClientSide:AllowedOrigins:0"] = "http://localhost:5173",
            });
        });

        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IHostedService>();

            services.AddAuthentication(options =>
                {
                    options.DefaultAuthenticateScheme = TestAuthHandler.SchemeName;
                    options.DefaultChallengeScheme = TestAuthHandler.SchemeName;
                    options.DefaultScheme = TestAuthHandler.SchemeName;
                })
                .AddScheme<AuthenticationSchemeOptions, TestAuthHandler>(TestAuthHandler.SchemeName, _ => { });
        });
    }

    public async Task SeedAsync(params object[] entities)
    {
        using var scope = Services.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        await dbContext.Database.EnsureDeletedAsync();
        await dbContext.Database.EnsureCreatedAsync();

        if (entities.Length > 0)
        {
            dbContext.AddRange(entities);
            await dbContext.SaveChangesAsync();
        }
    }
}
