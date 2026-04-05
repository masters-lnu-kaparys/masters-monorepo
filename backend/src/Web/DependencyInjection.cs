using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Web.Services;
using Microsoft.AspNetCore.Mvc;

namespace Microsoft.Extensions.DependencyInjection;

public static class DependencyInjection
{
    public static void AddWebServices(this IHostApplicationBuilder builder)
    {
        builder.Services.AddDatabaseDeveloperPageExceptionFilter();

        builder.Services.AddScoped<IUser, CurrentUser>();
        builder.Services.AddScoped<IParkingReadService, ParkingReadService>();

        builder.Services.AddHostedService<ParkingRealtimeBroadcaster>();
        builder.Services.AddSignalR();

        builder.Services.AddHttpContextAccessor();
        builder.Services.AddHealthChecks()
            .AddDbContextCheck<ApplicationDbContext>();

        builder.Services.AddCors(options =>
        {
            var allowedOrigins = builder.Configuration
                .GetSection("ClientSide:AllowedOrigins")
                .Get<string[]>()!;
            options.AddDefaultPolicy(
                policy =>
                {
                    policy
                        .SetIsOriginAllowedToAllowWildcardSubdomains()
                        .WithOrigins(allowedOrigins)
                        .AllowAnyMethod()
                        .AllowAnyHeader()
                        .AllowCredentials();
                });
        });

        builder.Services.AddExceptionHandler<CustomExceptionHandler>();

        builder.Services.Configure<ApiBehaviorOptions>(options =>
            options.SuppressModelStateInvalidFilter = true);

        builder.Services.AddEndpointsApiExplorer();

        builder.Services.AddOpenApiDocument(configure =>
        {
            configure.Title = "Masters.Api API";
        });
    }
}
