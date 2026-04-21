type OsrmRouteResponse = {
  code: string;
  routes?: Array<{
    distance: number;
    duration: number;
    geometry: {
      type: "LineString";
      coordinates: [number, number][];
    };
  }>;
};

export type RouteSummary = {
  distanceMeters: number;
  durationSeconds: number;
  coordinates: [number, number][];
};

const OSRM_BASE_URL = "https://router.project-osrm.org";

export async function fetchDrivingRoute(
  origin: [number, number],
  destination: [number, number],
): Promise<RouteSummary> {
  const coordinates = `${origin[1]},${origin[0]};${destination[1]},${destination[0]}`;
  const url = `${OSRM_BASE_URL}/route/v1/driving/${coordinates}?overview=full&geometries=geojson`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Routing request failed with status ${response.status}.`);
  }

  const payload = (await response.json()) as OsrmRouteResponse;

  if (payload.code !== "Ok" || !payload.routes?.length) {
    throw new Error("No route found.");
  }

  const route = payload.routes[0];

  return {
    distanceMeters: route.distance,
    durationSeconds: route.duration,
    coordinates: route.geometry.coordinates.map(([longitude, latitude]) => [latitude, longitude]),
  };
}
