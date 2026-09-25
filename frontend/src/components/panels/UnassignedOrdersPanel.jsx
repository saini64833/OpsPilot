import { useAppState } from "../../store/useAppState";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";
import { ORDER_STATUS_COLOR, ORDER_STATUS_LABEL } from "../../lib/statusColors";

export default function UnassignedOrdersPanel() {
  const { state } = useAppState();
  const unassigned = Object.values(state.orders).filter(
    (o) => o.status === "UNASSIGNED" || o.status === "UNPLACED"
  );

  return (
    <Panel
      title="Unassigned orders"
      accent="var(--color-status-unassigned)"
      badge={
        unassigned.length > 0 && (
          <StatusBadge label={unassigned.length} color="var(--color-status-unassigned)" pulse />
        )
      }
    >
      {unassigned.length === 0 ? (
        <p className="text-xs text-[var(--color-text-muted)]">Nothing waiting on placement.</p>
      ) : (
        <ul className="space-y-2">
          {unassigned.map((o) => {
            const color = ORDER_STATUS_COLOR[o.status];
            return (
              <li key={o.id} className="text-xs pl-3" style={{ borderLeft: `2px solid ${color}` }}>
                <div className="flex items-center justify-between font-mono text-[var(--color-text)]">
                  <span>#{o.id.slice(0, 8)}</span>
                  <span style={{ color }}>{ORDER_STATUS_LABEL[o.status]}</span>
                </div>
                <div className="text-[var(--color-text-muted)] mt-0.5">
                  {o.status === "UNPLACED"
                    ? `Raw OCR: "${o.raw_ocr_text || "none"}"`
                    : `${o.pickup_label || "pickup"} → ${o.delivery_address || "no address yet"}`}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
