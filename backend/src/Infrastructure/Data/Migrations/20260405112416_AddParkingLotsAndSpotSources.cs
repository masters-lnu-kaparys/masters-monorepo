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
            migrationBuilder.CreateTable(
                name: "ParkingLots",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Name = table.Column<string>(type: "nvarchar(128)", maxLength: 128, nullable: false),
                    City = table.Column<string>(type: "nvarchar(128)", maxLength: 128, nullable: false),
                    Address = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: false),
                    Latitude = table.Column<double>(type: "float", nullable: false),
                    Longitude = table.Column<double>(type: "float", nullable: false),
                    Created = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedBy = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    LastModified = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    LastModifiedBy = table.Column<string>(type: "nvarchar(max)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ParkingLots", x => x.Id);
                });

            migrationBuilder.AddColumn<long>(
                name: "ParkingLotId",
                table: "ParkingSpots",
                type: "bigint",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "SourceKind",
                table: "ParkingSpots",
                type: "int",
                nullable: false,
                defaultValue: 1);

            migrationBuilder.Sql(
                """
                IF EXISTS (SELECT 1 FROM ParkingSpots)
                BEGIN
                    INSERT INTO ParkingLots (Name, City, Address, Latitude, Longitude, Created, LastModified)
                    VALUES (N'Імпортована парковка', N'Ужгород', N'Старі дані до появи карти', 48.6208, 22.2879, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET());

                    DECLARE @ImportedLotId bigint = SCOPE_IDENTITY();

                    UPDATE ParkingSpots
                    SET ParkingLotId = @ImportedLotId
                    WHERE ParkingLotId IS NULL;
                END
                """);

            migrationBuilder.AlterColumn<long>(
                name: "ParkingLotId",
                table: "ParkingSpots",
                type: "bigint",
                nullable: false,
                oldClrType: typeof(long),
                oldType: "bigint",
                oldNullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_ParkingSpots_ParkingLotId_DisplayName",
                table: "ParkingSpots",
                columns: new[] { "ParkingLotId", "DisplayName" });

            migrationBuilder.CreateIndex(
                name: "IX_ParkingLots_City_Name",
                table: "ParkingLots",
                columns: new[] { "City", "Name" },
                unique: true);

            migrationBuilder.AddForeignKey(
                name: "FK_ParkingSpots_ParkingLots_ParkingLotId",
                table: "ParkingSpots",
                column: "ParkingLotId",
                principalTable: "ParkingLots",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_ParkingSpots_ParkingLots_ParkingLotId",
                table: "ParkingSpots");

            migrationBuilder.DropTable(
                name: "ParkingLots");

            migrationBuilder.DropIndex(
                name: "IX_ParkingSpots_ParkingLotId_DisplayName",
                table: "ParkingSpots");

            migrationBuilder.DropColumn(
                name: "ParkingLotId",
                table: "ParkingSpots");

            migrationBuilder.DropColumn(
                name: "SourceKind",
                table: "ParkingSpots");
        }
    }
}
