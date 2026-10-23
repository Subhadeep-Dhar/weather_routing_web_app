import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import InfoIcon from '@mui/icons-material/Info';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

interface HeaderProps {
  serverHealthy: boolean;
}

export const Header: React.FC<HeaderProps> = ({ serverHealthy }) => {
  const [infoOpen, setInfoOpen] = React.useState(false);

  return (
    <>
      <AppBar
        position="static"
        color="inherit"
        elevation={0}
        sx={{
          borderBottom: '1px solid #dadce0',
          backgroundColor: '#ffffff',
          px: { xs: 1, md: 3 },
        }}
      >
        <Toolbar disableGutters sx={{ justifyContent: 'space-between', minHeight: 64 }}>
          {/* Brand Identity */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                backgroundColor: '#e8f0fe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#1a73e8',
              }}
            >
              <LocalShippingIcon fontSize="medium" />
            </Box>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h6" component="div" sx={{ fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1.2 }}>
                  Spotter SafeRoute
                </Typography>
                <Chip
                  label="PRO"
                  size="small"
                  sx={{
                    height: 18,
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    backgroundColor: '#1a73e8',
                    color: '#ffffff',
                  }}
                />
              </Box>
              <Typography variant="caption" sx={{ color: '#5f6368', display: 'block', lineHeight: 1.1 }}>
                Weather-Aware Commercial Truck Routing & Safety Recommender
              </Typography>
            </Box>
          </Box>

          {/* Right Controls */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Chip
              icon={<CheckCircleIcon style={{ color: serverHealthy ? '#137333' : '#d93025' }} />}
              label={serverHealthy ? 'APIs Operational' : 'Offline / Reconnecting'}
              size="small"
              variant="outlined"
              sx={{
                borderColor: serverHealthy ? '#ceead6' : '#fad2cf',
                backgroundColor: serverHealthy ? '#e6f4ea' : '#fce8e6',
                color: serverHealthy ? '#137333' : '#d93025',
                fontSize: '0.75rem',
                display: { xs: 'none', sm: 'inline-flex' },
              }}
            />

            <Tooltip title="View Risk & Load Weight Rules">
              <IconButton size="small" onClick={() => setInfoOpen(true)} sx={{ color: '#5f6368' }}>
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Assessment Risk Rules Dialog */}
      <Dialog open={infoOpen} onClose={() => setInfoOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Spotter Weather Risk & Load Weight Assessment Rules
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            Weather Hazard Thresholds:
          </Typography>
          <Table size="small" sx={{ mb: 3 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f8f9fa' }}>
                <TableCell sx={{ fontWeight: 600 }}>Condition</TableCell>
                <TableCell sx={{ fontWeight: 600, color: '#137333' }}>Low</TableCell>
                <TableCell sx={{ fontWeight: 600, color: '#b06000' }}>Moderate</TableCell>
                <TableCell sx={{ fontWeight: 600, color: '#e37400' }}>High</TableCell>
                <TableCell sx={{ fontWeight: 600, color: '#d93025' }}>Severe</TableCell>
                <TableCell sx={{ fontWeight: 600, color: '#5c1319' }}>No Travel</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell sx={{ fontWeight: 500 }}>Wind</TableCell>
                <TableCell>&lt;25 mph</TableCell>
                <TableCell>25–34 mph</TableCell>
                <TableCell>35–44 mph</TableCell>
                <TableCell>45–54 mph</TableCell>
                <TableCell>&ge;55 mph</TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 500 }}>Rain</TableCell>
                <TableCell>&lt;0.10 in/hr</TableCell>
                <TableCell>0.10–0.25 in/hr</TableCell>
                <TableCell>0.25–0.50 in/hr</TableCell>
                <TableCell>0.50–1.00 in/hr</TableCell>
                <TableCell>&gt;1.00 in/hr</TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 500 }}>Snow</TableCell>
                <TableCell>&lt;0.5 in/hr</TableCell>
                <TableCell>0.5–1.0 in/hr</TableCell>
                <TableCell>1.0–2.0 in/hr</TableCell>
                <TableCell>2.0–3.0 in/hr</TableCell>
                <TableCell>&gt;3.0 in/hr</TableCell>
              </TableRow>
            </TableBody>
          </Table>

          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            Cargo-Weight Overrides:
          </Typography>
          <Box component="ul" sx={{ pl: 2, mb: 2, '& li': { mb: 0.5, fontSize: '0.9rem' } }}>
            <li><strong>&ge;55 mph Wind:</strong> No Travel for any cargo weight.</li>
            <li><strong>45–54 mph Wind AND cargo &gt;30,000 lb:</strong> No Travel override.</li>
            <li><strong>35–44 mph Wind AND cargo &gt;40,000 lb:</strong> Severe override.</li>
          </Box>

          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            Route Recommendation Priority:
          </Typography>
          <Box component="ol" sx={{ pl: 2, '& li': { mb: 0.5, fontSize: '0.9rem' } }}>
            <li><strong>1. Fewest Severe miles</strong> (strictly prioritized)</li>
            <li><strong>2. Fewest High-risk miles</strong></li>
            <li><strong>3. Lowest average risk score</strong></li>
            <li><strong>4. Shortest travel time</strong></li>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInfoOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
