# OpsPilot — Ops Copilot for Disrupted Deliveries

A dispatch console that tracks a small fleet of delivery riders on a live map, reads
photographed address labels with a pretrained OCR model, and proposes reassignments
when a rider breaks down — with every AI suggestion sitting behind explicit dispatcher
approval before it touches real state.

Built for the "Ops Copilot for Disrupted Deliveries" problem statement.

---

## What's built

### 1. Order intake & routing
- Orders are created with a pickup address, delivery address, weight, and priority.
- Pickup/delivery addresses are geocoded server-side (Photon/OpenStreetMap) into
  coordinates — the dispatcher never has to supply lat/lng manually.
- Assignment considers **remaining rider capacity**, **real road distance** (via OSRM,
  not straight-line), and **order priority**, not just "nearest rider."
- When no active rider has capacity, the order is marked `UNASSIGNED` and stays
  visible — it never silently disappears.
- Each order carries both a pickup location and a delivery address, and a rider
  travels to pickup before delivering (modeled explicitly in the live simulator).

### 2. Live map dashboard
- Riders and orders are plotted on a live map (Leaflet + OpenStreetMap/CARTO tiles).
- Rider positions update over a WebSocket as the simulator moves them along real
  road routes (OSRM), not straight lines.
- Unassigned and unplaced orders are shown in their own panel — always visible, never
  just missing from the list.
- Clicking a rider or order marker shows live status, load, and (for an assigned
  order) live distance/ETA to its next stop.

### 3. Pretrained OCR pipeline (image → text → structured address)
- **microsoft/trocr-base-printed** (Hugging Face `transformers` + `torch`) runs
  locally, in-process, to extract raw text from an uploaded photo.
- The raw OCR text is passed to an LLM (Gemini by default; Anthropic/OpenAI also
  supported) which returns a structured, validated address (`street`, `city`,
  `state`, `zip`) or explicitly flags low confidence.
- Low-confidence or malformed LLM output is never guessed at — the order is marked
  `UNPLACED` and the raw OCR text stays attached to it so a dispatcher can enter the
  address manually.
- Every stage of this pipeline (OCR failure, low confidence, LLM parse error,
  successful placement) is written to the audit log with the raw text/response
  attached.

### 4. Disruption handling
- A dispatcher can simulate a rider breakdown. The rider is marked `BROKEN_DOWN`
  immediately; its existing orders are **not** touched automatically.
- An LLM proposes a reassignment plan for that rider's remaining orders. Every
  suggestion is re-validated against real rider capacity/existence in code before
  it's ever shown to a dispatcher — the LLM's arithmetic is never trusted blindly.
- Proposals are stored as `pending` and rendered in a dedicated panel. A dispatcher
  can **accept**, **edit** (pick a different rider than the one suggested), or
  **reject** each one individually.
- **No proposal mutates order/rider state on its own.** The only code path that
  changes an order's assignment as a result of an LLM suggestion is
  `POST /proposals/{id}/accept` in `routers/proposals.py` — everything upstream of
  that only ever reads state and writes a pending proposal.
- A rider can be restored (`POST /riders/{id}/restore`) once fixed; only orders that
  are still genuinely `UNASSIGNED` are eligible for re-routing — orders already
  handed to another rider via an approved proposal are not pulled back.

### 5. Audit log
Every meaningful state transition is written to a single `audit_log` table in the
same database transaction as the change itself, so a mutation can never happen
without a trace (and vice versa). Each entry records: entity type/id, actor
(`system` / `llm` / `dispatcher`), action, before/after state, any raw LLM/OCR
payload, and a timestamp. Visible live in the UI's Audit Log panel, with failure
entries (`ocr_failed`, `llm_parse_error`, `geocoding_failed`, etc.) expandable to
show the actual error message.

### 6. Resilience
- OCR and LLM calls are wrapped in try/except; a failure marks the order `UNPLACED`
  with the original image/text preserved — it never partially updates order state.
- The LLM call automatically retries on transient failures (exponential backoff, via
  `tenacity`) before giving up.
- Road-routing calls (OSRM) fall back to a straight-line estimate if the routing
  service is unreachable, so riders keep moving and orders can still be scored
  instead of the whole app freezing.
- Every order has one of `UNASSIGNED`, `ASSIGNED`, `IN_TRANSIT`, `DELIVERED`,
  `FAILED`, or `UNPLACED` at all times — an order is never deleted or silently
  dropped as a result of reassignment or a failed pipeline stage.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL |
| OCR | Hugging Face `transformers` + `torch`, `microsoft/trocr-base-handwritten` (local inference, no external OCR API) |
| LLM | Google Gemini by default (`gemini-3.1-flash-lite`); Anthropic and OpenAI also supported via `LLM_PROVIDER` |
| Geocoding | Photon (OpenStreetMap-based, via `geopy`) |
| Road routing | OSRM public routing API, with a straight-line fallback |
| Frontend | React (JavaScript), Vite, Tailwind CSS v4, React-Leaflet |
| Live updates | WebSocket |
| Infra | Docker + Docker Compose |

---

## Project structure

