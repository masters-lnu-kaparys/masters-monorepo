using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Masters.Api.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddParkingMonitoringSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[ParkingSpots]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [ParkingSpots] (
                        [Id] bigint NOT NULL IDENTITY,
                        [DeviceId] nvarchar(128) NOT NULL,
                        [DisplayName] nvarchar(128) NOT NULL,
                        [IsOccupied] bit NOT NULL,
                        [LastDistanceCm] float NULL,
                        [LastTelemetryAtUtc] datetimeoffset NULL,
                        [Created] datetimeoffset NOT NULL,
                        [CreatedBy] nvarchar(max) NULL,
                        [LastModified] datetimeoffset NOT NULL,
                        [LastModifiedBy] nvarchar(max) NULL,
                        CONSTRAINT [PK_ParkingSpots] PRIMARY KEY ([Id])
                    );
                END
                """);

            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[ParkingTelemetry]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [ParkingTelemetry] (
                        [Id] bigint NOT NULL IDENTITY,
                        [ParkingSpotId] bigint NOT NULL,
                        [MeasuredAtUtc] datetimeoffset NOT NULL,
                        [ReceivedAtUtc] datetimeoffset NOT NULL,
                        [DistanceCm] float NOT NULL,
                        [Occupied] bit NOT NULL,
                        CONSTRAINT [PK_ParkingTelemetry] PRIMARY KEY ([Id]),
                        CONSTRAINT [FK_ParkingTelemetry_ParkingSpots_ParkingSpotId]
                            FOREIGN KEY ([ParkingSpotId]) REFERENCES [ParkingSpots] ([Id]) ON DELETE CASCADE
                    );
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE name = N'IX_ParkingSpots_DeviceId'
                      AND object_id = OBJECT_ID(N'[ParkingSpots]')
                )
                BEGIN
                    CREATE UNIQUE INDEX [IX_ParkingSpots_DeviceId]
                    ON [ParkingSpots] ([DeviceId]);
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.foreign_keys
                    WHERE name = N'FK_ParkingTelemetry_ParkingSpots_ParkingSpotId'
                ) AND OBJECT_ID(N'[ParkingTelemetry]', N'U') IS NOT NULL
                  AND OBJECT_ID(N'[ParkingSpots]', N'U') IS NOT NULL
                BEGIN
                    ALTER TABLE [ParkingTelemetry]
                    ADD CONSTRAINT [FK_ParkingTelemetry_ParkingSpots_ParkingSpotId]
                    FOREIGN KEY ([ParkingSpotId]) REFERENCES [ParkingSpots] ([Id]) ON DELETE CASCADE;
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE name = N'IX_ParkingTelemetry_MeasuredAtUtc'
                      AND object_id = OBJECT_ID(N'[ParkingTelemetry]')
                )
                BEGIN
                    CREATE INDEX [IX_ParkingTelemetry_MeasuredAtUtc]
                    ON [ParkingTelemetry] ([MeasuredAtUtc]);
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE name = N'IX_ParkingTelemetry_ParkingSpotId_MeasuredAtUtc'
                      AND object_id = OBJECT_ID(N'[ParkingTelemetry]')
                )
                BEGIN
                    CREATE UNIQUE INDEX [IX_ParkingTelemetry_ParkingSpotId_MeasuredAtUtc]
                    ON [ParkingTelemetry] ([ParkingSpotId], [MeasuredAtUtc]);
                END
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[ParkingTelemetry]', N'U') IS NOT NULL
                BEGIN
                    DROP TABLE [ParkingTelemetry];
                END
                """);

            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[ParkingSpots]', N'U') IS NOT NULL
                BEGIN
                    DROP TABLE [ParkingSpots];
                END
                """);
        }
    }
}
