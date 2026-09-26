import { useState } from "react";
import { Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { ORDER_STATUS_COLOR, ORDER_STATUS_LABEL } from "../../lib/statusColors";
import { api } from "../../api/client";

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

// Pickup = circle, delivery = diamond, dashed line between once both are
// known. Color is the order's status, so an UNASSIGNED or UNPLACED order is
// the most visually loud thing on the map, never the most hidden.
//
// "Go via road" calls the backend's /routes/order/{id} endpoint, which asks
// OSRM for the live route from the assigned rider's CURRENT position to
// wherever the order needs to go next (pickup while ASSIGNED, delivery once
// IN_TRANSIT) - see backend/routers/routes.py. Nothing is cached here, so
// clicking again after the rider moves (or after a breakdown reassigns the
// order to a different rider) redraws the up-to-date route.
export default function OrderMarker({ order }) {
  const color = ORDER_STATUS_COLOR[order.status] || "#64748b";
  const hasPickup = order.pickup_lat != null && order.pickup_lng != null;
  const hasDelivery = order.delivery_lat != null && order.delivery_lng != null;
  const isRoutable = Boolean(order.rider_id) && ["ASSIGNED", "IN_TRANSIT"].includes(order.status);

  const [route, setRoute] = useState(null); // { positions, distanceKm, durationMin }
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState(null);

  async function handleGoViaRoad() {
    setLoadingRoute(true);
    setRouteError(null);
    try {
      const data = await api.getOrderRoute(order.id);
      setRoute({
        // Backend returns GeoJSON [lng, lat]; Leaflet wants [lat, lng].
        positions: data.coordinates.map(([lng, lat]) => [lat, lng]),
        distanceKm: data.distance / 1000,
        durationMin: data.duration / 60,
      });
    } catch (err) {
      setRouteError(err.message);
    } finally {
      setLoadingRoute(false);
    }
  }

  const routeLabel = order.status === "IN_TRANSIT" ? "rider → delivery" : "rider → pickup";

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
                    <button
                      type="button"
                      onClick={handleGoViaRoad}
                      disabled={loadingRoute}
                      className="text-xs font-medium underline disabled:opacity-50"
                      style={{ color: "var(--color-accent, #2dd4bf)" }}
                    >
                      {loadingRoute ? "Routing…" : `Go via road (${routeLabel})`}
                    </button>
                    {routeError && (
                      <div className="text-xs mt-1" style={{ color: "#f87171" }}>
                        {routeError}
                      </div>
                    )}
                    {route && (
                      <div className="text-xs mt-1 opacity-80">
                        {route.distanceKm.toFixed(1)} km · {Math.round(route.durationMin)} min by road
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-xs opacity-60">Route available once a rider is assigned</div>
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
      {hasPickup && hasDelivery && (
        <Polyline
          positions={[
            [order.pickup_lat, order.pickup_lng],
            [order.delivery_lat, order.delivery_lng],
          ]}
          pathOptions={{ color, weight: 2, dashArray: "4 4", opacity: 0.8 }}
        />
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