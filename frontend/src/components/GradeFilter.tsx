import React from 'react';
import { GradeFilterType, GRADE_FILTERS } from '../data/topicPresets';
import './GradeFilter.css';

interface GradeFilterProps {
  activeFilter: GradeFilterType;
  onFilterChange: (filter: GradeFilterType) => void;
  theme: 'default' | 'pink-floral';
}

const GradeFilter: React.FC<GradeFilterProps> = ({ activeFilter, onFilterChange, theme }) => {
  return (
    <div className={`grade-filter-compact ${theme}`}>
      <span className="filter-prompt">I want</span>
      <div className="filter-pills">
        {GRADE_FILTERS.map((filter) => (
          <button
            key={filter.value}
            className={`filter-pill ${activeFilter === filter.value ? 'active' : ''} ${filter.value === 'foundation' ? 'foundation-tier' : filter.value === 'higher' ? 'higher-tier' : ''}`}
            onClick={() => onFilterChange(filter.value)}
            type="button"
            aria-pressed={activeFilter === filter.value}
          >
            {filter.label}
          </button>
        ))}
      </div>
      <span className="filter-prompt">questions</span>
    </div>
  );
};

export default GradeFilter;
