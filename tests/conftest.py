"""Pytest configuration and shared fixtures."""

import pytest
from hypothesis import settings, Verbosity

# Configure Hypothesis for property-based testing
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("ci", max_examples=1000, verbosity=Verbosity.verbose)
settings.load_profile("default")


@pytest.fixture
def sample_query_intent():
    """Sample QueryIntent for testing."""
    from src.models import QueryIntent
    return QueryIntent(
        topic="Number",
        subtopic="Fractions",
        tier="Foundation",
        count=5,
        confidence=0.95,
        specification_version="2024.1"
    )


@pytest.fixture
def sample_question():
    """Sample Question for testing."""
    from src.models import Question
    return Question(
        id="q1",
        question_text="Calculate 3/4 + 1/8. Show your working.",
        marks=2,
        tier="Foundation",
        topic="Number",
        subtopic="Fractions",
        mathematical_elements=["fractions", "addition"],
        difficulty_indicators=["basic_operations"]
    )


@pytest.fixture
def sample_mark_scheme():
    """Sample MarkScheme for testing."""
    from src.models import MarkScheme
    return MarkScheme(
        question_id="q1",
        marking_criteria="M1: Convert to common denominator (6/8 + 1/8), A1: Correct answer 7/8",
        method_marks=1,
        accuracy_marks=1,
        total_marks=2,
        common_errors=["Adding denominators", "Incorrect conversion"]
    )


@pytest.fixture
def sample_specification_content():
    """Sample SpecificationContent for testing."""
    from src.models import SpecificationContent
    return SpecificationContent(
        content="Students should be able to add and subtract fractions with the same denominator.",
        topic="Number",
        tier="Foundation",
        version="2024.1",
        learning_objectives=[
            "Add fractions with same denominator",
            "Subtract fractions with same denominator"
        ],
        domain="number",
        subtopic="fractions",
        key_concepts=["numerator", "denominator", "equivalent fractions"],
        common_misconceptions=["Adding denominators"],
        assessment_objectives=["AO1", "AO2"],
        marks_range=[1, 4]
    )