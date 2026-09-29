import { useState, useEffect, useRef } from "react";
import { Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { ORDER_STATUS_COLOR, ORDER_STATUS_LABEL } from "../../lib/statusColors";
import { api } from "../../api/client";
import { useAppState } from "../../store/useAppState"; 

function getDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; 
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; 
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
  const riderIsActive = rider?.status === "active";

  const color = ORDER_STATUS_COLOR[order.status] || "#64748b";
  const hasPickup = order.pickup_lat != null && order.pickup_lng != null;
  const hasDelivery = order.delivery_lat != null && order.delivery_lng != null;

  const isRoutable =
    Boolean(order.rider_id) &&
    riderIsActive &&
    ["ASSIGNED", "IN_TRANSIT"].includes(order.status);

  const riderBrokenDown = Boolean(order.rider_id) && rider && !riderIsActive;

  const [route, setRoute] = useState(null);
  const [routeError, setRouteError] = useState(null);
  const [speed, setSpeed] = useState(null); 

  const prevRiderPos = useRef(null);
  const prevTime = useRef(null);

  useEffect(() => {
    prevRiderPos.current = null;
    prevTime.current = null;
    setSpeed(null);
  }, [order.rider_id]);

  // 1. Calculate live speed (km/h)
  useEffect(() => {
    if (!riderIsActive) {
      setSpeed(null);
      prevRiderPos.current = null;
      prevTime.current = null;
      return;
    }

    if (rider) {
      const now = Date.now();
      if (prevRiderPos.current && prevTime.current) {
        const distKm = getDistance(
          prevRiderPos.current.lat,
          prevRiderPos.current.lng,
          rider.lat,
          rider.lng,
        );
        const timeHours = (now - prevTime.current) / (1000 * 60 * 60);
        if (timeHours > 0) {
          setSpeed(distKm / timeHours);
        }
      }
      prevRiderPos.current = { lat: rider.lat, lng: rider.lng };
      prevTime.current = now;
    }
  }, [rider?.lat, rider?.lng, riderIsActive]);

  // 2. Fetch route ONLY when order status changes to prevent API spam
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
  }, [isRoutable, order.status, order.id]); 

  const routeLabel =
    order.status === "IN_TRANSIT" ? "Rider → Delivery" : "Rider → Pickup";

  // 3. Dynamically calculate distance and time ticking down
  let liveRemainingKm = 0;
  let liveRemainingMin = 0;

  if (isRoutable && rider) {
    const destLat = order.status === "ASSIGNED" ? order.pickup_lat : order.delivery_lat;
    const destLng = order.status === "ASSIGNED" ? order.pickup_lng : order.delivery_lng;
    
    // 1.25 multiplier accounts for road curves instead of a straight line
    liveRemainingKm = getDistance(rider.lat, rider.lng, destLat, destLng) * 1.25;
    
    // Use actual moving speed, or fallback to 40km/h average if temporarily stopped
    const currentSpeed = speed > 5 ? speed : 40; 
    liveRemainingMin = (liveRemainingKm / currentSpeed) * 60;
  }

  return (
    <>
      {hasPickup && (
        <Marker
          position={[order.pickup_lat, order.pickup_lng]}
          icon={pinIcon(color, "circle")}
        >
          <Popup>
            <div className="font-sans text-sm min-w-40">
              <div className="font-semibold font-mono text-xs opacity-70">
                #{order.id.slice(0, 8)}
              </div>
              <div className="mt-1">{order.pickup_label || "Pickup point"}</div>
              <div className="text-xs mt-1" style={{ color }}>
                {ORDER_STATUS_LABEL[order.status] || order.status}
              </div>

              <div className="mt-2 pt-2 border-t border-black/10">
                {isRoutable ? (
                  <>
                    <div
                      className="text-xs font-bold mb-1"
                      style={{ color: "var(--color-accent, #2dd4bf)" }}
                    >
                      Live Tracking ({routeLabel})
                    </div>
                    {routeError && (
                      <div
                        className="text-xs mt-1"
                        style={{ color: "#f87171" }}
                      >
                        {routeError}
                      </div>
                    )}
                    {route && (
                      <div className="flex flex-col gap-1 text-xs mt-1 opacity-90">
                        <div className="flex justify-between">
                          <span className="opacity-70">Speed:</span>
                          <span className="font-mono">
                            {speed !== null ? `${Math.round(speed)} km/h` : "0 km/h"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="opacity-70">Remaining Dist:</span>
                          <span className="font-mono">
                            {liveRemainingKm.toFixed(2)} km
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="opacity-70">Remaining Time:</span>
                          <span className="font-mono">
                            {Math.ceil(liveRemainingMin)} min
                          </span>
                        </div>
                      </div>
                    )}
                  </>
                ) : riderBrokenDown ? (
                  <div className="text-xs" style={{ color: "#f87171" }}>
                    Rider{" "}
                    {rider.status === "offline" ? "offline" : "broken down"} —
                    tracking paused, awaiting reassignment
                  </div>
                ) : order.status === "DELIVERED" ? (
                  // FIX: Explicitly handle delivered status
                  <div className="text-xs opacity-60">
                    Order successfully delivered
                  </div>
                ) : order.status === "FAILED" ? (
                  // FIX: Explicitly handle failed status
                  <div className="text-xs" style={{ color: "#f87171" }}>
                    Delivery failed
                  </div>
                ) : (
                  <div className="text-xs opacity-60">
                    Metrics available once assigned
                  </div>
                )}
              </div>
            </div>
          </Popup>
        </Marker>
      )}

      {hasDelivery && (
        <Marker
          position={[order.delivery_lat, order.delivery_lng]}
          icon={pinIcon(color, "square")}
        >
          <Popup>
            <div className="font-sans text-sm min-w-40">
              <div className="font-semibold font-mono text-xs opacity-70">
                #{order.id.slice(0, 8)}
              </div>
              <div className="mt-1">
                {order.delivery_address || "Address pending"}
              </div>
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