"""Tests for agent utilities (citation_utils, response_parsers, prompt_templates)."""

import pytest
from src.agents.citation_utils import CitationMapper
from src.agents.response_parsers import ResponseParser
from src.agents.prompt_templates import PromptTemplateManager
from src.core.base_agent import RetrievalResult


class TestCitationMapper:
    """Test CitationMapper functionality."""

    def test_map_citations(self):
        """Test mapping citation numbers to chunk IDs."""
        results = [
            RetrievalResult(chunk_text="Text 1", score=0.9, chunk_id="chunk_0"),
            RetrievalResult(chunk_text="Text 2", score=0.8, chunk_id="chunk_1"),
            RetrievalResult(chunk_text="Text 3", score=0.7, chunk_id="chunk_2"),
        ]

        citations = ["1", "2", "3"]
        chunk_ids = CitationMapper.map_citations(citations, results)

        assert chunk_ids == ["chunk_0", "chunk_1", "chunk_2"]

    def test_map_citations_out_of_range(self):
        """Test citation mapping with out of range numbers."""
        results = [
            RetrievalResult(chunk_text="Text 1", score=0.9, chunk_id="chunk_0"),
        ]

        citations = ["1", "5", "10"]
        chunk_ids = CitationMapper.map_citations(citations, results)

        assert chunk_ids == ["chunk_0"]  # Only valid citation

    def test_format_chunks_for_prompt(self):
        """Test formatting chunks for prompt."""
        results = [
            RetrievalResult(chunk_text="Text 1", score=0.9, chunk_id="chunk_0"),
            RetrievalResult(chunk_text="Text 2", score=0.8, chunk_id="chunk_1"),
        ]

        formatted = CitationMapper.format_chunks_for_prompt(results, include_scores=False)

        assert "[1] Text 1" in formatted
        assert "[2] Text 2" in formatted
        assert "Score" not in formatted

    def test_format_chunks_with_scores(self):
        """Test formatting chunks with scores."""
        results = [
            RetrievalResult(chunk_text="Text 1", score=0.9, chunk_id="chunk_0"),
        ]

        formatted = CitationMapper.format_chunks_for_prompt(results, include_scores=True)

        assert "[1] (Score: 0.90) Text 1" in formatted

    def test_format_empty_chunks(self):
        """Test formatting empty chunk list."""
        formatted = CitationMapper.format_chunks_for_prompt([])
        assert "No relevant passages" in formatted

    def test_extract_chunk_ids(self):
        """Test extracting chunk IDs from results."""
        results = [
            RetrievalResult(chunk_text="Text 1", score=0.9, chunk_id="chunk_0"),
            RetrievalResult(chunk_text="Text 2", score=0.8, chunk_id="chunk_1"),
        ]

        chunk_ids = CitationMapper.extract_chunk_ids(results)
        assert chunk_ids == ["chunk_0", "chunk_1"]


class TestResponseParser:
    """Test ResponseParser functionality."""

    def test_parse_json_response(self):
        """Test parsing JSON from response."""
        response = '{"key": "value", "number": 42}'
        result = ResponseParser.parse_json_response(response)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = '''```json
{
  "key": "value",
  "number": 42
}
```'''
        result = ResponseParser.parse_json_response(response)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_trailing_comma(self):
        """Test parsing JSON with trailing commas."""
        response = '{"key": "value", "number": 42,}'
        result = ResponseParser.parse_json_response(response)

        assert result == {"key": "value", "number": 42}

    def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError."""
        response = "This is not JSON at all"

        with pytest.raises(ValueError):
            ResponseParser.parse_json_response(response)

    def test_extract_citations(self):
        """Test extracting citation markers."""
        text = "This is from source [1] and also from [2] and [5]."
        citations = ResponseParser.extract_citations(text)

        assert citations == ["1", "2", "5"]

    def test_extract_citations_none(self):
        """Test extracting citations when none present."""
        text = "This has no citations."
        citations = ResponseParser.extract_citations(text)

        assert citations == []

    def test_parse_sectioned_response(self):
        """Test parsing sectioned response."""
        response = """DESCRIPTION: This is the description.
It spans multiple lines.

REASONING: This is the reasoning.
Also multiple lines."""

        sections = ResponseParser.parse_sectioned_response(response)

        assert "description" in sections
        assert "reasoning" in sections
        assert "This is the description" in sections["description"]
        assert "This is the reasoning" in sections["reasoning"]

    def test_parse_sectioned_response_no_sections(self):
        """Test parsing response with no sections."""
        response = "Just plain text with no sections."
        sections = ResponseParser.parse_sectioned_response(response)

        assert len(sections) == 0

    def test_clean_response(self):
        """Test cleaning response text."""
        response = "  Text with   extra   whitespace  \n\n\n\n  and newlines  "
        cleaned = ResponseParser.clean_response(response)

        # Clean response removes trailing spaces, normalizes newlines, but preserves internal spaces
        assert "Text with   extra   whitespace" in cleaned
        assert cleaned.count('\n\n') >= 1  # Multiple newlines normalized to max 2


class TestPromptTemplateManager:
    """Test PromptTemplateManager functionality."""

    def test_get_template(self):
        """Test getting a template by name."""
        template = PromptTemplateManager.get_template("narrator_system")

        assert "Narrator" in template
        assert "Rules:" in template

    def test_get_nonexistent_template_raises_error(self):
        """Test that getting nonexistent template raises ValueError."""
        with pytest.raises(ValueError):
            PromptTemplateManager.get_template("nonexistent_template")

    def test_format_template(self):
        """Test formatting a template with variables."""
        # Use a simple template
        PromptTemplateManager.TEMPLATES["test_template"] = "Hello {name}, you are {age} years old."

        formatted = PromptTemplateManager.format_template(
            "test_template",
            name="Alice",
            age=30
        )

        assert formatted == "Hello Alice, you are 30 years old."

        # Clean up
        del PromptTemplateManager.TEMPLATES["test_template"]

    def test_format_template_missing_variable_raises_error(self):
        """Test that missing variable raises ValueError."""
        PromptTemplateManager.TEMPLATES["test_template"] = "Hello {name}"

        with pytest.raises(ValueError):
            PromptTemplateManager.format_template("test_template", age=30)

        # Clean up
        del PromptTemplateManager.TEMPLATES["test_template"]

    def test_all_required_templates_exist(self):
        """Test that all required templates exist."""
        required_templates = [
            "narrator_system",
            "narrator_user",
            "scene_planner_system",
            "scene_planner_user",
            "npc_manager_system",
            "npc_manager_user",
            "npc_persona_extraction_system",
            "npc_persona_extraction_user",
            "rules_referee_system",
            "rules_referee_user",
        ]

        for template_name in required_templates:
            assert template_name in PromptTemplateManager.TEMPLATES
            assert len(PromptTemplateManager.get_template(template_name)) > 0
