// frontend/src/components/ApplyFormProgramDop.jsx
import React, { useState, useEffect } from 'react';
import SelectableCard from './SelectableCard';
import SelectedTrailCard from './SelectedTrailCard';
import './ApplyForm.css';

import {
  Stepper,
  Step,
  StepButton,
  Box,
  Card,
  CardContent,
  Button,
  Typography,      // ← added
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const API_URL = process.env.REACT_APP_API_URL;
const PROGRAM_DAYS = ['Ned', 'Pon', 'Tor', 'Sre', 'Čet'];

export default function ApplyFormProgramDop({ onSubmit }) {
  const theme = useTheme();
  const token = localStorage.getItem('access_token');

  const [dayActivities, setDayActivities]                     = useState([]);
  const [appliedDays, setAppliedDays]                         = useState([]);
  const [selectedDay, setSelectedDay]                         = useState('');
  const [selectedOption, setSelectedOption]                   = useState(null);
  const [hasSubmitted, setHasSubmitted]                       = useState(false);
  const [isApplied, setIsApplied]                             = useState(false);
  const [selectedActivityDetails, setSelectedActivityDetails] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/morning_applications`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    })
      .then(async res => res.ok ? res.json() : [])
      .then(data => setAppliedDays(data.map(a => a.day)))
      .catch(console.error);
  }, [token]);

  const dayOptions = PROGRAM_DAYS;
  useEffect(() => {
    if (!selectedDay && dayOptions.length) {
      const defaultDay =
        appliedDays.find(d => dayOptions.includes(d)) ||
        dayOptions[0];
      setSelectedDay(defaultDay);
    }
  }, [dayOptions, appliedDays, selectedDay]);

  useEffect(() => {
    if (!selectedDay) return;
    let cancelled = false;

    async function loadForDay() {
      try {
        const appRes  = await fetch(
          `${API_URL}/morning_application?day=${encodeURIComponent(selectedDay)}`,
          {
            headers: { Authorization: `Bearer ${token}` },
            credentials: 'include',
          }
        );
        const appData = await appRes.json();
        if (cancelled) return;

        if (appRes.ok && appData.answers != null) {
          let ans = appData.answers;
          if (Array.isArray(ans)) ans = ans[0];

          setIsApplied(true);
          setHasSubmitted(true);
          setSelectedOption(String(ans));
          setSelectedActivityDetails({
            id:          String(appData.id),
            name:        appData.name,
            description: appData.description,
            free_spots:  appData.free_spots,
            equipment:   appData.equipment,
            location:    appData.location,
          });
          setDayActivities([]);
        } else {
          setIsApplied(false);
          setHasSubmitted(false);
          setSelectedOption(null);
          setSelectedActivityDetails(null);

          const listRes  = await fetch(
            `${API_URL}/morning_activities?day=${encodeURIComponent(selectedDay)}`,
            {
              headers: { Authorization: `Bearer ${token}` },
              credentials: 'include',
            }
          );
          if (!listRes.ok) throw new Error('Failed to fetch activities');
          const listData = await listRes.json();
          if (!cancelled) setDayActivities(listData);
        }
      } catch (err) {
        console.error(err);
      }
    }

    loadForDay();
    return () => { cancelled = true; };
  }, [token, selectedDay]);

  const handleSelect = id => {
    if (isApplied) return;
    setSelectedOption(id);
  };

  const handleSubmit = async e => {
    e?.preventDefault();
    if (!selectedOption) {
      alert('Prosim izberite eno od aktivnosti preden se prijavite.');
      return;
    }
    setHasSubmitted(true);
    try {
      const resp = await fetch(`${API_URL}/apply_morning`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          Authorization: `Bearer ${token}`,
        },
        credentials: 'include',
        body: new URLSearchParams({
          answers: selectedOption,
          day:     selectedDay,
        }),
      });
      if (!resp.ok) throw new Error('Submission failed');

      setIsApplied(true);
      setAppliedDays(prev =>
        prev.includes(selectedDay) ? prev : [...prev, selectedDay]
      );
      const chosen = dayActivities.find(a => String(a.id) === selectedOption);
      if (chosen) {
        setSelectedActivityDetails({
          id:          String(chosen.id),
          name:        chosen.name,
          description: chosen.description,
          free_spots:  chosen.free_spots,
          equipment:   null,
          location:    null,
        });
      }
      onSubmit(selectedOption);
    } catch (error) {
      console.error(error);
      alert('Nekaj je šlo narobe. Prosim, poskusite osvežiti stran.');
      setHasSubmitted(false);
    }
  };

  const handleStepClick = day => {
    setSelectedDay(day);
    setSelectedOption(null);
    setHasSubmitted(false);
    setIsApplied(false);
    setSelectedActivityDetails(null);
    setDayActivities([]);
  };

  const freeActivities = dayActivities.filter(a => a.free_spots > 0);

  return (
    <Box className="apply-form-container">
      {/* NAV CARD & DAY SELECTOR */}
      <Card className="nav-card">
        <CardContent className="nav-card__content">
          <Stepper
            nonLinear
            activeStep={dayOptions.indexOf(selectedDay)}
            alternativeLabel
            className="stepper"
          >
            {dayOptions.map(day => {
              const isActive = day === selectedDay;
              return (
                <Step
                  key={day}
                  completed={appliedDays.includes(day)}
                  className="step"
                >
                  <StepButton
                    sx={{
                      borderRadius: '50%',
                      color: isActive
                        ? theme.palette.primary.main
                        : 'inherit',
                      fontWeight: isActive ? 500 : undefined,
                    }}
                    icon={
                      appliedDays.includes(day)
                        ? <CheckCircleIcon fontSize="medium" />
                        : undefined
                    }
                    onClick={() => handleStepClick(day)}
                  >
                    {day}
                  </StepButton>
                </Step>
              );
            })}
          </Stepper>

          {/* program description */}
          <Box mt={2}>
            <Typography variant="body1" color="textSecondary" align="center" sx={{ fontWeight: 'bold' }}>
              Če ni drugače napisano, se dopoldanski program začne ob 9.00.
            </Typography>
          </Box>

          <Box textAlign="center" mt={2}>
            {!isApplied && (
              <Button
                variant="contained"
                size="large"
                onClick={handleSubmit}
                disabled={!selectedOption || hasSubmitted}
              >
                Prijava na program
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>

      <form className="apply-form" onSubmit={handleSubmit}>
        <div className={isApplied ? 'selected-card-container' : 'cards-container'}>
          {isApplied ? (
            selectedActivityDetails ? (
              <SelectedTrailCard
                title={selectedActivityDetails.name}
                description={selectedActivityDetails.description}
                freeSpots={selectedActivityDetails.free_spots}
                equipment={selectedActivityDetails.equipment}
                location={selectedActivityDetails.location}
              />
            ) : (
              <p>Ni najdene prijavljene aktivnosti za ta dan.</p>
            )
          ) : (
            freeActivities.map(act => (
              <SelectableCard
                key={act.id}
                id={String(act.id)}
                title={act.name}
                description={act.description}
                freeSpots={act.free_spots}
                selected={String(act.id) === selectedOption}
                onSelect={() => handleSelect(String(act.id))}
              />
            ))
          )}
        </div>
      </form>
    </Box>
);
}