/**
 * Custom hook for browser state management
 * Handles navigation history, metrics tracking, and load states
 */

import { useState, useCallback, useRef } from 'react';
import type {
  BrowserState,
  BrowserActions,
  HistoryEntry,
} from '../types';

const DEFAULT_URL = 'https://example.com';

/** Validates and normalizes a URL string */
const normalizeUrl = (url: string): string => {
  const trimmed = url.trim();
  if (trimmed === '') return DEFAULT_URL;
  
  // If it starts with http:// or https://, use as-is
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  
  // If it looks like a domain, add https://
  if (/^[a-zA-Z0-9][-a-zA-Z0-9]*\.[-a-zA-Z0-9.]+$/.test(trimmed) ||
      /^localhost(:\d+)?$/.test(trimmed)) {
    return `https://${trimmed}`;
  }
  
  // Otherwise, treat as a search query or default to https
  if (trimmed.includes('.') && !trimmed.includes(' ')) {
    return `https://${trimmed}`;
  }
  
  // Default to example.com for invalid inputs
  return DEFAULT_URL;
};

/** Hook return type with state and actions */
interface UseBrowserReturn {
  readonly state: BrowserState;
  readonly actions: BrowserActions;
}

export const useBrowser = (): UseBrowserReturn => {
  // Initialize session start time once
  const sessionStartTimeRef = useRef<number>(Date.now());
  
  const [state, setState] = useState<BrowserState>({
    currentUrl: DEFAULT_URL,
    history: [{ url: DEFAULT_URL, timestamp: Date.now() }],
    currentHistoryIndex: 0,
    isLoading: false,
    loadError: null,
    metrics: {
      pagesLoaded: 0,
      sessionStartTime: sessionStartTimeRef.current,
      failedLoads: 0,
      totalLoadTime: 0,
    },
    pageLoadStartTime: null,
  });

  /** Navigate to a new URL, adding to history */
  const navigate = useCallback((url: string): void => {
    const normalizedUrl = normalizeUrl(url);
    const newEntry: HistoryEntry = {
      url: normalizedUrl,
      timestamp: Date.now(),
    };

    setState((prev) => {
      // Remove any forward history when navigating to a new page
      const newHistory = prev.history.slice(0, prev.currentHistoryIndex + 1);
      
      return {
        ...prev,
        currentUrl: normalizedUrl,
        history: [...newHistory, newEntry],
        currentHistoryIndex: newHistory.length,
        isLoading: true,
        loadError: null,
        pageLoadStartTime: Date.now(),
      };
    });
  }, []);

  /** Go back in history if possible */
  const goBack = useCallback((): void => {
    setState((prev) => {
      if (prev.currentHistoryIndex <= 0) return prev;
      
      const newIndex = prev.currentHistoryIndex - 1;
      return {
        ...prev,
        currentUrl: prev.history[newIndex].url,
        currentHistoryIndex: newIndex,
        isLoading: true,
        loadError: null,
        pageLoadStartTime: Date.now(),
      };
    });
  }, []);

  /** Go forward in history if possible */
  const goForward = useCallback((): void => {
    setState((prev) => {
      if (prev.currentHistoryIndex >= prev.history.length - 1) return prev;
      
      const newIndex = prev.currentHistoryIndex + 1;
      return {
        ...prev,
        currentUrl: prev.history[newIndex].url,
        currentHistoryIndex: newIndex,
        isLoading: true,
        loadError: null,
        pageLoadStartTime: Date.now(),
      };
    });
  }, []);

  /** Reload the current page */
  const reload = useCallback((): void => {
    setState((prev) => ({
      ...prev,
      isLoading: true,
      loadError: null,
      pageLoadStartTime: Date.now(),
    }));
  }, []);

  /** Mark the start of a page load */
  const handleLoadStart = useCallback((): void => {
    setState((prev) => ({
      ...prev,
      isLoading: true,
      loadError: null,
      pageLoadStartTime: Date.now(),
    }));
  }, []);

  /** Handle successful page load and update metrics */
  const handleLoadSuccess = useCallback((): void => {
    setState((prev) => {
      const loadTime = prev.pageLoadStartTime 
        ? Date.now() - prev.pageLoadStartTime 
        : 0;
      
      return {
        ...prev,
        isLoading: false,
        loadError: null,
        metrics: {
          ...prev.metrics,
          pagesLoaded: prev.metrics.pagesLoaded + 1,
          totalLoadTime: prev.metrics.totalLoadTime + loadTime,
        },
        pageLoadStartTime: null,
      };
    });
  }, []);

  /** Handle page load error and update metrics */
  const handleLoadError = useCallback((error?: string): void => {
    setState((prev) => ({
      ...prev,
      isLoading: false,
      loadError: error || 'Failed to load page',
      metrics: {
        ...prev.metrics,
        failedLoads: prev.metrics.failedLoads + 1,
      },
      pageLoadStartTime: null,
    }));
  }, []);

  return {
    state,
    actions: {
      navigate,
      goBack,
      goForward,
      reload,
      handleLoadStart,
      handleLoadSuccess,
      handleLoadError,
    },
  };
};