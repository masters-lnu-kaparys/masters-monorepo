# Masters.Api - Parking Monitoring

Monorepo backend for IoT parking monitoring:
- `src/Web` - HTTP API (`/api/*`) + SignalR hub (`/hubs/parking`)
- `src/Worker` - Azure IoT Hub Event Hub consumer that persists telemetry to SQL Server
- `src/Infrastructure` - EF Core + SQL Server storage
- `../frontend` - React + Vite + MUI dashboard

## Prerequisites

- .NET SDK `9.0.100`
- SQL Server / LocalDB (default: `(localdb)\\mssqllocaldb`)
- Node.js `20.19+` or `22.12+` for Vite 7 (Node 21 may work with warnings)

## Build

```bash
cd .\backend
dotnet build Masters.Api.sln -tl
```

## Database Setup

Apply migrations before first run:

```bash
cd .\backend
dotnet ef database update --project .\src\Infrastructure --startup-project .\src\Web
```

## Run Backend API

```bash
cd .\backend\src\Web
dotnet run
```

API base URL (development): `http://localhost:5000` (also `https://localhost:5001`)

## Run Worker

```bash
cd .\backend\src\Worker
dotnet run
```

Worker config file: `src/Worker/appsettings.json`

Important settings:
- `ConnectionStrings:Masters.ApiDb`
- `RealtimeEventHub:Enabled`
- `RealtimeEventHub:ConnectionString`
- `RealtimeEventHub:EventHubName`
- `RealtimeEventHub:ConsumerGroup`

Set `RealtimeEventHub:Enabled` to `true` to consume IoT Hub telemetry.

Expected telemetry payload:

```json
{
  "deviceId": "ps-uzh-lot1-spot001",
  "ts": 1735689600,
  "distanceCm": 37.4,
  "occupied": true
}
```

## Run Frontend Dashboard

```bash
cd .\frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`

Optional env var for API target:
- `VITE_API_BASE_URL` (default: `http://localhost:5000`)

## API Endpoints

- `GET /api/dashboard/summary`
- `GET /api/spots`
- `GET /api/spots/{spotId}/history?fromUtc=&toUtc=&maxPoints=`
- `SignalR hub: /hubs/parking` (`dashboardSnapshot` event)

## Tests

Run backend tests:

```bash
cd .\backend
dotnet test Masters.Api.sln -tl
```

Run frontend production build check:

```bash
cd .\frontend
npm run build
```
