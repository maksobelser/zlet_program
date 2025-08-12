// frontend/src/components/SelectedTrailCard.jsx
import React from 'react';
import { Button } from '@mui/material';
import './SelectedTrailCard.css';  // ← make sure this stays!

export default function SelectedTrailCard({
  title,
  description,
  onCancel,
  equipment,   // ← new
  location,    // ← new
}) {
  return (
    <div className="selected-trail-card">
      <h2 className="selected-trail-card__title">{title}</h2>
      <p className="selected-trail-card__description">{description}</p>
      
      {/* NEW: show equipment if provided */}
      {equipment && (
        <p className="selected-trail-card__subtitle">
          <strong>Oprema:</strong><br />
          {equipment}
        </p>
      )}

      {/* NEW: show location if provided */}
      {location && (
        <p className="selected-trail-card__subtitle">
          <strong>Lokacija:</strong><br />
          {location}
        </p>
      )}

      {onCancel && title !== 'Izlet na morje' && (
        <Button
          variant="outlined"
          size="medium"
          onClick={onCancel}
          sx={{ mt: 2 }}
        >
          Prekliči prijavo
        </Button>
      )}
      <p className="selected-trail-card__message"></p>
    </div>
  );
}