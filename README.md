# Smart Parking

Кодова база курсової роботи за напрямом розробки IoT-орієнтованих веб-систем для моніторингу міського середовища.

Проєкт демонструє систему контролю зайнятості паркувальних місць у реальному часі. Рішення поєднує фізичний IoT-вузол на базі ESP32 та ультразвукового датчика HC-SR04, хмарний прийом телеметрії через Azure IoT Hub, серверну обробку даних і клієнтський веб-застосунок з інтерактивною картою парковок.

## Мета роботи

Метою роботи є розроблення прототипу smart parking системи, яка дозволяє:

- отримувати вимірювання від фізичного IoT-пристрою;
- визначати стан окремого паркомісця за відстанню до об'єкта;
- зберігати історію телеметрії;
- показувати парковки та пристрої на карті;
- відображати кількість вільних і зайнятих місць;
- керувати парковками, паркомісцями та прив'язкою пристроїв через адміністративний інтерфейс.

## Основні можливості

- Вхід користувача через зовнішній провайдер автентифікації.
- Перегляд міських парковок на інтерактивній карті.
- Відображення поточного стану паркомісць: вільне або зайняте.
- Перегляд деталей вибраної парковки та списку її місць.
- Оновлення даних у реальному часі через SignalR.
- Побудова маршруту до вибраної парковки.
- Адміністративне створення, редагування та видалення парковок.
- Додавання реальних і симульованих паркомісць.
- Прив'язування фізичного `DeviceId` до конкретного місця.
- Перегляд виявлених, але ще не прив'язаних пристроїв.
- Надсилання команд на фізичний IoT-вузол: `ping`, `measureNow`, `setThresholds`, `reboot`.
- Підтримка української та англійської мов інтерфейсу.

## Архітектура

```text
ESP32 + HC-SR04
      |
      | MQTT over TLS
      v
Azure IoT Hub
      |
      | Event Hubs-compatible stream
      v
Worker service
      |
      v
SQL Server / LocalDB
      ^
      |
ASP.NET Core Web API + SignalR
      ^
      |
React + TypeScript frontend
```

Система працює у гібридному режимі: фізичний пристрій може надсилати реальні вимірювання, а частина паркомісць може оновлюватися симулятором для демонстрації поведінки міської парковки.

## Технології

### IoT-вузол

- ESP32-WROOM-32.
- Ультразвуковий датчик HC-SR04.
- Arduino IDE / Arduino sketch.
- MQTT over TLS.
- Azure IoT Hub.

### Серверна частина

- .NET 9.
- ASP.NET Core Web API.
- Entity Framework Core.
- SQL Server / LocalDB.
- Azure Event Hubs SDK.
- SignalR.
- Auth0 JWT Bearer authentication.

### Клієнтська частина

- React.
- TypeScript.
- Vite.
- Material UI.
- Leaflet.
- OpenStreetMap.
- Auth0 React SDK.
- SignalR client.

## Структура репозиторію

```text
.
├── backend/
│   ├── src/Web/              # ASP.NET Core API та SignalR hub
│   ├── src/Worker/           # Обробник телеметрії з IoT Hub / Event Hubs
│   ├── src/Application/      # Прикладна логіка
│   ├── src/Domain/           # Доменна модель
│   ├── src/Infrastructure/   # EF Core, SQL Server, зовнішні сервіси
│   └── tests/                # Тести серверної частини
├── frontend/                 # React + TypeScript клієнтський застосунок
├── sketch_dec15a/            # Arduino sketch для ESP32
└── docs/                     # Допоміжна документація та плани
```

## Запуск локально

### Передумови

- .NET SDK 9.0.
- SQL Server або LocalDB.
- Node.js 20.19+ або 22.12+.
- npm.
- За потреби: Azure IoT Hub для роботи з фізичним пристроєм.

### 1. База даних

```powershell
cd backend
dotnet ef database update --project .\src\Infrastructure --startup-project .\src\Web
```

За замовчуванням використовується LocalDB:

