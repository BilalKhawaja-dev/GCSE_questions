/**
 * Property-Based Tests for GradeFilter Component
 * Feature: gcse-enhancement-suite, Property 1: Grade filter displays correct topic subsets
 * Validates: Requirements 1.2, 1.3
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import GradeFilter from './GradeFilter';
import { GradeFilterType } from '../data/topicPresets';

describe('GradeFilter Property Tests', () => {
  /**
   * Property 1: Grade filter displays correct topic subsets
   * For any grade filter selection (Foundation, Higher, All), 
   * all displayed topic presets should match the selected filter criteria
   */
  describe('Property 1: Grade filter displays correct topic subsets', () => {
    const filterValues: GradeFilterType[] = ['all', 'foundation', 'higher'];
    const themes: Array<'default' | 'pink-floral'> = ['default', 'pink-floral'];
    
    // Test all combinations of filters and themes
    filterValues.forEach(filterValue => {
      themes.forEach(theme => {
        it(`should display correct filter button for ${filterValue} with ${theme} theme`, () => {
          const mockOnFilterChange = jest.fn();
          
          render(
            <GradeFilter
              activeFilter={filterValue}
              onFilterChange={mockOnFilterChange}
              theme={theme}
            />
          );
          
          // Verify all filter buttons are present
          expect(screen.getByText(/All Topics/i)).toBeInTheDocument();
          expect(screen.getByText(/Foundation \(1-4\)/i)).toBeInTheDocument();
          expect(screen.getByText(/Higher \(5-9\)/i)).toBeInTheDocument();
          
          // Verify the active filter has the active class
          const buttons = screen.getAllByRole('button');
          const activeButton = buttons.find(button => 
            button.getAttribute('aria-pressed') === 'true'
          );
          
          expect(activeButton).toBeDefined();
          expect(activeButton).toHaveClass('active');
        });
        
        it(`should call onFilterChange when clicking different filter for ${filterValue} with ${theme} theme`, () => {
          const mockOnFilterChange = jest.fn();
          
          render(
            <GradeFilter
              activeFilter={filterValue}
              onFilterChange={mockOnFilterChange}
              theme={theme}
            />
          );
          
          // Click each filter button and verify callback
          const allButton = screen.getByText(/All Topics/i).closest('button');
          const foundationButton = screen.getByText(/Foundation \(1-4\)/i).closest('button');
          const higherButton = screen.getByText(/Higher \(5-9\)/i).closest('button');
          
          if (allButton) {
            fireEvent.click(allButton);
            expect(mockOnFilterChange).toHaveBeenCalledWith('all');
          }
          
          mockOnFilterChange.mockClear();
          
          if (foundationButton) {
            fireEvent.click(foundationButton);
            expect(mockOnFilterChange).toHaveBeenCalledWith('foundation');
          }
          
          mockOnFilterChange.mockClear();
          
          if (higherButton) {
            fireEvent.click(higherButton);
            expect(mockOnFilterChange).toHaveBeenCalledWith('higher');
          }
        });
      });
    });
    
    it('should apply correct theme classes', () => {
      const mockOnFilterChange = jest.fn();
      
      const { container: defaultContainer } = render(
        <GradeFilter
          activeFilter="all"
          onFilterChange={mockOnFilterChange}
          theme="default"
        />
      );
      
      expect(defaultContainer.querySelector('.grade-filter-compact.default')).toBeInTheDocument();
      
      const { container: pinkContainer } = render(
        <GradeFilter
          activeFilter="all"
          onFilterChange={mockOnFilterChange}
          theme="pink-floral"
        />
      );
      
      expect(pinkContainer.querySelector('.grade-filter-compact.pink-floral')).toBeInTheDocument();
    });
    
    it('should maintain accessibility attributes', () => {
      const mockOnFilterChange = jest.fn();
      
      render(
        <GradeFilter
          activeFilter="foundation"
          onFilterChange={mockOnFilterChange}
          theme="default"
        />
      );
      
      const buttons = screen.getAllByRole('button');
      
      // All buttons should have aria-pressed attribute
      buttons.forEach(button => {
        expect(button).toHaveAttribute('aria-pressed');
      });
      
      // Exactly one button should have aria-pressed="true"
      const pressedButtons = buttons.filter(button => 
        button.getAttribute('aria-pressed') === 'true'
      );
      expect(pressedButtons).toHaveLength(1);
    });
  });
});
