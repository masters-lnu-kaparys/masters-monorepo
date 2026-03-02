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
            migrationBuilder.CreateTable(
                name: "ParkingSpots",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    DeviceId = table.Column<string>(type: "nvarchar(128)", maxLength: 128, nullable: false),
                    DisplayName = table.Column<string>(type: "nvarchar(128)", maxLength: 128, nullable: false),
                    IsOccupied = table.Column<bool>(type: "bit", nullable: false),
                    LastDistanceCm = table.Column<double>(type: "float", nullable: true),
                    LastTelemetryAtUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    Created = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedBy = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    LastModified = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    LastModifiedBy = table.Column<string>(type: "nvarchar(max)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ParkingSpots", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "ParkingTelemetry",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ParkingSpotId = table.Column<long>(type: "bigint", nullable: false),
                    MeasuredAtUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    ReceivedAtUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    DistanceCm = table.Column<double>(type: "float", nullable: false),
                    Occupied = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ParkingTelemetry", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ParkingTelemetry_ParkingSpots_ParkingSpotId",
                        column: x => x.ParkingSpotId,
                        principalTable: "ParkingSpots",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_ParkingSpots_DeviceId",
                table: "ParkingSpots",
                column: "DeviceId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ParkingTelemetry_MeasuredAtUtc",
                table: "ParkingTelemetry",
                column: "MeasuredAtUtc");

            migrationBuilder.CreateIndex(
                name: "IX_ParkingTelemetry_ParkingSpotId_MeasuredAtUtc",
                table: "ParkingTelemetry",
                columns: new[] { "ParkingSpotId", "MeasuredAtUtc" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ParkingTelemetry");

            migrationBuilder.DropTable(
                name: "ParkingSpots");
        }
    }
}
