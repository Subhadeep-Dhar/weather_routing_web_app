export interface LocationInfo {
  name: string;
  lat: number;
  lon: number;
}

export interface WeatherDetails {
  wind_speed_mph: number | null;
  rain_intensity_in_hr: number | null;
  snow_intensity_in_hr: number | null;
  temperature_f: number | null;
  forecast_timestamp: string;
  data_status?: "available" | "missing" | "out_of_range";
}

export interface HazardClassifications {
  wind: string;
  effective_wind: string;
  rain: string;
  snow: string;
}

export interface HourlyTimelineItem {
  hour_offset: number;
  timestamp: string;
  wind_speed_mph: number | null;
  rain_intensity_in_hr: number | null;
  snow_intensity_in_hr: number | null;
  temperature_f: number | null;
  effective_risk: "Low" | "Moderate" | "High" | "Severe" | "No Travel" | "Unknown";
  risk_score: number | null;
}

export interface Checkpoint {
  index: number;
  distance_from_origin_miles: number;
  segment_distance_miles: number;
  lat: number;
  lon: number;
  eta: string;
  elapsed_hours: number;
  weather: WeatherDetails;
  hazard_classifications: HazardClassifications;
  cargo_override_applied: string | null;
  effective_risk: "Low" | "Moderate" | "High" | "Severe" | "No Travel" | "Unknown";
  risk_score: number | null;
  timeline_48h: HourlyTimelineItem[];
}

export interface RiskMileage {
  low_miles: number;
  moderate_miles: number;
  high_miles: number;
  severe_miles: number;
  no_travel_miles: number;
  unknown_miles: number;
  evaluated_miles: number;
  total_accounted_miles: number;
}

export interface RouteGeometry {
  type: string;
  coordinates: [number, number][]; // [lon, lat]
}

export interface RouteItem {
  route_id: string;
  name: string;
  distance_miles: number;
  duration_hours: number;
  geometry: RouteGeometry;
  checkpoints: Checkpoint[];
  checkpoint_count: number;
  has_no_travel: boolean;
  overall_classification: string;
  risk_mileage: RiskMileage;
  weather_coverage_pct: number;
  is_weather_complete: boolean;
  average_risk_score: number | null;
  recommendation_reasons: string[];
  is_recommended: boolean;
  rank: number;
  // Commercial Truck Transit Model & Terrain Metadata
  duration_raw_osrm_hours?: number;
  duration_raw_osrm_seconds?: number;
  duration_truck_hours?: number;
  duration_truck_seconds?: number;
  average_truck_speed_mph?: number;
  average_truck_speed_kmh?: number;
  raw_implied_car_speed_kmh?: number;
  terrain_classification?: 'mountain' | 'ghat_corridor' | 'rolling' | 'flat';
  terrain_label?: string;
  sinuosity?: number;
  elevation_span_meters?: number;
  elevation_delta_meters?: number;
  model_assumptions?: string[];
  disclaimer_type?: 'mountain' | 'ghat' | 'rolling' | 'highway';
}

export interface TripAnalysisRequest {
  origin: string;
  destination: string;
  departure_time: string;
  cargo_weight_lbs: number;
  checkpoint_interval_miles: 10 | 25 | 50;
}

export interface TripAnalysisResponse {
  request_params: {
    origin: LocationInfo;
    destination: LocationInfo;
    departure_time: string;
    cargo_weight_lbs: number;
    checkpoint_interval_miles: number;
  };
  routes_count: number;
  routes: RouteItem[];
  corridor_timeline: {
    hours_available: number;
    step_hours: number;
  };
}
