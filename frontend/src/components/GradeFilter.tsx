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
      <div className="filter-pills">
        {GRADE_FILTERS.filter(f => f.value !== 'all').map((filter) => (
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
      
      <select className="grade-dropdown" defaultValue="all">
        <option value="all">All Grades</option>
        <option value="1">Grade 1</option>
        <option value="2">Grade 2</option>
        <option value="3">Grade 3</option>
        <option value="4">Grade 4</option>
        <option value="5">Grade 5</option>
        <option value="6">Grade 6</option>
        <option value="7">Grade 7</option>
        <option value="8">Grade 8</option>
        <option value="9">Grade 9</option>
      </select>
    </div>
  );
};

export default GradeFilter;
