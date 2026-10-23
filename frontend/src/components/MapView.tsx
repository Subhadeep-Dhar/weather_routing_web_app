import React, { useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Box, Button, Typography, Chip } from '@mui/material';
import LayersIcon from '@mui/icons-material/Layers';
import type { RouteItem, Checkpoint } from '../types/api';
import { WeatherHeatmap } from './WeatherHeatmap';
import { RISK_COLORS } from '../theme';

interface MapViewProps {
  routes: RouteItem[];
  selectedRoute: RouteItem | null;
  selectedCheckpoint: Checkpoint | null;
  onSelectRoute: (routeId: string) => void;
  onSelectCheckpoint: (checkpoint: Checkpoint) => void;
  hourOffset: number;
  showHeatmap: boolean;
  onToggleHeatmap: () => void;
}

// Auto fit bounds helper component
const FitRouteBounds: React.FC<{ coordinates: [number, number][] }> = ({ coordinates }) => {
  const map = useMap();
  useEffect(() => {
    if (coordinates && coordinates.length > 0) {
      const latLngs = coordinates.map((coord) => [coord[1], coord[0]] as [number, number]);
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 13, animate: true });
    }
  }, [coordinates, map]);

  return null;
};

// Create custom circular DivIcon for checkpoints
function createCheckpointIcon(
  index: number,
  effectiveRisk: 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel' | 'Unknown',
  isSelected: boolean
): L.DivIcon {
  const style = RISK_COLORS[effectiveRisk] || RISK_COLORS.Low;
  const size = isSelected ? 32 : 26;
  const fontSize = isSelected ? 12 : 11;
  const borderWidth = isSelected ? 3 : 2;

  const html = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      background-color: ${style.main};
      border: ${borderWidth}px solid #ffffff;
      box-shadow: 0 2px 5px rgba(0,0,0,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: 700;
      font-size: ${fontSize}px;
      font-family: Roboto, sans-serif;
      transform: translate(-50%, -50%);
      cursor: pointer;
    ">
      ${index + 1}
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-checkpoint-pin',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Create start/destination terminal icons
function createTerminalIcon(label: string, color: string): L.DivIcon {
  const html = `
    <div style="
      background-color: ${color};
      color: #ffffff;
      border-radius: 12px;
      padding: 3px 8px;
      font-size: 11px;
      font-weight: 700;
      font-family: Roboto, sans-serif;
      box-shadow: 0 2px 6px rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      gap: 4px;
      border: 2px solid #ffffff;
      transform: translate(-50%, -100%);
      white-space: nowrap;
    ">
      ${label}
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-terminal-pin',
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
}

export const MapView: React.FC<MapViewProps> = ({
  routes,
  selectedRoute,
  selectedCheckpoint,
  onSelectRoute,
  onSelectCheckpoint,
  hourOffset,
  showHeatmap,
  onToggleHeatmap,
}) => {
  const defaultCenter: [number, number] = [39.8283, -98.5795]; // Center of USA
  const defaultZoom = 4;

  const activeCoordinates = selectedRoute?.geometry?.coordinates || [];

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        minHeight: { xs: 450, md: 550 },
        position: 'relative',
        borderRadius: 3,
        overflow: 'hidden',
        border: '1px solid #dadce0',
      }}
    >
      {/* Floating Map Controls */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 1000,
          display: 'flex',
          gap: 1,
        }}
      >
        <Button
          size="small"
          variant="contained"
          startIcon={<LayersIcon />}
          onClick={onToggleHeatmap}
          sx={{
            backgroundColor: showHeatmap ? '#1a73e8' : '#ffffff',
            color: showHeatmap ? '#ffffff' : '#3c4043',
            border: '1px solid #dadce0',
            fontSize: '0.78rem',
            fontWeight: 600,
            boxShadow: '0 1px 4px rgba(60,64,67,0.3)',
            '&:hover': {
              backgroundColor: showHeatmap ? '#1557b0' : '#f1f3f4',
            },
          }}
        >
          {showHeatmap ? 'Heatmap: Visible' : 'Heatmap: Hidden'}
        </Button>
      </Box>

      {/* Map Container */}
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        style={{ width: '100%', height: '100%' }}
        scrollWheelZoom={true}
      >
        {/* OpenStreetMap Standard Carto Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Fit Bounds automatically when route coordinates update */}
        {activeCoordinates.length > 0 && <FitRouteBounds coordinates={activeCoordinates} />}

        {/* Weather Heatmap Corridor Layer */}
        {selectedRoute && (
          <WeatherHeatmap
            checkpoints={selectedRoute.checkpoints}
            hourOffset={hourOffset}
            visible={showHeatmap}
          />
        )}

        {/* Inactive Alternative Routes (subtle gray with click to select) */}
        {routes
          .filter((r) => r.route_id !== selectedRoute?.route_id)
          .map((altRoute) => {
            const coords = altRoute.geometry?.coordinates?.map(
              (c) => [c[1], c[0]] as [number, number]
            ) || [];
            return (
              <Polyline
                key={`alt-${altRoute.route_id}`}
                positions={coords}
                pathOptions={{
                  color: '#9aa0a6',
                  weight: 4,
                  opacity: 0.65,
                  dashArray: '6, 8',
                }}
                eventHandlers={{
                  click: () => onSelectRoute(altRoute.route_id),
                }}
              />
            );
          })}

        {/* Active Selected Route Polyline (Bold Google Blue) */}
        {selectedRoute && activeCoordinates.length > 0 && (
          <Polyline
            positions={activeCoordinates.map((c) => [c[1], c[0]] as [number, number])}
            pathOptions={{
              color: '#1a73e8',
              weight: 6,
              opacity: 0.9,
            }}
          />
        )}

        {/* Origin Marker */}
        {activeCoordinates.length > 0 && (
          <Marker
            position={[activeCoordinates[0][1], activeCoordinates[0][0]]}
            icon={createTerminalIcon('ORIGIN', '#137333')}
          >
            <Popup>
              <strong>Trip Origin</strong>
            </Popup>
          </Marker>
        )}

        {/* Destination Marker */}
        {activeCoordinates.length > 0 && (
          <Marker
            position={[
              activeCoordinates[activeCoordinates.length - 1][1],
              activeCoordinates[activeCoordinates.length - 1][0],
            ]}
            icon={createTerminalIcon('DESTINATION', '#d93025')}
          >
            <Popup>
              <strong>Trip Destination</strong>
            </Popup>
          </Marker>
        )}

        {/* Checkpoint Markers with Risk Color & Number */}
        {selectedRoute?.checkpoints.map((cp) => {
          const timelineItem =
            hourOffset > 0 && cp.timeline_48h && cp.timeline_48h[hourOffset]
              ? cp.timeline_48h[hourOffset]
              : null;
          const currentRisk = timelineItem ? timelineItem.effective_risk : cp.effective_risk;
          const isSelected = selectedCheckpoint?.index === cp.index;

          return (
            <Marker
              key={`cp-${cp.index}`}
              position={[cp.lat, cp.lon]}
              icon={createCheckpointIcon(cp.index, currentRisk, isSelected)}
              eventHandlers={{
                click: () => onSelectCheckpoint(cp),
              }}
            >
              <Popup>
                <Box sx={{ p: 0.5 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    Checkpoint #{cp.index + 1} ({cp.distance_from_origin_miles.toFixed(1)} mi)
                  </Typography>
                  <Chip
                    label={currentRisk}
                    size="small"
                    sx={{
                      my: 0.5,
                      fontWeight: 700,
                      backgroundColor: RISK_COLORS[currentRisk]?.light,
                      color: RISK_COLORS[currentRisk]?.main,
                    }}
                  />
                  <Typography variant="body2" sx={{ fontSize: '0.8rem', color: '#3c4043' }}>
                    Wind: {timelineItem ? timelineItem.wind_speed_mph : cp.weather.wind_speed_mph} mph | Rain:{' '}
                    {timelineItem ? timelineItem.rain_intensity_in_hr : cp.weather.rain_intensity_in_hr} in/hr
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => onSelectCheckpoint(cp)}
                    sx={{ mt: 1, fontSize: '0.7rem' }}
                  >
                    Inspect Full Details
                  </Button>
                </Box>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </Box>
  );
};
