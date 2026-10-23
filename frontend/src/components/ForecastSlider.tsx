import React, { useState, useEffect } from 'react';
import {
  Paper,
  Box,
  Typography,
  Slider,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import ReplayIcon from '@mui/icons-material/Replay';
import ScheduleIcon from '@mui/icons-material/Schedule';

interface ForecastSliderProps {
  currentHourOffset: number;
  onHourChange: (hour: number) => void;
  baseDepartureTimeIso: string;
}

export const ForecastSlider: React.FC<ForecastSliderProps> = ({
  currentHourOffset,
  onHourChange,
  baseDepartureTimeIso,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);

  // Playback timer
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isPlaying) {
      interval = setInterval(() => {
        if (currentHourOffset >= 48) {
          setIsPlaying(false);
        } else {
          onHourChange(currentHourOffset + 1);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, currentHourOffset, onHourChange]);

  // Compute forecasted date/time
  const forecastedDateStr = React.useMemo(() => {
    try {
      const dt = new Date(baseDepartureTimeIso);
      dt.setHours(dt.getHours() + currentHourOffset);
      return dt.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return `+${currentHourOffset} hrs`;
    }
  }, [baseDepartureTimeIso, currentHourOffset]);

  return (
    <Paper
      elevation={2}
      sx={{
        p: 2,
        borderRadius: 3,
        border: '1px solid #dadce0',
        backgroundColor: '#ffffff',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScheduleIcon sx={{ color: '#1a73e8', fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#202124' }}>
            0–48 Hour Trip Corridor Forecast Slider
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={`+${currentHourOffset} hrs`}
            color={currentHourOffset === 0 ? 'default' : 'primary'}
            size="small"
            sx={{ fontWeight: 700, fontSize: '0.75rem' }}
          />
          <Typography variant="caption" sx={{ fontWeight: 600, color: '#3c4043' }}>
            {forecastedDateStr}
          </Typography>
        </Box>
      </Box>

      {/* Slider Control Row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Tooltip title={isPlaying ? 'Pause forecast simulation' : 'Simulate 48h weather progression'}>
          <IconButton
            size="small"
            color="primary"
            onClick={() => setIsPlaying(!isPlaying)}
            sx={{ border: '1px solid #dadce0' }}
          >
            {isPlaying ? <PauseIcon fontSize="small" /> : <PlayArrowIcon fontSize="small" />}
          </IconButton>
        </Tooltip>

        <Tooltip title="Reset to Departure Time (+0h)">
          <IconButton
            size="small"
            onClick={() => {
              setIsPlaying(false);
              onHourChange(0);
            }}
            sx={{ color: '#5f6368' }}
          >
            <ReplayIcon fontSize="small" />
          </IconButton>
        </Tooltip>

        <Box sx={{ flex: 1, px: 1 }}>
          <Slider
            value={currentHourOffset}
            min={0}
            max={48}
            step={1}
            marks={[
              { value: 0, label: '0h (Depart)' },
              { value: 12, label: '+12h' },
              { value: 24, label: '+24h' },
              { value: 36, label: '+36h' },
              { value: 48, label: '+48h' },
            ]}
            onChange={(_, val) => {
              setIsPlaying(false);
              onHourChange(val as number);
            }}
            valueLabelDisplay="auto"
            valueLabelFormat={(val) => `+${val}h`}
            sx={{
              color: '#1a73e8',
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
              '& .MuiSlider-markLabel': {
                fontSize: '0.7rem',
                color: '#5f6368',
              },
            }}
          />
        </Box>
      </Box>
    </Paper>
  );
};
