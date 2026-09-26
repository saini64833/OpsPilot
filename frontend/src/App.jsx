import { useCallback, useEffect, useState } from "react";
import { AppStateProvider, useAppState } from "./store/useAppState";
import { useLiveStream } from "./api/stream";
import { api } from "./api/client";
import MapView from "./components/map/MapView";
import UnassignedOrdersPanel from "./components/panels/UnassignedOrdersPanel";
import DispatcherPanel from "./components/panels/DispatcherPanel";
import AuditLogPanel from "./components/panels/AuditLogPanel";
import NewOrderForm from "./components/forms/NewOrderForm";
import PhotoUploadForm from "./components/forms/PhotoUploadForm";
import Panel from "./components/ui/Panel";
import { RIDER_STATUS_COLOR, RIDER_STATUS_LABEL } from "./lib/statusColors";

function TickerStat({ label, value, color }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="font-mono text-lg leading-none"
        style={{ color: color || "var(--color-text)" }}
      >
        {value}
      </span>
      <span className="text-xs text-text-muted">{label}</span>
    </div>
  );
}

function TopBar({ counts }) {
  return (
    <header
      className="h-14 shrink-0 flex items-center justify-between px-4 border-b"
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      <div className="flex items-center gap-3">
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{
            background: "var(--color-status-active)",
            boxShadow: "0 0 6px var(--color-status-active)",
          }}
        />
        <span className="font-semibold tracking-tight">OpsPilot</span>
        <span className="text-xs text-text-muted">
          dispatch console
        </span>
      </div>
      <div className="flex items-center gap-6">
        <TickerStat label="active riders" value={counts.activeRiders} />
        <TickerStat
          label="in transit"
          value={counts.inTransit}
          color="var(--color-status-transit)"
        />
        <TickerStat
          label="unassigned"
          value={counts.unassigned}
          color="var(--color-status-unassigned)"
        />
        <TickerStat
          label="pending approval"
          value={counts.pending}
          color={counts.pending > 0 ? "var(--color-accent)" : undefined}
        />
      </div>
    </header>
  );
}

