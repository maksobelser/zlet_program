import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { CssBaseline } from '@mui/material';
import { ThemeProvider, createTheme, StyledEngineProvider } from '@mui/material/styles';

const theme = createTheme({
  typography: {
    // Default body font
    fontFamily: "'Open Sans', sans-serif",
    fontSize: 13, // Base font size in px
    fontWeightRegular: 400,
    fontWeightBold: 700,
    h1: {
      fontFamily: "'Mikado Black', 'Open Sans', sans-serif",
      fontWeight: 900,
      fontSize: '2.5rem',
    },
    h2: {
      fontFamily: "'Mikado Black', 'Open Sans', sans-serif",
      fontWeight: 900,
      fontSize: '2rem',
    },
    h3: {
      fontFamily: "'Mikado Black', 'Open Sans', sans-serif",
      fontWeight: 900,
    },
    h4: {
      fontFamily: "'Mikado Black', 'Open Sans', sans-serif",
      fontWeight: 900,
    },
    h5: {
      fontFamily: "'Mikado Black', 'Open Sans', sans-serif",
      fontWeight: 900,
    },
    h6: {
      fontFamily: "'Mikado' Black, 'Open Sans', sans-serif",
      fontWeight: 900,
    },
    body1: {
      fontFamily: "'Open Sans', sans-serif",
      fontWeight: 400,
    },
    body2: {
      fontFamily: "'Open Sans', sans-serif",
      fontWeight: 400,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <StyledEngineProvider injectFirst>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </StyledEngineProvider>
);