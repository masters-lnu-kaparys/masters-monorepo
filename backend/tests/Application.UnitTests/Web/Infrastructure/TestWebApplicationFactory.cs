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
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;

namespace Masters.Api.Application.UnitTests.Web.Infrastructure;

internal sealed class TestWebApplicationFactory : WebApplicationFactory<Program>
{
    private bool _seeded;
    private readonly string _connectionString =
        $"Server=(localdb)\\mssqllocaldb;Database=Masters.ApiDb.Testing.{Guid.NewGuid():N};Trusted_Connection=True;MultipleActiveResultSets=true";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.ConfigureAppConfiguration((_, configurationBuilder) =>
        {
            configurationBuilder.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ConnectionStrings:DefaultConnection"] = _connectionString,
                [$"{Auth0Options.SectionName}:Domain"] = "parking-demo.eu.auth0.com",
                [$"{Auth0Options.SectionName}:Audience"] = "https://parking-api",
                [$"{Auth0Options.SectionName}:RolesClaimType"] = "https://masters.api/roles",
                ["ClientSide:AllowedOrigins:0"] = "http://localhost:5173",
            });
        });

        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IHostedService>();
            // Minimal-host startup may read its connection before configuration callbacks.
            // Replace the provider options too, so the test DB cannot fall back to appsettings.
            services.RemoveAll<ApplicationDbContext>();
            services.RemoveAll<DbContextOptions<ApplicationDbContext>>();
            services.RemoveAll<IDbContextOptionsConfiguration<ApplicationDbContext>>();
            services.AddDbContext<ApplicationDbContext>(options => options.UseSqlServer(_connectionString));

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

        // Never let a configuration regression turn test setup into a working DB reset.
        ValidateOwnedConnection(dbContext.Database.GetConnectionString()!, _connectionString);

        await dbContext.Database.EnsureDeletedAsync();
        await dbContext.Database.EnsureCreatedAsync();
        _seeded = true;

        if (entities.Length > 0)
        {
            dbContext.AddRange(entities);
            await dbContext.SaveChangesAsync();
        }
    }

    internal static void ValidateOwnedConnection(string actualConnection, string expectedConnection)
    {
        var actual = new SqlConnectionStringBuilder(actualConnection);
        var expected = new SqlConnectionStringBuilder(expectedConnection);
        if (!string.Equals(actual.DataSource, expected.DataSource, StringComparison.OrdinalIgnoreCase)
            || !string.Equals(actual.InitialCatalog, expected.InitialCatalog, StringComparison.Ordinal))
        {
            throw new InvalidOperationException("Refusing to reset a database outside this test factory.");
        }

    }

    public override async ValueTask DisposeAsync()
    {
        try
        {
            if (_seeded)
            {
                using var scope = Services.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                ValidateOwnedConnection(db.Database.GetConnectionString()!, _connectionString);
                await db.Database.EnsureDeletedAsync();
            }
        }
        finally { await base.DisposeAsync(); }
    }
}
