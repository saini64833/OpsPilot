import { useState } from "react";
import { useAppState } from "../../store/useAppState";
import Panel from "../ui/Panel";

const ACTOR_COLOR = {
  system: "var(--color-status-offline)",
  llm: "var(--color-status-unplaced)",
  dispatcher: "var(--color-accent)",
};

export default function AuditLogPanel() {
  const { state } = useAppState();
  const [openId, setOpenId] = useState(null);
  const entries = [...state.auditLog].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  return (
    <Panel title="Audit log" accent="var(--color-text-muted)">
      {entries.length === 0 ? (
        <p className="text-xs text-[var(--color-text-muted)]">No activity yet.</p>
      ) : (
        <ul className="space-y-1.5 max-h-64 overflow-y-auto">
          {entries.map((e) => {
            const hasDetail = e.notes || e.raw_payload || e.before_state || e.after_state;
            const isOpen = openId === e.id;
            return (
              <li key={e.id} className="text-xs font-mono">
                <div
                  className={`flex items-start gap-2 ${hasDetail ? "cursor-pointer" : ""}`}
                  onClick={() => hasDetail && setOpenId(isOpen ? null : e.id)}
                >
                  <span className="text-[var(--color-text-muted)] shrink-0">
                    {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "--:--:--"}
                  </span>
                  <span className="shrink-0" style={{ color: ACTOR_COLOR[e.actor] || "var(--color-text)" }}>
                    {e.actor}
                  </span>
                  <span
                    className="text-[var(--color-text)]"
                    style={e.action.includes("failed") || e.action.includes("error") ? { color: "var(--color-status-broken)" } : undefined}
                  >
                    {e.action}
                  </span>
                  <span className="text-[var(--color-text-muted)]">
                    {e.entity_type}#{(e.entity_id || "").slice(0, 6)}
                  </span>
                  {hasDetail && (
                    <span className="text-[var(--color-text-muted)] ml-auto shrink-0">{isOpen ? "▲" : "▼"}</span>
                  )}
                </div>
                {isOpen && hasDetail && (
                  <div
                    className="mt-1 ml-4 p-2 rounded whitespace-pre-wrap break-words"
                    style={{ background: "var(--color-surface-raised)", border: "1px solid var(--color-border)" }}
                  >
                    {e.notes && (
                      <div style={{ color: "var(--color-status-broken)" }}>{e.notes}</div>
                    )}
                    {e.raw_payload && (
                      <pre className="text-[var(--color-text-muted)] mt-1">
                        {JSON.stringify(e.raw_payload, null, 2)}
                      </pre>
                    )}
                    {(e.before_state || e.after_state) && (
                      <div className="text-[var(--color-text-muted)] mt-1">
                        {e.before_state && <span>before: {JSON.stringify(e.before_state)}</span>}
                        {e.before_state && e.after_state && " → "}
                        {e.after_state && <span>after: {JSON.stringify(e.after_state)}</span>}
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}