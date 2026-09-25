import { useState } from "react";
import { useAppState } from "../../store/useAppState";
import { api } from "../../api/client";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";

// Every proposal here is PENDING - none of it has touched real order/rider
// state yet. Accept/Edit/Reject are the only three actions that can change
// that, matching the backend's approval boundary in routers/proposals.py.
export default function DispatcherPanel() {
  const { state, dispatch } = useAppState();
  const [editingId, setEditingId] = useState(null);
  const [editedRiderId, setEditedRiderId] = useState("");
  const [error, setError] = useState(null);

  const pending = Object.values(state.proposals).filter((p) => p.status === "pending");
  const activeRiders = Object.values(state.riders).filter((r) => r.status === "active");

  async function refreshRelated() {
    const [riders, orders] = await Promise.all([api.getRiders(), api.getOrders()]);
    dispatch({ type: "SET_RIDERS", payload: riders });
    dispatch({ type: "SET_ORDERS", payload: orders });
  }

  async function handleAccept(proposal, overrideRiderId) {
    setError(null);
    try {
      const payload =
        overrideRiderId !== undefined
          ? { final_payload: { ...proposal.proposed_payload, suggested_rider_id: overrideRiderId || null } }
          : {};
      const updated = await api.acceptProposal(proposal.id, payload);
      dispatch({ type: "UPSERT_PROPOSAL", payload: updated });
      setEditingId(null);
      await refreshRelated();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleReject(proposal) {
    setError(null);
    try {
      const updated = await api.rejectProposal(proposal.id);
      dispatch({ type: "UPSERT_PROPOSAL", payload: updated });
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <Panel
      title="Pending approvals"
      accent="var(--color-accent)"
      badge={
        pending.length > 0 && <StatusBadge label={pending.length} color="var(--color-accent)" pulse />
      }
    >
      {error && <p className="text-xs mb-2" style={{ color: "var(--color-status-broken)" }}>{error}</p>}
      {pending.length === 0 ? (
        <p className="text-xs text-[var(--color-text-muted)]">Nothing waiting on your decision.</p>
      ) : (
        <ul className="space-y-3">
          {pending.map((p) => (
            <li
              key={p.id}
              className="text-xs p-2 rounded"
              style={{ background: "var(--color-surface-raised)", border: "1px solid var(--color-border)" }}
            >
              <div className="font-mono">
                #{(p.target_order_id || "").slice(0, 8)} →{" "}
                {p.proposed_payload.suggested_rider_id ? (
                  <span style={{ color: "var(--color-accent)" }}>
                    #{p.proposed_payload.suggested_rider_id.slice(0, 8)}
                  </span>
                ) : (
                  <span style={{ color: "var(--color-status-unassigned)" }}>no eligible rider</span>
                )}
              </div>
              <div className="text-[var(--color-text-muted)] mt-1">{p.reason}</div>

              {editingId === p.id ? (
                <div className="mt-2 flex items-center gap-2">
                  <select
                    className="text-xs p-1 rounded flex-1 bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)]"
                    value={editedRiderId}
                    onChange={(e) => setEditedRiderId(e.target.value)}
                  >
                    <option value="">Leave unassigned</option>
                    {activeRiders.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({(r.capacity_weight - r.current_load).toFixed(1)} kg free)
                      </option>
                    ))}
                  </select>
                  <button
                    className="px-2 py-1 rounded text-[var(--color-bg)] font-medium"
                    style={{ background: "var(--color-accent)" }}
                    onClick={() => handleAccept(p, editedRiderId)}
                  >
                    Confirm
                  </button>
                </div>
              ) : (
                <div className="mt-2 flex gap-2">
                  <button
                    className="px-2 py-1 rounded text-[var(--color-bg)] font-medium"
                    style={{ background: "var(--color-status-active)" }}
                    onClick={() => handleAccept(p)}
                  >
                    Accept
                  </button>
                  <button
                    className="px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text)]"
                    onClick={() => {
                      setEditingId(p.id);
                      setEditedRiderId(p.proposed_payload.suggested_rider_id || "");
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="px-2 py-1 rounded text-[var(--color-bg)] font-medium"
                    style={{ background: "var(--color-status-broken)" }}
                    onClick={() => handleReject(p)}
                  >
                    Reject
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
