import React, { useRef, useEffect, useCallback } from 'react';
import type { BrowserFrameProps } from '../types';

/**
 * BrowserFrame component - iframe wrapper for displaying web content
 * Handles load events and security attributes
 */
export const BrowserFrame: React.FC<BrowserFrameProps> = ({
  src,
  onLoad,
  onError,
  isLoading,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const lastSrcRef = useRef<string>(src);

  // Track src changes to detect reloads
  useEffect(() => {
    if (src !== lastSrcRef.current) {
      lastSrcRef.current = src;
    }
  }, [src]);

  const [blockedUrl, setBlockedUrl] = React.useState<string | null>(null);

  const handleLoad = useCallback((): void => {
    // Check if iframe actually has content or if it was blocked
    const iframe = iframeRef.current;
    if (iframe) {
      try {
        // If we can access contentDocument, it's same-origin (likely blocked site)
        // If it throws, it's cross-origin which is normal for external sites
        const doc = iframe.contentDocument;
        if (doc && doc.body && doc.body.innerHTML === '') {
          // Empty body suggests blocked content
          setBlockedUrl(src);
        } else {
          setBlockedUrl(null);
        }
      } catch {
        // Cross-origin error is expected for external sites
        setBlockedUrl(null);
      }
    }
    onLoad();
  }, [onLoad, src]);

  const handleError = useCallback((): void => {
    onError('Failed to load page');
  }, [onError]);

  // Handle iframe load timeout
  useEffect(() => {
    if (!isLoading) return;

    const timeoutId = window.setTimeout(() => {
      // If still loading after 30 seconds, treat as error
      if (isLoading) {
        onError();
      }
    }, 30000);

    return (): void => {
      window.clearTimeout(timeoutId);
    };
  }, [isLoading, onError, src]);

  return (
    <div className="browser-frame-container">
      {isLoading && (
        <div className="frame-loading-overlay" aria-live="polite">
          <div className="loading-indicator">
            <span className="loading-spinner-large" />
            <span>Loading...</span>
          </div>
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={src}
        onLoad={handleLoad}
        onError={handleError}
        className="browser-frame"
        title="Browser content"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
        allow="fullscreen"
      />
      {blockedUrl && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'white',
          padding: '20px',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
          textAlign: 'center',
          zIndex: 10
        }}>
          <h3>⚠️ Site Blocked</h3>
          <p><strong>{blockedUrl}</strong> prevents embedding.</p>
          <p style={{fontSize: '14px', color: '#666'}}>
            Try: example.com, wikipedia.org, github.com
          </p>
        </div>
      )}
    </div>
  );
};