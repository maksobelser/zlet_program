// frontend/src/components/ListApplicationsLeader.js
import React, { useState, useEffect } from 'react';
import {
  Stepper,
  Step,
  StepButton,
  Box,
  Card,
  CardContent,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TableContainer,
  Paper,
  Typography,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SelectedTrailCard from './SelectedTrailCard';
import './ListApplicationsLeader.css';

const API_URL = process.env.REACT_APP_API_URL;
// cancellation deadline: June 29, 2025 at 18:00 local time
const CANCEL_DEADLINE = new Date(2025, 5, 29, 18, 0, 0);
// Hard-coded program days (in Slovenian abbreviations)
const PROGRAM_DAYS = ['Ned', 'Pon', 'Tor', 'Sre', 'Čet'];

export default function ListApplicationsLeader() {
  const token = localStorage.getItem('access_token');

  const [appliedDays, setAppliedDays]             = useState([]);
  const [selectedDay, setSelectedDay]             = useState('');
  const [groupApplications, setGroupApplications] = useState([]);

  const now       = new Date();
  const canCancel = now < CANCEL_DEADLINE;
  const dayOptions = PROGRAM_DAYS;

  // 1) fetch which days the leader has ANY afternoon applications
  useEffect(() => {
    fetch(`${API_URL}/afternoon_applications`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    })
      .then(async res => (res.ok ? res.json() : []))
      .then(data => setAppliedDays(data.map(a => a.day)))
      .catch(console.error);
  }, [token]);

  // 2) pick a default selectedDay
  useEffect(() => {
    if (!selectedDay && dayOptions.length) {
      const defaultDay =
        appliedDays.find(d => dayOptions.includes(d)) ||
        dayOptions[0];
      setSelectedDay(defaultDay);
    }
  }, [dayOptions, appliedDays, selectedDay]);

  // 3) fetch group applications whenever selectedDay changes
  useEffect(() => {
    if (!selectedDay) return;

    fetch(
      `${API_URL}/group_applications?day=${encodeURIComponent(selectedDay)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
      }
    )
      .then(async res => {
        if (!res.ok) {
          throw new Error(`Fetch failed: ${res.status}`);
        }
        return res.json();
      })
      .then(data => setGroupApplications(data))
      .catch(console.error);
  }, [token, selectedDay]);

  // only treat it as the “Izlet na morje” card when every application is exactly that
  const isIzletDay =
    groupApplications.length > 0 &&
    groupApplications.every(app => app.name === 'Izlet na morje');

  return (
    <Box className="apply-form-container">
      <Card className="nav-card">
        <CardContent className="nav-card__content">
          <Stepper
            nonLinear
            activeStep={dayOptions.indexOf(selectedDay)}
            alternativeLabel
            className="stepper"
          >
            {dayOptions.map(day => (
              <Step
                key={day}
                completed={appliedDays.includes(day)}
                className="step"
              >
                <StepButton
                  sx={{ borderRadius: '50%' }}
                  icon={
                    appliedDays.includes(day)
                      ? <CheckCircleIcon fontSize="medium" />
                      : undefined
                  }
                  onClick={() => setSelectedDay(day)}
                >
                  {day}
                </StepButton>
              </Step>
            ))}
          </Stepper>
          {/* program description */}
          <Box mt={2}>
            <Typography variant="body1" color="textSecondary" align="center" sx={{ fontWeight: 'bold' }}>
              Če ni drugače napisano, se popoldanski program začne ob 14.30.
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Removed any padding here so the table spans flush with the cards */}
      <Box sx={{ maxWidth: 1400, margin: '0 auto', px: 0 }}>
        {groupApplications.length > 0 ? (
          isIzletDay ? (
            // grab title/description from the API response
            <SelectedTrailCard
              title={groupApplications[0]?.name}
              description={groupApplications[0]?.description}
            />
          ) : (
            <TableContainer component={Paper} className="table-card">
              <Table sx={{ tableLayout: 'fixed', width: '100%' }}>
                <colgroup>
                  <col style={{ width: '18%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '40%' }} />
                  <col style={{ width: '22%' }} />
                </colgroup>
                <TableHead>
                  <TableRow>
                    <TableCell>Ime in Priimek</TableCell>
                    <TableCell>Program</TableCell>
                    <TableCell>Oprema</TableCell>
                    <TableCell>Lokacija</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {groupApplications.map(app => (
                    <TableRow key={app.user_id}>
                      <TableCell>
                        {[app.first_name, app.surname].filter(Boolean).join(' ')}
                      </TableCell>
                      <TableCell>{app.name ?? '-'}</TableCell>
                        <TableCell className="table-card__preline">
                          {app.equipment ?? '-'}
                        </TableCell>                      
                      <TableCell>{app.location ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )
        ) : (
          <Typography align="center">
            Ni prijav vaših članov skupine za ta dan.
          </Typography>
        )}
      </Box>
    </Box>
  );
}