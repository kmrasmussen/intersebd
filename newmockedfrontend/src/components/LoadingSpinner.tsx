import React from 'react';

const LoadingSpinner: React.FC = () => {
  // Basic inline styles for a simple spinner
  const spinnerStyle: React.CSSProperties = {
    border: '4px solid rgba(0, 0, 0, 0.1)',
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    borderLeftColor: '#09f', // Or your theme color
    animation: 'spin 1s ease infinite',
  };

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh', // Take full viewport height
  };

  // Keyframes need to be added globally, e.g., in your index.css or App.css
  // Add this to your global CSS file:
  /*
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  */

  return (
    <div style={containerStyle}>
      <div style={spinnerStyle}></div>
    </div>
  );
};

export default LoadingSpinner;