/**
 * Type definitions for the browser application
 * All interfaces use strict typing with no `any` types
 */

/** Represents a single entry in the browser history */
export interface HistoryEntry {
  readonly url: string;
  readonly timestamp: number;
  readonly title?: string;
}

/** Navigation state tracking for back/forward functionality */
export interface NavigationState {
  readonly canGoBack: boolean;
  readonly canGoForward: boolean;
  readonly currentIndex: number;
}

/** Metrics collected during a browsing session */
export interface SessionMetrics {
  readonly pagesLoaded: number;
  readonly sessionStartTime: number;
  readonly failedLoads: number;
  readonly totalLoadTime: number;
}

/** Props for the AddressBar component */
export interface AddressBarProps {
  readonly currentUrl: string;
  readonly onNavigate: (url: string) => void;
  readonly isLoading: boolean;
}

/** Props for the Navigation component */
export interface NavigationProps {
  readonly onBack: () => void;
  readonly onForward: () => void;
  readonly onReload: () => void;
  readonly canGoBack: boolean;
  readonly canGoForward: boolean;
  readonly isLoading: boolean;
}

/** Props for the BrowserFrame component */
export interface BrowserFrameProps {
  readonly src: string;
  readonly onLoad: () => void;
  readonly onError: (error?: string) => void;
  readonly isLoading: boolean;
}

/** Props for the Dashboard component */
export interface DashboardProps {
  readonly metrics: SessionMetrics;
  readonly currentUrl: string;
  readonly historyLength: number;
}

/** Complete browser state managed by useBrowser hook */
export interface BrowserState {
  readonly currentUrl: string;
  readonly history: readonly HistoryEntry[];
  readonly currentHistoryIndex: number;
  readonly isLoading: boolean;
  readonly loadError: string | null;
  readonly metrics: SessionMetrics;
  readonly pageLoadStartTime: number | null;
}

/** Actions available from the useBrowser hook */
export interface BrowserActions {
  readonly navigate: (url: string) => void;
  readonly goBack: () => void;
  readonly goForward: () => void;
  readonly reload: () => void;
  readonly handleLoadStart: () => void;
  readonly handleLoadSuccess: () => void;
  readonly handleLoadError: (error?: string) => void;
}