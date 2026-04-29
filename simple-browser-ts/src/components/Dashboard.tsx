import React from 'react';
import type { SessionMetrics } from '../types';

interface DashboardProps {
  readonly metrics: SessionMetrics;
}

export const Dashboard: React.FC<DashboardProps> = ({ metrics }) => {
  const sessionDuration = Math.floor((Date.now() - metrics.sessionStartTime) / 60000);
  const avgLoadTime = metrics.pagesLoaded > 0
    ? Math.round(metrics.totalLoadTime / metrics.pagesLoaded / 1000)
    : 0;

  return (
    <div style={{
      backgroundColor: 'white',
      padding: '15px',
      borderBottom: '1px solid #ddd'
    }}>
      <h3 style={{ margin: '0 0 10px 0' }}>📊 Dashboard</h3>
      <div style={{
        display: 'flex',
        justifyContent: 'space-around'
      }}>
        <Metric label="Pages Loaded" value={metrics.pagesLoaded.toString()} />
        <Metric label="Session Time" value={`${sessionDuration}m`} />
        <Metric label="Failed Loads" value={metrics.failedLoads.toString()} />
        <Metric label="Avg Load Time" value={`${avgLoadTime}s`} />
      </div>
    </div>
  );
};

interface MetricProps {
  readonly label: string;
  readonly value: string;
}

const Metric: React.FC<MetricProps> = ({ label, value }) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{
      fontSize: '24px',
      fontWeight: 'bold',
      color: '#6200ee'
    }}>
      {value}
    </div>
    <div style={{
      fontSize: '12px',
      color: '#666'
    }}>
      {label}
    </div>
  </div>
);

export default Dashboard;
