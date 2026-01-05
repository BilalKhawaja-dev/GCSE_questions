import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import './ThemeToggle.css';

const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label={`Switch to ${theme === 'default' ? 'pink floral' : 'default'} theme`}
      title={`Switch to ${theme === 'default' ? 'pink floral' : 'default'} theme`}
    >
      {theme === 'default' ? (
        <span className="theme-icon">🌸</span>
      ) : (
        <span className="theme-icon">🎨</span>
      )}
    </button>
  );
};

export default ThemeToggle;