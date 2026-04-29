import React, { useState, useCallback, type FormEvent, type ChangeEvent } from 'react';
import type { AddressBarProps } from '../types';

/**
 * AddressBar component for URL input and navigation
 * Includes validation and loading state indicator
 */
export const AddressBar: React.FC<AddressBarProps> = ({
  currentUrl,
  onNavigate,
  isLoading,
}) => {
  const [inputValue, setInputValue] = useState<string>(currentUrl);
  const [isFocused, setIsFocused] = useState<boolean>(false);

  // Update input when currentUrl changes externally
  React.useEffect(() => {
    if (!isFocused) {
      setInputValue(currentUrl);
    }
  }, [currentUrl, isFocused]);

  const handleSubmit = useCallback((e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    onNavigate(inputValue);
  }, [inputValue, onNavigate]);

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>): void => {
    setInputValue(e.target.value);
  }, []);

  const handleFocus = useCallback((): void => {
    setIsFocused(true);
  }, []);

  const handleBlur = useCallback((): void => {
    setIsFocused(false);
    // Reset to current URL if empty or on blur
    if (inputValue.trim() === '') {
      setInputValue(currentUrl);
    }
  }, [inputValue, currentUrl]);

  return (
    <form onSubmit={handleSubmit} className="address-bar">
      <div className={`address-bar-container ${isLoading ? 'loading' : ''}`}>
        <span className="protocol-indicator">
          {currentUrl.startsWith('https') ? '🔒' : '⚠️'}
        </span>
        <input
          type="text"
          value={inputValue}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder="Enter URL or search..."
          className="address-input"
          aria-label="Address bar"
        />
        {isLoading && <span className="loading-spinner" aria-label="Loading" />}
        <button 
          type="submit" 
          className="navigate-button"
          aria-label="Navigate to URL"
        >
          →
        </button>
      </div>
    </form>
  );
};