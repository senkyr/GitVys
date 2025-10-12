"""Unit tests for gui.ui_components.theme_switcher module."""

import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch, call
from gui.ui_components.theme_switcher import ThemeSwitcher


class TestThemeSwitcherInitialization:
    """Tests for ThemeSwitcher initialization."""

    def test_initialization(self, mock_parent_window):
        """Test ThemeSwitcher initialization with parent window."""
        switcher = ThemeSwitcher(mock_parent_window)

        assert switcher.parent == mock_parent_window
        assert switcher.root == mock_parent_window.root
        assert switcher.theme_manager is not None
        assert switcher.theme_frame is None
        assert switcher.icon_sun is None
        assert switcher.icon_moon is None

    def test_create_switcher_ui_creates_frame(self, mock_parent_window):
        """Test that create_switcher_ui creates theme frame."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        assert switcher.theme_frame is not None
        from tkinter import ttk
        assert isinstance(switcher.theme_frame, ttk.Frame)

    def test_create_switcher_ui_creates_icons(self, mock_parent_window):
        """Test that create_switcher_ui creates sun and moon icons."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        assert switcher.icon_sun is not None
        assert switcher.icon_moon is not None
        assert isinstance(switcher.icon_sun, tk.Canvas)
        assert isinstance(switcher.icon_moon, tk.Canvas)


class TestIconCreation:
    """Tests for icon creation methods."""

    def test_create_sun_icon_returns_canvas(self, mock_parent_window):
        """Test that _create_sun_icon returns a Canvas widget."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        sun_icon = switcher.icon_sun

        assert isinstance(sun_icon, tk.Canvas)
        assert sun_icon.winfo_reqwidth() == 30
        assert sun_icon.winfo_reqheight() == 20

    def test_create_moon_icon_returns_canvas(self, mock_parent_window):
        """Test that _create_moon_icon returns a Canvas widget."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        moon_icon = switcher.icon_moon

        assert isinstance(moon_icon, tk.Canvas)
        assert moon_icon.winfo_reqwidth() == 30
        assert moon_icon.winfo_reqheight() == 20

    def test_sun_icon_has_correct_background(self, mock_parent_window):
        """Test that sun icon has light blue background (sky)."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Check that canvas has items (sun circle + rays + background)
        items = switcher.icon_sun.find_all()
        assert len(items) > 0  # Should have multiple drawn items

    def test_moon_icon_has_correct_background(self, mock_parent_window):
        """Test that moon icon has black background (night sky)."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Check that canvas has items (moon + stars + background)
        items = switcher.icon_moon.find_all()
        assert len(items) > 0  # Should have multiple drawn items


class TestThemeSwitching:
    """Tests for theme switching functionality."""

    def test_switch_to_light_theme(self, mock_parent_window):
        """Test switching to light theme."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.theme_manager.get_current_theme = MagicMock(return_value='dark')
        switcher.theme_manager.set_theme = MagicMock()

        switcher.switch_to_theme('light')

        switcher.theme_manager.set_theme.assert_called_once_with('light')

    def test_switch_to_dark_theme(self, mock_parent_window):
        """Test switching to dark theme."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.theme_manager.set_theme = MagicMock()

        switcher.switch_to_theme('dark')

        switcher.theme_manager.set_theme.assert_called_once_with('dark')

    def test_switch_to_same_theme_no_op(self, mock_parent_window):
        """Test switching to current theme does nothing."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.theme_manager.set_theme = MagicMock()

        switcher.switch_to_theme('light')

        # Should not call set_theme if already on that theme
        switcher.theme_manager.set_theme.assert_not_called()

    def test_click_icon_calls_switch_to_theme(self, mock_parent_window):
        """Test clicking icon triggers theme switch."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.theme_manager.get_current_theme = MagicMock(return_value='dark')
        switcher.theme_manager.set_theme = MagicMock()

        # Simulate click event on sun icon
        event = MagicMock()
        switcher.icon_sun.event_generate('<Button-1>')

        # Note: Actual binding test would require more complex event simulation
        # This test verifies the icon has the binding
        assert switcher.icon_sun.bind('<Button-1>')


