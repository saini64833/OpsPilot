import { Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { ORDER_STATUS_COLOR, ORDER_STATUS_LABEL } from "../../lib/statusColors";

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
export default function OrderMarker({ order }) {
  const color = ORDER_STATUS_COLOR[order.status] || "#64748b";
  const hasPickup = order.pickup_lat != null && order.pickup_lng != null;
  const hasDelivery = order.delivery_lat != null && order.delivery_lng != null;

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
    </>
  );
}
