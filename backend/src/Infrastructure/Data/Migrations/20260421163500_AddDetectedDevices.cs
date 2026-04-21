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
            migrationBuilder.CreateTable(
                name: "DetectedDevices",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    DeviceId = table.Column<string>(type: "nvarchar(128)", maxLength: 128, nullable: false),
                    FirstSeenAtUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    LastSeenAtUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    LastMeasuredAtUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    LastDistanceCm = table.Column<double>(type: "float", nullable: false),
                    LastOccupied = table.Column<bool>(type: "bit", nullable: false),
                    Created = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedBy = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    LastModified = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    LastModifiedBy = table.Column<string>(type: "nvarchar(max)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DetectedDevices", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_DetectedDevices_DeviceId",
                table: "DetectedDevices",
                column: "DeviceId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_DetectedDevices_LastSeenAtUtc",
                table: "DetectedDevices",
                column: "LastSeenAtUtc");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "DetectedDevices");
        }
    }
}