```
OpsPilot/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── main.py                  # FastAPI entrypoint, router registration
│   ├── config.py                # environment/settings
│   ├── database.py              # SQLAlchemy engine/session
│   ├── models/                  # Order, Rider, Proposal, AuditLog
│   ├── schemas/                 # Pydantic request/response + LLM output schemas
│   ├── routers/                 # orders, riders, proposals, ocr, routes, stream, audit
│   ├── services/
│   │   ├── routing.py           # capacity + real-road-distance assignment
│   │   ├── road_routing.py      # OSRM client with retry + straight-line fallback
│   │   ├── geocoder.py          # address text -> lat/lng
│   │   ├── ocr_service.py       # local TrOCR inference
│   │   ├── llm_address_cleanup.py
│   │   ├── llm_reassignment.py
│   │   ├── simulator.py         # moves riders along real routes, advances order status
│   │   └── audit.py
│   ├── seed_data.py             # demo riders/orders
│   └── check_llm.py             # standalone LLM connectivity/sanity check
└── frontend/
    └── src/
        ├── App.jsx               # dashboard layout, live ticker bar
        ├── api/                  # REST client + WebSocket hook
        ├── store/                # app state (Context + reducer)
        └── components/
            ├── map/               # MapView, RiderMarker, OrderMarker
            ├── panels/            # Unassigned orders, Dispatcher approvals, Audit log
            └── forms/             # New order, Order from photo
```

---

## Setup & run

### Prerequisites
- Docker Desktop
- A free LLM API key — Gemini recommended: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 1. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and set:
```
LLM_PROVIDER=gemini
LLM_API_KEY=your_key_here
```
Never commit a real key — `.env` is gitignored; `.env.example` should always stay a
template with empty values.

### 2. Start everything
```bash
docker compose up --build
```
This starts three services: `db` (Postgres), `backend` (FastAPI on port 8000), and
`frontend` (Vite dev server on port 5173). First build downloads the TrOCR model
weights, so it can take a few minutes.

### 3. Seed demo data
In a second terminal:
```bash
docker compose exec backend python seed_data.py
```

### 4. Open the app
- Dashboard: [http://localhost:5173](http://localhost:5173)
- API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Verify the LLM connection (optional but recommended)
```bash
docker compose exec backend python check_llm.py
```
Runs the exact same LLM call the app uses, against a sample OCR-style string and a
sample reassignment context, and prints whether each one parsed correctly — a fast
way to confirm your API key/provider are configured correctly before relying on the
full pipeline.

---

## Trying the core flows

1. **Create a typed order** — fill in the "New order" form with a pickup/delivery
   address near your seeded riders. It should appear on the map, `ASSIGNED` to the
   nearest eligible rider.
2. **Create an order from a photo** — use "Order from photo," attach a photo of
   printed or handwritten text that looks like an address, and watch it go through
   OCR → LLM cleanup → geocoding → assignment. A blank or unreadable image will
   correctly land as `UNPLACED` rather than guessing.
3. **Simulate a disruption** — click "Simulate breakdown" on a rider carrying
   orders. Check the "Pending approvals" panel for the LLM's reassignment proposal,
   then accept, edit, or reject it.
4. **Check the audit trail** — the Audit Log panel shows every step above, with
   failures expandable to show the actual error.

---

## Design decisions worth noting

- **Initial rider positions**: seeded riders start clustered around a small area of
  New Delhi (Connaught Place) matching the seed orders, so the demo shows immediate,
  visible pickup/delivery activity rather than riders scattered too far to reach
  anything.
- **Human-approval boundary**: the only function in the codebase permitted to change
  `order.rider_id` or `order.status` as a result of an LLM suggestion is
  `accept_proposal` in `routers/proposals.py`. Every LLM-originated suggestion is a
  `Proposal` row with `status="pending"` until a dispatcher acts on it.
- **OCR model choice**: `microsoft/trocr-base-handwritten` was chosen over
  `-base-printed` to also support handwritten address labels; if your test images
  are exclusively printed, `-base-printed` will read them more reliably.
- **Road routing**: rider-to-pickup and pickup-to-delivery legs use real road
  distance/geometry from OSRM rather than straight-line distance, so assignment
  scoring and the simulator's rider movement reflect actual streets.

---

## Known limitations / future improvements

- **External network dependencies**: geocoding (Photon) and routing (OSRM) both call
  public, rate-limited services. Under heavy or sustained use these can throttle;
  the app falls back gracefully (straight-line routing) but doesn't cache geocoding
  results yet.
- **No authentication**: there's a single implicit "dispatcher" — a real deployment
  would need login and per-dispatcher audit attribution.
- **No manual re-assignment UI** for an order that's already `UNASSIGNED` outside of
  the breakdown/proposal flow — a dispatcher currently can't force-assign a stuck
  order to a specific rider directly; only automatic routing and the
  breakdown-proposal flow move orders.
- **OCR confidence heuristic**: since TrOCR doesn't expose a single clean confidence
  score, it's approximated from average token probability — a calibrated confidence
  model would be a meaningful accuracy improvement.
- **Test coverage**: automated tests exist for routing, the OCR pipeline, the
  reassignment proposer, and the approval boundary; deepening these (particularly
  concurrent-request and partial-failure scenarios) would strengthen confidence
  further.
- **Deployment**: designed to run via `docker compose up`; for a hosted demo link,
  the OCR model's memory footprint (~1GB+) needs a host with enough RAM (Render's
  free tier, for example, is too small without switching OCR to a hosted inference
  API for that specific deployment).