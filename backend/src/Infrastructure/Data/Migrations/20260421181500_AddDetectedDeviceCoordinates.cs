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
            migrationBuilder.AddColumn<double>(
                name: "LastLatitude",
                table: "DetectedDevices",
                type: "float",
                nullable: true);

            migrationBuilder.AddColumn<double>(
                name: "LastLongitude",
                table: "DetectedDevices",
                type: "float",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "LastLatitude",
                table: "DetectedDevices");

            migrationBuilder.DropColumn(
                name: "LastLongitude",
                table: "DetectedDevices");
        }
    }
}
