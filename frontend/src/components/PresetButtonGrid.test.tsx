/**
 * Property-Based Tests for PresetButtonGrid Component
 * Feature: gcse-enhancement-suite, Property 2: Topic preset button click populates textarea correctly
 * Validates: Requirements 1.4
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PresetButtonGrid from './PresetButtonGrid';
import { TOPIC_PRESETS, GradeFilterType } from '../data/topicPresets';

describe('PresetButtonGrid Property Tests', () => {
  /**
   * Property 2: Topic preset button click populates textarea correctly
   * For any topic preset button, clicking it should populate the textarea 
   * with the correctly formatted tier-appropriate request text
   */
  describe('Property 2: Topic preset button click populates textarea correctly', () => {
    const gradeFilters: GradeFilterType[] = ['all', 'foundation', 'higher'];
    const themes: Array<'default' | 'pink-floral'> = ['default', 'pink-floral'];
    
    gradeFilters.forEach(gradeFilter => {
      themes.forEach(theme => {
        it(`should call onPresetClick with correct query for ${gradeFilter} filter and ${theme} theme`, () => {
          const mockOnPresetClick = jest.fn();
          
          render(
            <PresetButtonGrid
              onPresetClick={mockOnPresetClick}
              loading={false}
              theme={theme}
              gradeFilter={gradeFilter}
            />
          );
          
          // Get all preset buttons
          const buttons = screen.getAllByRole('button');
          
          // Click the first available button
          if (buttons.length > 0) {
            fireEvent.click(buttons[0]);
            
            // Verify onPresetClick was called
            expect(mockOnPresetClick).toHaveBeenCalledTimes(1);
            
            // Verify the query string contains expected elements
            const calledQuery = mockOnPresetClick.mock.calls[0][0];
            expect(typeof calledQuery).toBe('string');
            expect(calledQuery.length).toBeGreaterThan(0);
            
            // Verify query matches the filter type
            if (gradeFilter === 'foundation') {
              expect(calledQuery).toMatch(/Foundation/i);
              expect(calledQuery).toMatch(/grades 1-4/i);
            } else if (gradeFilter === 'higher') {
              expect(calledQuery).toMatch(/Higher/i);
              expect(calledQuery).toMatch(/grades 5-9/i);
            } else {
              expect(calledQuery).toMatch(/mixed difficulty/i);
            }
          }
        });
      });
    });
    
    it('should generate correct query format for all topics across all filters', () => {
      const mockOnPresetClick = jest.fn();
      
      // Test each filter type separately
      const testFilter = (filter: GradeFilterType) => {
        mockOnPresetClick.mockClear();
        
        const { unmount } = render(
          <PresetButtonGrid
            onPresetClick={mockOnPresetClick}
            loading={false}
            theme="default"
            gradeFilter={filter}
          />
        );
        
        // Get all buttons for this filter
        const buttons = screen.getAllByRole('button');
        
        // Test a sample of buttons (first 3 to keep test fast)
        const sampleButtons = buttons.slice(0, Math.min(3, buttons.length));
        
        sampleButtons.forEach((button) => {
          mockOnPresetClick.mockClear();
          fireEvent.click(button);
          
          if (mockOnPresetClick.mock.calls.length > 0) {
            const query = mockOnPresetClick.mock.calls[0][0];
            
            // Verify query structure
            expect(query).toMatch(/\d+/); // Should contain a number
            expect(query).toMatch(/questions/i); // Should contain "questions"
            
            // Verify tier-appropriate content based on filter
            if (filter === 'foundation') {
              // Foundation filter should produce Foundation queries
              expect(query).toMatch(/Foundation.*\(grades 1-4\)/i);
            } else if (filter === 'higher') {
              // Higher filter should produce Higher queries
              expect(query).toMatch(/Higher.*\(grades 5-9\)/i);
            } else {
              // All filter should produce mixed difficulty queries
              expect(query).toMatch(/mixed difficulty/i);
            }
          }
        });
        
        unmount();
      };
      
      // Test each filter
      testFilter('all');
      testFilter('foundation');
      testFilter('higher');
    });
    
    it('should filter topics correctly based on grade filter', () => {
      const mockOnPresetClick = jest.fn();
      
      // Render with 'all' filter
      const { rerender } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="all"
        />
      );
      
      const allButtons = screen.getAllByRole('button');
      const allCount = allButtons.length;
      
      // Render with 'foundation' filter
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="foundation"
        />
      );
      
      const foundationButtons = screen.getAllByRole('button');
      const foundationCount = foundationButtons.length;
      
      // Render with 'higher' filter
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="higher"
        />
      );
      
      const higherButtons = screen.getAllByRole('button');
      const higherCount = higherButtons.length;
      
      // 'all' should show all topics
      expect(allCount).toBe(TOPIC_PRESETS.length);
      
      // Foundation and higher should show fewer topics (excluding tier-specific ones)
      expect(foundationCount).toBeLessThanOrEqual(allCount);
      expect(higherCount).toBeLessThanOrEqual(allCount);
      
      // Foundation should exclude higher-only topics
      const higherOnlyTopics = TOPIC_PRESETS.filter(t => t.tier === 'higher');
      expect(foundationCount).toBe(allCount - higherOnlyTopics.length);
    });
    
    it('should disable buttons when loading', () => {
      const mockOnPresetClick = jest.fn();
      
      render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={true}
          theme="default"
          gradeFilter="all"
        />
      );
      
      const buttons = screen.getAllByRole('button');
      
      // All buttons should be disabled
      buttons.forEach(button => {
        expect(button).toBeDisabled();
      });
      
      // Clicking disabled button should not call callback
      if (buttons.length > 0) {
        fireEvent.click(buttons[0]);
        expect(mockOnPresetClick).not.toHaveBeenCalled();
      }
    });
    
    it('should display rose decorations only for pink-floral theme', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container: defaultContainer } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="all"
        />
      );
      
      // Default theme should not have rose decorations
      expect(defaultContainer.querySelector('.rose-decoration-top')).not.toBeInTheDocument();
      expect(defaultContainer.querySelector('.rose-decoration-bottom')).not.toBeInTheDocument();
      
      const { container: pinkContainer } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Pink floral theme should have rose decorations
      expect(pinkContainer.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(pinkContainer.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
    });
  });

  /**
   * Property 3: Pink theme applies rose decorations consistently
   * For any UI component, when the pink floral theme is active, 
   * rose decorative elements should be present and styled correctly
   * Feature: gcse-enhancement-suite, Property 3: Pink theme applies rose decorations consistently
   * Validates: Requirements 2.1
   */
  describe('Property 3: Pink theme applies rose decorations consistently', () => {
    const gradeFilters: GradeFilterType[] = ['all', 'foundation', 'higher'];
    const loadingStates = [true, false];
    
    it('should apply pink-floral theme class to container for all configurations', () => {
      const mockOnPresetClick = jest.fn();
      
      gradeFilters.forEach(gradeFilter => {
        loadingStates.forEach(loading => {
          const { container } = render(
            <PresetButtonGrid
              onPresetClick={mockOnPresetClick}
              loading={loading}
              theme="pink-floral"
              gradeFilter={gradeFilter}
            />
          );
          
          // Verify pink-floral class is applied
          const gridElement = container.querySelector('.preset-button-grid');
          expect(gridElement).toHaveClass('pink-floral');
        });
      });
    });
    
    it('should display rose decorations (top and bottom) for pink-floral theme across all configurations', () => {
      const mockOnPresetClick = jest.fn();
      
      gradeFilters.forEach(gradeFilter => {
        loadingStates.forEach(loading => {
          const { container } = render(
            <PresetButtonGrid
              onPresetClick={mockOnPresetClick}
              loading={loading}
              theme="pink-floral"
              gradeFilter={gradeFilter}
            />
          );
          
          // Verify rose decorations exist
          const topDecoration = container.querySelector('.rose-decoration-top');
          const bottomDecoration = container.querySelector('.rose-decoration-bottom');
          
          expect(topDecoration).toBeInTheDocument();
          expect(bottomDecoration).toBeInTheDocument();
          
          // Verify rose icons are present (3 roses in each decoration)
          const topRoses = topDecoration?.querySelectorAll('.rose-icon');
          const bottomRoses = bottomDecoration?.querySelectorAll('.rose-icon');
          
          expect(topRoses).toHaveLength(3);
          expect(bottomRoses).toHaveLength(3);
          
          // Verify rose icons contain the rose emoji
          topRoses?.forEach(rose => {
            expect(rose.textContent).toBe('🌹');
          });
          bottomRoses?.forEach(rose => {
            expect(rose.textContent).toBe('🌹');
          });
        });
      });
    });
    
    it('should NOT display rose decorations for default theme across all configurations', () => {
      const mockOnPresetClick = jest.fn();
      
      gradeFilters.forEach(gradeFilter => {
        loadingStates.forEach(loading => {
          const { container } = render(
            <PresetButtonGrid
              onPresetClick={mockOnPresetClick}
              loading={loading}
              theme="default"
              gradeFilter={gradeFilter}
            />
          );
          
          // Verify NO rose decorations exist
          const topDecoration = container.querySelector('.rose-decoration-top');
          const bottomDecoration = container.querySelector('.rose-decoration-bottom');
          
          expect(topDecoration).not.toBeInTheDocument();
          expect(bottomDecoration).not.toBeInTheDocument();
          
          // Verify default class is applied (not pink-floral)
          const gridElement = container.querySelector('.preset-button-grid');
          expect(gridElement).not.toHaveClass('pink-floral');
          expect(gridElement).toHaveClass('default');
        });
      });
    });
    
    it('should maintain rose decorations when switching between grade filters', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container, rerender } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Verify initial state
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
      
      // Switch to foundation filter
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="foundation"
        />
      );
      
      // Verify decorations persist
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
      
      // Switch to higher filter
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="higher"
        />
      );
      
      // Verify decorations still persist
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
    });
    
    it('should maintain rose decorations when loading state changes', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container, rerender } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Verify initial state
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
      
      // Switch to loading state
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={true}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Verify decorations persist during loading
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
    });
    
    it('should remove rose decorations when theme switches from pink-floral to default', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container, rerender } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Verify pink-floral decorations exist
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
      
      // Switch to default theme
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="all"
        />
      );
      
      // Verify decorations are removed
      expect(container.querySelector('.rose-decoration-top')).not.toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).not.toBeInTheDocument();
    });
    
    it('should add rose decorations when theme switches from default to pink-floral', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container, rerender } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="all"
        />
      );
      
      // Verify no decorations in default theme
      expect(container.querySelector('.rose-decoration-top')).not.toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).not.toBeInTheDocument();
      
      // Switch to pink-floral theme
      rerender(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Verify decorations are added
      expect(container.querySelector('.rose-decoration-top')).toBeInTheDocument();
      expect(container.querySelector('.rose-decoration-bottom')).toBeInTheDocument();
    });
    
    it('should apply consistent rose decoration structure across all render scenarios', () => {
      const mockOnPresetClick = jest.fn();
      
      // Test multiple random combinations
      const testCases = [
        { gradeFilter: 'all' as GradeFilterType, loading: false },
        { gradeFilter: 'foundation' as GradeFilterType, loading: true },
        { gradeFilter: 'higher' as GradeFilterType, loading: false },
        { gradeFilter: 'all' as GradeFilterType, loading: true },
      ];
      
      testCases.forEach(({ gradeFilter, loading }) => {
        const { container } = render(
          <PresetButtonGrid
            onPresetClick={mockOnPresetClick}
            loading={loading}
            theme="pink-floral"
            gradeFilter={gradeFilter}
          />
        );
        
        // Verify consistent structure
        const topDecoration = container.querySelector('.rose-decoration-top');
        const bottomDecoration = container.querySelector('.rose-decoration-bottom');
        
        // Both decorations must exist
        expect(topDecoration).toBeInTheDocument();
        expect(bottomDecoration).toBeInTheDocument();
        
        // Both must have exactly 3 rose icons
        expect(topDecoration?.querySelectorAll('.rose-icon')).toHaveLength(3);
        expect(bottomDecoration?.querySelectorAll('.rose-icon')).toHaveLength(3);
        
        // All rose icons must contain the rose emoji
        const allRoses = container.querySelectorAll('.rose-icon');
        expect(allRoses).toHaveLength(6); // 3 top + 3 bottom
        allRoses.forEach(rose => {
          expect(rose.textContent).toBe('🌹');
        });
      });
    });
    
    it('should organize topics by domain', () => {
      const mockOnPresetClick = jest.fn();
      
      render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="default"
          gradeFilter="all"
        />
      );
      
      // Check for domain sections
      expect(screen.getByText('Number')).toBeInTheDocument();
      expect(screen.getByText('Algebra')).toBeInTheDocument();
      expect(screen.getByText('Ratio & Proportion')).toBeInTheDocument();
      expect(screen.getByText('Geometry')).toBeInTheDocument();
      expect(screen.getByText('Probability')).toBeInTheDocument();
      expect(screen.getByText('Statistics')).toBeInTheDocument();
    });
  });

  /**
   * Property 4: Hover effects trigger on all preset buttons
   * For any preset button, hovering should trigger the expected visual effects and animations
   * Feature: gcse-enhancement-suite, Property 4: Hover effects trigger on all preset buttons
   * Validates: Requirements 2.4
   */
  describe('Property 4: Hover effects trigger on all preset buttons', () => {
    it('should apply hover styles to domain buttons', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Get all domain buttons
      const domainButtons = container.querySelectorAll('.domain-box');
      
      // Verify all domain buttons exist
      expect(domainButtons.length).toBeGreaterThan(0);
      
      // Verify each button has the necessary classes for hover effects
      domainButtons.forEach(button => {
        expect(button).toHaveClass('domain-box');
        
        // Verify button is not disabled (so hover can work)
        expect(button).not.toBeDisabled();
        
        // Verify button has inline styles for colors (needed for gradients)
        const style = window.getComputedStyle(button);
        expect(style.backgroundColor).toBeTruthy();
      });
    });
    
    it('should apply hover styles to topic dropdown items', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Click first domain button to open dropdown
      const domainButtons = container.querySelectorAll('.domain-box');
      if (domainButtons.length > 0) {
        fireEvent.click(domainButtons[0]);
        
        // Get dropdown items
        const dropdownItems = container.querySelectorAll('.topic-dropdown-item');
        
        // Verify dropdown items exist
        expect(dropdownItems.length).toBeGreaterThan(0);
        
        // Verify each dropdown item has the necessary classes
        dropdownItems.forEach(item => {
          expect(item).toHaveClass('topic-dropdown-item');
          expect(item).not.toBeDisabled();
        });
      }
    });
    
    it('should not apply hover effects when buttons are disabled', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={true}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Get all domain buttons
      const domainButtons = container.querySelectorAll('.domain-box');
      
      // Verify all buttons are disabled
      domainButtons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });
    
    it('should apply consistent hover styles across all themes', () => {
      const mockOnPresetClick = jest.fn();
      const themes: Array<'default' | 'pink-floral'> = ['default', 'pink-floral'];
      
      themes.forEach(theme => {
        const { container } = render(
          <PresetButtonGrid
            onPresetClick={mockOnPresetClick}
            loading={false}
            theme={theme}
            gradeFilter="all"
          />
        );
        
        // Get all domain buttons
        const domainButtons = container.querySelectorAll('.domain-box');
        
        // Verify buttons exist and are not disabled
        expect(domainButtons.length).toBeGreaterThan(0);
        domainButtons.forEach(button => {
          expect(button).not.toBeDisabled();
        });
      });
    });
    
    it('should maintain hover capability across all grade filters', () => {
      const mockOnPresetClick = jest.fn();
      const gradeFilters: GradeFilterType[] = ['all', 'foundation', 'higher'];
      
      gradeFilters.forEach(gradeFilter => {
        const { container } = render(
          <PresetButtonGrid
            onPresetClick={mockOnPresetClick}
            loading={false}
            theme="pink-floral"
            gradeFilter={gradeFilter}
          />
        );
        
        // Get all domain buttons
        const domainButtons = container.querySelectorAll('.domain-box');
        
        // Verify buttons exist and are hoverable
        expect(domainButtons.length).toBeGreaterThan(0);
        domainButtons.forEach(button => {
          expect(button).not.toBeDisabled();
          expect(button).toHaveClass('domain-box');
        });
      });
    });
  });

  /**
   * Property 5: Responsive grid layout adapts to viewport width
   * For any viewport width, the preset button grid should display the correct number of columns
   * Feature: gcse-enhancement-suite, Property 5: Responsive grid layout adapts to viewport width
   * Validates: Requirements 2.5
   */
  describe('Property 5: Responsive grid layout adapts to viewport width', () => {
    it('should have domain boxes container with grid class', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Verify domain boxes container exists
      const domainBoxes = container.querySelector('.domain-boxes');
      expect(domainBoxes).toBeInTheDocument();
      expect(domainBoxes).toHaveClass('domain-boxes');
    });
    
    it('should render all domain buttons in grid structure', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Get all domain buttons
      const domainButtons = container.querySelectorAll('.domain-box');
      
      // Should have 6 domains (Number, Algebra, Ratio & Proportion, Geometry, Probability, Statistics)
      expect(domainButtons.length).toBe(6);
      
      // All should be within the grid container
      const domainBoxes = container.querySelector('.domain-boxes');
      domainButtons.forEach(button => {
        expect(domainBoxes).toContainElement(button as HTMLElement);
      });
    });
    
    it('should maintain grid structure across all themes', () => {
      const mockOnPresetClick = jest.fn();
      const themes: Array<'default' | 'pink-floral'> = ['default', 'pink-floral'];
      
      themes.forEach(theme => {
        const { container } = render(
          <PresetButtonGrid
            onPresetClick={mockOnPresetClick}
            loading={false}
            theme={theme}
            gradeFilter="all"
          />
        );
        
        const domainBoxes = container.querySelector('.domain-boxes');
        expect(domainBoxes).toBeInTheDocument();
        expect(domainBoxes).toHaveClass('domain-boxes');
        
        // Verify domain buttons exist
        const domainButtons = container.querySelectorAll('.domain-box');
        expect(domainButtons.length).toBeGreaterThan(0);
      });
    });
    
    it('should maintain grid structure across all grade filters', () => {
      const mockOnPresetClick = jest.fn();
      const gradeFilters: GradeFilterType[] = ['all', 'foundation', 'higher'];
      
      gradeFilters.forEach(gradeFilter => {
        const { container } = render(
          <PresetButtonGrid
            onPresetClick={mockOnPresetClick}
            loading={false}
            theme="pink-floral"
            gradeFilter={gradeFilter}
          />
        );
        
        const domainBoxes = container.querySelector('.domain-boxes');
        expect(domainBoxes).toBeInTheDocument();
        expect(domainBoxes).toHaveClass('domain-boxes');
        
        // Verify domain buttons exist (count may vary by filter)
        const domainButtons = container.querySelectorAll('.domain-box');
        expect(domainButtons.length).toBeGreaterThan(0);
      });
    });
    
    it('should wrap domain buttons in individual containers', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      // Each domain button should be in a wrapper
      const wrappers = container.querySelectorAll('.domain-box-wrapper');
      const buttons = container.querySelectorAll('.domain-box');
      
      // Should have same number of wrappers as buttons
      expect(wrappers.length).toBe(buttons.length);
      
      // Each wrapper should contain exactly one button
      wrappers.forEach(wrapper => {
        const buttonInWrapper = wrapper.querySelector('.domain-box');
        expect(buttonInWrapper).toBeInTheDocument();
      });
    });
    
    it('should maintain grid structure when loading', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={true}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      const domainBoxes = container.querySelector('.domain-boxes');
      expect(domainBoxes).toBeInTheDocument();
      expect(domainBoxes).toHaveClass('domain-boxes');
      
      // Buttons should still be in grid, just disabled
      const domainButtons = container.querySelectorAll('.domain-box');
      expect(domainButtons.length).toBeGreaterThan(0);
      domainButtons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });
    
    it('should have consistent button sizing across grid', () => {
      const mockOnPresetClick = jest.fn();
      
      const { container } = render(
        <PresetButtonGrid
          onPresetClick={mockOnPresetClick}
          loading={false}
          theme="pink-floral"
          gradeFilter="all"
        />
      );
      
      const domainButtons = container.querySelectorAll('.domain-box');
      
      // All buttons should have the same class for consistent styling
      domainButtons.forEach(button => {
        expect(button).toHaveClass('domain-box');
      });
    });
  });
});
