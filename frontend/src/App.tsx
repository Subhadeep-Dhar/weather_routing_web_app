import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  CssBaseline,
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  CircularProgress,
} from '@mui/material';
import NavigationIcon from '@mui/icons-material/Navigation';
import { theme } from './theme';
import { Header } from './components/Header';
import { TripForm } from './components/TripForm';
import { RouteComparison } from './components/RouteComparison';
import { MapView } from './components/MapView';
import { ForecastSlider } from './components/ForecastSlider';
import { CheckpointDetails } from './components/CheckpointDetails';
import { SafetyLegend } from './components/SafetyLegend';
import { analyzeTrip, checkSystemHealth } from './api/client';
import type { TripAnalysisRequest, TripAnalysisResponse, Checkpoint } from './types/api';

export const App: React.FC = () => {
  const [analysisResult, setAnalysisResult] = useState<TripAnalysisResponse | null>(null);
  const [lastSubmittedReq, setLastSubmittedReq] = useState<TripAnalysisRequest | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [selectedRouteId, setSelectedRouteId] = useState<string>('');
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<Checkpoint | null>(null);
  const [hourOffset, setHourOffset] = useState<number>(0);
  const [showHeatmap, setShowHeatmap] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [serverHealthy, setServerHealthy] = useState<boolean>(true);

  // Check health on mount
  useEffect(() => {
    checkSystemHealth().then((healthy) => setServerHealthy(healthy));
  }, []);

  const handleTripSubmit = async (req: TripAnalysisRequest) => {
    setIsLoading(true);
    setErrorMessage(null);
    setLastSubmittedReq(req);
    setIsStale(false);
    try {
      const data = await analyzeTrip(req);
      setAnalysisResult(data);
      if (data.routes && data.routes.length > 0) {
        setSelectedRouteId(data.routes[0].route_id);
      }
      setSelectedCheckpoint(null);
      setHourOffset(0);
    } catch (err: any) {
      console.error('Trip analysis failed:', err);
      const msg =
        err?.response?.data?.error ||
        err?.message ||
        'Failed to calculate routes and weather. Please verify locations and backend connection.';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormDirty = () => {
    if (analysisResult) {
      setIsStale(true);
    }
  };

  const selectedRoute =
    analysisResult?.routes.find((r) => r.route_id === selectedRouteId) ||
    analysisResult?.routes[0] ||
    null;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', backgroundColor: '#f8f9fa', display: 'flex', flexDirection: 'column' }}>
        {/* Navigation Header */}
        <Header serverHealthy={serverHealthy} />

        {/* Main Application Container */}
        <Container maxWidth="xl" sx={{ py: 3, flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Grid container spacing={3} sx={{ flex: 1 }}>
            {/* Left Control Panel (Trip Inputs, Legend, Checkpoint Details) */}
            <Grid size={{ xs: 12, lg: 4 }} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <TripForm
                onSubmit={handleTripSubmit}
                isLoading={isLoading}
                errorMessage={errorMessage}
                onFormDirty={handleFormDirty}
              />

              {/* Selected Checkpoint Inspection Card */}
              {selectedCheckpoint && (
                <CheckpointDetails
                  checkpoint={selectedCheckpoint}
                  totalRouteDistanceMiles={selectedRoute?.distance_miles || 0}
                  onClose={() => setSelectedCheckpoint(null)}
                  hourOffset={hourOffset}
                />
              )}

              {/* Hazard & Threshold Legend */}
              <SafetyLegend />
            </Grid>

            {/* Right Map & Analysis Panel */}
            <Grid size={{ xs: 12, lg: 8 }} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {/* Honest Initial Empty State Card (Before analysis) */}
              {!analysisResult && (
                <Paper
                  elevation={0}
                  sx={{
                    p: 2.2,
                    borderRadius: 2.5,
                    border: '1px solid #c2e7ff',
                    backgroundColor: '#f8fafd',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      width: 44,
                      height: 44,
                      borderRadius: '50%',
                      backgroundColor: '#e8f0fe',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#1a73e8',
                      flexShrink: 0,
                    }}
                  >
                    <NavigationIcon fontSize="medium" />
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#1a73e8', mb: 0.25 }}>
                      Ready for Safe Route Analysis
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#5f6368', fontSize: '0.84rem', lineHeight: 1.35 }}>
                      Default corridor loaded: <strong>Siliguri, West Bengal → Gangtok, Sikkim</strong> (42,000 lb load, 10-mile interval). Click <strong>"Analyze Safe Routes"</strong> to evaluate turn-by-turn geometries, ETA-aligned weather forecasts, and commercial cargo wind overrides.
                    </Typography>
                  </Box>
                </Paper>
              )}

              {/* Route Comparison Options Cards */}
              {analysisResult && (
                <RouteComparison
                  routes={analysisResult.routes}
                  selectedRouteId={selectedRouteId}
                  onSelectRoute={(id) => {
                    setSelectedRouteId(id);
                    setSelectedCheckpoint(null);
                  }}
                  isStale={isStale}
                  onReanalyze={() => lastSubmittedReq && handleTripSubmit(lastSubmittedReq)}
                />
              )}

              {/* Interactive Map View */}
              <Box sx={{ flex: 1, minHeight: 450, position: 'relative' }}>
                {isLoading && (
                  <Paper
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      zIndex: 1100,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backdropFilter: 'blur(2px)',
                    }}
                  >
                    <CircularProgress size={48} sx={{ color: '#1a73e8', mb: 2 }} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#202124' }}>
                      Sampling Route Weather & Calculating Hazard Overrides...
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#5f6368' }}>
                      Evaluating OSRM corridors and Open-Meteo forecasts
                    </Typography>
                  </Paper>
                )}

                <MapView
                  routes={analysisResult?.routes || []}
                  selectedRoute={selectedRoute}
                  selectedCheckpoint={selectedCheckpoint}
                  onSelectRoute={(id) => {
                    setSelectedRouteId(id);
                    setSelectedCheckpoint(null);
                  }}
                  onSelectCheckpoint={(cp) => setSelectedCheckpoint(cp)}
                  hourOffset={hourOffset}
                  showHeatmap={showHeatmap}
                  onToggleHeatmap={() => setShowHeatmap(!showHeatmap)}
                />
              </Box>

              {/* 0-48 Hour Forecast Slider */}
              {analysisResult && (
                <ForecastSlider
                  currentHourOffset={hourOffset}
                  onHourChange={(h) => setHourOffset(h)}
                  baseDepartureTimeIso={analysisResult.request_params.departure_time}
                />
              )}
            </Grid>
          </Grid>
        </Container>
      </Box>
    </ThemeProvider>
  );
};

export default App;
