from rest_framework import serializers
from datetime import datetime, timezone


class TripAnalysisRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Origin city, address, or lat,lon string"
    )
    destination = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Destination city, address, or lat,lon string"
    )
    departure_time = serializers.DateTimeField(
        required=False,
        default=lambda: datetime.now(timezone.utc),
        help_text="ISO 8601 departure timestamp"
    )
    cargo_weight_lbs = serializers.FloatField(
        required=True,
        min_value=0.0,
        max_value=150000.0,
        help_text="Cargo weight in pounds (0 to 150,000 lb)"
    )
    checkpoint_interval_miles = serializers.ChoiceField(
        choices=[10, 25, 50],
        default=25,
        help_text="Checkpoint interval: 10, 25, or 50 miles"
    )
