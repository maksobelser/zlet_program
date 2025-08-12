import React from 'react';
import { Outlet } from 'react-router-dom';
import Topbar from './Topbar';
import { Box } from '@mui/material';

export default function Layout() {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column', // stack Topbar and content vertically
        height: '100vh',
        backgroundImage: "url(/wallpaper.jpeg)",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }}
    >
      <Topbar />
      <Box
        component="main"
        sx={{ p: 2, flexGrow: 1, overflow: 'auto' }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}