import { useState, useEffect, useRef } from "react";
import { Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { ORDER_STATUS_COLOR, ORDER_STATUS_LABEL } from "../../lib/statusColors";
import { api } from "../../api/client";
import { useAppState } from "../../store/useAppState"; // Added to track live rider data

// Helper to calculate distance for live speed
function getDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Radius of Earth in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in km
}

function pinIcon(color, shape) {
  const style =
    shape === "square"
      ? `width:12px;height:12px;background:${color};border:2px solid #0a0e1a;transform:rotate(45deg);`
      : `width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #0a0e1a;`;
  return L.divIcon({
    className: "",
    html: `<div style="${style}box-shadow:0 0 6px 1px ${color}aa;"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export default function OrderMarker({ order }) {
  const { state } = useAppState();
  const rider = order.rider_id ? state.riders[order.rider_id] : null;

  const color = ORDER_STATUS_COLOR[order.status] || "#64748b";
  const hasPickup = order.pickup_lat != null && order.pickup_lng != null;
  const hasDelivery = order.delivery_lat != null && order.delivery_lng != null;
  const isRoutable = Boolean(order.rider_id) && ["ASSIGNED", "IN_TRANSIT"].includes(order.status);

  const [route, setRoute] = useState(null);
  const [routeError, setRouteError] = useState(null);
  const [speed, setSpeed] = useState(0);

  const prevRiderPos = useRef(null);
  const prevTime = useRef(null);

  // 1. Calculate live speed (km/h) whenever the rider moves
  useEffect(() => {
    if (rider) {
      const now = Date.now();
      if (prevRiderPos.current && prevTime.current) {
        const distKm = getDistance(
          prevRiderPos.current.lat,
          prevRiderPos.current.lng,
          rider.lat,
          rider.lng
        );
        const timeHours = (now - prevTime.current) / (1000 * 60 * 60);
        if (timeHours > 0) {
          setSpeed(distKm / timeHours);
        }
      }
      prevRiderPos.current = { lat: rider.lat, lng: rider.lng };
      prevTime.current = now;
    }
  }, [rider?.lat, rider?.lng]);

  // 2. Fetch remaining route. Updates dynamically as rider.lat/lng changes.
  useEffect(() => {
    let isCancelled = false;

    async function fetchLiveRoute() {
      if (!isRoutable) {
        setRoute(null);
        return;
      }
      try {
        const data = await api.getOrderRoute(order.id);
        if (!isCancelled && data) {
          setRoute({
            positions: data.coordinates.map(([lng, lat]) => [lat, lng]),
            distanceKm: data.distance / 1000,
            durationMin: data.duration / 60,
          });
        }
      } catch (err) {
        if (!isCancelled) setRouteError(err.message);
      }
    }

    fetchLiveRoute();

    return () => {
      isCancelled = true;
    };
  }, [isRoutable, order.status, rider?.lat, rider?.lng]);

  const routeLabel = order.status === "IN_TRANSIT" ? "Rider → Delivery" : "Rider → Pickup";

  return (
    <>
      {hasPickup && (
        <Marker position={[order.pickup_lat, order.pickup_lng]} icon={pinIcon(color, "circle")}>
          <Popup>
            <div className="font-sans text-sm min-w-40">
              <div className="font-semibold font-mono text-xs opacity-70">#{order.id.slice(0, 8)}</div>
              <div className="mt-1">{order.pickup_label || "Pickup point"}</div>
              <div className="text-xs mt-1" style={{ color }}>
                {ORDER_STATUS_LABEL[order.status] || order.status}
              </div>

              <div className="mt-2 pt-2 border-t border-black/10">
                {isRoutable ? (
                  <>
                    <div className="text-xs font-bold mb-1" style={{ color: "var(--color-accent, #2dd4bf)" }}>
                      Live Tracking ({routeLabel})
                    </div>
                    {routeError && (
                      <div className="text-xs mt-1" style={{ color: "#f87171" }}>
                        {routeError}
                      </div>
                    )}
                    {route && (
                      <div className="flex flex-col gap-1 text-xs mt-1 opacity-90">
                        <div className="flex justify-between">
                          <span className="opacity-70">Speed:</span>
                          <span className="font-mono">{Math.round(speed)} km/h</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="opacity-70">Remaining Dist:</span>
                          <span className="font-mono">{route.distanceKm.toFixed(2)} km</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="opacity-70">Remaining Time:</span>
                          <span className="font-mono">{Math.round(route.durationMin)} min</span>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-xs opacity-60">Metrics available once assigned</div>
                )}
              </div>
            </div>
          </Popup>
        </Marker>
      )}

      {hasDelivery && (
        <Marker position={[order.delivery_lat, order.delivery_lng]} icon={pinIcon(color, "square")}>
          <Popup>
            <div className="font-sans text-sm min-w-40">
              <div className="font-semibold font-mono text-xs opacity-70">#{order.id.slice(0, 8)}</div>
              <div className="mt-1">{order.delivery_address || "Address pending"}</div>
              <div className="text-xs mt-1" style={{ color }}>
                {ORDER_STATUS_LABEL[order.status] || order.status}
              </div>
            </div>
          </Popup>
        </Marker>
      )}

      {route && (
        <Polyline
          positions={route.positions}
          pathOptions={{ color, weight: 4, opacity: 0.9 }}
        />
      )}
    </>
  );
}