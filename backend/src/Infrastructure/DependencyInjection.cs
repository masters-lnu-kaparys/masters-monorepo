using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Infrastructure.Data.Interceptors;
using Masters.Api.Infrastructure.Localization;
using Masters.Api.Infrastructure.Options;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;

namespace Microsoft.Extensions.DependencyInjection;

public static class DependencyInjection
{
    public static void AddInfrastructureServices(this IHostApplicationBuilder builder)
    {
        var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
        Guard.Against.Null(connectionString, message: "Connection string 'DefaultConnection' not found.");

        builder.Services.Configure<DemoMapOptions>(builder.Configuration.GetSection(DemoMapOptions.SectionName));
        builder.Services.Configure<DemoTopologyOptions>(builder.Configuration.GetSection(DemoTopologyOptions.SectionName));

        builder.Services.AddScoped<ISaveChangesInterceptor, AuditableEntityInterceptor>();

        builder.Services.AddDbContext<ApplicationDbContext>((sp, options) =>
        {
            options.AddInterceptors(sp.GetServices<ISaveChangesInterceptor>());
            options.UseSqlServer(connectionString);
            options.ConfigureWarnings(warnings => warnings.Ignore(RelationalEventId.PendingModelChangesWarning));
        });

        builder.Services.AddScoped<IApplicationDbContext>(provider => provider.GetRequiredService<ApplicationDbContext>());
        builder.Services.AddSingleton<IApplicationText, ApplicationText>();
        builder.Services.AddScoped<ApplicationDbContextInitialiser>();
        builder.Services.AddSingleton(TimeProvider.System);
    }
}
