import React from 'react';
import { Circle, LayerGroup } from 'react-leaflet';
import type { Checkpoint } from '../types/api';

interface WeatherHeatmapProps {
  checkpoints: Checkpoint[];
  hourOffset: number;
  visible: boolean;
}

// Converts weather severity (wind, rain, snow) to real heatmap color and opacity
function getHeatmapColorAndOpacity(
  windMph: number,
  rainInHr: number,
  snowInHr: number
): { color: string; fillOpacity: number; radiusMeters: number } {
  // Compute normalized hazard intensity (0.0 to 1.0)
  const windScore = Math.min(windMph / 60.0, 1.0);
  const rainScore = Math.min(rainInHr / 1.5, 1.0);
  const snowScore = Math.min(snowInHr / 4.0, 1.0);

  const maxHazard = Math.max(windScore, rainScore, snowScore);

  let color = '#34a853'; // Clear green
  let fillOpacity = 0.22;
  const baseRadius = 24000; // ~15 miles radius corridor circle

  if (maxHazard > 0.8 || windMph >= 55 || rainInHr > 1.0 || snowInHr > 3.0) {
    color = '#5c1319'; // Severe / No Travel deep dark red
    fillOpacity = 0.55;
  } else if (maxHazard > 0.6 || windMph >= 45 || rainInHr >= 0.5 || snowInHr >= 2.0) {
    color = '#d93025'; // Severe Google Red
    fillOpacity = 0.48;
  } else if (maxHazard > 0.4 || windMph >= 35 || rainInHr >= 0.25 || snowInHr >= 1.0) {
    color = '#ea8600'; // High Orange
    fillOpacity = 0.40;
  } else if (maxHazard > 0.2 || windMph >= 25 || rainInHr >= 0.1 || snowInHr >= 0.5) {
    color = '#f9ab00'; // Moderate Amber
    fillOpacity = 0.32;
  }

  return { color, fillOpacity, radiusMeters: baseRadius };
}

export const WeatherHeatmap: React.FC<WeatherHeatmapProps> = ({
  checkpoints,
  hourOffset,
  visible,
}) => {
  if (!visible || !checkpoints || checkpoints.length === 0) return null;

  return (
    <LayerGroup>
      {checkpoints.map((cp) => {
        const timelineItem =
          hourOffset > 0 && cp.timeline_48h && cp.timeline_48h[hourOffset]
            ? cp.timeline_48h[hourOffset]
            : null;

        const wind = timelineItem ? timelineItem.wind_speed_mph : cp.weather.wind_speed_mph;
        const rain = timelineItem ? timelineItem.rain_intensity_in_hr : cp.weather.rain_intensity_in_hr;
        const snow = timelineItem ? timelineItem.snow_intensity_in_hr : cp.weather.snow_intensity_in_hr;

        const { color, fillOpacity, radiusMeters } = getHeatmapColorAndOpacity(wind, rain, snow);

        return (
          <React.Fragment key={`heatmap-${cp.index}-${hourOffset}`}>
            {/* Outer halo */}
            <Circle
              center={[cp.lat, cp.lon]}
              radius={radiusMeters * 1.4}
              pathOptions={{
                color: 'transparent',
                fillColor: color,
                fillOpacity: fillOpacity * 0.4,
                weight: 0,
              }}
            />
            {/* Inner core corridor intensity */}
            <Circle
              center={[cp.lat, cp.lon]}
              radius={radiusMeters}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: fillOpacity,
                weight: 1,
                opacity: 0.3,
              }}
            />
          </React.Fragment>
        );
      })}
    </LayerGroup>
  );
};