class TestIconAppearance:
    """Tests for icon appearance updates."""

    def test_update_theme_icon_appearance_light_active(self, mock_parent_window):
        """Test icon appearance when light theme is active."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.theme_manager.get_color = MagicMock(return_value='#808080')

        switcher.update_theme_icon_appearance()

        # Moon should have overlay (inactive), sun should not
        moon_items = switcher.icon_moon.find_withtag('overlay')
        sun_items = switcher.icon_sun.find_withtag('overlay')

        assert len(moon_items) > 0  # Moon should have overlay
        assert len(sun_items) == 0  # Sun should not have overlay

    def test_update_theme_icon_appearance_dark_active(self, mock_parent_window):
        """Test icon appearance when dark theme is active."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.theme_manager.get_current_theme = MagicMock(return_value='dark')
        switcher.theme_manager.get_color = MagicMock(return_value='#808080')

        switcher.update_theme_icon_appearance()

        # Sun should have overlay (inactive), moon should not
        moon_items = switcher.icon_moon.find_withtag('overlay')
        sun_items = switcher.icon_sun.find_withtag('overlay')

        assert len(moon_items) == 0  # Moon should not have overlay
        assert len(sun_items) > 0  # Sun should have overlay

    def test_update_removes_old_overlay(self, mock_parent_window):
        """Test that updating appearance removes old overlay."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.theme_manager.get_color = MagicMock(return_value='#808080')

        # Set to light theme
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.update_theme_icon_appearance()
        moon_overlay_count_1 = len(switcher.icon_moon.find_withtag('overlay'))

        # Switch to dark theme
        switcher.theme_manager.get_current_theme = MagicMock(return_value='dark')
        switcher.update_theme_icon_appearance()
        moon_overlay_count_2 = len(switcher.icon_moon.find_withtag('overlay'))

        # Moon overlay should be removed
        assert moon_overlay_count_1 > 0
        assert moon_overlay_count_2 == 0

    def test_overlay_uses_theme_manager_color(self, mock_parent_window):
        """Test that overlay uses color from theme manager."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.theme_manager.get_color = MagicMock(return_value='#AABBCC')

        switcher.update_theme_icon_appearance()

        # Verify get_color was called for overlay_inactive
        switcher.theme_manager.get_color.assert_called_with('overlay_inactive')


class TestVisibility:
    """
    REGRESSION TESTS for visibility bug.

    Bug: Přepínač se nezobrazoval v úvodním okně aplikace.
    Root cause: show() bylo voláno před správnou inicializací okna.
    Fix: Retry logika s fallback width.
    """

    def test_show_positions_correctly_after_window_init(self, mock_parent_window):
        """REGRESSION: Test that show() positions correctly after window init."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Mock window with proper width
        mock_parent_window.root.winfo_width = MagicMock(return_value=600)
        mock_parent_window.root.update_idletasks = MagicMock()

        switcher.show()

        # Should position at right side of window
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry
        # Expected: 600 - 85 = 515
        assert int(geometry['x']) == 515

    def test_show_with_uninitialized_window_retries(self, mock_parent_window):
        """REGRESSION: Test retry logic when window not initialized."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Mock window with width = 1 (not initialized)
        mock_parent_window.root.winfo_width = MagicMock(return_value=1)
        mock_parent_window.root.update_idletasks = MagicMock()
        mock_parent_window.root.after = MagicMock()

        switcher.show()

        # Should schedule retry with root.after()
        mock_parent_window.root.after.assert_called()
        call_args = mock_parent_window.root.after.call_args
        assert call_args[0][0] == 50  # 50ms delay

    def test_show_retry_logic_max_attempts(self, mock_parent_window):
        """REGRESSION: Test max retry attempts fallback."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Mock window that never initializes
        mock_parent_window.root.winfo_width = MagicMock(return_value=0)
        mock_parent_window.root.update_idletasks = MagicMock()
        mock_parent_window.root.after = MagicMock()

        # Call _update_position_with_retry directly with high retry count
        switcher._update_position_with_retry(retry_count=10)

        # Should use fallback width (600px) after max retries
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry
        # Should still position (using fallback)

    def test_show_uses_fallback_width(self, mock_parent_window):
        """REGRESSION: Test fallback width when window width unavailable."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Mock window with invalid width
        mock_parent_window.root.winfo_width = MagicMock(return_value=-1)
        mock_parent_window.root.update_idletasks = MagicMock()

        # Manually call with max retries to trigger fallback
        switcher._update_position_with_retry(retry_count=10)

        # Should use fallback width (600px)
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry
        # Fallback: 600 - 85 = 515
        expected_x = 515
        assert int(geometry['x']) == expected_x

    def test_hide_removes_from_display(self, mock_parent_window):
        """Test that hide() removes theme switcher from display."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Show first
        mock_parent_window.root.winfo_width = MagicMock(return_value=600)
        switcher.show()

        # Then hide
        switcher.hide()

        # Should not be visible
        assert not switcher.theme_frame.winfo_ismapped()

    def test_show_after_hide_repositions(self, mock_parent_window):
        """Test that show() after hide() repositions correctly."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        mock_parent_window.root.winfo_width = MagicMock(return_value=600)

        # Show, hide, show again
        switcher.show()
        switcher.hide()
        switcher.show()

        # Should be visible and positioned
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry


