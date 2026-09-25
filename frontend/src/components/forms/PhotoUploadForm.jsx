import { useState } from "react";
import { api } from "../../api/client";
import { useAppState } from "../../store/useAppState";
import Panel from "../ui/Panel";

const inputCls =
  "bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1.5 text-xs text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] outline-none w-full";

// Creates the order first (so it's visible immediately, even before OCR
// runs), then uploads the image to trigger the OCR -> LLM pipeline.
export default function PhotoUploadForm() {
  const { dispatch } = useAppState();
  const [pickupLabel, setPickupLabel] = useState("");
  const [pickupLat, setPickupLat] = useState("");
  const [pickupLng, setPickupLng] = useState("");
  const [weight, setWeight] = useState("");
  const [priority, setPriority] = useState("normal");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setStatus(null);
    if (!file) {
      setError("Attach a photo of the address label first.");
      return;
    }
    setSubmitting(true);
    try {
      const order = await api.createOrder({
        pickup_label: pickupLabel || null,
        pickup_lat: parseFloat(pickupLat),
        pickup_lng: parseFloat(pickupLng),
        weight: parseFloat(weight),
        priority,
      });
      dispatch({ type: "UPSERT_ORDER", payload: order });

      try {
        const result = await api.uploadOcrImage(order.id, file);
        setStatus(
          result.status === "placed"
            ? `Placed: ${result.delivery_address}`
            : `Low confidence - raw text: "${result.raw_text}". Enter the address manually.`
        );
      } catch {
        setStatus("OCR failed for this image. Order saved as unplaced - retry or enter manually.");
      }

      const refreshed = await api.getOrder(order.id);
      dispatch({ type: "UPSERT_ORDER", payload: refreshed });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Panel title="Order from photo" accent="var(--color-status-unplaced)">
      <form onSubmit={handleSubmit} className="space-y-2">
        {error && <p className="text-xs" style={{ color: "var(--color-status-broken)" }}>{error}</p>}
        {status && <p className="text-xs" style={{ color: "var(--color-accent)" }}>{status}</p>}
        <input
          className={inputCls}
          placeholder="Pickup label"
          value={pickupLabel}
          onChange={(e) => setPickupLabel(e.target.value)}
        />
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder="Pickup lat"
            value={pickupLat}
            onChange={(e) => setPickupLat(e.target.value)}
            required
          />
          <input
            className={inputCls}
            placeholder="Pickup lng"
            value={pickupLng}
            onChange={(e) => setPickupLng(e.target.value)}
            required
          />
        </div>
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder="Weight (kg)"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            required
          />
          <select className={inputCls} value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="low">Low priority</option>
            <option value="normal">Normal priority</option>
            <option value="high">High priority</option>
          </select>
        </div>
        <label className="block text-xs text-[var(--color-text-muted)]">
          <input
            type="file"
            accept="image/*"
            className="block w-full text-xs mt-1 text-[var(--color-text-muted)] file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:font-medium file:text-[var(--color-bg)] file:bg-[var(--color-accent)]"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-1.5 rounded text-xs font-medium text-[var(--color-bg)] disabled:opacity-50"
          style={{ background: "var(--color-status-unplaced)" }}
        >
          {submitting ? "Processing…" : "Upload & extract address"}
        </button>
      </form>
    </Panel>
  );
}
