using System.Globalization;
using Masters.Api.Application.Common.Interfaces;

namespace Masters.Api.Infrastructure.Localization;

public sealed class ApplicationText : IApplicationText
{
    private static readonly IReadOnlyDictionary<string, string> English = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["validation.generic"] = "One or more validation failures have occurred.",
        ["validation.lotId.required"] = "Parking lot id must be greater than zero.",
        ["validation.spotId.required"] = "Parking spot id must be greater than zero.",
        ["validation.lot.name.required"] = "Parking lot name is required.",
        ["validation.lot.name.max"] = "Parking lot name must be 128 characters or fewer.",
        ["validation.lot.city.required"] = "City is required.",
        ["validation.lot.city.max"] = "City must be 128 characters or fewer.",
        ["validation.lot.address.required"] = "Address is required.",
        ["validation.lot.address.max"] = "Address must be 256 characters or fewer.",
        ["validation.lot.latitude.range"] = "Latitude must be between -90 and 90.",
        ["validation.lot.longitude.range"] = "Longitude must be between -180 and 180.",
        ["validation.spot.displayName.required"] = "Parking spot name is required.",
        ["validation.spot.displayName.max"] = "Parking spot name must be 128 characters or fewer.",
        ["validation.spot.sourceKind.invalid"] = "Parking spot source type is invalid.",
        ["validation.spot.deviceId.max"] = "Device ID must be 128 characters or fewer.",
        ["validation.spot.deviceId.requiredForReal"] = "Device ID is required for real parking spots.",
        ["validation.spot.deviceId.duplicate"] = "A parking spot with the same device ID already exists.",
        ["validation.spot.deviceId.generateFailed"] = "Unable to generate a unique device ID for the simulated parking spot.",
        ["validation.command.type.invalid"] = "Device command type is invalid.",
        ["validation.command.thresholds.required"] = "Both threshold values are required for this command.",
        ["validation.command.thresholds.positive"] = "Threshold values must be greater than zero.",
        ["validation.command.thresholds.order"] = "The free threshold must be greater than the occupied threshold.",
        ["validation.command.realSpotRequired"] = "Commands can only be sent to a real parking spot with a device ID.",
        ["errors.parkingLot.notFound"] = "Parking lot with id '{0}' was not found.",
        ["errors.parkingSpot.notFound"] = "Parking spot with id '{0}' was not found.",
        ["errors.deviceCommands.notConfigured"] = "Device commands are not configured for this environment.",
        ["problem.validation.title"] = "Validation failed.",
        ["problem.notFound.title"] = "The requested resource was not found.",
        ["problem.unauthorized.title"] = "Authentication is required.",
        ["problem.forbidden.title"] = "You do not have permission to perform this action.",
    };

    private static readonly IReadOnlyDictionary<string, string> Ukrainian = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["validation.generic"] = "Під час перевірки даних виникли помилки.",
        ["validation.lotId.required"] = "Ідентифікатор парковки має бути більшим за нуль.",
        ["validation.spotId.required"] = "Ідентифікатор місця має бути більшим за нуль.",
        ["validation.lot.name.required"] = "Вкажіть назву парковки.",
        ["validation.lot.name.max"] = "Назва парковки має містити не більше 128 символів.",
        ["validation.lot.city.required"] = "Вкажіть місто.",
        ["validation.lot.city.max"] = "Назва міста має містити не більше 128 символів.",
        ["validation.lot.address.required"] = "Вкажіть адресу.",
        ["validation.lot.address.max"] = "Адреса має містити не більше 256 символів.",
        ["validation.lot.latitude.range"] = "Широта має бути в межах від -90 до 90.",
        ["validation.lot.longitude.range"] = "Довгота має бути в межах від -180 до 180.",
        ["validation.spot.displayName.required"] = "Вкажіть назву місця.",
        ["validation.spot.displayName.max"] = "Назва місця має містити не більше 128 символів.",
        ["validation.spot.sourceKind.invalid"] = "Вказано некоректний тип джерела місця.",
        ["validation.spot.deviceId.max"] = "Device ID має містити не більше 128 символів.",
        ["validation.spot.deviceId.requiredForReal"] = "Для реального паркомісця потрібно вказати Device ID.",
        ["validation.spot.deviceId.duplicate"] = "Паркомісце з таким Device ID уже існує.",
        ["validation.spot.deviceId.generateFailed"] = "Не вдалося згенерувати унікальний Device ID для симульованого місця.",
        ["validation.command.type.invalid"] = "Вказано некоректний тип команди для пристрою.",
        ["validation.command.thresholds.required"] = "Для цієї команди потрібно вказати обидва порогові значення.",
        ["validation.command.thresholds.positive"] = "Порогові значення мають бути більшими за нуль.",
        ["validation.command.thresholds.order"] = "Поріг вільного місця має бути більшим за поріг зайнятості.",
        ["validation.command.realSpotRequired"] = "Команди можна надсилати лише на реальне місце з прив’язаним Device ID.",
        ["errors.parkingLot.notFound"] = "Парковку з ідентифікатором '{0}' не знайдено.",
        ["errors.parkingSpot.notFound"] = "Місце з ідентифікатором '{0}' не знайдено.",
        ["errors.deviceCommands.notConfigured"] = "Канал надсилання команд до пристроїв не налаштовано для цього середовища.",
        ["problem.validation.title"] = "Помилка перевірки даних.",
        ["problem.notFound.title"] = "Запитаний ресурс не знайдено.",
        ["problem.unauthorized.title"] = "Потрібна автентифікація.",
        ["problem.forbidden.title"] = "У вас недостатньо прав для виконання цієї дії.",
    };

    public string this[string key] => ResolveDictionary().TryGetValue(key, out var value)
        ? value
        : English.TryGetValue(key, out var fallback)
            ? fallback
            : key;

    public string Format(string key, params object?[] args)
    {
        return string.Format(CultureInfo.CurrentUICulture, this[key], args);
    }

    private static IReadOnlyDictionary<string, string> ResolveDictionary()
    {
        return CultureInfo.CurrentUICulture.TwoLetterISOLanguageName.Equals("uk", StringComparison.OrdinalIgnoreCase)
            ? Ukrainian
            : English;
    }
}
