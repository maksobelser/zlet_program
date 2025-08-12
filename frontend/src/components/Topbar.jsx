// frontend/src/components/Topbar.jsx

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Toolbar,
  IconButton,
  Button,
  Drawer,
  List,
  ListItem,
  ListItemText,
  useTheme,
  useMediaQuery,
  Typography     // ← import Typography
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
import { Link, useLocation } from 'react-router-dom';
import api from '../api';

// define pages once at module scope
const pages = [
  { key: 'bivak',       label: 'Bivak trasa',             path: '/prijava-bivak' },
  { key: 'program_dop', label: 'Dopoldanski program',     path: '/prijava-program-dop' },
  { key: 'program_pop', label: 'Prijava na pop program',  path: '/prijava-program-pop' },
  { key: 'prijave_vod', label: 'Prijave članov - popoldne',          path: '/prijave-clani' },
];

export default function Topbar() {
  const [isLeader, setIsLeader] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Fetch leader flag
  useEffect(() => {
    api.get('/users/me')
      .then(({ data }) => setIsLeader(data.leader))
      .catch(err => console.error(err));
  }, []);

  // Figure out which page is active
  const currentPageKey = useMemo(() => {
    const match = pages.find(p => p.path === location.pathname);
    return match ? match.key : null;
  }, [location.pathname]);

  // Get the current page’s label
  const currentPageLabel = useMemo(() => {
    const match = pages.find(p => p.key === currentPageKey);
    return match ? match.label : '';
  }, [currentPageKey]);

  // Filter pages based on leader flag
  const pagesToShow = isLeader
    ? pages.filter(p => ['bivak', 'program_dop', 'prijave_vod'].includes(p.key))
    : pages.filter(p => p.key === 'program_pop');

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/';
  };

  const toggleDrawer = open => event => {
    if (event.type === 'keydown' && (event.key === 'Tab' || event.key === 'Shift')) {
      return;
    }
    setDrawerOpen(open);
  };

  const drawerList = (
    <Box
      sx={{ width: 250 }}
      role="presentation"
      onClick={toggleDrawer(false)}
      onKeyDown={toggleDrawer(false)}
    >
      <List>
        {pagesToShow.map(page => (
          <ListItem
            button
            key={page.key}
            component={Link}
            to={page.path}
            selected={currentPageKey === page.key}
          >
            <ListItemText primary={page.label} />
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: 1400,
        mx: 'auto',
        pt: 2,
        pb: 2,
        px: 2
      }}
    >
      <Paper
        elevation={3}
        sx={{
          width: '100%',
          borderRadius: 4,
          border: '1px solid #ddd',
          backgroundColor: 'rgba(243, 234, 229, 0.96)'
        }}
      >
        <Toolbar
          sx={{
            minHeight: { xs: 56, sm: 64 },
            p: 0,
            px: 2,
            display: 'flex',
            alignItems: 'center'
          }}
        >
          {isMobile ? (
            <>
              <IconButton
                color="inherit"
                edge="start"
                onClick={toggleDrawer(true)}
                sx={{ mr: 1 }}
              >
                <MenuIcon />
              </IconButton>
              <Typography
                variant="subtitle1"
                component="div"
                sx={{ flexGrow: 1, ml: 1 }}
              >
                {currentPageLabel}
              </Typography>

              <Drawer
                anchor="left"
                open={drawerOpen}
                onClose={toggleDrawer(false)}
                PaperProps={{
                  sx: {
                    backgroundColor: 'rgba(243, 234, 229, 0.96)',
                  }
                }}
                BackdropProps={{
                  sx: { backgroundColor: 'rgba(0,0,0,0.1)' }
                }}
              >
                {drawerList}
              </Drawer>
            </>
          ) : (
            <Box sx={{ display: 'flex', gap: 1 }}>
              {pagesToShow.map(page => (
                <Button
                  key={page.key}
                  component={Link}
                  to={page.path}
                  variant={currentPageKey === page.key ? 'contained' : 'text'}
                  size="small"
                  color="inherit"
                >
                  {page.label}
                </Button>
              ))}
            </Box>
          )}

          {!isMobile && <Box sx={{ flexGrow: 1 }} />}
          <Button
            onClick={handleLogout}
            startIcon={<LogoutIcon />}
            variant="outlined"
            size="small"
            sx={isMobile ? { ml: 0 } : {}}
          >
            Odjava
          </Button>
        </Toolbar>
      </Paper>
    </Box>
  );
}