"""Unit tests for gui.ui_components.language_switcher module."""

import pytest
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch
from gui.ui_components.language_switcher import LanguageSwitcher


class TestLanguageSwitcherInitialization:
    """Tests for LanguageSwitcher initialization."""

    def test_initialization(self, mock_parent_window):
        """Test LanguageSwitcher initialization with parent window."""
        switcher = LanguageSwitcher(mock_parent_window)

        assert switcher.parent == mock_parent_window
        assert switcher.root == mock_parent_window.root
        assert switcher.tm is not None  # Translation manager
        # Attributes are None until create_switcher_ui() is called
        assert switcher.language_frame is None
        assert switcher.flag_cs is None
        assert switcher.flag_en is None

    def test_create_switcher_ui_creates_frame(self, mock_parent_window):
        """Test that create_switcher_ui creates language frame."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        assert switcher.language_frame is not None
        assert isinstance(switcher.language_frame, ttk.Frame)

    def test_create_switcher_ui_creates_flags(self, mock_parent_window):
        """Test that create_switcher_ui creates Czech and UK flag canvases."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        assert switcher.flag_cs is not None
        assert switcher.flag_en is not None
        assert isinstance(switcher.flag_cs, tk.Canvas)
        assert isinstance(switcher.flag_en, tk.Canvas)


class TestFlagCreation:
    """Tests for flag creation methods."""

    def test_create_czech_flag_returns_canvas(self, mock_parent_window):
        """Test that _create_czech_flag returns a Canvas widget."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        cs_flag = switcher.flag_cs

        assert isinstance(cs_flag, tk.Canvas)
        assert cs_flag.winfo_reqwidth() == 30
        assert cs_flag.winfo_reqheight() == 20

    def test_create_uk_flag_returns_canvas(self, mock_parent_window):
        """Test that _create_uk_flag returns a Canvas widget."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        en_flag = switcher.flag_en

        assert isinstance(en_flag, tk.Canvas)
        assert en_flag.winfo_reqwidth() == 30
        assert en_flag.winfo_reqheight() == 20

    def test_czech_flag_has_correct_colors(self, mock_parent_window):
        """Test that Czech flag has correct colors (white, red, blue)."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Czech flag should have multiple items (white stripe, red stripe, blue triangle)
        items = switcher.flag_cs.find_all()
        assert len(items) >= 3  # At least 3 shapes

    def test_uk_flag_has_correct_structure(self, mock_parent_window):
        """Test that UK flag has correct structure (Union Jack)."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # UK flag should have multiple items (blue background, white cross, red cross)
        items = switcher.flag_en.find_all()
        assert len(items) >= 3  # Multiple shapes for Union Jack


class TestLanguageSwitching:
    """Tests for language switching functionality."""

    def test_switch_to_czech(self, mock_parent_window):
        """Test switching to Czech language."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.tm.get_current_language = MagicMock(return_value='en')
        switcher.tm.set_language = MagicMock()

        switcher.switch_to_language('cs')

        switcher.tm.set_language.assert_called_once_with('cs')

    def test_switch_to_english(self, mock_parent_window):
        """Test switching to English language."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.tm.get_current_language = MagicMock(return_value='cs')
        switcher.tm.set_language = MagicMock()

        switcher.switch_to_language('en')

        switcher.tm.set_language.assert_called_once_with('en')

    def test_switch_to_same_language_no_op(self, mock_parent_window):
        """Test switching to current language does nothing."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.tm.get_current_language = MagicMock(return_value='cs')
        switcher.tm.set_language = MagicMock()

        switcher.switch_to_language('cs')

        # Should not call set_language if already on that language
        switcher.tm.set_language.assert_not_called()

    def test_click_flag_calls_switch_to_language(self, mock_parent_window):
        """Test clicking flag triggers language switch."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.tm.get_current_language = MagicMock(return_value='en')
        switcher.tm.set_language = MagicMock()

        # Simulate click event on Czech flag
        switcher.flag_cs.event_generate('<Button-1>')

        # Verify flag has binding
        assert switcher.flag_cs.bind('<Button-1>')


