using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Web.Services;
using Microsoft.AspNetCore.Mvc;
using NSwag;

namespace Microsoft.Extensions.DependencyInjection;

public static class DependencyInjection
{
    public const string FrontendCorsPolicy = "FrontendDevCors";

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
            options.AddPolicy(FrontendCorsPolicy, policyBuilder =>
            {
                policyBuilder
                    .WithOrigins("http://localhost:5173")
                    .AllowAnyHeader()
                    .AllowAnyMethod()
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
