import "leaflet/dist/leaflet.css"; 
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import RiderMarker from "./RiderMarker";
import OrderMarker from "./OrderMarker";
import { useAppState } from "../../store/useAppState";

const DEFAULT_CENTER = [28.6139, 77.209];
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
  
  // FIX: Filter out delivered orders so they are removed from the map
  const activeOrders = Object.values(state.orders).filter(
    (order) => order.status !== "delivered"
  );

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={13}
      className="h-full w-full z-0"
      style={{ background: "var(--color-bg)" }}
    >
      <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />
      
      {riders.map((rider) => (
        <div key={rider.id}>
          <RiderMarker rider={rider} />
          
          {rider.status === "active" && rider.route && (
            <Polyline
              positions={rider.route.map((coord) => [coord[1], coord[0]])}
              color="#3b82f6"
              weight={4}
              dashArray="6, 8"
              opacity={0.7}
            />
          )}
        </div>
      ))}
      
      {/* Render only the active (non-delivered) orders */}
      {activeOrders.map((order) => (
        <OrderMarker key={order.id} order={order} />
      ))}
    </MapContainer>
  );
}