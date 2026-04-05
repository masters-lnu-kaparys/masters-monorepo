using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Worker;
using Masters.Api.Worker.Options;
using Masters.Api.Worker.Services;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.Configure<RealtimeEventHubOptions>(builder.Configuration.GetSection(RealtimeEventHubOptions.SectionName));
builder.Services.Configure<SimulationOptions>(builder.Configuration.GetSection(SimulationOptions.SectionName));
builder.AddInfrastructureServices();
builder.Services.AddScoped<IUser, WorkerUser>();
builder.Services.AddSingleton<TelemetryPayloadParser>();
builder.Services.AddScoped<IParkingTelemetryWriter, ParkingTelemetryWriter>();
builder.Services.AddHostedService<Worker>();
builder.Services.AddHostedService<ParkingSimulationService>();

var host = builder.Build();

using (var scope = host.Services.CreateScope())
{
    var initialiser = scope.ServiceProvider.GetRequiredService<ApplicationDbContextInitialiser>();
    await initialiser.InitialiseAsync();
}

await host.RunAsync();
