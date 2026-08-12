/** Utilidades de polígono de parcela (Leaflet lat/lon ↔ GeoJSON). */

export type LatLngTuple = [number, number]; // [lat, lon]

export type GeoJsonPolygon = {
  type: "Polygon";
  coordinates: number[][][]; // [[[lon, lat], ...]]
};

export function ringFromGeoJson(poly?: GeoJsonPolygon | null): LatLngTuple[] {
  if (!poly?.coordinates?.[0]?.length) return [];
  const ring = poly.coordinates[0].map(
    ([lon, lat]) => [lat, lon] as LatLngTuple,
  );
  // Quitar vértice de cierre duplicado para edición/dibujo
  if (
    ring.length >= 2 &&
    ring[0][0] === ring[ring.length - 1][0] &&
    ring[0][1] === ring[ring.length - 1][1]
  ) {
    return ring.slice(0, -1);
  }
  return ring;
}

export function geoJsonFromRing(ring: LatLngTuple[]): GeoJsonPolygon | null {
  if (ring.length < 3) return null;
  const coords = ring.map(([lat, lon]) => [lon, lat]);
  const first = coords[0];
  const last = coords[coords.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    coords.push([...first]);
  }
  return { type: "Polygon", coordinates: [coords] };
}

export function centroidFromRing(
  ring: LatLngTuple[],
): { lat: number; lon: number } | null {
  if (!ring.length) return null;
  const lat = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const lon = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return { lat, lon };
}

/** Bounds Leaflet [[south, west], [north, east]]. */
export function boundsFromRing(
  ring: LatLngTuple[],
): [[number, number], [number, number]] | null {
  if (!ring.length) return null;
  let minLat = ring[0][0];
  let maxLat = ring[0][0];
  let minLon = ring[0][1];
  let maxLon = ring[0][1];
  for (const [lat, lon] of ring) {
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
  }
  if (minLat === maxLat) {
    minLat -= 0.0005;
    maxLat += 0.0005;
  }
  if (minLon === maxLon) {
    minLon -= 0.0005;
    maxLon += 0.0005;
  }
  return [
    [minLat, minLon],
    [maxLat, maxLon],
  ];
}

/** Distancia aproximada en metros entre dos puntos lat/lon. */
export function distanceMeters(a: LatLngTuple, b: LatLngTuple): number {
  const mLat = 111_320;
  const mLon = 111_320 * Math.cos((a[0] * Math.PI) / 180);
  const dy = (a[0] - b[0]) * mLat;
  const dx = (a[1] - b[1]) * mLon;
  return Math.hypot(dx, dy);
}

/** Área aproximada en hectáreas (shoelace equirectangular). */
export function areaHaFromRing(ring: LatLngTuple[]): number | null {
  if (ring.length < 3) return null;
  const lat0 = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const mLat = 111_320;
  const mLon = 111_320 * Math.cos((lat0 * Math.PI) / 180);
  const xy = ring.map(([lat, lon]) => [lon * mLon, lat * mLat] as const);
  let area = 0;
  for (let i = 0; i < xy.length; i++) {
    const [x1, y1] = xy[i];
    const [x2, y2] = xy[(i + 1) % xy.length];
    area += x1 * y2 - x2 * y1;
  }
  return Math.round((Math.abs(area) / 2 / 10_000) * 10000) / 10000;
}
