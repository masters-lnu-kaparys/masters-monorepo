using Masters.Api.Infrastructure.Data;
using Masters.Api.Worker;
using Masters.Api.Worker.Options;
using Masters.Api.Worker.Services;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.Configure<RealtimeEventHubOptions>(builder.Configuration.GetSection(RealtimeEventHubOptions.SectionName));
builder.AddInfrastructureServices();
builder.Services.AddSingleton<TelemetryPayloadParser>();
builder.Services.AddHostedService<Worker>();

var host = builder.Build();

using (var scope = host.Services.CreateScope())
{
    var initialiser = scope.ServiceProvider.GetRequiredService<ApplicationDbContextInitialiser>();
    await initialiser.InitialiseAsync();
}

await host.RunAsync();
