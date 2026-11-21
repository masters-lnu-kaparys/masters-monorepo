using Masters.Api.Domain.Entities;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Options;
using Masters.Api.Application.UnitTests.Web.Infrastructure;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;

namespace Masters.Api.Application.UnitTests.Infrastructure;

public class DatabaseInitialiserTests
{
    [Test]
    public void TestResetMustRejectDifferentServerOrDatabase()
    {
        const string expected = "Server=(localdb)\\mssqllocaldb;Database=Masters.ApiDb.Testing.guard;Integrated Security=true";
        Should.Throw<InvalidOperationException>(() => TestWebApplicationFactory.ValidateOwnedConnection(
            expected.Replace("Testing.guard", "Working"), expected));
        Should.Throw<InvalidOperationException>(() => TestWebApplicationFactory.ValidateOwnedConnection(
            expected.Replace("(localdb)\\mssqllocaldb", "another-server"), expected));
    }

    [TestCase("empty")]
    [TestCase("matching_schema")]
    [TestCase("partial_schema")]
    public async Task InitialisationMustPreserveDataAndRejectAnIncompatibleBaseline(string scenario)
    {
        var database = "Masters.ApiDb.Testing.Initialiser." + Guid.NewGuid().ToString("N");
        var connection = new SqlConnectionStringBuilder {
            DataSource = @"(localdb)\mssqllocaldb", InitialCatalog = database,
            IntegratedSecurity = true, TrustServerCertificate = true
        }.ConnectionString;
        await using var db = new ApplicationDbContext(new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlServer(connection).Options);
        var init = new ApplicationDbContextInitialiser(NullLogger<ApplicationDbContextInitialiser>.Instance, db,
            Options.Create(new DemoTopologyOptions { SeedOnStartup = false, Lots = [] }));
        try
        {
            if (scenario != "empty")
            {
                await db.Database.EnsureCreatedAsync();
                db.ParkingLots.Add(new ParkingLot { Name = "Keep this record", City = "Test", Address = "Test" });
                await db.SaveChangesAsync();
            }
            if (scenario == "partial_schema")
            {
                await db.Database.ExecuteSqlRawAsync("DROP INDEX [IX_ParkingSpots_DeviceId] ON [ParkingSpots]");
                var error = Should.ThrowAsync<InvalidOperationException>(() => init.InitialiseAsync());
                (await error).Message.ShouldContain("No migration history was changed");
                (await db.Database.GetAppliedMigrationsAsync()).ShouldBeEmpty();
            }
            else
            {
                await init.InitialiseAsync();
                await init.InitialiseAsync();
                (await db.Database.GetAppliedMigrationsAsync()).ShouldContain("20260421203819_InitialCreate");
            }
            if (scenario != "empty") (await db.ParkingLots.SingleAsync()).Name.ShouldBe("Keep this record");
        }
        finally
        {
            // Both the full generated catalog and the server must still be ours.
            TestWebApplicationFactory.ValidateOwnedConnection(db.Database.GetConnectionString()!, connection);
            await db.Database.EnsureDeletedAsync();
        }
    }
}