function RidersPanel({ riders, onBreakdown, onRestore }) {
  const [actionRider, setActionRider] = useState(null);

  return (
    <Panel title="Riders" accent="var(--color-status-active)">
      {riders.length === 0 ? (
        <div className="py-6 text-center text-xs text-text-muted">
          No riders available.
        </div>
      ) : (
        <ul className="space-y-2">
          {riders.map((r) => {
            const color = RIDER_STATUS_COLOR[r.status];
            const isLoading = actionRider === r.id;

            const capacity =
              r.capacity_weight > 0
                ? Math.min(100, (r.current_load / r.capacity_weight) * 100)
                : 0;

            return (
              <li
                key={r.id}
                className="rounded-lg border p-3 transition hover:bg-bg"
                style={{
                  borderColor: "var(--color-border)",
                }}
              >
                {/* Rider header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="inline-block w-2 h-2 rounded-full shrink-0"
                      style={{
                        background: color,
                        boxShadow: `0 0 5px ${color}`,
                      }}
                    />

                    <span className="font-medium text-sm truncate">
                      {r.name}
                    </span>
                  </div>

                  <span
                    className="text-[10px] uppercase tracking-wider font-medium"
                    style={{ color }}
                  >
                    {RIDER_STATUS_LABEL[r.status]}
                  </span>
                </div>

                {/* Capacity */}
                <div className="mt-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-text-muted">
                      Load
                    </span>

                    <span className="font-mono text-[10px] text-text-muted">
                      {r.current_load} / {r.capacity_weight} kg
                    </span>
                  </div>

                  <div
                    className="h-1.5 w-full rounded-full overflow-hidden"
                    style={{
                      background: "var(--color-border)",
                    }}
                  >
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${capacity}%`,
                        background:
                          capacity >= 90
                            ? "var(--color-status-broken)"
                            : capacity >= 70
                              ? "var(--color-accent)"
                              : "var(--color-status-active)",
                      }}
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-3 flex items-center justify-end gap-3">
                  {r.status === "active" ? (
                    <button
                      disabled={isLoading}
                      className="text-[11px] font-medium text-(--color-status-broken) hover:underline disabled:opacity-50"
                      onClick={async () => {
                        try {
                          setActionRider(r.id);
                          await onBreakdown(r.id);
                        } finally {
                          setActionRider(null);
                        }
                      }}
                    >
                      {isLoading ? "Processing..." : "Simulate breakdown"}
                    </button>
                  ) : r.status === "broken_down" ? (
                    <button
                      disabled={isLoading}
                      className="rounded-md border px-2.5 py-1 text-[11px] font-medium text-(--color-status-active) hover:bg-bg disabled:opacity-50"
                      style={{
                        borderColor: "var(--color-status-active)",
                      }}
                      onClick={async () => {
                        try {
                          setActionRider(r.id);
                          await onRestore(r.id);
                        } finally {
                          setActionRider(null);
                        }
                      }}
                    >
                      {isLoading ? "Restoring..." : "Restore rider"}
                    </button>
                  ) : (
                    <span className="text-[10px] text-text-muted">
                      No actions
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

function Dashboard() {
  const { state, dispatch } = useAppState();

  const loadAll = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    try {
      const [riders, orders, proposals, auditLog] = await Promise.all([
        api.getRiders(),
        api.getOrders(),
        api.getProposals("pending"),
        api.getAuditLog(),
      ]);
      dispatch({ type: "SET_RIDERS", payload: riders });
      dispatch({ type: "SET_ORDERS", payload: orders });
      dispatch({ type: "SET_PROPOSALS", payload: proposals });
      dispatch({ type: "SET_AUDIT_LOG", payload: auditLog });
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: e.message });
    } finally {
      dispatch({ type: "SET_LOADING", payload: false });
    }
  }, [dispatch]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleLiveMessage = useCallback(
    (msg) => {
      if (msg.type === "riders_updated") {
        dispatch({ type: "PATCH_RIDERS", payload: msg.riders });
      }
    },
    [dispatch],
  );
  useLiveStream(handleLiveMessage);

  async function handleBreakdown(riderId) {
    try {
      await api.breakdownRider(riderId);

      const [riders, proposals, auditLog] = await Promise.all([
        api.getRiders(),
        api.getProposals("pending"),
        api.getAuditLog(),
      ]);

      dispatch({ type: "SET_RIDERS", payload: riders });
      dispatch({ type: "SET_PROPOSALS", payload: proposals });
      dispatch({ type: "SET_AUDIT_LOG", payload: auditLog });
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: e.message });
    }
  }
  async function handleRestore(riderId) {
    try {
      await api.restoreRider(riderId);

      const [riders, orders, proposals, auditLog] = await Promise.all([
        api.getRiders(),
        api.getOrders(),
        api.getProposals("pending"),
        api.getAuditLog(),
      ]);

      dispatch({ type: "SET_RIDERS", payload: riders });
      dispatch({ type: "SET_ORDERS", payload: orders });
      dispatch({ type: "SET_PROPOSALS", payload: proposals });
      dispatch({ type: "SET_AUDIT_LOG", payload: auditLog });
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: e.message });
    }
  }
  const riders = Object.values(state.riders);
  const orders = Object.values(state.orders);
  const counts = {
    activeRiders: riders.filter((r) => r.status === "active").length,
    inTransit: orders.filter((o) => o.status === "IN_TRANSIT").length,
    unassigned: orders.filter(
      (o) => o.status === "UNASSIGNED" || o.status === "UNPLACED",
    ).length,
    pending: Object.values(state.proposals).filter(
      (p) => p.status === "pending",
    ).length,
  };

  return (
    <div
      className="h-screen w-screen flex flex-col"
      style={{ background: "var(--color-bg)" }}
    >
      <TopBar counts={counts} />
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 p-3 min-w-0">
          <div
            className="h-full w-full rounded overflow-hidden border"
            style={{ borderColor: "var(--color-border)" }}
          >
            <MapView />
          </div>
        </div>
        <aside
          className="w-96 shrink-0 overflow-y-auto px-4 border-l"
          style={{
            background: "var(--color-surface)",
            borderColor: "var(--color-border)",
          }}
        >
          {state.error && (
            <div
              className="mt-4 rounded-lg border px-3 py-2.5 text-xs flex items-start gap-2"
              style={{
                background:
                  "color-mix(in srgb, var(--color-status-broken) 10%, transparent)",
                borderColor:
                  "color-mix(in srgb, var(--color-status-broken) 30%, transparent)",
                color: "var(--color-status-broken)",
              }}
            >
              <span className="mt-0.5">!</span>
              <span className="leading-relaxed">{state.error}</span>
            </div>
          )}
          <RidersPanel
            riders={riders}
            onBreakdown={handleBreakdown}
            onRestore={handleRestore}
          />
          <NewOrderForm />
          <PhotoUploadForm />
          <UnassignedOrdersPanel />
          <DispatcherPanel />
          <AuditLogPanel />
        </aside>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppStateProvider>
      <Dashboard />
    </AppStateProvider>
  );
}