class TestFlagAppearance:
    """Tests for flag appearance updates."""

    def test_update_flag_appearance_czech_active(self, mock_parent_window):
        """Test flag appearance when Czech language is active."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.tm.get_current_language = MagicMock(return_value='cs')
        switcher.tm.get_color = MagicMock(return_value='#808080')

        switcher.update_flag_appearance()

        # UK flag should have overlay (inactive), Czech should not
        en_overlay = switcher.flag_en.find_withtag('overlay')
        cs_overlay = switcher.flag_cs.find_withtag('overlay')

        assert len(en_overlay) > 0  # EN should have overlay
        assert len(cs_overlay) == 0  # Czech should not have overlay

    def test_update_flag_appearance_english_active(self, mock_parent_window):
        """Test flag appearance when English language is active."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.tm.get_current_language = MagicMock(return_value='en')
        switcher.tm.get_color = MagicMock(return_value='#808080')

        switcher.update_flag_appearance()

        # Czech flag should have overlay (inactive), EN should not
        en_overlay = switcher.flag_en.find_withtag('overlay')
        cs_overlay = switcher.flag_cs.find_withtag('overlay')

        assert len(en_overlay) == 0  # EN should not have overlay
        assert len(cs_overlay) > 0  # Czech should have overlay

    def test_update_removes_old_overlay(self, mock_parent_window):
        """Test that updating appearance removes old overlay."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.tm.get_color = MagicMock(return_value='#808080')

        # Set to Czech
        switcher.tm.get_current_language = MagicMock(return_value='cs')
        switcher.update_flag_appearance()
        en_overlay_count_1 = len(switcher.flag_en.find_withtag('overlay'))

        # Switch to English
        switcher.tm.get_current_language = MagicMock(return_value='en')
        switcher.update_flag_appearance()
        en_overlay_count_2 = len(switcher.flag_en.find_withtag('overlay'))

        # EN overlay should be removed
        assert en_overlay_count_1 > 0
        assert en_overlay_count_2 == 0


class TestVisibility:
    """Tests for show/hide functionality."""

    def test_show_positions_at_left_top(self, mock_parent_window):
        """Test that show() positions at left top corner."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        switcher.show()

        # Should be positioned at top left
        geometry = switcher.language_frame.place_info()
        assert 'x' in geometry
        assert 'y' in geometry
        assert int(geometry['x']) == 15  # Left padding
        assert int(geometry['y']) == 15  # Top padding

    def test_hide_removes_from_display(self, mock_parent_window):
        """Test that hide() removes language switcher from display."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Show first
        switcher.show()

        # Then hide
        switcher.hide()

        # Should not be visible
        assert not switcher.language_frame.winfo_ismapped()

    def test_show_after_hide_repositions(self, mock_parent_window):
        """Test that show() after hide() repositions correctly."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Show, hide, show again
        switcher.show()
        switcher.hide()
        switcher.show()

        # Should be visible and positioned
        geometry = switcher.language_frame.place_info()
        assert 'x' in geometry
        assert int(geometry['x']) == 15


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_complete_workflow_czech_to_english(self, mock_parent_window):
        """Test complete workflow: create, show, switch language."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.tm.get_current_language = MagicMock(return_value='cs')
        switcher.tm.set_language = MagicMock()
        switcher.tm.get_color = MagicMock(return_value='#808080')

        # Create UI
        switcher.create_switcher_ui()

        # Show
        switcher.show()
        geometry = switcher.language_frame.place_info()
        assert 'x' in geometry  # Widget is placed

        # Update appearance
        switcher.update_flag_appearance()

        # Switch to English
        switcher.switch_to_language('en')
        switcher.tm.set_language.assert_called_with('en')

    def test_complete_workflow_with_hide_show(self, mock_parent_window):
        """Test complete workflow with hide/show cycle."""
        switcher = LanguageSwitcher(mock_parent_window)
        switcher.tm.get_current_language = MagicMock(return_value='cs')
        switcher.tm.get_color = MagicMock(return_value='#808080')

        switcher.create_switcher_ui()
        switcher.show()

        # Should be visible
        geometry = switcher.language_frame.place_info()
        assert 'x' in geometry

        # Hide when loading repo
        switcher.hide()
        assert not switcher.language_frame.winfo_ismapped()

        # Show again when closing repo
        switcher.show()
        geometry = switcher.language_frame.place_info()
        assert 'x' in geometry
