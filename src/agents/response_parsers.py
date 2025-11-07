"""Response parsers for structured LLM responses."""

import re
import json
from typing import Dict, List, Any, Optional


class ResponseParser:
    """Parse structured LLM responses."""

    @staticmethod
    def parse_json_response(response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.

        Handles JSON wrapped in markdown code blocks and malformed JSON.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be parsed
        """
        # Remove markdown code blocks if present
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, response)
        if matches:
            response = matches[0]

        # Try to find JSON object in response
        json_obj_pattern = r'\{[\s\S]*\}'
        json_matches = re.findall(json_obj_pattern, response)
        if json_matches:
            response = json_matches[0]

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            # Remove trailing commas
            response = re.sub(r',(\s*[}\]])', r'\1', response)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse JSON: {e}") from e

    @staticmethod
    def extract_citations(response: str) -> List[str]:
        """Extract citation markers [1], [2] from text.

        Args:
            response: Text with citation markers

        Returns:
            List of citation numbers as strings
        """
        citations = re.findall(r'\[(\d+)\]', response)
        return citations

    @staticmethod
    def parse_sectioned_response(response: str) -> Dict[str, str]:
        """Parse response with sections like DESCRIPTION:, REASONING:.

        Args:
            response: Response with uppercase section headers

        Returns:
            Dictionary mapping section names to content
        """
        sections = {}
        current_section = None
        current_content = []

        for line in response.split('\n'):
            # Check if line is a section header (uppercase word followed by colon)
            if ':' in line:
                parts = line.split(':', 1)
                if parts[0].strip().isupper():
                    # Save previous section
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()

                    # Start new section
                    current_section = parts[0].strip().lower()
                    current_content = [parts[1].strip()] if len(parts) > 1 and parts[1].strip() else []
                    continue

            # Add line to current section
            if current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    @staticmethod
    def clean_response(response: str) -> str:
        """Clean LLM response by removing extra whitespace and formatting.

        Args:
            response: Raw LLM response

        Returns:
            Cleaned response
        """
        # Remove leading/trailing whitespace
        response = response.strip()

        # Normalize multiple newlines to max 2
        response = re.sub(r'\n{3,}', '\n\n', response)

        # Remove leading/trailing spaces from each line
        lines = [line.rstrip() for line in response.split('\n')]
        response = '\n'.join(lines)

        return response
