# Spotter Full Stack Assessment — Loom Walkthrough Script

**Project:** Weather-Aware Truck Routing  
**Presenter:** Full Stack Candidate  
**Target Duration:** 5–10 Minutes  
**Repository:** [https://github.com/Subhadeep-Dhar/weather_routing_web_app](https://github.com/Subhadeep-Dhar/weather_routing_web_app)

---

## Video Outline & Timestamp Guide

### 1. Introduction & Architecture (0:00 – 1:30)
- **Problem Statement:** Commercial truck drivers face dynamic, localized road hazards (gusts, freezing rain, blizzard snow) that require balancing travel time against load safety. Heavy loads alter lateral stability, requiring cargo-specific wind overrides.
- **Full Stack Architecture:**
  - **Frontend:** React 19 + TypeScript + Vite + Google Material Design 3 tokens + Leaflet / React-Leaflet.
  - **Backend:** Python + Django 6.1 + Django REST Framework.
  - **Zero-Budget Strategy:** Zero paid APIs, zero subscriptions. Integrates OSRM (turn-by-turn road geometry routing), Open-Meteo API (batch multi-coordinate hourly forecasts), and Photon/Nominatim (OSM forward geocoding).

### 2. Live Demo — Trip Planning & Route Generation (1:30 – 3:30)
- **Inputs Demonstrated:**
  - Origin: `Chicago, IL` (showing debounced autocomplete dropdown)
  - Destination: `Indianapolis, IN` (showing location swap functionality)
  - Departure Date/Time: Scheduled departure time
  - Cargo Weight: Demonstrating standard commercial presets (`Empty 15k`, `Medium 30k`, `Heavy 42k`, `Max Gross 78k`)
  - Checkpoint Sampling Frequency: Toggling between `Every 10 mi`, `Every 25 mi`, and `Every 50 mi`
- **Click "Analyze Safe Routes":**
  - Show live request processing without fake mocks.
  - OSRM generates 3 genuine physical highway alternatives (e.g., via I-65 S, alternative state routes).

### 3. Route Comparison & Lexicographical Safety Ranking (3:30 – 5:00)
- **Show Route Comparison Cards:**
  - Highlight the `RECOMMENDED` badge on Option 1.
  - Explain the 4-tier lexicographical ranking hierarchy:
    1. Fewest Severe miles (strictly dominates travel time).
    2. Fewest High-risk miles.
    3. Lowest average risk score (distance-weighted).
    4. Shortest travel duration.
  - Point out the category mileage pills: `Low`, `Mod`, `High`, `Severe`, `No Travel`.
  - Explain distance reconciliation: the sum of category miles strictly matches the total route distance.

### 4. Checkpoint Weather & Cargo Weight Overrides (5:00 – 7:00)
- **Interactive Map Inspection:**
  - Zoom into the Leaflet map showing color-coded risk markers along the corridor.
  - Click on a checkpoint pin to open the Checkpoint Details inspection card.
  - Review weather metrics: Wind speed (mph), Rain intensity (in/hr), Snow intensity (in/hr), Temperature (°F), and ETA.
  - **Demonstrate the Cargo Weight Override:**
    - Explain that wind at 45–54 mph is normally Severe, but with cargo >30,000 lb, it triggers **No Travel**.
    - Explain that wind at 35–44 mph is normally High, but with cargo >40,000 lb, it triggers **Severe**.
    - Show the explicit warning banner and override reason when active.

### 5. Corridor Weather Heatmap & 0–48h Forecast Slider (7:00 – 8:30)
- **Weather Heatmap:**
  - Toggle the Heatmap Visible / Hidden button.
  - Explain that this is a real data-grounded corridor heatmap whose radius and Gaussian opacity are driven by actual precipitation and wind intensity along the trip corridor.
- **Forecast Slider:**
  - Scrub through the 0–48 hour slider.
  - Click the "Play" button to simulate temporal progression.
  - Demonstrate how checkpoint risk indicators and corridor weather update instantaneously without making redundant network calls.

### 6. Automated Testing & Engineering Rigor (8:30 – 9:30)
- **Show Terminal:**
  - Run `pytest -v` in the backend showing 38 passing tests covering all threshold boundaries (25, 35, 45, 55 mph wind; 0.10, 0.25, 0.50, 1.00 in/hr rain; 0.5, 1.0, 2.0, 3.0 in/hr snow; 30k and 40k lb cargo boundaries).
  - Run `npm run build` in the frontend demonstrating clean TypeScript type checks and asset optimization.
- **Wrap up:** Reiterate adherence to zero-budget operation, real live API integration, and assessment criteria.
