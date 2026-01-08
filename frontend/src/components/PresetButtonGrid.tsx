import React, { useMemo, useState } from 'react';
import { TopicPreset, TOPIC_PRESETS, DOMAIN_LABELS, GradeFilterType, DomainType } from '../data/topicPresets';
import './PresetButtonGrid.css';

interface PresetButtonGridProps {
  onPresetClick: (query: string) => void;
  loading: boolean;
  theme: 'default' | 'pink-floral';
  gradeFilter: GradeFilterType;
  selectedTopics?: string[];
}

const DOMAIN_COLORS: Record<DomainType, { base: string; dark: string }> = {
  'number': { base: '#3b82f6', dark: '#2563eb' },        // Blue
  'algebra': { base: '#8b5cf6', dark: '#7c3aed' },       // Purple
  'ratio-proportion': { base: '#ec4899', dark: '#db2777' }, // Pink
  'geometry': { base: '#10b981', dark: '#059669' },      // Green
  'probability': { base: '#f59e0b', dark: '#d97706' },   // Orange
  'statistics': { base: '#ef4444', dark: '#dc2626' }     // Red
};

const PresetButtonGrid: React.FC<PresetButtonGridProps> = ({ 
  onPresetClick, 
  loading, 
  theme,
  gradeFilter,
  selectedTopics = []
}) => {
  const [expandedDomain, setExpandedDomain] = useState<DomainType | null>(null);

  // Filter topics based on grade filter
  const filteredTopics = useMemo(() => {
    if (gradeFilter === 'all') {
      return TOPIC_PRESETS;
    }
    
    return TOPIC_PRESETS.filter(topic => {
      if (gradeFilter === 'foundation') {
        return topic.tier === 'foundation' || topic.tier === 'both';
      }
      if (gradeFilter === 'higher') {
        return topic.tier === 'higher' || topic.tier === 'both';
      }
      return true;
    });
  }, [gradeFilter]);

  // Group topics by domain
  const topicsByDomain = useMemo(() => {
    const grouped: Record<DomainType, TopicPreset[]> = {
      'number': [],
      'algebra': [],
      'ratio-proportion': [],
      'geometry': [],
      'probability': [],
      'statistics': []
    };
    
    filteredTopics.forEach(topic => {
      grouped[topic.domain].push(topic);
    });
    
    return grouped;
  }, [filteredTopics]);

  const handlePresetClick = (topic: TopicPreset) => {
    if (loading) return;
    
    let query: string;
    switch (gradeFilter) {
      case 'foundation':
        query = topic.foundationQuery;
        break;
      case 'higher':
        query = topic.higherQuery;
        break;
      default:
        query = topic.allQuery;
    }
    
    onPresetClick(query);
    setExpandedDomain(null); // Close dropdown after selection
  };

  const toggleDomain = (domain: DomainType) => {
    setExpandedDomain(expandedDomain === domain ? null : domain);
  };

  return (
    <div className={`preset-selector preset-button-grid ${theme}`}>
      <div className="preset-hint">
        <span className="hint-icon">💡</span>
        <span>Quick select a topic:</span>
      </div>
      
      <div className="domain-boxes">
        {(Object.keys(topicsByDomain) as DomainType[]).map(domain => {
          const topics = topicsByDomain[domain];
          if (topics.length === 0) return null;
          
          const isExpanded = expandedDomain === domain;
          const domainColors = DOMAIN_COLORS[domain];
          
          return (
            <div key={domain} className="domain-box-wrapper">
              <button
                className="domain-box"
                style={{ 
                  '--domain-color': domainColors.base,
                  '--domain-color-dark': domainColors.dark,
                  backgroundColor: domainColors.base,
                  borderColor: domainColors.base
                } as React.CSSProperties}
                onClick={() => toggleDomain(domain)}
                disabled={loading}
                type="button"
              >
                <span className="domain-box-label">{DOMAIN_LABELS[domain]}</span>
                <span className="domain-box-arrow">{isExpanded ? '▲' : '▼'}</span>
              </button>
              
              {isExpanded && (
                <div className="topic-dropdown">
                  {topics.map(topic => (
                    <button
                      key={topic.id}
                      className="topic-dropdown-item"
                      onClick={() => handlePresetClick(topic)}
                      disabled={loading}
                      type="button"
                    >
                      <span className="topic-icon">{topic.icon}</span>
                      <span className="topic-name">{topic.title}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PresetButtonGrid;
