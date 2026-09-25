import { useAppState } from "../../store/useAppState";
import Panel from "../ui/Panel";

const ACTOR_COLOR = {
  system: "var(--color-status-offline)",
  llm: "var(--color-status-unplaced)",
  dispatcher: "var(--color-accent)",
};

export default function AuditLogPanel() {
  const { state } = useAppState();
  const entries = [...state.auditLog].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  return (
    <Panel title="Audit log" accent="var(--color-text-muted)">
      {entries.length === 0 ? (
        <p className="text-xs text-[var(--color-text-muted)]">No activity yet.</p>
      ) : (
        <ul className="space-y-1.5 max-h-64 overflow-y-auto">
          {entries.map((e) => (
            <li key={e.id} className="text-xs font-mono flex items-start gap-2">
              <span className="text-[var(--color-text-muted)] shrink-0">
                {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "--:--:--"}
              </span>
              <span className="shrink-0" style={{ color: ACTOR_COLOR[e.actor] || "var(--color-text)" }}>
                {e.actor}
              </span>
              <span className="text-[var(--color-text)]">{e.action}</span>
              <span className="text-[var(--color-text-muted)]">
                {e.entity_type}#{(e.entity_id || "").slice(0, 6)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
