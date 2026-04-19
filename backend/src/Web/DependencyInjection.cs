using Masters.Api.Application.Common.Interfaces;
using Masters.Api.Application.Common.Security;
using Masters.Api.Infrastructure.Data;
using Masters.Api.Web.Options;
using Masters.Api.Web.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Localization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.IdentityModel.Tokens;
using NSwag;
using NSwag.Generation.Processors.Security;
using System.Globalization;

namespace Microsoft.Extensions.DependencyInjection;

public static class DependencyInjection
{
    public static void AddWebServices(this IHostApplicationBuilder builder)
    {
        builder.Services.AddDatabaseDeveloperPageExceptionFilter();

        builder.Services.Configure<Auth0Options>(builder.Configuration.GetSection(Auth0Options.SectionName));
        builder.Services.Configure<RequestLocalizationOptions>(options =>
        {
            var supportedCultures = new[]
            {
                new CultureInfo("uk"),
                new CultureInfo("en"),
            };

            options.DefaultRequestCulture = new RequestCulture("uk");
            options.SupportedCultures = supportedCultures;
            options.SupportedUICultures = supportedCultures;
            options.ApplyCurrentCultureToResponseHeaders = true;
        });

        var auth0Options = builder.Configuration
            .GetSection(Auth0Options.SectionName)
            .Get<Auth0Options>() ?? new Auth0Options();

        var authority = auth0Options.Domain.StartsWith("https://", StringComparison.OrdinalIgnoreCase)
            ? auth0Options.Domain.TrimEnd('/') + "/"
            : $"https://{auth0Options.Domain.TrimEnd('/')}/";

        builder.Services
            .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(options =>
            {
                options.Authority = authority;
                options.Audience = auth0Options.Audience;
                options.MapInboundClaims = false;
                options.TokenValidationParameters = new TokenValidationParameters
                {
                    NameClaimType = "sub",
                    RoleClaimType = auth0Options.RolesClaimType
                };
                options.Events = new JwtBearerEvents
                {
                    OnMessageReceived = context =>
                    {
                        var accessToken = context.Request.Query["access_token"];
                        var path = context.HttpContext.Request.Path;

                        if (!string.IsNullOrWhiteSpace(accessToken)
                            && path.StartsWithSegments("/hubs/parking"))
                        {
                            context.Token = accessToken;
                        }

                        return Task.CompletedTask;
                    }
                };
            });

        builder.Services.AddAuthorizationBuilder()
            .AddPolicy(Policies.UserAccess, policy => policy.RequireAuthenticatedUser())
            .AddPolicy(Policies.AdminAccess, policy => policy.RequireRole(Roles.Admin));

        builder.Services.AddScoped<IUser, CurrentUser>();
        builder.Services.AddScoped<IUserAuthorizationService, UserAuthorizationService>();
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
                .Get<string[]>() ?? [];

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
            configure.AddSecurity(
                "Bearer",
                [],
                new OpenApiSecurityScheme
                {
                    Type = OpenApiSecuritySchemeType.Http,
                    Scheme = "bearer",
                    BearerFormat = "JWT",
                    In = OpenApiSecurityApiKeyLocation.Header,
                    Name = "Authorization",
                    Description = "Enter: Bearer {your JWT token}"
                });
            configure.OperationProcessors.Add(new AspNetCoreOperationSecurityScopeProcessor("Bearer"));
        });
    }
}
