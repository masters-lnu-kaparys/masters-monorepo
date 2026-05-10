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
    private const string InitialParkingMonitoringMigrationId = "20260302204719_AddParkingMonitoringSchema";
    private const string ParkingLotsMigrationId = "20260405112416_AddParkingLotsAndSpotSources";
    private const string ParkingSpotCoordinatesMigrationId = "20260421203000_AddParkingSpotCoordinates";
    private const string EfCoreProductVersion = "9.0.0";

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

            await EnsureMigrationHistoryForExistingSchemaAsync();
            await _context.Database.MigrateAsync();
            await EnsureParkingSpotCoordinateColumnsAsync();
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

            for (var index = 0; index < lotOptions.RealSpotDeviceIds.Length; index++)
            {
                var realDeviceId = lotOptions.RealSpotDeviceIds[index];

                if (existingDeviceIds.Contains(realDeviceId))
                {
                    continue;
                }

                lot.Spots.Add(new ParkingSpot
                {
                    DeviceId = realDeviceId,
                    DisplayName = ParkingSpotDisplayNameGenerator.Build(
                        lotOptions.Key,
                        SpotSourceKind.Real,
                        index + 1),
                    SourceKind = SpotSourceKind.Real
                });
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
                    DisplayName = ParkingSpotDisplayNameGenerator.Build(
                        lotOptions.Key,
                        SpotSourceKind.Simulated,
                        index),
                    SourceKind = SpotSourceKind.Simulated
                });
            }
        }

        await _context.SaveChangesAsync();
    }

    private async Task EnsureMigrationHistoryForExistingSchemaAsync()
    {
        var hasParkingSpotsTable = await TableExistsAsync("ParkingSpots");

        if (!hasParkingSpotsTable)
        {
            return;
        }

        var appliedMigrations = await GetAppliedMigrationIdsAsync();

        if (appliedMigrations.Count > 0)
        {
            return;
        }

        await EnsureMigrationHistoryTableExistsAsync();

        if (await HasInitialParkingMonitoringSchemaAsync())
        {
            await InsertMigrationHistoryRecordAsync(InitialParkingMonitoringMigrationId);
            _logger.LogInformation(
                "Marked migration {MigrationId} as applied for an existing parking schema.",
                InitialParkingMonitoringMigrationId);
        }

        if (await HasParkingLotsSchemaAsync())
        {
            await InsertMigrationHistoryRecordAsync(ParkingLotsMigrationId);
            _logger.LogInformation(
                "Marked migration {MigrationId} as applied for an existing parking lot schema.",
                ParkingLotsMigrationId);
        }

        if (await HasParkingSpotCoordinateSchemaAsync())
        {
            await InsertMigrationHistoryRecordAsync(ParkingSpotCoordinatesMigrationId);
            _logger.LogInformation(
                "Marked migration {MigrationId} as applied for an existing parking spot coordinate schema.",
                ParkingSpotCoordinatesMigrationId);
        }
    }

    private async Task<bool> HasInitialParkingMonitoringSchemaAsync()
    {
        return await TableExistsAsync("ParkingSpots")
            && await TableExistsAsync("ParkingTelemetry");
    }

    private async Task<bool> HasParkingLotsSchemaAsync()
    {
        return await TableExistsAsync("ParkingLots")
            && await ColumnExistsAsync("ParkingSpots", "ParkingLotId")
            && await ColumnExistsAsync("ParkingSpots", "SourceKind");
    }

    private async Task<bool> HasParkingSpotCoordinateSchemaAsync()
    {
        return await TableExistsAsync("ParkingSpots")
            && await ColumnExistsAsync("ParkingSpots", "LastLatitude")
            && await ColumnExistsAsync("ParkingSpots", "LastLongitude");
    }

    private async Task EnsureParkingSpotCoordinateColumnsAsync()
    {
        if (!await TableExistsAsync("ParkingSpots"))
        {
            return;
        }

        if (!await ColumnExistsAsync("ParkingSpots", "LastLatitude"))
        {
            await ExecuteNonQueryAsync(
                """
                ALTER TABLE [ParkingSpots]
                ADD [LastLatitude] float NULL;
                """);
        }

        if (!await ColumnExistsAsync("ParkingSpots", "LastLongitude"))
        {
            await ExecuteNonQueryAsync(
                """
                ALTER TABLE [ParkingSpots]
                ADD [LastLongitude] float NULL;
                """);
        }
    }

    private async Task<bool> TableExistsAsync(string tableName)
    {
        var result = await ExecuteScalarAsync(
            """
            SELECT COUNT(1)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = @tableName
            """,
            ("@tableName", tableName));

        return IsPositiveCount(result);
    }

    private async Task<bool> ColumnExistsAsync(string tableName, string columnName)
    {
        var result = await ExecuteScalarAsync(
            """
            SELECT COUNT(1)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = @tableName
              AND COLUMN_NAME = @columnName
            """,
            ("@tableName", tableName),
            ("@columnName", columnName));

        return IsPositiveCount(result);
    }

    private async Task<HashSet<string>> GetAppliedMigrationIdsAsync()
    {
        if (!await TableExistsAsync("__EFMigrationsHistory"))
        {
            return [];
        }

        var connection = _context.Database.GetDbConnection();
        var shouldCloseConnection = false;

        if (connection.State != System.Data.ConnectionState.Open)
        {
            await connection.OpenAsync();
            shouldCloseConnection = true;
        }

        try
        {
            await using var command = connection.CreateCommand();
            command.CommandText = "SELECT [MigrationId] FROM [__EFMigrationsHistory]";

            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            await using var reader = await command.ExecuteReaderAsync();

            while (await reader.ReadAsync())
            {
                results.Add(reader.GetString(0));
            }

            return results;
        }
        finally
        {
            if (shouldCloseConnection)
            {
                await connection.CloseAsync();
            }
        }
    }

    private async Task EnsureMigrationHistoryTableExistsAsync()
    {
        await ExecuteNonQueryAsync(
            """
            IF OBJECT_ID(N'[__EFMigrationsHistory]') IS NULL
            BEGIN
                CREATE TABLE [__EFMigrationsHistory] (
                    [MigrationId] nvarchar(150) NOT NULL,
                    [ProductVersion] nvarchar(32) NOT NULL,
                    CONSTRAINT [PK___EFMigrationsHistory] PRIMARY KEY ([MigrationId])
                );
            END
            """);
    }

    private async Task InsertMigrationHistoryRecordAsync(string migrationId)
    {
        await ExecuteNonQueryAsync(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM [__EFMigrationsHistory]
                WHERE [MigrationId] = @migrationId
            )
            BEGIN
                INSERT INTO [__EFMigrationsHistory] ([MigrationId], [ProductVersion])
                VALUES (@migrationId, @productVersion);
            END
            """,
            ("@migrationId", migrationId),
            ("@productVersion", EfCoreProductVersion));
    }

    private async Task<object?> ExecuteScalarAsync(string commandText, params (string Name, object Value)[] parameters)
    {
        var connection = _context.Database.GetDbConnection();
        var shouldCloseConnection = false;

        if (connection.State != System.Data.ConnectionState.Open)
        {
            await connection.OpenAsync();
            shouldCloseConnection = true;
        }

        try
        {
            await using var command = connection.CreateCommand();
            command.CommandText = commandText;

            foreach (var (name, value) in parameters)
            {
                var parameter = command.CreateParameter();
                parameter.ParameterName = name;
                parameter.Value = value;
                command.Parameters.Add(parameter);
            }

            return await command.ExecuteScalarAsync();
        }
        finally
        {
            if (shouldCloseConnection)
            {
                await connection.CloseAsync();
            }
        }
    }

    private async Task ExecuteNonQueryAsync(string commandText, params (string Name, object Value)[] parameters)
    {
        var connection = _context.Database.GetDbConnection();
        var shouldCloseConnection = false;

        if (connection.State != System.Data.ConnectionState.Open)
        {
            await connection.OpenAsync();
            shouldCloseConnection = true;
        }

        try
        {
            await using var command = connection.CreateCommand();
            command.CommandText = commandText;

            foreach (var (name, value) in parameters)
            {
                var parameter = command.CreateParameter();
                parameter.ParameterName = name;
                parameter.Value = value;
                command.Parameters.Add(parameter);
            }

            await command.ExecuteNonQueryAsync();
        }
        finally
        {
            if (shouldCloseConnection)
            {
                await connection.CloseAsync();
            }
        }
    }

    private static bool IsPositiveCount(object? result)
    {
        return result is int count && count > 0
            || result is long longCount && longCount > 0
            || result is decimal decimalCount && decimalCount > 0;
    }

    private static string BuildSimulatedDeviceId(string lotKey, int index)
    {
        return $"sim-lviv-{lotKey}-spot{index:000}";
    }
}
