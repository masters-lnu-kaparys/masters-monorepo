using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Masters.Api.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddDetectedDevices : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[DetectedDevices]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [DetectedDevices] (
                        [Id] bigint NOT NULL IDENTITY,
                        [DeviceId] nvarchar(128) NOT NULL,
                        [FirstSeenAtUtc] datetimeoffset NOT NULL,
                        [LastSeenAtUtc] datetimeoffset NOT NULL,
                        [LastMeasuredAtUtc] datetimeoffset NOT NULL,
                        [LastDistanceCm] float NOT NULL,
                        [LastOccupied] bit NOT NULL,
                        [Created] datetimeoffset NOT NULL,
                        [CreatedBy] nvarchar(max) NULL,
                        [LastModified] datetimeoffset NOT NULL,
                        [LastModifiedBy] nvarchar(max) NULL,
                        CONSTRAINT [PK_DetectedDevices] PRIMARY KEY ([Id])
                    );
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE [name] = N'IX_DetectedDevices_DeviceId'
                      AND [object_id] = OBJECT_ID(N'[DetectedDevices]')
                )
                BEGIN
                    CREATE UNIQUE INDEX [IX_DetectedDevices_DeviceId]
                    ON [DetectedDevices] ([DeviceId]);
                END
                """);

            migrationBuilder.Sql(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE [name] = N'IX_DetectedDevices_LastSeenAtUtc'
                      AND [object_id] = OBJECT_ID(N'[DetectedDevices]')
                )
                BEGIN
                    CREATE INDEX [IX_DetectedDevices_LastSeenAtUtc]
                    ON [DetectedDevices] ([LastSeenAtUtc]);
                END
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[DetectedDevices]', N'U') IS NOT NULL
                BEGIN
                    DROP TABLE [DetectedDevices];
                END
                """);
        }
    }
}
