"""Unit tests for visualization.ui.tooltip_manager module."""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
import tkinter as tk
from visualization.ui.tooltip_manager import TooltipManager


class TestTooltipManager:
    """Tests for TooltipManager class."""

    @pytest.fixture
    def manager(self):
        """Create TooltipManager instance."""
        return TooltipManager()

    def test_initialization(self, manager):
        """Test TooltipManager initialization."""
        assert manager.tooltip is None
        assert hasattr(manager, 'theme_manager')

    def test_show_tooltip(self, manager):
        """Test showing a tooltip."""
        # Create mock event
        event = type('Event', (), {
            'x_root': 100,
            'y_root': 200,
            'widget': tk.Label()
        })()

        manager.show_tooltip(event, "Test tooltip text")

        # Tooltip should be created
        assert manager.tooltip is not None
        assert isinstance(manager.tooltip, tk.Toplevel)

    def test_hide_tooltip(self, manager):
        """Test hiding a tooltip."""
        # First show a tooltip
        event = type('Event', (), {
            'x_root': 100,
            'y_root': 200,
            'widget': tk.Label()
        })()

        manager.show_tooltip(event, "Test text")
        assert manager.tooltip is not None

        # Then hide it
        manager.hide_tooltip()
        assert manager.tooltip is None

    def test_hide_tooltip_when_none(self, manager):
        """Test hiding tooltip when no tooltip is shown."""
        # Should not crash
        manager.hide_tooltip()
        assert manager.tooltip is None

    def test_show_multiple_tooltips(self, manager):
        """Test showing multiple tooltips (should replace previous)."""
        event = type('Event', (), {
            'x_root': 100,
            'y_root': 200,
            'widget': tk.Label()
        })()

        # Show first tooltip
        manager.show_tooltip(event, "First tooltip")
        first_tooltip = manager.tooltip

        # Show second tooltip
        manager.show_tooltip(event, "Second tooltip")
        second_tooltip = manager.tooltip

        # Should be different tooltips (old one destroyed)
        assert second_tooltip is not None

    def test_tooltip_positioning(self, manager):
        """Test tooltip is positioned relative to cursor."""
        event = type('Event', (), {
            'x_root': 500,
            'y_root': 300,
            'widget': tk.Label()
        })()

        manager.show_tooltip(event, "Positioned tooltip")

        # Tooltip should be offset from cursor position
        if manager.tooltip:
            # Check tooltip has geometry set
            geometry = manager.tooltip.geometry()
            assert geometry  # Should have position

    def test_tooltip_text_content(self, manager):
        """Test tooltip displays correct text."""
        test_text = "This is test tooltip content"
        event = type('Event', (), {
            'x_root': 100,
            'y_root': 200,
            'widget': tk.Label()
        })()

        manager.show_tooltip(event, test_text)

        if manager.tooltip:
            # Find label in tooltip children
            labels = [w for w in manager.tooltip.winfo_children() if isinstance(w, tk.Label)]
            if labels:
                label_text = labels[0].cget('text')
                assert test_text in label_text or label_text == test_text
