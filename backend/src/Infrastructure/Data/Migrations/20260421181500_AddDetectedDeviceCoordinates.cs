using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Masters.Api.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddDetectedDeviceCoordinates : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[DetectedDevices]', N'LastLatitude') IS NULL
                BEGIN
                    ALTER TABLE [DetectedDevices]
                    ADD [LastLatitude] float NULL;
                END
                """);

            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[DetectedDevices]', N'LastLongitude') IS NULL
                BEGIN
                    ALTER TABLE [DetectedDevices]
                    ADD [LastLongitude] float NULL;
                END
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[DetectedDevices]', N'LastLatitude') IS NOT NULL
                BEGIN
                    ALTER TABLE [DetectedDevices]
                    DROP COLUMN [LastLatitude];
                END
                """);

            migrationBuilder.Sql(
                """
                IF COL_LENGTH(N'[DetectedDevices]', N'LastLongitude') IS NOT NULL
                BEGIN
                    ALTER TABLE [DetectedDevices]
                    DROP COLUMN [LastLongitude];
                END
                """);
        }
    }
}
