import React from 'react';
import './LoaderOverlay.css';
import { useLoading } from '../contexts/LoadingContext';

export default function LoaderOverlay() {
  const { loading } = useLoading();

  if (!loading) return null;

  return (
    <div className="loader-backdrop" aria-hidden>
      <div className="loader-card" role="status" aria-live="polite">
        <div className="spinner" />
        <div className="loader-text">Working on your query…</div>
      </div>
    </div>
  );
}
