import { useState } from "react";
import { api } from "../../api/client";
import { useAppState } from "../../store/useAppState";
import Panel from "../ui/Panel";

const initial = {
  pickup_label: "",
  pickup_lat: "",
  pickup_lng: "",
  delivery_address: "",
  delivery_lat: "",
  delivery_lng: "",
  weight: "",
  priority: "normal",
};

const inputCls =
  "bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1.5 text-xs text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] outline-none w-full";

export default function NewOrderForm() {
  const { dispatch } = useAppState();
  const [form, setForm] = useState(initial);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload = {
        pickup_label: form.pickup_label || null,
        pickup_lat: parseFloat(form.pickup_lat),
        pickup_lng: parseFloat(form.pickup_lng),
        delivery_address: form.delivery_address || null,
        delivery_lat: form.delivery_lat ? parseFloat(form.delivery_lat) : null,
        delivery_lng: form.delivery_lng ? parseFloat(form.delivery_lng) : null,
        weight: parseFloat(form.weight),
        priority: form.priority,
      };
      const order = await api.createOrder(payload);
      dispatch({ type: "UPSERT_ORDER", payload: order });
      setForm(initial);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Panel title="New order" accent="var(--color-status-assigned)">
      <form onSubmit={handleSubmit} className="space-y-2">
        {error && <p className="text-xs" style={{ color: "var(--color-status-broken)" }}>{error}</p>}
        <input
          className={inputCls}
          placeholder="Pickup label (e.g. Store 1)"
          value={form.pickup_label}
          onChange={(e) => update("pickup_label", e.target.value)}
        />
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder="Pickup lat"
            value={form.pickup_lat}
            onChange={(e) => update("pickup_lat", e.target.value)}
            required
          />
          <input
            className={inputCls}
            placeholder="Pickup lng"
            value={form.pickup_lng}
            onChange={(e) => update("pickup_lng", e.target.value)}
            required
          />
        </div>
        <input
          className={inputCls}
          placeholder="Delivery address"
          value={form.delivery_address}
          onChange={(e) => update("delivery_address", e.target.value)}
        />
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder="Delivery lat"
            value={form.delivery_lat}
            onChange={(e) => update("delivery_lat", e.target.value)}
          />
          <input
            className={inputCls}
            placeholder="Delivery lng"
            value={form.delivery_lng}
            onChange={(e) => update("delivery_lng", e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder="Weight (kg)"
            value={form.weight}
            onChange={(e) => update("weight", e.target.value)}
            required
          />
          <select
            className={inputCls}
            value={form.priority}
            onChange={(e) => update("priority", e.target.value)}
          >
            <option value="low">Low priority</option>
            <option value="normal">Normal priority</option>
            <option value="high">High priority</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-1.5 rounded text-xs font-medium text-bg disabled:opacity-50"
          style={{ background: "var(--color-accent)" }}
        >
          {submitting ? "Creating…" : "Create order"}
        </button>
      </form>
    </Panel>
  );
}