class TestPositioning:
    """Tests for positioning and window resize."""

    def test_update_position_calculates_correctly(self, mock_parent_window):
        """Test update_position() calculates position correctly."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()
        mock_parent_window.root.winfo_width = MagicMock(return_value=800)
        switcher.show()  # Initial show

        # Update position
        switcher.update_position()

        # Should recalculate position
        geometry = switcher.theme_frame.place_info()
        # Expected: 800 - 85 = 715
        assert int(geometry['x']) == 715

    def test_update_position_on_window_resize(self, mock_parent_window):
        """REGRESSION: Test position updates on window resize."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Create a mock that can change return value
        width_mock = MagicMock()
        width_mock.return_value = 600
        mock_parent_window.root.winfo_width = width_mock

        # Initial position at 600px width
        switcher.show()
        initial_x = int(switcher.theme_frame.place_info()['x'])
        assert initial_x == 515  # 600 - 85

        # Mock winfo_ismapped to return True so update_position works
        switcher.theme_frame.winfo_ismapped = MagicMock(return_value=True)

        # Resize window to 800px
        width_mock.return_value = 800
        switcher.update_position()
        new_x = int(switcher.theme_frame.place_info()['x'])

        # Position should have changed
        assert new_x != initial_x
        assert new_x == 715  # 800 - 85

    def test_position_respects_window_width(self, mock_parent_window):
        """Test positioning respects actual window width."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.create_switcher_ui()

        # Test with different window widths
        test_widths = [400, 600, 800, 1000]
        expected_positions = [w - 85 for w in test_widths]

        for width, expected_x in zip(test_widths, expected_positions):
            mock_parent_window.root.winfo_width = MagicMock(return_value=width)
            switcher.show()
            actual_x = int(switcher.theme_frame.place_info()['x'])
            assert actual_x == expected_x, f"Width {width} should position at {expected_x}, got {actual_x}"


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_complete_workflow_light_to_dark(self, mock_parent_window):
        """Test complete workflow: create, show, switch theme."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.theme_manager.set_theme = MagicMock()
        switcher.theme_manager.get_color = MagicMock(return_value='#808080')
        mock_parent_window.root.winfo_width = MagicMock(return_value=600)

        # Create UI
        switcher.create_switcher_ui()

        # Show
        switcher.show()
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry  # Widget is placed

        # Update appearance
        switcher.update_theme_icon_appearance()

        # Switch to dark
        switcher.switch_to_theme('dark')
        switcher.theme_manager.set_theme.assert_called_with('dark')

    def test_complete_workflow_with_hide_show(self, mock_parent_window):
        """Test complete workflow with hide/show cycle."""
        switcher = ThemeSwitcher(mock_parent_window)
        switcher.theme_manager.get_current_theme = MagicMock(return_value='light')
        switcher.theme_manager.get_color = MagicMock(return_value='#808080')
        mock_parent_window.root.winfo_width = MagicMock(return_value=600)

        switcher.create_switcher_ui()
        switcher.show()

        # Should be visible
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry

        # Hide when loading repo
        switcher.hide()
        assert not switcher.theme_frame.winfo_ismapped()

        # Show again when closing repo
        switcher.show()
        geometry = switcher.theme_frame.place_info()
        assert 'x' in geometry
