#!/usr/bin/env python3
"""
Question Bank Processor

This script processes large collections of GCSE questions to create
a comprehensive question bank for AI reference.
"""

import json
import re
from typing import Dict, List, Any
from pathlib import Path

class QuestionBankProcessor:
    """Process and enhance question banks for AI reference"""
    
    def __init__(self):
        self.question_patterns = {
            'calculation': r'calculate|work out|find|determine',
            'explanation': r'explain|describe|show|justify',
            'application': r'use|apply|solve|model',
            'analysis': r'compare|analyse|evaluate|assess'
        }
    
    def categorize_question(self, question_text: str) -> Dict[str, Any]:
        """Categorize question by type and complexity"""
        
        question_lower = question_text.lower()
        
        # Determine question type
        question_type = 'calculation'  # default
        for qtype, pattern in self.question_patterns.items():
            if re.search(pattern, question_lower):
                question_type = qtype
                break
        
        # Estimate complexity
        complexity_indicators = {
            'simple': ['add', 'subtract', 'multiply', 'divide', 'find'],
            'medium': ['solve', 'calculate', 'work out', 'determine'],
            'complex': ['analyse', 'evaluate', 'justify', 'compare', 'model']
        }
        
        complexity = 'simple'
        for level, indicators in complexity_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                complexity = level
        
        return {
            'type': question_type,
            'complexity': complexity,
            'word_count': len(question_text.split()),
            'has_diagram': 'diagram' in question_lower or 'figure' in question_lower,
            'mathematical_content': bool(re.search(r'[+\-×÷=<>()\[\]{}]', question_text))
        }
    
    def enhance_question_metadata(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance questions with additional metadata"""
        
        enhanced_questions = []
        
        for question in questions:
            question_text = question.get('question_text', '')
            
            # Add categorization
            categorization = self.categorize_question(question_text)
            
            # Add enhanced metadata
            enhanced_question = {
                **question,
                'metadata': {
                    **categorization,
                    'enhanced_timestamp': datetime.now().isoformat(),
                    'ai_reference_quality': self.calculate_ai_reference_quality(question),
                    'topic_keywords': self.extract_topic_keywords(question_text),
                    'difficulty_indicators': self.extract_difficulty_indicators(question)
                }
            }
            
            enhanced_questions.append(enhanced_question)
        
        return enhanced_questions
    
    def calculate_ai_reference_quality(self, question: Dict[str, Any]) -> float:
        """Calculate quality score for AI reference purposes"""
        
        score = 1.0
        
        # Check for complete mark scheme
        mark_scheme = question.get('mark_scheme', {})
        if not mark_scheme:
            score -= 0.3
        
        # Check for clear question text
        question_text = question.get('question_text', '')
        if len(question_text) < 20:
            score -= 0.2
        
        # Check for appropriate marks
        marks = question.get('marks', 0)
        if marks <= 0 or marks > 10:
            score -= 0.2
        
        # Bonus for mathematical content
        if re.search(r'[+\-×÷=<>()\[\]{}]', question_text):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def extract_topic_keywords(self, question_text: str) -> List[str]:
        """Extract topic-specific keywords from question text"""
        
        topic_keywords = {
            'number': ['fraction', 'decimal', 'percentage', 'ratio', 'proportion'],
            'algebra': ['equation', 'solve', 'x', 'y', 'formula', 'expression'],
            'geometry': ['angle', 'triangle', 'circle', 'area', 'perimeter', 'volume'],
            'statistics': ['mean', 'median', 'mode', 'range', 'data', 'graph'],
            'probability': ['probability', 'chance', 'likely', 'outcome', 'event']
        }
        
        found_keywords = []
        question_lower = question_text.lower()
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    found_keywords.append(keyword)
        
        return list(set(found_keywords))
    
    def extract_difficulty_indicators(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Extract indicators of question difficulty"""
        
        question_text = question.get('question_text', '')
        marks = question.get('marks', 0)
        
        indicators = {
            'mark_allocation': marks,
            'text_complexity': len(question_text.split()),
            'mathematical_operations': len(re.findall(r'[+\-×÷=<>]', question_text)),
            'multi_step': 'then' in question_text.lower() or 'next' in question_text.lower(),
            'requires_explanation': any(word in question_text.lower() for word in ['explain', 'show', 'justify']),
            'contextual': any(word in question_text.lower() for word in ['shop', 'school', 'garden', 'recipe'])
        }
        
        return indicators

# Usage example:
if __name__ == "__main__":
    processor = QuestionBankProcessor()
    
    # Load questions from JSON file
    with open('questions.json', 'r') as f:
        questions = json.load(f)
    
    # Enhance questions
    enhanced_questions = processor.enhance_question_metadata(questions)
    
    # Save enhanced questions
    with open('enhanced_questions.json', 'w') as f:
        json.dump(enhanced_questions, f, indent=2)
    
    print(f"Enhanced {len(enhanced_questions)} questions")
