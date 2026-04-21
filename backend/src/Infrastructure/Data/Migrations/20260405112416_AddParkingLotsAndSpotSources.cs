using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Masters.Api.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddParkingLotsAndSpotSources : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[ParkingLots]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [ParkingLots] (
                        [Id] bigint NOT NULL IDENTITY,
                        [Name] nvarchar(128) NOT NULL,
                        [City] nvarchar(128) NOT NULL,
                        [Address] nvarchar(256) NOT NULL,
                        [Latitude] float NOT NULL,
                        [Longitude] float NOT NULL,
                        [Created] datetimeoffset NOT NULL,
                        [CreatedBy] nvarchar(max) NULL,
                        [LastModified] datetimeoffset NOT NULL,
                        [LastModifiedBy] nvarchar(max) NULL,
                        CONSTRAINT [PK_ParkingLots] PRIMARY KEY ([Id])
                    );
                END
                """);

            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[ParkingSpots]', N'ParkingLotId') IS NULL
                BEGIN
                    ALTER TABLE [ParkingSpots]
                    ADD [ParkingLotId] bigint NULL;
                END
                """);

            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[ParkingSpots]', N'SourceKind') IS NULL
                BEGIN
                    ALTER TABLE [ParkingSpots]
                    ADD [SourceKind] int NOT NULL
                        CONSTRAINT [DF_ParkingSpots_SourceKind] DEFAULT (1);
                END
                """);

            migrationBuilder.Sql(
                """
                IF EXISTS (SELECT 1 FROM [ParkingSpots] WHERE [ParkingLotId] IS NULL)
                BEGIN
                    DECLARE @ImportedLotId bigint = (
                        SELECT TOP (1) [Id]
                        FROM [ParkingLots]
                        WHERE [Name] = N'Імпортована парковка'
                          AND [City] = N'Ужгород'
                    );

                    IF @ImportedLotId IS NULL
                    BEGIN
                        INSERT INTO [ParkingLots] ([Name], [City], [Address], [Latitude], [Longitude], [Created], [LastModified])
                        VALUES (N'Імпортована парковка', N'Ужгород', N'Старі дані до появи карти', 48.6208, 22.2879, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET());

                        SET @ImportedLotId = SCOPE_IDENTITY();
                    END

                    UPDATE [ParkingSpots]
                    SET [ParkingLotId] = @ImportedLotId
                    WHERE [ParkingLotId] IS NULL;
                END
                """);

            migrationBuilder.Sql(
                """
                IF EXISTS (
                    SELECT 1
                    FROM sys.columns
                    WHERE object_id = OBJECT_ID(N'[ParkingSpots]')
                      AND [name] = N'ParkingLotId'
                      AND [is_nullable] = 1
                )
                BEGIN
                    ALTER TABLE [ParkingSpots]
                    ALTER COLUMN [ParkingLotId] bigint NOT NULL;
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE [name] = N'IX_ParkingSpots_ParkingLotId_DisplayName'
                      AND [object_id] = OBJECT_ID(N'[ParkingSpots]')
                )
                BEGIN
                    CREATE INDEX [IX_ParkingSpots_ParkingLotId_DisplayName]
                    ON [ParkingSpots] ([ParkingLotId], [DisplayName]);
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE [name] = N'IX_ParkingLots_City_Name'
                      AND [object_id] = OBJECT_ID(N'[ParkingLots]')
                )
                BEGIN
                    CREATE UNIQUE INDEX [IX_ParkingLots_City_Name]
                    ON [ParkingLots] ([City], [Name]);
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.foreign_keys
                    WHERE [name] = N'FK_ParkingSpots_ParkingLots_ParkingLotId'
                ) AND OBJECT_ID(N'[ParkingSpots]', N'U') IS NOT NULL
                  AND OBJECT_ID(N'[ParkingLots]', N'U') IS NOT NULL
                BEGIN
                    ALTER TABLE [ParkingSpots]
                    ADD CONSTRAINT [FK_ParkingSpots_ParkingLots_ParkingLotId]
                    FOREIGN KEY ([ParkingLotId]) REFERENCES [ParkingLots] ([Id]) ON DELETE CASCADE;
                END
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF EXISTS (
                    SELECT 1
                    FROM sys.foreign_keys
                    WHERE [name] = N'FK_ParkingSpots_ParkingLots_ParkingLotId'
                )
                BEGIN
                    ALTER TABLE [ParkingSpots]
                    DROP CONSTRAINT [FK_ParkingSpots_ParkingLots_ParkingLotId];
                END
                """);

            migrationBuilder.Sql(
                """
                IF EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE [name] = N'IX_ParkingSpots_ParkingLotId_DisplayName'
                      AND [object_id] = OBJECT_ID(N'[ParkingSpots]')
                )
                BEGIN
                    DROP INDEX [IX_ParkingSpots_ParkingLotId_DisplayName] ON [ParkingSpots];
                END
                """);

            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[ParkingSpots]', N'SourceKind') IS NOT NULL
                BEGIN
                    DECLARE @DefaultConstraintName nvarchar(128);
                    SELECT @DefaultConstraintName = dc.[name]
                    FROM sys.default_constraints dc
                    INNER JOIN sys.columns c
                        ON c.[default_object_id] = dc.[object_id]
                    WHERE dc.[parent_object_id] = OBJECT_ID(N'[ParkingSpots]')
                      AND c.[name] = N'SourceKind';

                    IF @DefaultConstraintName IS NOT NULL
                    BEGIN
                        EXEC(N'ALTER TABLE [ParkingSpots] DROP CONSTRAINT [' + @DefaultConstraintName + ']');
                    END

                    ALTER TABLE [ParkingSpots]
                    DROP COLUMN [SourceKind];
                END
                """);

            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[ParkingSpots]', N'ParkingLotId') IS NOT NULL
                BEGIN
                    ALTER TABLE [ParkingSpots]
                    DROP COLUMN [ParkingLotId];
                END
                """);

            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[ParkingLots]', N'U') IS NOT NULL
                BEGIN
                    DROP TABLE [ParkingLots];
                END
                """);
        }
    }
}
