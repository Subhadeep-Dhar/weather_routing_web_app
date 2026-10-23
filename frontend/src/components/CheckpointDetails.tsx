import React from 'react';
import {
  Paper,
  Box,
  Typography,
  Chip,
  IconButton,
  Grid,
  Alert,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import AirIcon from '@mui/icons-material/Air';
import WaterDropIcon from '@mui/icons-material/WaterDrop';
import AcUnitIcon from '@mui/icons-material/AcUnit';
import ThermostatIcon from '@mui/icons-material/Thermostat';
import SpeedIcon from '@mui/icons-material/Speed';
import CloudQueueIcon from '@mui/icons-material/CloudQueue';
import type { Checkpoint } from '../types/api';
import { RISK_COLORS } from '../theme';

interface CheckpointDetailsProps {
  checkpoint: Checkpoint | null;
  totalRouteDistanceMiles: number;
  onClose: () => void;
  hourOffset: number;
}

export const CheckpointDetails: React.FC<CheckpointDetailsProps> = ({
  checkpoint,
  totalRouteDistanceMiles,
  onClose,
  hourOffset,
}) => {
  if (!checkpoint) return null;

  // If slider offset is active (>0), pull conditions from timeline_48h
  const timelineItem =
    hourOffset > 0 && checkpoint.timeline_48h && checkpoint.timeline_48h[hourOffset]
      ? checkpoint.timeline_48h[hourOffset]
      : null;

  const effectiveRisk = timelineItem ? timelineItem.effective_risk : checkpoint.effective_risk;
  const windMph = timelineItem ? timelineItem.wind_speed_mph : checkpoint.weather.wind_speed_mph;
  const rainInHr = timelineItem ? timelineItem.rain_intensity_in_hr : checkpoint.weather.rain_intensity_in_hr;
  const snowInHr = timelineItem ? timelineItem.snow_intensity_in_hr : checkpoint.weather.snow_intensity_in_hr;
  const tempF = timelineItem ? timelineItem.temperature_f : checkpoint.weather.temperature_f;
  const forecastTimestamp = timelineItem
    ? timelineItem.timestamp
    : checkpoint.weather.forecast_timestamp;

  const riskStyle = RISK_COLORS[effectiveRisk] || RISK_COLORS.Low;

  return (
    <Paper
      elevation={3}
      sx={{
        p: 2,
        borderRadius: 3,
        border: `1.5px solid ${riskStyle.border}`,
        backgroundColor: '#ffffff',
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={`Checkpoint #${checkpoint.index + 1}`}
            size="small"
            sx={{ fontWeight: 700, backgroundColor: '#f1f3f4', color: '#202124' }}
          />
          <Chip
            label={riskStyle.label}
            size="small"
            sx={{
              fontWeight: 700,
              backgroundColor: riskStyle.light,
              color: riskStyle.main,
              border: `1px solid ${riskStyle.border}`,
            }}
          />
          {hourOffset > 0 && (
            <Chip
              label={`Forecast +${hourOffset}h`}
              size="small"
              variant="outlined"
              color="primary"
              sx={{ fontSize: '0.68rem', height: 20 }}
            />
          )}
        </Box>

        <IconButton size="small" onClick={onClose} sx={{ color: '#5f6368' }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Transit & ETA Metric summary */}
      <Box sx={{ display: 'flex', gap: 2, mb: 1.5, color: '#3c4043', flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <SpeedIcon sx={{ fontSize: 16, color: '#5f6368' }} />
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            Mile {checkpoint.distance_from_origin_miles.toFixed(1)} / {totalRouteDistanceMiles.toFixed(1)}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ color: '#5f6368' }}>
          Segment: <strong>{checkpoint.segment_distance_miles.toFixed(1)} mi</strong>
        </Typography>
        <Typography variant="body2" sx={{ color: '#5f6368' }}>
          Arrival ETA:{' '}
          <strong>
            {new Date(checkpoint.eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </strong>
        </Typography>
      </Box>

      {/* Data Source & Forecast Horizon Banner */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 1.25,
          py: 0.75,
          mb: 1.5,
          borderRadius: 2,
          backgroundColor: '#f1f3f4',
          color: '#3c4043',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <CloudQueueIcon fontSize="small" sx={{ color: '#1a73e8' }} />
          <Typography variant="caption" sx={{ fontWeight: 600 }}>
            Data Source: Open-Meteo Forecast Model
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: '#5f6368' }}>
          Forecast Time: {forecastTimestamp.replace('T', ' ')}
        </Typography>
      </Box>

      {/* Cargo override banner if present */}
      {checkpoint.cargo_override_applied && (
        <Alert severity="warning" sx={{ py: 0.5, mb: 1.5, fontSize: '0.78rem' }}>
          <strong>Cargo Override Applied:</strong> {checkpoint.cargo_override_applied}
        </Alert>
      )}

      {/* Forecast unavailable notice if Unknown */}
      {effectiveRisk === 'Unknown' && (
        <Alert severity="info" sx={{ py: 0.5, mb: 1.5, fontSize: '0.78rem' }}>
          <strong>Forecast Notice:</strong> Hourly weather forecast is unavailable or out-of-range for this ETA. Exercise caution.
        </Alert>
      )}

      {/* Weather conditions grid */}
      <Grid container spacing={1}>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Box sx={{ p: 1, border: '1px solid #e8eaed', borderRadius: 2, textAlign: 'center', backgroundColor: '#f8f9fa' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 0.25 }}>
              <AirIcon fontSize="small" sx={{ color: '#1a73e8' }} />
              <Typography variant="caption" sx={{ fontWeight: 600, color: '#5f6368' }}>
                Wind Speed
              </Typography>
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {windMph !== null && windMph !== undefined ? `${windMph} mph` : 'N/A'}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.68rem', color: '#5f6368' }}>
              Class: {checkpoint.hazard_classifications.effective_wind}
            </Typography>
          </Box>
        </Grid>

        <Grid size={{ xs: 6, sm: 3 }}>
          <Box sx={{ p: 1, border: '1px solid #e8eaed', borderRadius: 2, textAlign: 'center', backgroundColor: '#f8f9fa' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 0.25 }}>
              <WaterDropIcon fontSize="small" sx={{ color: '#007b83' }} />
              <Typography variant="caption" sx={{ fontWeight: 600, color: '#5f6368' }}>
                Rain Intensity
              </Typography>
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {rainInHr !== null && rainInHr !== undefined ? `${rainInHr} in/hr` : 'N/A'}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.68rem', color: '#5f6368' }}>
              Class: {checkpoint.hazard_classifications.rain}
            </Typography>
          </Box>
        </Grid>

        <Grid size={{ xs: 6, sm: 3 }}>
          <Box sx={{ p: 1, border: '1px solid #e8eaed', borderRadius: 2, textAlign: 'center', backgroundColor: '#f8f9fa' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 0.25 }}>
              <AcUnitIcon fontSize="small" sx={{ color: '#185abc' }} />
              <Typography variant="caption" sx={{ fontWeight: 600, color: '#5f6368' }}>
                Snowfall
              </Typography>
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {snowInHr !== null && snowInHr !== undefined ? `${snowInHr} in/hr` : 'N/A'}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.68rem', color: '#5f6368' }}>
              Class: {checkpoint.hazard_classifications.snow}
            </Typography>
          </Box>
        </Grid>

        <Grid size={{ xs: 6, sm: 3 }}>
          <Box sx={{ p: 1, border: '1px solid #e8eaed', borderRadius: 2, textAlign: 'center', backgroundColor: '#f8f9fa' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 0.25 }}>
              <ThermostatIcon fontSize="small" sx={{ color: '#ea8600' }} />
              <Typography variant="caption" sx={{ fontWeight: 600, color: '#5f6368' }}>
                Temperature
              </Typography>
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {tempF !== null && tempF !== undefined ? `${tempF} °F` : 'N/A'}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.68rem', color: '#1a73e8', fontWeight: 600 }}>
              ETA Forecast
            </Typography>
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
};
