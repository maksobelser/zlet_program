// src/components/Login.js

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Box, TextField, Button, Typography, Alert } from '@mui/material';
import api from '../api';
import { saveToken } from '../utils/auth';

export default function Login() {
  const [email, setEmail] = useState('');
  const [memberId, setMemberId] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      // 1) log in
      const resp = await api.post(
        '/auth/jwt/login',
        new URLSearchParams({
          username: email,
          password: memberId,
        })
      );

      // 2) stash your token
      saveToken(resp.data.access_token);
      localStorage.setItem('access_token', resp.data.access_token);

      // 3) fetch your profile to see if you're a leader
      const { data: user } = await api.get('/users/me');

      // 4) route to the correct “entry” page
      if (user.leader) {
        navigate('/prijava-bivak');
      } else {
        navigate('/prijava-program-pop');
      }

    } catch (err) {
      const resp = err.response;
      // if login simply not open yet
      if (resp?.status === 403) {
        const detail = resp.data.detail || '';
        if (detail.includes('early applicants')) {
          setError(
            'Prijava še ni odprta za vaš vod.' +
            'Odprta bo 22. 6. 2025 ob 18:00.'
          );
        } else if (detail.includes('your group')) {
          setError(
            'Prijava še ni odprta za vaš vod. ' +
            'Odprta bo 24. 6. 2025 ob 18:00.'
          );
        } else {
          // fallback to whatever detail the server provided
          setError(detail);
        }
      } else {
        // invalid credentials or other errors
        setError('Prijava neuspešna, prosim preverite uporabniško ime in geslo.');
      }
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundImage: 'url(../wallpaper.jpeg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }}
    >
      <Container maxWidth="xs">
        <Box
          sx={{
            position: 'absolute',
            top: { xs: 16, sm: 32 },
            left: { xs: 16, sm: '50%' },
            transform: { xs: 'none', sm: 'translateX(-50%)' },
            p: 3,
            boxShadow: 3,
            borderRadius: 4,
            width: { xs: 'calc(100% - 32px)', sm: 380 },
            backgroundColor: 'rgba(255, 255, 255, 0.2)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(20px)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              mb: 2,
            }}
          >
            <Box>
              <Typography variant="h5" component="h1" gutterBottom>
                Prijava
              </Typography>
              <Typography variant="body1" sx={{ maxWidth: 300, mb: 2 }}>
                Če se ne uspete prijaviti,<br />prosim pišite na{' '}
                <a href="mailto:karin.krizman@taborniki.si">
                  karin.krizman@taborniki.si
                </a>
              </Typography>
            </Box>
            <img
              src="zlet-logo-transparent.png"
              alt="ZLET logo"
              style={{ height: 115, width: 'auto' }}
            />
          </Box>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: -1 }}>
            <TextField
              fullWidth
              required
              margin="normal"
              id="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              InputProps={{
                sx: { borderRadius: 4, backgroundColor: '#fff' },
              }}
            />
            <TextField
              fullWidth
              required
              margin="normal"
              id="clanska_st"
              placeholder="Članska številka"
              autoComplete="off"
              type="password"
              value={memberId}
              onChange={(e) => setMemberId(e.target.value)}
              InputProps={{
                sx: { borderRadius: 4, backgroundColor: '#fff' },
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{
                mt: 4,
                height: 56,
                borderRadius: 4,
                backgroundColor: '#000',
                color: '#fff',
                textTransform: 'none',
                '&:hover': { backgroundColor: '#555' },
                fontSize: 18,
                fontFamily: 'Mikado',
              }}
            >
              Prijava
            </Button>
          </Box>
        </Box>
      </Container>
    </Box>
  );
}