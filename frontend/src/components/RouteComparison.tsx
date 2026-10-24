import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  Alert,
  Tooltip,
} from '@mui/material';
import StarIcon from '@mui/icons-material/Star';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import StraightenIcon from '@mui/icons-material/Straighten';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import type { RouteItem } from '../types/api';
import { RISK_COLORS } from '../theme';

interface RouteComparisonProps {
  routes: RouteItem[];
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
  isStale?: boolean;
  onReanalyze?: () => void;
}

export const RouteComparison: React.FC<RouteComparisonProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
  isStale = false,
  onReanalyze,
}) => {
  if (!routes || routes.length === 0) return null;

  const selectedRoute = routes.find((r) => r.route_id === selectedRouteId) || routes[0];

  return (
    <Box sx={{ mb: 2 }}>
      {/* Parameter change warning banner */}
      {isStale && (
        <Alert
          severity="warning"
          sx={{
            mb: 2,
            fontSize: '0.82rem',
            alignItems: 'center',
            backgroundColor: '#fef7e0',
            border: '1px solid #f9ab00',
            color: '#7a4100',
          }}
          action={
            onReanalyze ? (
              <Chip
                label="Recalculate Routes"
                color="warning"
                size="small"
                onClick={onReanalyze}
                sx={{ fontWeight: 700, cursor: 'pointer' }}
              />
            ) : undefined
          }
        >
          <strong>Trip parameters were changed.</strong> The route options below reflect previous calculations. Click <strong>"Analyze Safe Routes"</strong> to update weather hazard projections.
        </Alert>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: '#202124' }}>
          Evaluated Route Options ({routes.length})
        </Typography>
        <Typography variant="caption" sx={{ color: '#5f6368' }}>
          Ranked by: 1. Severe Miles → 2. High Miles → 3. Avg Risk → 4. Time
        </Typography>
      </Box>

      <Grid container spacing={1.5}>
        {routes.map((route) => {
          const isSelected = route.route_id === selectedRouteId;
          const isRecommended = route.is_recommended;

          return (
            <Grid key={route.route_id} size={{ xs: 12, md: 4 }}>
              <Card
                elevation={0}
                sx={{
                  border: isSelected ? '2px solid #1a73e8' : '1px solid #dadce0',
                  borderRadius: 2.5,
                  backgroundColor: isSelected ? '#f8fafd' : '#ffffff',
                  position: 'relative',
                  transition: 'all 0.15s ease-in-out',
                  height: '100%',
                  '&:hover': {
                    borderColor: isSelected ? '#1a73e8' : '#bdc1c6',
                    boxShadow: '0 2px 6px rgba(60,64,67,0.12)',
                  },
                }}
              >
                <CardActionArea
                  onClick={() => onSelectRoute(route.route_id)}
                  sx={{ p: 0.5, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}
                >
                  <CardContent sx={{ p: 1.5, pb: '12px !important' }}>
                    {/* Header Badges */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                        <Chip
                          label={`Option ${route.rank}`}
                          size="small"
                          sx={{
                            fontWeight: 700,
                            fontSize: '0.7rem',
                            backgroundColor: isSelected ? '#1a73e8' : '#f1f3f4',
                            color: isSelected ? '#ffffff' : '#3c4043',
                          }}
                        />
                        {isRecommended && (
                          <Chip
                            icon={<StarIcon sx={{ fontSize: '13px !important', color: '#ffffff !important' }} />}
                            label={route.is_weather_complete ? "RECOMMENDED" : "RECOMMENDED (INCOMPLETE COV)"}
                            size="small"
                            sx={{
                              fontWeight: 700,
                              fontSize: '0.68rem',
                              backgroundColor: route.is_weather_complete ? '#137333' : '#b06000',
                              color: '#ffffff',
                            }}
                          />
                        )}
                      </Box>

                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 600,
                          color: route.average_risk_score !== null ? '#5f6368' : '#d93025',
                        }}
                      >
                        {route.average_risk_score !== null
                          ? `Avg Risk: ${route.average_risk_score.toFixed(2)}${!route.is_weather_complete ? ` (${route.weather_coverage_pct}% cov)` : ''}`
                          : 'Avg Risk: N/A (Unknown)'}
                      </Typography>
                    </Box>

                    {/* Route Name */}
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#202124', mb: 1, lineHeight: 1.2 }}>
                      {route.name}
                    </Typography>

                    {/* Distance & Time */}
                    <Box sx={{ display: 'flex', gap: 1.5, mb: 1, color: '#3c4043', alignItems: 'flex-start' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.2 }}>
                        <StraightenIcon sx={{ fontSize: 16, color: '#5f6368' }} />
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {route.distance_miles} mi
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                        <AccessTimeIcon sx={{ fontSize: 16, color: '#1a73e8', mt: 0.2 }} />
                        <Tooltip
                          title={
                            <Box sx={{ p: 0.5 }}>
                              <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', color: '#8ab4f8', mb: 0.5 }}>
                                Heuristic Transit Model Breakdown:
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block' }}>
                                • <strong>Heuristic Truck ETA:</strong> {route.duration_hours} hrs ({route.average_truck_speed_mph || '~25'} mph avg)
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block' }}>
                                • <strong>Raw OSRM Car Baseline:</strong> {route.duration_raw_osrm_hours || route.duration_hours} hrs ({route.raw_implied_car_speed_kmh || '~75'} km/h)
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block' }}>
                                • <strong>Terrain:</strong> {route.terrain_label || 'Standard Highway'} (Elev span: {route.elevation_span_meters ? `${Math.round(route.elevation_span_meters)}m` : '0m'})
                              </Typography>
                              {route.model_assumptions && route.model_assumptions.length > 0 && (
                                <Typography variant="caption" sx={{ display: 'block', fontStyle: 'italic', color: '#dadce0', mt: 0.5 }}>
                                  Heuristic Rule: {route.model_assumptions[0]}
                                </Typography>
                              )}
                            </Box>
                          }
                        >
                          <Box sx={{ cursor: 'help' }}>
                            <Typography variant="body2" sx={{ fontWeight: 700, color: '#1a73e8', lineHeight: 1.2 }}>
                              ~{route.duration_hours} hrs*
                            </Typography>
                            {route.duration_raw_osrm_hours && (
                              <Typography variant="caption" sx={{ color: '#70757a', fontSize: '0.67rem', display: 'block' }}>
                                (Car: {route.duration_raw_osrm_hours}h)
                              </Typography>
                            )}
                          </Box>
                        </Tooltip>
                      </Box>
                      <Box sx={{ ml: 'auto', textAlign: 'right' }}>
                        <Typography variant="caption" sx={{ color: '#5f6368', display: 'block', fontSize: '0.7rem' }}>
                          {route.checkpoint_count} checks
                        </Typography>
                        {route.terrain_label && (
                          <Chip
                            label={route.terrain_label.split('/')[0].trim()}
                            size="small"
                            sx={{
                              fontSize: '0.62rem',
                              height: 18,
                              backgroundColor: route.terrain_classification === 'mountain' ? '#fef7e0' : route.terrain_classification === 'ghat_corridor' ? '#e8f0fe' : '#f1f3f4',
                              color: route.terrain_classification === 'mountain' ? '#b06000' : route.terrain_classification === 'ghat_corridor' ? '#1a73e8' : '#5f6368',
                              fontWeight: 600,
                              mt: 0.25,
                            }}
                          />
                        )}
                      </Box>
                    </Box>

                    {/* Hazard Breakdown Mileage Chips */}
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1.5 }}>
                      {route.risk_mileage.no_travel_miles > 0 && (
                        <Tooltip title="No Travel Miles: Unsafe conditions">
                          <Chip
                            label={`No Travel: ${route.risk_mileage.no_travel_miles} mi`}
                            size="small"
                            sx={{
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              backgroundColor: RISK_COLORS['No Travel'].light,
                              color: RISK_COLORS['No Travel'].main,
                              border: `1px solid ${RISK_COLORS['No Travel'].border}`,
                            }}
                          />
                        </Tooltip>
                      )}

                      <Tooltip title="Severe Risk Miles">
                        <Chip
                          label={`Severe: ${route.risk_mileage.severe_miles} mi`}
                          size="small"
                          sx={{
                            fontSize: '0.68rem',
                            fontWeight: 600,
                            backgroundColor: route.risk_mileage.severe_miles > 0 ? RISK_COLORS.Severe.light : '#f8f9fa',
                            color: route.risk_mileage.severe_miles > 0 ? RISK_COLORS.Severe.main : '#70757a',
                            border: `1px solid ${route.risk_mileage.severe_miles > 0 ? RISK_COLORS.Severe.border : '#e8eaed'}`,
                          }}
                        />
                      </Tooltip>

                      <Tooltip title="High Risk Miles">
                        <Chip
                          label={`High: ${route.risk_mileage.high_miles} mi`}
                          size="small"
                          sx={{
                            fontSize: '0.68rem',
                            fontWeight: 600,
                            backgroundColor: route.risk_mileage.high_miles > 0 ? RISK_COLORS.High.light : '#f8f9fa',
                            color: route.risk_mileage.high_miles > 0 ? RISK_COLORS.High.main : '#70757a',
                            border: `1px solid ${route.risk_mileage.high_miles > 0 ? RISK_COLORS.High.border : '#e8eaed'}`,
                          }}
                        />
                      </Tooltip>

                      <Tooltip title="Moderate Risk Miles">
                        <Chip
                          label={`Mod: ${route.risk_mileage.moderate_miles} mi`}
                          size="small"
                          sx={{
                            fontSize: '0.68rem',
                            backgroundColor: route.risk_mileage.moderate_miles > 0 ? RISK_COLORS.Moderate.light : '#f8f9fa',
                            color: route.risk_mileage.moderate_miles > 0 ? RISK_COLORS.Moderate.main : '#70757a',
                          }}
                        />
                      </Tooltip>

                      <Tooltip title="Low Risk Miles">
                        <Chip
                          label={`Low: ${route.risk_mileage.low_miles} mi`}
                          size="small"
                          sx={{
                            fontSize: '0.68rem',
                            backgroundColor: RISK_COLORS.Low.light,
                            color: RISK_COLORS.Low.main,
                          }}
                        />
                      </Tooltip>

                      {route.risk_mileage.unknown_miles > 0 && (
                        <Tooltip title={`Unmonitored Segments: Weather forecast unavailable (${route.weather_coverage_pct}% coverage)`}>
                          <Chip
                            label={`Unknown: ${route.risk_mileage.unknown_miles} mi`}
                            size="small"
                            sx={{
                              fontSize: '0.68rem',
                              fontWeight: 600,
                              backgroundColor: '#f1f3f4',
                              color: '#5f6368',
                              border: '1px dashed #dadce0',
                            }}
                          />
                        </Tooltip>
                      )}
                    </Box>

                    {/* Incomplete Coverage Alert if present */}
                    {!route.is_weather_complete && (
                      <Alert
                        severity="warning"
                        icon={<WarningAmberIcon fontSize="inherit" />}
                        sx={{
                          py: 0.2,
                          px: 1,
                          mb: 1,
                          fontSize: '0.72rem',
                          backgroundColor: '#fef7e0',
                          color: '#b06000',
                          '& .MuiAlert-icon': { mr: 0.5 },
                        }}
                      >
                        Incomplete weather coverage ({route.weather_coverage_pct}%) — safety cannot be fully evaluated
                      </Alert>
                    )}

                    {/* No Travel Alert if present */}
                    {route.has_no_travel && (
                      <Alert
                        severity="error"
                        icon={<WarningAmberIcon fontSize="inherit" />}
                        sx={{
                          py: 0.2,
                          px: 1,
                          mb: 1,
                          fontSize: '0.72rem',
                          backgroundColor: '#fce8e6',
                          color: '#c5221f',
                          '& .MuiAlert-icon': { mr: 0.5 },
                        }}
                      >
                        Dangerous: Contains No Travel segments
                      </Alert>
                    )}

                    {/* Recommendation Reasons */}
                    <Box sx={{ mt: 0.5, borderTop: '1px dashed #e8eaed', pt: 0.8 }}>
                      {route.recommendation_reasons.slice(0, 2).map((reason, idx) => (
                        <Typography
                          key={idx}
                          variant="caption"
                          sx={{
                            display: 'block',
                            fontSize: '0.72rem',
                            color: isRecommended ? '#137333' : '#5f6368',
                            fontWeight: isRecommended ? 600 : 400,
                            lineHeight: 1.25,
                          }}
                        >
                          • {reason}
                        </Typography>
                      ))}
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Contextual Corridor Warning Notice */}
      {selectedRoute && selectedRoute.terrain_classification === 'mountain' && (
        <Alert
          severity="warning"
          icon={<WarningAmberIcon fontSize="small" />}
          sx={{
            mt: 1.5,
            fontSize: '0.78rem',
            backgroundColor: '#fef7e0',
            color: '#7a4100',
            border: '1px solid #f9ab00',
            '& .MuiAlert-icon': { color: '#b06000' },
          }}
        >
          <strong>Mountain Corridor Notice ({selectedRoute.terrain_label}):</strong> Severe elevation change ({selectedRoute.elevation_span_meters ? `${Math.round(selectedRoute.elevation_span_meters)}m` : 'mountain'} rise) and high sinuosity ({selectedRoute.sinuosity}x). Heuristic transit model governs heavy commercial speed to 20–28 km/h (12–17 mph) for low-gear engine braking and torque limits, with operational buffers for brake-cooling and checkpoint queues.
        </Alert>
      )}

      {selectedRoute && selectedRoute.terrain_classification === 'ghat_corridor' && (
        <Alert
          severity="info"
          sx={{
            mt: 1.5,
            fontSize: '0.78rem',
            backgroundColor: '#e8f0fe',
            color: '#174ea6',
            border: '1px solid #c2e7ff',
          }}
        >
          <strong>Ghat Pass Corridor Notice ({selectedRoute.terrain_label}):</strong> Route crosses a mountainous pass section ({selectedRoute.elevation_span_meters ? `${Math.round(selectedRoute.elevation_span_meters)}m` : 'ghat'} span). Durations reflect heuristic heavy-vehicle crawl speeds through switchbacks combined with connecting highway cruising.
        </Alert>
      )}

      {/* Unified duration transparency footnote */}
      <Box sx={{ mt: 1.5, px: 0.5 }}>
        <Typography variant="caption" sx={{ color: '#5f6368', fontSize: '0.72rem', display: 'block', lineHeight: 1.35 }}>
          *<strong>Heuristic Transit Duration Transparency:</strong> Displays an <em>Estimated Commercial Truck Transit Time</em> derived from transparent heuristic transport engineering assumptions (mountain grade crawl speeds, high sinuosity cornering, fleet speed limiters, and standard commercial rest buffers) alongside the unconstrained <em>OSRM Car Baseline</em>. <em>Observed transit times</em> are not tracked and will vary with live traffic congestion, border inspections, and weather events.
        </Typography>
      </Box>
    </Box>
  );
};
