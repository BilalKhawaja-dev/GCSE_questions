"""
PDF Export Service for GCSE Question Generator V2

This service handles PDF generation with proper mathematical formatting,
including questions, mark schemes, and metadata as required by specifications 5.6, 5.7, 5.8.
"""

import io
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


class PDFExportService:
    """Service for generating PDF exports of question sets with mathematical formatting"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for PDF generation"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Question style
        self.styles.add(ParagraphStyle(
            name='Question',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=10,
            leftIndent=0
        ))
        
        # Mark scheme style
        self.styles.add(ParagraphStyle(
            name='MarkScheme',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=15,
            leftIndent=20,
            textColor=colors.darkblue
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=5
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='Header',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            textColor=colors.darkblue
        ))
    
    def generate_pdf(self, session_data: Dict[str, Any], user_info: Optional[Dict[str, str]] = None) -> bytes:
        """
        Generate PDF from session data with questions, mark schemes, and metadata
        
        Args:
            session_data: Dictionary containing session information and questions
            user_info: Optional user information for personalization
            
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build PDF content
        story = []
        
        # Add title and metadata
        story.extend(self._build_header(session_data, user_info))
        
        # Add questions and mark schemes
        story.extend(self._build_questions_section(session_data.get('generated_questions', [])))
        
        # Add session metadata
        story.extend(self._build_metadata_section(session_data))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _build_header(self, session_data: Dict[str, Any], user_info: Optional[Dict[str, str]]) -> List[Any]:
        """Build PDF header with title and basic information"""
        story = []
        
        # Main title
        title = "GCSE Mathematics Question Set"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Session information table
        session_info = [
            ['Generated:', self._format_timestamp(session_data.get('timestamp'))],
            ['Topic:', session_data.get('metadata', {}).get('topic', 'Mixed')],
            ['Tier:', session_data.get('metadata', {}).get('tier', 'Foundation').title()],
            ['Question Count:', str(session_data.get('metadata', {}).get('question_count', 0))]
        ]
        
        if user_info:
            session_info.insert(0, ['Teacher:', user_info.get('username', 'Unknown')])
        
        info_table = Table(session_info, colWidths=[1.5*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 30))
        
        return story
    
    def _build_questions_section(self, questions: List[Dict[str, Any]]) -> List[Any]:
        """Build the questions and mark schemes section"""
        story = []
        
        if not questions:
            story.append(Paragraph("No questions available.", self.styles['Normal']))
            return story
        
        story.append(Paragraph("Questions and Mark Schemes", self.styles['Header']))
        story.append(Spacer(1, 15))
        
        for i, question in enumerate(questions, 1):
            # Question number and difficulty
            difficulty = question.get('difficulty_score', 'N/A')
            question_header = f"Question {i} (Difficulty: {difficulty}/10)"
            story.append(Paragraph(question_header, self.styles['Heading3']))
            story.append(Spacer(1, 8))
            
            # Question text with mathematical formatting
            question_text = self._format_mathematical_text(question.get('question_text', ''))
            story.append(Paragraph(question_text, self.styles['Question']))
            story.append(Spacer(1, 10))
            
            # Mark scheme
            story.append(Paragraph("Mark Scheme:", self.styles['Heading4']))
            mark_scheme = self._format_mathematical_text(question.get('mark_scheme', ''))
            story.append(Paragraph(mark_scheme, self.styles['MarkScheme']))
            
            # Question metadata
            metadata_items = []
            if question.get('topic'):
                metadata_items.append(f"Topic: {self._format_mathematical_text(question['topic'])}")
            if question.get('subtopic'):
                metadata_items.append(f"Subtopic: {self._format_mathematical_text(question['subtopic'])}")
            if question.get('assessment_objective'):
                metadata_items.append(f"Assessment Objective: {self._format_mathematical_text(question['assessment_objective'])}")
            
            if metadata_items:
                metadata_text = " | ".join(metadata_items)
                story.append(Paragraph(metadata_text, self.styles['Metadata']))
            
            story.append(Spacer(1, 20))
        
        return story
    
    def _build_metadata_section(self, session_data: Dict[str, Any]) -> List[Any]:
        """Build the session metadata section"""
        story = []
        
        story.append(Paragraph("Session Information", self.styles['Header']))
        story.append(Spacer(1, 10))
        
        # Session details table
        metadata = session_data.get('metadata', {})
        session_details = [
            ['Session ID:', session_data.get('session_id', 'N/A')],
            ['Original Query:', session_data.get('query', 'N/A')],
            ['Generation Time:', f"{metadata.get('generation_time', 0):.2f} seconds"],
            ['Specification Version:', metadata.get('specification_version', 'N/A')]
        ]
        
        details_table = Table(session_details, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Footer
        footer_text = f"Generated by GCSE Question Generator V2 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(footer_text, self.styles['Metadata']))
        
        return story
    
    def _format_mathematical_text(self, text: str) -> str:
        """
        Format mathematical text for PDF display
        Ensures mathematical notation is properly rendered in PDF
        """
        if not text:
            return ""
        
        # First, escape HTML characters for ReportLab to prevent parsing issues
        formatted_text = text.replace('&', '&amp;')
        formatted_text = formatted_text.replace('<', '&lt;')
        formatted_text = formatted_text.replace('>', '&gt;')
        formatted_text = formatted_text.replace('"', '&quot;')
        formatted_text = formatted_text.replace("'", '&#x27;')
        
        # Replace common mathematical symbols with their Unicode equivalents
        # These should already be converted by the math_rendering service
        replacements = {
            '×': '×',  # multiplication
            '÷': '÷',  # division
            '±': '±',  # plus-minus
            '≤': '≤',  # less than or equal
            '≥': '≥',  # greater than or equal
            '²': '²',  # squared
            '³': '³',  # cubed
            '√': '√',  # square root
            '¼': '¼',  # quarter
            '½': '½',  # half
            '¾': '¾',  # three quarters
        }
        
        for original, replacement in replacements.items():
            formatted_text = formatted_text.replace(original, replacement)
        
        # Remove any remaining problematic characters that could cause parsing issues
        import re
        # Remove any characters that could be interpreted as HTML tags
        # This is a simple approach that removes angle brackets that aren't part of HTML entities
        formatted_text = re.sub(r'&lt;\?', '&lt;?', formatted_text)  # Handle specific case like "0<?"
        
        return formatted_text
    
    def _format_timestamp(self, timestamp: Optional[int]) -> str:
        """Format timestamp for display"""
        if not timestamp:
            return "Unknown"
        
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return "Invalid timestamp"
    
    def generate_filename(self, session_data: Dict[str, Any], user_info: Optional[Dict[str, str]] = None) -> str:
        """
        Generate appropriate filename for PDF export
        
        Args:
            session_data: Session data containing metadata
            user_info: Optional user information
            
        Returns:
            str: Formatted filename
        """
        # Base components
        timestamp = session_data.get('timestamp')
        if timestamp:
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
        else:
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        topic = session_data.get('metadata', {}).get('topic', 'mixed')
        tier = session_data.get('metadata', {}).get('tier', 'foundation')
        question_count = session_data.get('metadata', {}).get('question_count', 0)
        
        # Clean topic name for filename
        clean_topic = topic.lower().replace(' ', '_').replace('-', '_')
        
        # Build filename
        filename_parts = [
            'gcse_questions',
            clean_topic,
            tier.lower(),
            f'{question_count}q',
            date_str
        ]
        
        if user_info and user_info.get('username'):
            # Add username if available (sanitized)
            clean_username = user_info['username'].lower().replace(' ', '_')[:10]
            filename_parts.insert(-1, clean_username)
        
        return '_'.join(filename_parts) + '.pdf'


# Singleton instance for use across the application
pdf_export_service = PDFExportService()