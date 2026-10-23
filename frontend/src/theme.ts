import { createTheme } from '@mui/material/styles';

export const RISK_COLORS = {
  Low: {
    main: '#137333',
    light: '#e6f4ea',
    contrastText: '#ffffff',
    border: '#ceead6',
    label: 'Low Risk',
  },
  Moderate: {
    main: '#b06000',
    light: '#fef7e0',
    contrastText: '#ffffff',
    border: '#feefc3',
    label: 'Moderate Risk',
  },
  High: {
    main: '#e37400',
    light: '#feefe3',
    contrastText: '#ffffff',
    border: '#fedfc8',
    label: 'High Risk',
  },
  Severe: {
    main: '#d93025',
    light: '#fce8e6',
    contrastText: '#ffffff',
    border: '#fad2cf',
    label: 'Severe Risk',
  },
  'No Travel': {
    main: '#5c1319',
    light: '#f9d8d6',
    contrastText: '#ffffff',
    border: '#f2b8b5',
    label: 'No Travel Hazard',
  },
  Unknown: {
    main: '#5f6368',
    light: '#f1f3f4',
    contrastText: '#ffffff',
    border: '#dadce0',
    label: 'Data Unavailable',
  },
} as const;

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1a73e8', // Google Blue
      light: '#e8f0fe',
      dark: '#1557b0',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#5f6368', // Google Grey
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#202124',
      secondary: '#5f6368',
    },
    divider: '#dadce0',
  },
  typography: {
    fontFamily: '"Roboto", "Segoe UI", "Helvetica Neue", -apple-system, sans-serif',
    h5: {
      fontWeight: 600,
      letterSpacing: '-0.02em',
      color: '#202124',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1.1rem',
      color: '#202124',
    },
    subtitle1: {
      fontWeight: 500,
      fontSize: '0.95rem',
      color: '#3c4043',
    },
    body2: {
      fontSize: '0.85rem',
      color: '#5f6368',
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 1px 2px rgba(60,64,67,0.3)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: '1px solid #dadce0',
          boxShadow: '0 1px 3px rgba(60,64,67,0.08)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
  },
});
