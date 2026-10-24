import logging
from datetime import datetime, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripAnalysisRequestSerializer
from .services.geocoding import geocode_address
from .services.routing import fetch_route_options
from .services.checkpoints import generate_route_checkpoints
from .services.weather import enrich_checkpoints_with_weather
from .services.recommender import calculate_route_metrics, rank_and_recommend_routes
from .services.truck_eta_model import calculate_defensible_truck_eta

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """System health check endpoint."""
    def get(self, request):
        return Response({
            "status": "healthy",
            "service": "spotter-weather-aware-truck-routing",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


class GeocodeAutocompleteView(APIView):
    """Location autocomplete for origin and destination input fields."""
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q or len(q) < 2:
            return Response([])
        results = geocode_address(q, limit=6)
        return Response(results)


class TripAnalysisView(APIView):
    """
    Primary route analysis endpoint.
    Accepts: origin, destination, departure_time, cargo_weight_lbs, checkpoint_interval_miles.
    Generates 3 route options, samples checkpoints, enriches with arrival-aligned weather,
    applies exact risk thresholds and cargo-weight overrides, and ranks lexicographically.
    """
    def post(self, request):
        serializer = TripAnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        origin_query = data["origin"].strip()
        dest_query = data["destination"].strip()
        departure_time = data["departure_time"]
        cargo_weight = data["cargo_weight_lbs"]
        interval_miles = float(data["checkpoint_interval_miles"])

        # 1. Geocode Origin and Destination
        origin_results = geocode_address(origin_query, limit=1)
        if not origin_results:
            return Response(
                {"error": f"Unable to resolve origin address: '{origin_query}'. Please check the location."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        origin_info = origin_results[0]

        dest_results = geocode_address(dest_query, limit=1)
        if not dest_results:
            return Response(
                {"error": f"Unable to resolve destination address: '{dest_query}'. Please check the location."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dest_info = dest_results[0]

        # 2. Fetch up to 3 distinct route alternatives from OSRM
        raw_routes = fetch_route_options(
            origin_info["lat"], origin_info["lon"],
            dest_info["lat"], dest_info["lon"]
        )

        if not raw_routes:
            return Response(
                {"error": "Routing service could not find driving routes between the selected locations."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        processed_routes = []
        dep_time_iso = departure_time.isoformat()

        for r in raw_routes:
            coords = r["geometry"].get("coordinates", [])
            total_dist = r["distance_miles"]
            raw_duration_s = r["duration_seconds"]

            # Sample subset of geometry points for elevation profiling
            sample_step = max(1, len(coords) // 10)
            ckpt_sample_coords = [(c[1], c[0]) for c in coords[::sample_step]]

            # Calculate defensible commercial truck transit time and terrain profile
            truck_eta_data = calculate_defensible_truck_eta(
                distance_miles=total_dist,
                raw_duration_seconds=raw_duration_s,
                origin_lat=origin_info["lat"],
                origin_lon=origin_info["lon"],
                dest_lat=dest_info["lat"],
                dest_lon=dest_info["lon"],
                cargo_weight_lbs=cargo_weight,
                checkpoint_coords=ckpt_sample_coords,
            )

            truck_duration_s = truck_eta_data["duration_truck_seconds"]
            truck_duration_h = truck_eta_data["duration_truck_hours"]

            # 3. Generate checkpoints along real route geometry with realistic commercial truck pacing
            checkpoints = generate_route_checkpoints(
                coordinates=coords,
                total_route_distance_miles=total_dist,
                total_duration_seconds=truck_duration_s,
                departure_time=departure_time,
                interval_miles=interval_miles,
            )

            # 4. Enrich checkpoints with real arrival-time weather and risk classifications
            enriched_checkpoints = enrich_checkpoints_with_weather(
                checkpoints=checkpoints,
                cargo_weight_lbs=cargo_weight,
                departure_time_iso=dep_time_iso,
            )

            # 5. Calculate route metrics, mileage breakdown, and distance reconciliation
            route_metrics = calculate_route_metrics(
                route_id=r["route_id"],
                name=r["name"],
                distance_miles=total_dist,
                duration_hours=truck_duration_h,
                checkpoints=enriched_checkpoints,
                geometry=r["geometry"],
                truck_eta_data=truck_eta_data,
            )
            processed_routes.append(route_metrics)

        # 6. Rank routes using assessment's exact lexicographical priority rules
        ranked_routes = rank_and_recommend_routes(processed_routes)

        return Response({
            "request_params": {
                "origin": origin_info,
                "destination": dest_info,
                "departure_time": dep_time_iso,
                "cargo_weight_lbs": cargo_weight,
                "checkpoint_interval_miles": interval_miles,
            },
            "routes_count": len(ranked_routes),
            "routes": ranked_routes,
            "corridor_timeline": {
                "hours_available": 48,
                "step_hours": 1,
            },
        })
