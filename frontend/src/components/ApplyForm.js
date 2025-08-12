// frontend/src/components/ApplyForm.jsx

import React, { useState, useEffect } from 'react';
import SelectableCard from './SelectableCard';
import SelectedTrailCard from './SelectedTrailCard';
import './ApplyForm.css';

const API_URL = process.env.REACT_APP_API_URL;

export default function ApplyForm({ onSubmit }) {
  const token = localStorage.getItem('access_token');
  const [trails, setTrails] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [isApplied, setIsApplied] = useState(false);

  // fetch trails
  useEffect(() => {
    fetch(`${API_URL}/trails`, {
      headers: { 'Authorization': `Bearer ${token}` },
      credentials: 'include',
    })
      .then(async res => {
        if (!res.ok) throw new Error(`Failed to fetch trails: ${res.status}`);
        const data = await res.json();
        setTrails(data);
      })
      .catch(console.error);
  }, [token]);

  // check existing application
  useEffect(() => {
    fetch(`${API_URL}/application`, {
      headers: { 'Authorization': `Bearer ${token}` },
      credentials: 'include',
    })
      .then(async res => {
        if (res.ok) {
          const data = await res.json();
          setSelectedOption(data.answers);
          setHasSubmitted(true);
          setIsApplied(true);
        }
      })
      .catch(() => {});
  }, [token]);

  const handleSelect = id => {
    if (isApplied) return;
    setSelectedOption(id);
  };

  const handleSubmit = async e => {
    e.preventDefault();
    if (!selectedOption) {
      alert('Prosim izberite eno od poti preden se prijavite.');
      return;
    }
    setHasSubmitted(true);
    try {
      const resp = await fetch(`${API_URL}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
        body: new URLSearchParams({ answers: selectedOption }),
      });
      if (!resp.ok) throw new Error(`Submission failed with status ${resp.status}`);
      setIsApplied(true);
      onSubmit(selectedOption);
    } catch (error) {
      console.error(error);
      alert('Nekaj je šlo narobe. Prosim, poskusite osvežiti stran.');
      setHasSubmitted(false);
    }
  };

  // free‐spot filter before apply
  const freeSpotTrails = trails.filter(t => t.free_spots > 0);
  const chosenTrail = trails.find(t => String(t.id) === selectedOption);

  return (
    <form className="apply-form" onSubmit={handleSubmit}>
      {!isApplied && (
        <button
          type="submit"
          className="apply-form__next"
          disabled={!selectedOption || hasSubmitted}
        >
          Prijava na traso
        </button>
      )}

      <div className={isApplied ? 'selected-card-container' : 'cards-container'}>
        {isApplied ? (
          chosenTrail && (
            <SelectedTrailCard
              title={chosenTrail.name}
              description={chosenTrail.description}
            />
          )
        ) : (
          freeSpotTrails.map(trail => (
            <SelectableCard
              key={trail.id}
              id={String(trail.id)}
              title={trail.name}
              description={trail.description}
              freeSpots={trail.free_spots}
              selected={String(trail.id) === selectedOption}
              onSelect={() => handleSelect(String(trail.id))}
            />
          ))
        )}
      </div>
    </form>
  );
}