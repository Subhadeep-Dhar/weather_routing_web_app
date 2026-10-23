import React from 'react';
import { Circle, LayerGroup } from 'react-leaflet';
import type { Checkpoint } from '../types/api';

interface WeatherHeatmapProps {
  checkpoints: Checkpoint[];
  hourOffset: number;
  visible: boolean;
}

/**
 * Derives dynamic heatmap color, opacity, and radius from actual weather values.
 * Uses exact assessment risk thresholds:
 * - Wind: 25 / 35 / 45 / 55 mph
 * - Rain: 0.10 / 0.25 / 0.50 / 1.00 in/hr
 * - Snow: 0.5 / 1.0 / 2.0 / 3.0 in/hr
 */
export function getHeatmapColorAndOpacity(
  windMph: number,
  rainInHr: number,
  snowInHr: number,
  segmentMiles: number = 25
): { color: string; fillOpacity: number; radiusMeters: number } {
  const windScore = Math.min(windMph / 55.0, 1.0);
  const rainScore = Math.min(rainInHr / 1.0, 1.0);
  const snowScore = Math.min(snowInHr / 3.0, 1.0);
  const maxHazard = Math.max(windScore, rainScore, snowScore);

  // Corridor radius scaled proportionally to segment spacing (bounded between 12km and 25km)
  const baseRadius = Math.max(12000, Math.min(25000, segmentMiles * 1200));

  let color = '#34a853'; // Clear / Low risk green
  let fillOpacity = 0.06 + 0.08 * maxHazard; // Subtle for calm weather, avoids opaque fog

  if (windMph >= 55.0 || rainInHr > 1.0 || snowInHr > 3.0) {
    color = '#5c1319'; // No Travel
    fillOpacity = Math.min(0.70, 0.52 + 0.18 * maxHazard);
  } else if (windMph >= 45.0 || rainInHr >= 0.5 || snowInHr >= 2.0) {
    color = '#d93025'; // Severe
    fillOpacity = Math.min(0.60, 0.40 + 0.15 * maxHazard);
  } else if (windMph >= 35.0 || rainInHr >= 0.25 || snowInHr >= 1.0) {
    color = '#ea8600'; // High
    fillOpacity = Math.min(0.48, 0.30 + 0.12 * maxHazard);
  } else if (windMph >= 25.0 || rainInHr >= 0.10 || snowInHr >= 0.5) {
    color = '#f9ab00'; // Moderate
    fillOpacity = Math.min(0.38, 0.20 + 0.10 * maxHazard);
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
        const segDist = cp.segment_distance_miles || 25;

        const { color, fillOpacity, radiusMeters } = getHeatmapColorAndOpacity(
          wind,
          rain,
          snow,
          segDist
        );

        return (
          <React.Fragment key={`heatmap-${cp.index}-${hourOffset}`}>
            {/* Outer halo for smooth corridor blending */}
            <Circle
              center={[cp.lat, cp.lon]}
              radius={radiusMeters * 1.3}
              pathOptions={{
                color: 'transparent',
                fillColor: color,
                fillOpacity: fillOpacity * 0.35,
                weight: 0,
              }}
            />
            {/* Core weather intensity */}
            <Circle
              center={[cp.lat, cp.lon]}
              radius={radiusMeters}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: fillOpacity,
                weight: 1,
                opacity: 0.25,
              }}
            />
          </React.Fragment>
        );
      })}
    </LayerGroup>
  );
};
