import React, { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  Chip,
  Collapse,
  Button,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { RISK_COLORS } from '../theme';

export const SafetyLegend: React.FC = () => {
  const [expanded, setExpanded] = useState(false);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: 2.5,
        border: '1px solid #dadce0',
        backgroundColor: '#ffffff',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="caption" sx={{ fontWeight: 700, color: '#3c4043', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Weather Hazard & Risk Legend
        </Typography>
        <Button
          size="small"
          onClick={() => setExpanded(!expanded)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ fontSize: '0.72rem', py: 0, minWidth: 'auto', color: '#1a73e8' }}
        >
          {expanded ? 'Hide Details' : 'View Thresholds'}
        </Button>
      </Box>

      {/* Primary Color Bar */}
      <Box sx={{ display: 'flex', gap: 0.75, mt: 1, flexWrap: 'wrap' }}>
        {(['Low', 'Moderate', 'High', 'Severe', 'No Travel'] as const).map((level) => {
          const style = RISK_COLORS[level];
          return (
            <Chip
              key={level}
              label={level}
              size="small"
              sx={{
                fontSize: '0.7rem',
                fontWeight: 600,
                backgroundColor: style.light,
                color: style.main,
                border: `1px solid ${style.border}`,
                height: 22,
              }}
            />
          );
        })}
      </Box>

      {/* Expandable Threshold Reference */}
      <Collapse in={expanded}>
        <Box sx={{ mt: 1.5, pt: 1, borderTop: '1px solid #f1f3f4', fontSize: '0.75rem', color: '#5f6368' }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, mb: 1 }}>
            <Box>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#202124', display: 'block' }}>
                Wind (mph)
              </Typography>
              <div>&lt;25: Low</div>
              <div>25–34: Mod</div>
              <div>35–44: High</div>
              <div>45–54: Severe</div>
              <div>&ge;55: No Travel</div>
            </Box>
            <Box>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#202124', display: 'block' }}>
                Rain (in/hr)
              </Typography>
              <div>&lt;0.10: Low</div>
              <div>0.10–0.25: Mod</div>
              <div>0.25–0.50: High</div>
              <div>0.50–1.00: Severe</div>
              <div>&gt;1.00: No Travel</div>
            </Box>
            <Box>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#202124', display: 'block' }}>
                Snow (in/hr)
              </Typography>
              <div>&lt;0.5: Low</div>
              <div>0.5–1.0: Mod</div>
              <div>1.0–2.0: High</div>
              <div>2.0–3.0: Severe</div>
              <div>&gt;3.0: No Travel</div>
            </Box>
          </Box>
          <Typography variant="caption" sx={{ display: 'block', fontStyle: 'italic', color: '#70757a' }}>
            * Cargo override: &gt;30k lb load at 45–54 mph triggers No Travel; &gt;40k lb at 35–44 mph triggers Severe.
          </Typography>
        </Box>
      </Collapse>
    </Paper>
  );
};
