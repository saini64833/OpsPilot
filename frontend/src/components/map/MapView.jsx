import { MapContainer, TileLayer } from "react-leaflet";
import RiderMarker from "./RiderMarker";
import OrderMarker from "./OrderMarker";
import { useAppState } from "../../store/useAppState";

// Center matches the seed data (Delhi) - swap if you seed a different city.
const DEFAULT_CENTER = [28.6139, 77.209];

// CARTO's raster basemaps now require a free API key (as of Aug 2026) -
// without one every tile is watermarked "API KEY REQUIRED". Get one free at
// https://carto.com/basemaps/apikey/ and put it in frontend/.env as
// VITE_CARTO_API_KEY. With no key set, we fall back to plain OpenStreetMap
// tiles so the map still works, just without the dark styling.
const CARTO_KEY = import.meta.env.VITE_CARTO_API_KEY;

const TILE_URL = CARTO_KEY
  ? `https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png?key=${CARTO_KEY}`
  : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const TILE_ATTRIBUTION = CARTO_KEY
  ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export default function MapView() {
  const { state } = useAppState();
  const riders = Object.values(state.riders);
  const orders = Object.values(state.orders);

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={13}
      className="h-full w-full z-0"
      style={{ background: "var(--color-bg)" }}
    >
      <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />
      {riders.map((rider) => (
        <RiderMarker key={rider.id} rider={rider} />
      ))}
      {orders.map((order) => (
        <OrderMarker key={order.id} order={order} />
      ))}
    </MapContainer>
  );
}
