import React, { useState } from 'react';
import { AddressBar } from './components/AddressBar';
import { BrowserFrame } from './components/BrowserFrame';
import { Navigation } from './components/Navigation';
import { Dashboard } from './components/Dashboard';
import { useBrowser } from './hooks/useBrowser';

export const App: React.FC = () => {
  const { state, actions } = useBrowser();
  const [showDashboard, setShowDashboard] = useState(false);

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: '#6200ee',
        color: 'white',
        padding: '12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h1 style={{ margin: 0, fontSize: '18px' }}>🌐 Simple Browser</h1>
        <button 
          onClick={() => setShowDashboard(!showDashboard)}
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            color: 'white',
            padding: '8px 12px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          {showDashboard ? '✕' : '📊'}
        </button>
      </div>

      {/* Dashboard */}
      {showDashboard && <Dashboard metrics={state.metrics} />}

      {/* Navigation */}
      <Navigation
        canGoBack={state.currentHistoryIndex > 0}
        canGoForward={state.currentHistoryIndex < state.history.length - 1}
        onBack={actions.goBack}
        onForward={actions.goForward}
        onReload={actions.reload}
        isLoading={state.isLoading}
      />

      {/* Address Bar */}
      <AddressBar
        currentUrl={state.currentUrl}
        onNavigate={actions.navigate}
        isLoading={state.isLoading}
      />

      {/* Browser Frame */}
      <BrowserFrame
        src={state.currentUrl}
        onLoad={actions.handleLoadSuccess}
        onError={actions.handleLoadError}
        isLoading={state.isLoading}
      />
    </div>
  );
};

export default App;
