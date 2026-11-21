# Серверна частина системи моніторингу паркомісць

- `src/Web` надає API, надсилає оновлення карти через SignalR і передає команди пристроям.
- `src/Worker` приймає телеметрію з Azure IoT Hub та генерує дані для симульованих паркомісць.
- `src/Infrastructure` містить доступ до SQL Server, міграції EF Core і клієнт Azure IoT Hub.

## Збірка та запуск

Потрібні .NET SDK 9, утиліта `dotnet-ef` і SQL Server або LocalDB. У режимі розроблення типовий рядок з’єднання вказує на LocalDB. Для іншої локальної бази задайте `ConnectionStrings:DefaultConnection`.

Команди виконуються з кореня репозиторію.

```powershell
dotnet build backend/Masters.Api.sln -tl /p:UseArtifactsOutput=false
dotnet ef database update --project backend/src/Infrastructure --startup-project backend/src/Web
```

Запустіть API й фонову службу в окремих терміналах.

```powershell
dotnet run --project backend/src/Web
dotnet run --project backend/src/Worker
```

API доступний за адресою `https://localhost:5001`. Документація OpenAPI відкривається за шляхом `/api`. [Запуск вебзастосунку](../frontend/README.md)

## Вхід

У Auth0 створіть застосунок для вебклієнта й API з аудиторією `https://masters.api`. Для локального клієнта додайте `http://localhost:5173/auth/callback` до дозволених адрес зворотного виклику, а `http://localhost:5173` до дозволених адрес виходу й джерел вебзапитів.

Увімкніть RBAC, створіть ролі `User` і `Admin` та підключіть дію після входу. Для дії додайте залежність `auth0` і задайте секрети `domain`, `clientId`, `clientSecret` та `defaultUserRoleId`. Дія надає новим обліковим записам роль `User` і додає ролі до токенів у полі `https://masters.api/roles`. [Шаблон дії Auth0](../docs/auth0/assign-default-user-role-post-login.js)

У налаштуваннях API задайте `Auth0:Domain`, `Auth0:Audience` і `Auth0:RolesClaimType`. Значення для клієнта наведено в його шаблоні середовища. [Шаблон змінних вебзастосунку](../frontend/.env.example)

## Телеметрія й команди

Для приймання показів від ESP32 задайте у фоновій службі `RealtimeEventHub:Enabled`, `RealtimeEventHub:ConnectionString`, `RealtimeEventHub:EventHubName` і `RealtimeEventHub:ConsumerGroup`. Симуляцію налаштовують через `Simulation:Enabled` та `Simulation:UpdateIntervalSeconds`.

Веб-API використовує `TelemetryFreshness:MaxAgeSeconds=330` для всіх місць. Це покриває максимальну паузу адаптивної прошивки 300 с і залишає 30 с на доставку.

Повідомлення від пристрою містить `deviceId`, `ts`, `distanceCm` і `occupied`. За наявності координат фоновий процес може прив’язати новий пристрій до найближчої парковки в радіусі `DeviceBinding:MaxParkingLotDistanceKm`.

Команди `ping`, `measureNow`, `setThresholds` і `reboot` надходять на пристрій через Azure IoT Hub. Для них задайте на сервері `IoTHubDeviceCommands:Enabled=true` і `IoTHubDeviceCommands:ConnectionString` із правом виклику методів пристроїв. [Налаштування прошивки](../sketch_dec15a/README.md)

## Тести

```powershell
dotnet test backend/Masters.Api.sln -tl /p:UseArtifactsOutput=false
```