```json
"DefaultConnection": "Server=(localdb)\\mssqllocaldb;Database=Masters.DefaultDb;Trusted_Connection=True;MultipleActiveResultSets=true"
```

### 2. Web API

```powershell
cd backend\src\Web
dotnet run
```

Локальні адреси API:

- `https://localhost:5001`
- `http://localhost:5000`

### 3. Worker

```powershell
cd backend\src\Worker
dotnet run
```

Worker може працювати у двох режимах:

- симуляція паркомісць для демонстрації;
- читання реальної телеметрії з Azure IoT Hub через Event Hubs-compatible endpoint.

### 4. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Клієнтський застосунок буде доступний за адресою:

```text
http://localhost:5173
```

## Налаштування середовища

Приклад змінних для клієнтської частини наведено у файлі:

```text
frontend/.env.example
```

Основні параметри:

- `VITE_API_BASE_URL` - адреса Web API;
- `VITE_AUTH0_DOMAIN` - домен Auth0 tenant;
- `VITE_AUTH0_CLIENT_ID` - ідентифікатор SPA-застосунку;
- `VITE_AUTH0_AUDIENCE` - audience API;
- `VITE_AUTH0_ROLE_CLAIM` - namespaced claim для ролей.

Основні параметри серверної частини:

- `ConnectionStrings:DefaultConnection`;
- `Auth0:Domain`;
- `Auth0:Audience`;
- `Auth0:RolesClaimType`;
- `RealtimeEventHub:Enabled`;
- `RealtimeEventHub:ConnectionString`;
- `RealtimeEventHub:EventHubName`;
- `IoTHubDeviceCommands:Enabled`;
- `IoTHubDeviceCommands:ConnectionString`.

## IoT-пристрій

Arduino sketch розміщено у каталозі:

```text
sketch_dec15a/
```

Фізичний вузол виконує такі дії:

- підключається до Wi-Fi;
- синхронізує час через NTP;
- формує SAS token для Azure IoT Hub;
- підключається до IoT Hub через MQTT over TLS;
- зчитує відстань з HC-SR04;
- визначає стан місця за порогами `occupiedBelowCm` та `freeAboveCm`;
- надсилає JSON-телеметрію з `deviceId`, часом, відстанню, станом та координатами;
- приймає direct method команди з Azure IoT Hub.

Приклад телеметрії:

```json
{
  "deviceId": "ps-uzh-lot1-spot001",
  "ts": 1735689600,
  "distanceCm": 37.4,
  "occupied": true,
  "latitude": 49.8387,
  "longitude": 23.9944
}
```

## Перевірка

Серверна частина:

```powershell
dotnet build backend/Masters.Api.sln -tl /p:UseArtifactsOutput=false
```

Клієнтська частина:

```powershell
cd frontend
npm run build
```

## Демонстраційний сценарій

1. Запустити SQL Server / LocalDB.
2. Застосувати міграції бази даних.
3. Запустити Web API.
4. Запустити Worker.
5. Запустити frontend.
6. Увійти в систему.
7. Відкрити карту парковок.
8. Переглянути стан місць у вибраній парковці.
9. В адміністративному режимі додати або змінити парковку чи паркомісце.
10. Передати вимірювання з фізичного пристрою або дочекатися симуляції.
11. Перевірити оновлення карти та деталей без перезавантаження сторінки.

## Безпека

Перед публікацією репозиторію у відкритий доступ потрібно переконатися, що в історії комітів немає реальних секретів:

- Wi-Fi SSID/password;
- Azure IoT Hub device keys;
- Azure IoT Hub service connection strings;
- Auth0 client secrets;
- production database connection strings.

Якщо секрет уже потрапив у Git-історію, його потрібно вважати скомпрометованим і перевипустити у відповідному сервісі.

## Статус

Проєкт є навчальним прототипом, створеним у межах курсової роботи. Він призначений для демонстрації повного циклу роботи smart parking системи: від фізичного вимірювання на IoT-вузлі до відображення актуального стану паркомісць у веб-інтерфейсі.
