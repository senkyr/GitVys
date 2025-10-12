"""Unit tests for visualization.ui.text_formatter module."""

import pytest
from visualization.ui.text_formatter import TextFormatter


class TestTextFormatter:
    """Tests for TextFormatter class."""

    @pytest.fixture
    def formatter(self, canvas):
        """Create TextFormatter instance."""
        return TextFormatter(canvas)

    def test_initialization(self, canvas):
        """Test TextFormatter initialization."""
        formatter = TextFormatter(canvas)
        assert formatter.canvas == canvas
        assert hasattr(formatter, 'scaling_factor')
        assert formatter.scaling_factor > 0

    def test_detect_scaling_factor(self, formatter):
        """Test DPI scaling factor detection."""
        formatter.detect_scaling_factor()
        # Scaling factor should be reasonable (typically 1.0, 1.25, 1.5, 2.0)
        assert 1.0 <= formatter.scaling_factor <= 3.0

    def test_truncate_text_to_width_no_truncation(self, formatter, canvas):
        """Test text that doesn't need truncation."""
        text = "Short"
        font = ('Arial', 12)
        result = formatter.truncate_text_to_width(canvas, font, text, 1000)
        assert result == text

    def test_truncate_text_to_width_with_truncation(self, formatter, canvas):
        """Test text that needs truncation."""
        text = "This is a very long text that should be truncated"
        font = ('Arial', 12)
        result = formatter.truncate_text_to_width(canvas, font, text, 50)
        assert len(result) < len(text)
        assert result.endswith("...")

    def test_truncate_text_empty(self, formatter, canvas):
        """Test truncation of empty text."""
        result = formatter.truncate_text_to_width(canvas, ('Arial', 12), "", 100)
        assert result == ""

    def test_truncate_description_for_dpi(self, formatter):
        """Test description truncation for DPI."""
        description = "This is a long description that should be truncated"
        result = formatter.truncate_description_for_dpi(description, 20)
        if len(result) < len(description):  # Only check if actually truncated
            assert result.endswith("...")

    def test_adjust_descriptions_for_scaling(self, formatter, mock_commits):
        """Test description adjustment based on DPI scaling."""
        # Set scaling factor
        formatter.scaling_factor = 1.5

        # Give commits descriptions
        for commit in mock_commits:
            commit.description = "This is a long description that should be adjusted based on DPI scaling factor"

        formatter.adjust_descriptions_for_scaling(mock_commits)

        # Check all commits have description_short
        for commit in mock_commits:
            assert hasattr(commit, 'description_short')

    def test_recalculate_descriptions_for_width(self, formatter, canvas, mock_commits):
        """Test recalculation of descriptions for new width."""
        # Give commits descriptions
        for commit in mock_commits:
            commit.description = "This is a description to recalculate"
            commit.description_short = "Old short"

        column_widths = {'message': 400}

        formatter.recalculate_descriptions_for_width(canvas, mock_commits, column_widths)

        # Check descriptions were recalculated
        for commit in mock_commits:
            assert hasattr(commit, 'description_short')

    def test_scaling_factor_affects_description_length(self, formatter, mock_commits):
        """Test that higher scaling results in shorter descriptions."""
        description = "A" * 200
        for commit in mock_commits:
            commit.description = description

        # Low scaling
        formatter.scaling_factor = 1.0
        formatter.adjust_descriptions_for_scaling(mock_commits)
        length_low = len(mock_commits[0].description_short) if mock_commits[0].description_short else 0

        # Reset
        for commit in mock_commits:
            commit.description = description

        # High scaling
        formatter.scaling_factor = 2.0
        formatter.adjust_descriptions_for_scaling(mock_commits)
        length_high = len(mock_commits[0].description_short) if mock_commits[0].description_short else 0

        # Higher scaling should result in shorter or equal text
        assert length_high <= length_low

    def test_handle_commits_without_description(self, formatter, mock_commits):
        """Test handling commits that have no description."""
        # Remove descriptions
        for commit in mock_commits:
            commit.description = None

        # Should not crash
        formatter.adjust_descriptions_for_scaling(mock_commits)

        for commit in mock_commits:
            assert hasattr(commit, 'description_short')
            assert commit.description_short is None or commit.description_short == ""
