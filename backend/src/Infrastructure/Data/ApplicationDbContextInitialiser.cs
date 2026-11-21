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
    private const string BaselineMigrationId = "20260421203819_InitialCreate";
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

            if (await _context.Database.CanConnectAsync())
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

        if (appliedMigrations.Contains(BaselineMigrationId))
        {
            return;
        }

        // A squashed migration can only be baselined against a matching schema.
        // Never pretend that a partial/older schema has already been migrated.
        await ValidateBaselineSchemaAsync();
        await EnsureMigrationHistoryTableExistsAsync();
        await InsertMigrationHistoryRecordAsync(BaselineMigrationId);
        _logger.LogInformation("Verified existing schema and registered migration {MigrationId}.", BaselineMigrationId);
    }

    private async Task ValidateBaselineSchemaAsync()
    {
        foreach (var table in _context.Model.GetRelationalModel().Tables)
        {
            var qualified = $"[{table.Schema ?? "dbo"}].[{table.Name}]";
            foreach (var column in table.Columns)
            {
                var sql = """
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA=@schema AND TABLE_NAME=@table AND COLUMN_NAME=@column
                      AND LOWER(DATA_TYPE + CASE WHEN DATA_TYPE IN ('nvarchar','varchar','varbinary')
                        THEN '(' + CASE WHEN CHARACTER_MAXIMUM_LENGTH=-1 THEN 'max'
                          ELSE CONVERT(varchar,CHARACTER_MAXIMUM_LENGTH) END + ')' ELSE '' END)=LOWER(@type)
                      AND IS_NULLABLE=@nullable
                    """;
                if (!IsPositiveCount(await ExecuteScalarAsync(sql, ("@schema", table.Schema ?? "dbo"),
                    ("@table", table.Name), ("@column", column.Name), ("@type", column.StoreType),
                    ("@nullable", column.IsNullable ? "YES" : "NO"))))
                    throw BaselineMismatch(qualified + "." + column.Name);
            }
            foreach (var index in table.Indexes)
            {
                var count = await ExecuteScalarAsync("""
                    SELECT COUNT(*) FROM sys.indexes i WHERE i.object_id=OBJECT_ID(@table)
                    AND i.name=@name AND i.is_unique=@unique
                    AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP (ORDER BY ic.key_ordinal)
                      FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                      WHERE ic.object_id=i.object_id AND ic.index_id=i.index_id AND ic.key_ordinal>0)=@columns
                    """, ("@table", qualified), ("@name", index.Name), ("@unique", index.IsUnique),
                    ("@columns", string.Join(',', index.Columns.Select(c => c.Name))));
                if (!IsPositiveCount(count)) throw BaselineMismatch(qualified + "." + index.Name);
            }
            foreach (var key in table.UniqueConstraints)
            {
                var count = await ExecuteScalarAsync("""
                    SELECT COUNT(*) FROM sys.key_constraints k WHERE k.parent_object_id=OBJECT_ID(@table)
                    AND k.name=@name AND (SELECT STRING_AGG(CONVERT(nvarchar(max),c.name),',') WITHIN GROUP (ORDER BY ic.key_ordinal)
                      FROM sys.index_columns ic JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                      WHERE ic.object_id=k.parent_object_id AND ic.index_id=k.unique_index_id AND ic.key_ordinal>0)=@columns
                    """, ("@table", qualified), ("@name", key.Name), ("@columns", string.Join(',', key.Columns.Select(c => c.Name))));
                if (!IsPositiveCount(count)) throw BaselineMismatch(qualified + "." + key.Name);
            }
            foreach (var fk in table.ForeignKeyConstraints)
            {
                var count = await ExecuteScalarAsync("""
                    SELECT COUNT(*) FROM sys.foreign_keys k WHERE k.parent_object_id=OBJECT_ID(@table)
                    AND k.referenced_object_id=OBJECT_ID(@principal) AND k.name=@name
                    AND k.delete_referential_action_desc=@deleteAction AND k.is_disabled=0
                    AND (SELECT STRING_AGG(CONVERT(nvarchar(max),pc.name+':'+rc.name),',') WITHIN GROUP (ORDER BY fc.constraint_column_id)
                      FROM sys.foreign_key_columns fc
                      JOIN sys.columns pc ON pc.object_id=fc.parent_object_id AND pc.column_id=fc.parent_column_id
                      JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
                      WHERE fc.constraint_object_id=k.object_id)=@columns
                    """, ("@table", qualified), ("@name", fk.Name),
                    ("@principal", $"[{fk.PrincipalTable.Schema ?? "dbo"}].[{fk.PrincipalTable.Name}]"),
                    ("@deleteAction", fk.OnDeleteAction == Microsoft.EntityFrameworkCore.Migrations.ReferentialAction.Cascade ? "CASCADE" : "NO_ACTION"),
                    ("@columns", string.Join(',', fk.Columns.Zip(fk.PrincipalColumns, (a,b) => a.Name + ":" + b.Name))));
                if (!IsPositiveCount(count)) throw BaselineMismatch(qualified + "." + fk.Name);
            }
        }
    }

    private static InvalidOperationException BaselineMismatch(string item) => new(
        $"Existing database schema does not match the baseline ({item}). No migration history was changed. " +
        "Back up this database and apply a reviewed schema upgrade, or configure a separate empty database. Do not delete existing data.");

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
