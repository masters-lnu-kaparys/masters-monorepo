using Masters.Api.Domain.Entities;
using Masters.Api.Domain.Enums;
using Masters.Api.Infrastructure.Options;
using Microsoft.AspNetCore.Builder;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Masters.Api.Infrastructure.Data;

public static class InitialiserExtensions
{
    public static async Task InitialiseDatabaseAsync(this WebApplication app)
    {
        using var scope = app.Services.CreateScope();

        var initialiser = scope.ServiceProvider.GetRequiredService<ApplicationDbContextInitialiser>();

        await initialiser.InitialiseAsync();
    }
}

public class ApplicationDbContextInitialiser
{
    private readonly ILogger<ApplicationDbContextInitialiser> _logger;
    private readonly ApplicationDbContext _context;
    private readonly DemoTopologyOptions _demoTopologyOptions;

    public ApplicationDbContextInitialiser(
        ILogger<ApplicationDbContextInitialiser> logger,
        ApplicationDbContext context,
        IOptions<DemoTopologyOptions> demoTopologyOptions)
    {
        _logger = logger;
        _context = context;
        _demoTopologyOptions = demoTopologyOptions.Value;
    }

    public async Task InitialiseAsync()
    {
        try
        {
            var connectionString = _context.Database.GetConnectionString();

            if (string.IsNullOrWhiteSpace(connectionString))
            {
                _logger.LogWarning("Database initialisation skipped because the connection string is empty.");
                return;
            }

            await _context.Database.MigrateAsync();
            await SeedDemoTopologyAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "An error occurred while initialising the database.");
            throw;
        }
    }

    private async Task SeedDemoTopologyAsync()
    {
        if (!_demoTopologyOptions.SeedOnStartup || !await TableExistsAsync("ParkingLots"))
        {
            return;
        }

        foreach (var lotOptions in _demoTopologyOptions.Lots)
        {
            var lot = await _context.ParkingLots
                .Include(x => x.Spots)
                .SingleOrDefaultAsync(
                    x => x.Name == lotOptions.Name);

            if (lot is null)
            {
                lot = new ParkingLot
                {
                    Name = lotOptions.Name,
                    City = lotOptions.City,
                    Address = lotOptions.Address,
                    Latitude = lotOptions.Latitude,
                    Longitude = lotOptions.Longitude
                };

                _context.ParkingLots.Add(lot);
            }
            else
            {
                lot.Address = lotOptions.Address;
                lot.Latitude = lotOptions.Latitude;
                lot.Longitude = lotOptions.Longitude;
            }

            var existingDeviceIds = lot.Spots
                .Select(x => x.DeviceId)
                .ToHashSet(StringComparer.OrdinalIgnoreCase);

            var displayOrder = lot.Spots.Count + 1;

            foreach (var realDeviceId in lotOptions.RealSpotDeviceIds.Where(realDeviceId => !existingDeviceIds.Contains(realDeviceId)))
            {
                lot.Spots.Add(new ParkingSpot
                {
                    DeviceId = realDeviceId,
                    DisplayName = $"Місце {displayOrder:00}",
                    SourceKind = SpotSourceKind.Real
                });

                displayOrder++;
            }

            for (var index = 1; index <= lotOptions.SimulatedSpotCount; index++)
            {
                var simulatedDeviceId = BuildSimulatedDeviceId(lotOptions.Key, index);

                if (existingDeviceIds.Contains(simulatedDeviceId))
                {
                    continue;
                }

                lot.Spots.Add(new ParkingSpot
                {
                    DeviceId = simulatedDeviceId,
                    DisplayName = $"Місце {displayOrder:00}",
                    SourceKind = SpotSourceKind.Simulated
                });

                displayOrder++;
            }
        }

        await _context.SaveChangesAsync();
    }

    private async Task<bool> TableExistsAsync(string tableName)
    {
        await using var connection = _context.Database.GetDbConnection();

        if (connection.State != System.Data.ConnectionState.Open)
        {
            await connection.OpenAsync();
        }

        await using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT COUNT(1)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = @tableName
            """;

        var parameter = command.CreateParameter();
        parameter.ParameterName = "@tableName";
        parameter.Value = tableName;
        command.Parameters.Add(parameter);

        var result = await command.ExecuteScalarAsync();

        return result is int count && count > 0
            || result is long longCount && longCount > 0
            || result is decimal decimalCount && decimalCount > 0;
    }

    private static string BuildSimulatedDeviceId(string lotKey, int index)
    {
        return $"sim-lviv-{lotKey}-spot{index:000}";
    }
}
