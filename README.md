# Spotter SafeRoute — Weather-Aware Commercial Truck Routing

[![Tests](https://img.shields.io/badge/pytest-38%20passed-brightgreen.svg)]()
[![Frontend](https://img.shields.io/badge/vite-v8.3.5-blue.svg)]()
[![Backend](https://img.shields.io/badge/django-v6.1.2-darkgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

> A full-stack web application designed for commercial truck drivers and dispatchers to evaluate the safest highway routes based on real-time arrival weather forecasts, cargo-weight wind overrides, and lexicographical safety rankings.

---

## 1. Project Overview & Deliverables

Built for the **Spotter Full Stack Developer Assessment**:
- **Frontend:** React 19 + TypeScript + Vite + Material UI (Google Material Design system) + Leaflet / React-Leaflet
- **Backend:** Python + Django 6.1 + Django REST Framework
- **Geospatial & Weather Integration:** OSRM (Open Source Routing Machine), Open-Meteo API, Photon (Komoot OSM) / Nominatim OSM
- **Zero-Budget Architecture:** 100% free legitimate public APIs without credit cards, API keys, or paid subscriptions.

### Assessment Requirements Traceability
- [x] **User Inputs:** Origin, Destination, Departure Date/Time, Cargo Weight (lbs), Checkpoint Interval (10, 25, 50 mi).
- [x] **3 Route Options:** Generates 3 distinct genuine driving route options via OSRM turn-by-turn road geometries (with lateral highway corridor discovery to ensure 3 distinct paths).
- [x] **Weather Sampling:** Samples weather every 10, 25, or 50 miles along the actual route geometry.
- [x] **Arrival-Aligned Weather:** Projects truck transit velocity to query forecasted conditions at the exact estimated time of arrival (ETA) at each checkpoint.
- [x] **Deterministic Hazard Rules:** Exact thresholds for Wind, Rain, and Snow.
- [x] **Cargo-Weight Overrides:**
  - $\ge 55\text{ mph Wind} \to \text{No Travel for any cargo weight}$
  - $45\text{--}54\text{ mph Wind} + \text{cargo} > 30,000\text{ lb} \to \text{No Travel override}$
  - $35\text{--}44\text{ mph Wind} + \text{cargo} > 40,000\text{ lb} \to \text{Severe override}$
- [x] **Lexicographical Recommendation Engine:**
  1. Fewest Severe miles
  2. Fewest High-risk miles
  3. Lowest average risk score (distance-weighted)
  4. Shortest travel duration
- [x] **Distance Reconciliation:** Voronoi/midpoint segment distance attribution ensuring the sum of category miles strictly reconciles with total route distance within 0.01 mi.
- [x] **Interactive Leaflet Map:** Renders active and alternative route polylines, start/finish terminals, and numbered checkpoint pins color-coded by hazard risk.
- [x] **Trip Corridor Weather Heatmap:** Dynamic canvas/SVG corridor heatmap layer driven by real precipitation and wind intensity.
- [x] **0–48 Hour Forecast Slider:** Real-time timeline scrubber with instant playback simulation updating corridor weather without network refetching.

---

## 2. Weather Hazard Classification & Load Rules

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| **Wind** | `< 25 mph` | `25–34 mph` | `35–44 mph` | `45–54 mph` | `≥ 55 mph` |
| **Rain** | `< 0.10 in/hr` | `0.10–0.25 in/hr` | `0.25–0.50 in/hr` | `0.50–1.00 in/hr` | `> 1.00 in/hr` |
| **Snow** | `< 0.5 in/hr` | `0.5–1.0 in/hr` | `1.0–2.0 in/hr` | `2.0–3.0 in/hr` | `> 3.0 in/hr` |

### Cargo Weight Overrides
Heavy loads change vehicle center of gravity and lateral stability. The engine applies:
- `Wind >= 55 mph` $\to$ **No Travel** for any load.
- `Wind 45–54 mph` AND `Cargo > 30,000 lb` $\to$ **No Travel** (overrides Severe).
- `Wind 35–44 mph` AND `Cargo > 40,000 lb` $\to$ **Severe** (overrides High).

Simultaneous conditions take the highest severity encountered. If any applicable rule results in **No Travel**, the checkpoint is classified as **No Travel** and the route is flagged with high-visibility warnings.

---

## 3. Architecture & Directory Structure

```
routing_web_app/
├── backend/
│   ├── manage.py
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── spotter_routing/
│   │   ├── settings.py           # CORS, caching, DRF configuration
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── routing_engine/
│       ├── urls.py
│       ├── views.py              # Health check, autocomplete, trip analysis
│       ├── serializers.py        # Strict input validation
│       ├── services/
│       │   ├── geocoding.py       # Photon (Komoot OSM) + Nominatim fallback
│       │   ├── routing.py         # OSRM turn geometries & 3-alternative generator
│       │   ├── checkpoints.py     # Geodesic sampling along polyline & Voronoi attribution
│       │   ├── weather.py         # Open-Meteo batch queries & ETA alignment
│       │   ├── risk_engine.py     # Pure boundary evaluator & cargo overrides
│       │   └── recommender.py     # Lexicographical 4-tier ranking & rationales
│       └── tests/
│           ├── test_risk_engine.py      # Thresholds & cargo weight boundaries
│           ├── test_checkpoints.py      # Sampling & distance reconciliation
│           ├── test_recommender.py      # Priority order & No Travel flags
│           └── test_api_endpoints.py    # DRF endpoints & validation
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx                # Master container & responsive layout
│       ├── theme.ts               # Google Material Design 3 tokens
│       ├── types/api.ts           # Strict TypeScript contracts
│       ├── api/client.ts          # Axios client with caching
│       └── components/
│           ├── Header.tsx         # Navbar with live health chip & rules modal
│           ├── TripForm.tsx       # Location autocomplete, load presets, interval
│           ├── RouteComparison.tsx# Option cards, recommendation badge, mileage pills
│           ├── MapView.tsx        # Leaflet map, polylines, numbered risk markers
│           ├── WeatherHeatmap.tsx # Corridor Gaussian heatmap overlay
│           ├── ForecastSlider.tsx # 0-48h interactive timeline scrubber
│           ├── CheckpointDetails.tsx # Inspection card for weather & overrides
│           └── SafetyLegend.tsx   # Visual key for hazard thresholds
└── README.md
```

---

## 4. Setup & Running Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ & npm 9+ (tested on Node v24.11)

### 1. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run automated tests
pytest -v

# Start development server on port 8000
python manage.py runserver 127.0.0.1:8000
```
Backend health check is accessible at `http://127.0.0.1:8000/api/health/`.

### 2. Frontend Setup
```bash
cd frontend

# Install packages
npm install

# Build production bundle (verifies TypeScript & assets)
npm run build

# Start frontend dev server on port 5173
npm run dev -- --host 127.0.0.1 --port 5173
```
Open `http://127.0.0.1:5173/` in your browser.

---

## 5. Verification & Automated Testing

### Backend Test Suite (38 Passed)
```bash
$ pytest -v
============================= test session starts =============================
routing_engine/tests/test_api_endpoints.py::TestApiEndpoints::test_health_check PASSED
routing_engine/tests/test_api_endpoints.py::TestApiEndpoints::test_geocode_autocomplete_empty PASSED
routing_engine/tests/test_api_endpoints.py::TestApiEndpoints::test_geocode_autocomplete_success PASSED
routing_engine/tests/test_api_endpoints.py::TestApiEndpoints::test_trip_analysis_validation_errors PASSED
routing_engine/tests/test_api_endpoints.py::TestApiEndpoints::test_trip_analysis_full_flow PASSED
routing_engine/tests/test_checkpoints.py::TestCheckpoints::test_haversine_distance PASSED
routing_engine/tests/test_checkpoints.py::TestCheckpoints::test_segment_distances_exact_reconciliation PASSED
routing_engine/tests/test_checkpoints.py::TestCheckpoints::test_generate_route_checkpoints_multiple_intervals PASSED
routing_engine/tests/test_checkpoints.py::TestCheckpoints::test_route_shorter_than_interval PASSED
routing_engine/tests/test_recommender.py::TestRecommender::test_priority_1_fewest_severe_miles_dominates_time PASSED
routing_engine/tests/test_recommender.py::TestRecommender::test_priority_2_fewest_high_miles_breaks_tie PASSED
routing_engine/tests/test_recommender.py::TestRecommender::test_priority_3_lowest_average_risk_breaks_tie PASSED
routing_engine/tests/test_recommender.py::TestRecommender::test_priority_4_shortest_time_breaks_tie PASSED
routing_engine/tests/test_recommender.py::TestRecommender::test_no_travel_route_is_flagged_and_deprioritized PASSED
routing_engine/tests/test_risk_engine.py::TestWindClassification::* [6 PASSED]
routing_engine/tests/test_risk_engine.py::TestRainClassification::* [6 PASSED]
routing_engine/tests/test_risk_engine.py::TestSnowClassification::* [6 PASSED]
routing_engine/tests/test_risk_engine.py::TestCargoWeightOverrides::* [3 PASSED]
routing_engine/tests/test_risk_engine.py::TestCombinedRiskEvaluation::* [2 PASSED]
============================= 38 passed in 1.31s ==============================
```

---

## 6. Loom Walkthrough Agenda (5–10 min)

1. **Architecture & Zero-Cost Stack (1:00):** Explanation of OSRM routing, Open-Meteo batch coordinates, Photon geocoder, and Django + React architecture.
2. **Trip Configuration (1:30):** Entering origin/destination, cargo weight (demonstrating empty vs heavy presets), and selecting checkpoint intervals (10, 25, 50 mi).
3. **Route Alternatives & Recommendation (2:00):** Inspecting the 3 genuine route options, why Option 1 is marked RECOMMENDED under lexicographical criteria, and examining mileage pills.
4. **Checkpoint Weather & Cargo Overrides (2:00):** Clicking checkpoints on the Leaflet map to inspect arrival weather, wind speed, rain intensity, and demonstrating how a heavy load (>30k or >40k lb) alters effective risk.
5. **Corridor Weather Heatmap & 0–48h Slider (2:00):** Scrubbing the timeline slider and observing dynamic corridor weather updates in real time.
6. **Codebase & Automated Test Review (1:00):** Running `pytest` and demonstrating distance reconciliation and pure business logic boundaries.

---

## 7. License
MIT License. Created for the Spotter Full Stack Developer Assessment.
