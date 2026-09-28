import { Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { RIDER_STATUS_COLOR, RIDER_STATUS_LABEL } from "../../lib/statusColors";

function riderIcon(status) {
  const color = RIDER_STATUS_COLOR[status] || RIDER_STATUS_COLOR.active;
  return L.divIcon({
    className: "",
    html: `<div style="
      width:16px;height:16px;border-radius:50%;
      background:${color};
      border:2px solid #0a0e1a;
      box-shadow:0 0 0 2px ${color}55, 0 0 8px 1px ${color}aa;
    "></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

export default function RiderMarker({ rider }) {
  const color = RIDER_STATUS_COLOR[rider.status] || RIDER_STATUS_COLOR.active;
  
  // Check if rider is active and has a route broadcasted from the simulator
  const isActive = rider.status === "active";
  const hasRoute = isActive && rider.route && rider.route.length > 0;

  // Routing APIs send [lng, lat], but Leaflet maps require [lat, lng]
  const pathPositions = hasRoute 
    ? rider.route.map((coord) => [coord[1], coord[0]]) 
    : [];

  return (
    <>
      <Marker position={[rider.lat, rider.lng]} icon={riderIcon(rider.status)}>
        <Popup>
          <div className="font-sans text-sm min-w-36">
            <div className="font-semibold">{rider.name}</div>
            <div className="text-xs mt-1" style={{ color }}>
              {RIDER_STATUS_LABEL[rider.status] || rider.status}
            </div>
            <div className="text-xs font-mono mt-1 opacity-80">
              {rider.current_load} / {rider.capacity_weight} kg
            </div>
          </div>
        </Popup>
      </Marker>

      {/* Renders the Google Maps style path line */}
      {hasRoute && (
        <Polyline 
          positions={pathPositions} 
          pathOptions={{ 
            color: "#3b82f6", // Google Maps-style blue path
            weight: 5, 
            opacity: 0.7 
          }} 
        />
      )}
    </>
  );
}