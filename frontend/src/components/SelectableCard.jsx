// frontend/src/components/SelectableCard.jsx

import React from 'react';
import './SelectableCard.css';

export default function SelectableCard({
  id,
  title,
  description,
  freeSpots,
  selected,
  onSelect,
}) {
  return (
    <div
      className={`selectable-card ${selected ? 'selected' : ''}`}
      onClick={onSelect}
      id={id}
    >
      <div className="selectable-card__main">
        <h3 className="selectable-card__title">{title}</h3>
        <p className="selectable-card__description">{description}</p>
      </div>
      {typeof freeSpots === 'number' && (
        <p className="selectable-card__free">
          Prosta mesta: {freeSpots}
        </p>
      )}
    </div>
  );
}