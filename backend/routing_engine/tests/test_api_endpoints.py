import pytest
from rest_framework.test import APIClient
from unittest.mock import patch


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestApiEndpoints:
    def test_health_check(self, api_client):
        resp = api_client.get("/api/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "spotter-weather-aware-truck-routing"

    def test_geocode_autocomplete_empty(self, api_client):
        resp = api_client.get("/api/geocode/?q=")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("routing_engine.views.geocode_address")
    def test_geocode_autocomplete_success(self, mock_geocode, api_client):
        mock_geocode.return_value = [
            {"name": "Chicago, IL, United States", "lat": 41.8781, "lon": -87.6298}
        ]
        resp = api_client.get("/api/geocode/?q=Chicago")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["lat"] == 41.8781

    def test_trip_analysis_validation_errors(self, api_client):
        # Missing required fields
        resp = api_client.post("/api/routes/analyze/", {}, format="json")
        assert resp.status_code == 400
        data = resp.json()
        assert "origin" in data["details"]
        assert "destination" in data["details"]
        assert "cargo_weight_lbs" in data["details"]

        # Invalid interval (only 10, 25, 50 permitted)
        resp2 = api_client.post("/api/routes/analyze/", {
            "origin": "Chicago, IL",
            "destination": "Atlanta, GA",
            "cargo_weight_lbs": 35000,
            "checkpoint_interval_miles": 15,  # Invalid
        }, format="json")
        assert resp2.status_code == 400
        assert "checkpoint_interval_miles" in resp2.json()["details"]

        # Negative cargo weight
        resp3 = api_client.post("/api/routes/analyze/", {
            "origin": "Chicago, IL",
            "destination": "Atlanta, GA",
            "cargo_weight_lbs": -500,
            "checkpoint_interval_miles": 25,
        }, format="json")
        assert resp3.status_code == 400
        assert "cargo_weight_lbs" in resp3.json()["details"]

    @patch("routing_engine.views.geocode_address")
    @patch("routing_engine.views.fetch_route_options")
    @patch("routing_engine.views.enrich_checkpoints_with_weather")
    def test_trip_analysis_full_flow(self, mock_weather, mock_routes, mock_geocode, api_client):
        mock_geocode.side_effect = lambda q, limit=1: [
            {"name": q, "lat": 40.0, "lon": -80.0}
        ]

        mock_routes.return_value = [
            {
                "route_id": "route_1",
                "name": "Via Highway 1",
                "distance_miles": 100.0,
                "duration_seconds": 7200.0,
                "duration_hours": 2.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-80.0, 40.0], [-79.0, 40.0]],
                },
            }
        ]

        # Mock enriched checkpoints
        mock_weather.side_effect = lambda checkpoints, cargo_weight_lbs, departure_time_iso: [
            {
                **cp,
                "weather": {
                    "wind_speed_mph": 20.0,
                    "rain_intensity_in_hr": 0.05,
                    "snow_intensity_in_hr": 0.0,
                    "temperature_f": 50.0,
                    "forecast_timestamp": "2026-10-24T08:00",
                },
                "hazard_classifications": {
                    "wind": "Low",
                    "effective_wind": "Low",
                    "rain": "Low",
                    "snow": "Low",
                },
                "cargo_override_applied": None,
                "effective_risk": "Low",
                "risk_score": 1.0,
                "timeline_48h": [],
            }
            for cp in checkpoints
        ]

        payload = {
            "origin": "Pittsburgh, PA",
            "destination": "Philadelphia, PA",
            "departure_time": "2026-10-24T08:00:00Z",
            "cargo_weight_lbs": 35000,
            "checkpoint_interval_miles": 25,
        }

        resp = api_client.post("/api/routes/analyze/", payload, format="json")
        assert resp.status_code == 200
        data = resp.json()

        assert "routes" in data
        assert len(data["routes"]) == 1
        route = data["routes"][0]
        assert route["route_id"] == "route_1"
        assert route["is_recommended"] is True
        assert route["rank"] == 1
        assert route["distance_miles"] == 100.0
        assert route["risk_mileage"]["total_accounted_miles"] == 100.0
        assert len(route["checkpoints"]) >= 4
