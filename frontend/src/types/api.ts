export interface LocationInfo {
  name: string;
  lat: number;
  lon: number;
}

export interface WeatherDetails {
  wind_speed_mph: number;
  rain_intensity_in_hr: number;
  snow_intensity_in_hr: number;
  temperature_f: number;
  forecast_timestamp: string;
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
  wind_speed_mph: number;
  rain_intensity_in_hr: number;
  snow_intensity_in_hr: number;
  temperature_f: number;
  effective_risk: "Low" | "Moderate" | "High" | "Severe" | "No Travel";
  risk_score: number;
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
  effective_risk: "Low" | "Moderate" | "High" | "Severe" | "No Travel";
  risk_score: number;
  timeline_48h: HourlyTimelineItem[];
}

export interface RiskMileage {
  low_miles: number;
  moderate_miles: number;
  high_miles: number;
  severe_miles: number;
  no_travel_miles: number;
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
  average_risk_score: number;
  recommendation_reasons: string[];
  is_recommended: boolean;
  rank: number;
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
