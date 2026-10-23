from django.urls import path
from .views import HealthCheckView, GeocodeAutocompleteView, TripAnalysisView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('geocode/', GeocodeAutocompleteView.as_view(), name='geocode_autocomplete'),
    path('routes/analyze/', TripAnalysisView.as_view(), name='trip_analysis'),
]
