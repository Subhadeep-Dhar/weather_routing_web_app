import React, { useState, useEffect } from 'react';
import {
  Paper,
  Box,
  Typography,
  TextField,
  Autocomplete,
  Button,
  CircularProgress,
  IconButton,
  ToggleButton,
  ToggleButtonGroup,
  Chip,
  Tooltip,
  Alert,
} from '@mui/material';
import SwapVertIcon from '@mui/icons-material/SwapVert';
import NavigationIcon from '@mui/icons-material/Navigation';
import FlashOnIcon from '@mui/icons-material/FlashOn';
import { fetchLocationSuggestions } from '../api/client';
import type { TripAnalysisRequest } from '../types/api';

interface TripFormProps {
  onSubmit: (req: TripAnalysisRequest) => void;
  isLoading: boolean;
  errorMessage: string | null;
  onFormDirty?: () => void;
}

export const TripForm: React.FC<TripFormProps> = ({ onSubmit, isLoading, errorMessage, onFormDirty }) => {
  const [originInput, setOriginInput] = useState('Siliguri, West Bengal, India');
  const [originOptions, setOriginOptions] = useState<string[]>([]);
  const [destInput, setDestInput] = useState('Gangtok, Sikkim, India');
  const [destOptions, setDestOptions] = useState<string[]>([]);

  // Departure date/time default to current time + 1 hour in local ISO string
  const [departureTime, setDepartureTime] = useState(() => {
    const d = new Date();
    d.setHours(d.getHours() + 1);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  });

  const [cargoWeight, setCargoWeight] = useState<number>(42000);
  const [intervalMiles, setIntervalMiles] = useState<10 | 25 | 50>(10);

  // Debounced autocomplete for Origin
  useEffect(() => {
    if (originInput.trim().length < 2) return;
    const timer = setTimeout(async () => {
      const suggestions = await fetchLocationSuggestions(originInput);
      setOriginOptions(suggestions.map((s) => s.name));
    }, 350);
    return () => clearTimeout(timer);
  }, [originInput]);

  // Debounced autocomplete for Destination
  useEffect(() => {
    if (destInput.trim().length < 2) return;
    const timer = setTimeout(async () => {
      const suggestions = await fetchLocationSuggestions(destInput);
      setDestOptions(suggestions.map((s) => s.name));
    }, 350);
    return () => clearTimeout(timer);
  }, [destInput]);

  const handleSwapLocations = () => {
    const temp = originInput;
    setOriginInput(destInput);
    setDestInput(temp);
    if (onFormDirty) onFormDirty();
  };

  const handlePresetTrip = (orig: string, dest: string, weight: number, interval: 10 | 25 | 50) => {
    setOriginInput(orig);
    setDestInput(dest);
    setCargoWeight(weight);
    setIntervalMiles(interval);
    if (onFormDirty) onFormDirty();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!originInput.trim() || !destInput.trim()) return;

    // Convert local datetime to UTC ISO string
    const utcIso = new Date(departureTime).toISOString();

    onSubmit({
      origin: originInput.trim(),
      destination: destInput.trim(),
      departure_time: utcIso,
      cargo_weight_lbs: Number(cargoWeight),
      checkpoint_interval_miles: intervalMiles,
    });
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: '1px solid #dadce0',
        backgroundColor: '#ffffff',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.05rem', color: '#202124' }}>
          Plan Truck Route
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Tooltip title="Reset to default corridor: Siliguri → Gangtok">
            <Button
              size="small"
              onClick={() => handlePresetTrip('Siliguri, West Bengal, India', 'Gangtok, Sikkim, India', 42000, 10)}
              sx={{ fontSize: '0.72rem', color: '#1a73e8', textTransform: 'none' }}
            >
              Default (India)
            </Button>
          </Tooltip>
          <Tooltip title="Load sample US highway corridor: Chicago → Indianapolis">
            <Button
              size="small"
              startIcon={<FlashOnIcon fontSize="small" />}
              onClick={() => handlePresetTrip('Chicago, IL', 'Indianapolis, IN', 42000, 25)}
              sx={{ fontSize: '0.72rem', color: '#5f6368', textTransform: 'none' }}
            >
              Sample US
            </Button>
          </Tooltip>
        </Box>
      </Box>

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2, fontSize: '0.85rem' }}>
          {errorMessage}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        {/* Origin Field */}
        <Box sx={{ mb: 1.5 }}>
          <Autocomplete
            freeSolo
            options={originOptions}
            value={originInput}
            onInputChange={(_, val) => {
              setOriginInput(val);
              if (onFormDirty) onFormDirty();
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Origin Location"
                size="small"
                required
                placeholder="e.g. Siliguri, West Bengal, India"
              />
            )}
          />
        </Box>

        {/* Swap Button */}
        <Box sx={{ display: 'flex', justifyContent: 'center', my: -0.75 }}>
          <IconButton size="small" onClick={handleSwapLocations} sx={{ color: '#5f6368' }}>
            <SwapVertIcon fontSize="small" />
          </IconButton>
        </Box>

        {/* Destination Field */}
        <Box sx={{ mb: 2 }}>
          <Autocomplete
            freeSolo
            options={destOptions}
            value={destInput}
            onInputChange={(_, val) => {
              setDestInput(val);
              if (onFormDirty) onFormDirty();
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Destination Location"
                size="small"
                required
                placeholder="e.g. Gangtok, Sikkim, India"
              />
            )}
          />
        </Box>

        {/* Departure Time */}
        <Box sx={{ mb: 2 }}>
          <TextField
            label="Departure Date & Time"
            type="datetime-local"
            size="small"
            fullWidth
            value={departureTime}
            onChange={(e) => {
              setDepartureTime(e.target.value);
              if (onFormDirty) onFormDirty();
            }}
            slotProps={{
              inputLabel: { shrink: true },
            }}
          />
        </Box>

        {/* Cargo Weight with Presets */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, color: '#3c4043' }}>
              Cargo Weight: {cargoWeight.toLocaleString()} lb
            </Typography>
            <Typography variant="caption" sx={{ color: '#5f6368' }}>
              {cargoWeight > 40000 ? 'Heavy Load (>40k)' : cargoWeight > 30000 ? 'Standard Load (>30k)' : 'Light/Empty (<30k)'}
            </Typography>
          </Box>
          <TextField
            type="number"
            size="small"
            fullWidth
            value={cargoWeight}
            onChange={(e) => {
              setCargoWeight(Math.max(0, Number(e.target.value)));
              if (onFormDirty) onFormDirty();
            }}
            slotProps={{
              htmlInput: { min: 0, max: 120000, step: 1000 },
            }}
            helperText="Impacts wind risk overrides: >30k lb triggers No Travel at 45-54 mph; >40k lb triggers Severe at 35-44 mph."
          />
          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.8, flexWrap: 'wrap' }}>
            {[
              { label: 'Empty (15k)', weight: 15000 },
              { label: 'Medium (30k)', weight: 30000 },
              { label: 'Heavy (42k)', weight: 42000 },
              { label: 'Max Gross (78k)', weight: 78000 },
            ].map((p) => (
              <Chip
                key={p.label}
                label={p.label}
                size="small"
                variant={cargoWeight === p.weight ? 'filled' : 'outlined'}
                color={cargoWeight === p.weight ? 'primary' : 'default'}
                onClick={() => {
                  setCargoWeight(p.weight);
                  if (onFormDirty) onFormDirty();
                }}
                sx={{ fontSize: '0.7rem', cursor: 'pointer' }}
              />
            ))}
          </Box>
        </Box>

        {/* Checkpoint Interval Selector */}
        <Box sx={{ mb: 2.5 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: '#3c4043', display: 'block', mb: 0.5 }}>
            Weather Sampling Frequency:
          </Typography>
          <ToggleButtonGroup
            value={intervalMiles}
            exclusive
            onChange={(_, val) => {
              if (val) {
                setIntervalMiles(val);
                if (onFormDirty) onFormDirty();
              }
            }}
            size="small"
            fullWidth
          >
            <ToggleButton value={10}>Every 10 mi</ToggleButton>
            <ToggleButton value={25}>Every 25 mi</ToggleButton>
            <ToggleButton value={50}>Every 50 mi</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Submit Button */}
        <Button
          type="submit"
          variant="contained"
          color="primary"
          fullWidth
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : <NavigationIcon />}
          sx={{ py: 1.2, fontWeight: 600, fontSize: '0.95rem' }}
        >
          {isLoading ? 'Analyzing Weather & Routes...' : 'Analyze Safe Routes'}
        </Button>
      </form>
    </Paper>
  );
};
