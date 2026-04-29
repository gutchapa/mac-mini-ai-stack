import React, { useCallback } from 'react';
import type { NavigationProps } from '../types';

/**
 * Navigation component with Back, Forward, and Reload buttons
 * Buttons are disabled based on navigation history state
 */
export const Navigation: React.FC<NavigationProps> = ({
  onBack,
  onForward,
  onReload,
  canGoBack,
  canGoForward,
  isLoading,
}) => {
  const handleBack = useCallback((): void => {
    if (canGoBack) onBack();
  }, [canGoBack, onBack]);

  const handleForward = useCallback((): void => {
    if (canGoForward) onForward();
  }, [canGoForward, onForward]);

  const handleReload = useCallback((): void => {
    onReload();
  }, [onReload]);

  return (
    <nav className="navigation-bar" aria-label="Browser navigation">
      <button
        type="button"
        onClick={handleBack}
        disabled={!canGoBack || isLoading}
        className="nav-button back-button"
        aria-label="Go back"
        title="Go back"
      >
        ← Back
      </button>
      <button
        type="button"
        onClick={handleForward}
        disabled={!canGoForward || isLoading}
        className="nav-button forward-button"
        aria-label="Go forward"
        title="Go forward"
      >
        Forward →
      </button>
      <button
        type="button"
        onClick={handleReload}
        disabled={isLoading}
        className="nav-button reload-button"
        aria-label="Reload page"
        title="Reload page"
      >
        {isLoading ? '⏳' : '↻'} Reload
      </button>
    </nav>
  );
};