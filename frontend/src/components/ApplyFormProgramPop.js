// frontend/src/components/ApplyFormProgramPop.jsx
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
// cancellation deadline: June 29, 2025 at 18:00 local time
const CANCEL_DEADLINE = new Date(2025, 5, 29, 18, 0, 0);

// -------------------------------------------------------------------
// Hard-coded program days (in Slovenian abbreviations)
// -------------------------------------------------------------------
const PROGRAM_DAYS = ['Ned', 'Pon', 'Tor', 'Sre', 'Čet'];

export default function ApplyFormProgramPop({ onSubmit }) {
  const theme = useTheme();
  const token = localStorage.getItem('access_token');

  // -------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------
  const [dayActivities, setDayActivities]                     = useState([]);
  const [appliedDays, setAppliedDays]                         = useState([]);
  const [selectedDay, setSelectedDay]                         = useState('');
  const [selectedOption, setSelectedOption]                   = useState(null);
  const [hasSubmitted, setHasSubmitted]                       = useState(false);
  const [isApplied, setIsApplied]                             = useState(false);
  const [selectedActivityDetails, setSelectedActivityDetails] = useState(null);

  // compute whether cancellation is still allowed
  const now       = new Date();
  const canCancel = now < CANCEL_DEADLINE;

  // -------------------------------------------------------------------
  // 1) fetch the days user has already applied (afternoon)
  // -------------------------------------------------------------------
  useEffect(() => {
    fetch(`${API_URL}/afternoon_applications`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    })
      .then(async res => {
        if (!res.ok) return [];
        return res.json();
      })
      .then(data => {
        setAppliedDays(data.map(a => a.day));
      })
      .catch(console.error);
  }, [token]);

  // -------------------------------------------------------------------
  // 2) derive & default the selectedDay
  // -------------------------------------------------------------------
  const dayOptions = PROGRAM_DAYS;
  useEffect(() => {
    if (!selectedDay && dayOptions.length) {
      const defaultDay =
        appliedDays.find(d => dayOptions.includes(d)) ||
        dayOptions[0];
      setSelectedDay(defaultDay);
    }
  }, [dayOptions, appliedDays, selectedDay]);

  // -------------------------------------------------------------------
  // 3) on each selectedDay change, first fetch "my application",
  //    then if not applied, fetch available activities.
  // -------------------------------------------------------------------
  useEffect(() => {
    if (!selectedDay) return;
    let cancelled = false;

    async function loadForDay() {
      try {
        // 3a) fetch my afternoon_application
        const appRes = await fetch(
          `${API_URL}/afternoon_application?day=${encodeURIComponent(selectedDay)}`,
          {
            headers: { Authorization: `Bearer ${token}` },
            credentials: 'include',
          }
        );
        const appData = await appRes.json();
        if (cancelled) return;

        if (appRes.ok && appData.answers != null) {
          // user has applied → show that and skip listing
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
          setDayActivities([]);  // clear previous list
        } else {
          // not applied → reset state, then fetch list
          setIsApplied(false);
          setHasSubmitted(false);
          setSelectedOption(null);
          setSelectedActivityDetails(null);

          const listRes = await fetch(
            `${API_URL}/afternoon_activities?day=${encodeURIComponent(selectedDay)}`,
            {
              headers: { Authorization: `Bearer ${token}` },
              credentials: 'include',
            }
          );
          const listData = await listRes.json();
          if (!listRes.ok) throw new Error(`Failed to fetch activities: ${listRes.status}`);
          if (!cancelled) {
            setDayActivities(listData);
          }
        }
      } catch (err) {
        console.error(err);
      }
    }

    loadForDay();
    return () => { cancelled = true; };
  }, [token, selectedDay]);

  // -------------------------------------------------------------------
  // handlers
  // -------------------------------------------------------------------
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
      const resp = await fetch(`${API_URL}/apply_afternoon`, {
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
      if (!resp.ok) throw new Error(`Submission failed: ${resp.status}`);

      // update local state
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

  const handleCancel = async () => {
    if (!selectedDay) return;
    try {
      const resp = await fetch(
        `${API_URL}/afternoon_application?day=${encodeURIComponent(selectedDay)}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
          credentials: 'include',
        }
      );
      if (!resp.ok) throw new Error(`Cancel failed: ${resp.status}`);

      // reset local state
      setIsApplied(false);
      setHasSubmitted(false);
      setSelectedOption(null);
      setSelectedActivityDetails(null);
      setAppliedDays(prev => prev.filter(d => d !== selectedDay));
    } catch (err) {
      console.error(err);
      alert('Nekaj je šlo narobe pri preklicu. Prosim, poskusite znova.');
    }
  };

  // -------------------------------------------------------------------
  // render
  // -------------------------------------------------------------------
  const freeActivities = dayActivities.filter(a => a.free_spots > 0);

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
                      color: isActive ? theme.palette.primary.main : 'inherit',
                      fontWeight: isActive ? 500 : undefined,
                    }}
                    icon={
                      appliedDays.includes(day)
                        ? <CheckCircleIcon fontSize="medium" />
                        : undefined
                    }
                    onClick={() => {
                      setSelectedDay(day);
                      setSelectedOption(null);
                      setHasSubmitted(false);
                      setIsApplied(false);
                      setSelectedActivityDetails(null);
                      setDayActivities([]);
                    }}
                  >
                    {day}
                  </StepButton>
                </Step>
              );
            })}
          </Stepper>

          {/* program description */}
          <Box mt={2}>
            <Typography variant="body1" color="textSecondary" align="center" sx={{ fontWeight: 'bold' }} >
              Če ni drugače napisano, se popoldanski program začne ob 14.30.
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
                onCancel={
                  selectedActivityDetails.name !== 'Izlet na morje' && canCancel
                    ? handleCancel
                    : undefined
                }
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