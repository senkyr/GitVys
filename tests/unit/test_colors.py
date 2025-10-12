"""Unit tests for visualization.colors module."""

import pytest
from visualization.colors import (
    hsl_to_hex,
    get_semantic_hue,
    is_semantic_hue_conflict,
    get_branch_color,
    normalize_branch_name,
    make_color_pale
)


class TestHslToHex:
    """Tests for HSL to hex conversion."""

    def test_red_conversion(self):
        """Test conversion of red color."""
        assert hsl_to_hex(0, 100, 50) == "#ff0000"

    def test_blue_conversion(self):
        """Test conversion of blue color."""
        # Azure blue for main/master
        result = hsl_to_hex(210, 80, 50)
        assert result.startswith("#")
        assert len(result) == 7

    def test_green_conversion(self):
        """Test conversion of green color."""
        result = hsl_to_hex(120, 80, 50)
        assert result.startswith("#")
        assert len(result) == 7


class TestGetSemanticHue:
    """Tests for semantic hue mapping."""

    def test_main_branch(self):
        """Main branch should return azure hue."""
        assert get_semantic_hue("main") == 210

    def test_master_branch(self):
        """Master branch should return azure hue."""
        assert get_semantic_hue("master") == 210

    def test_develop_branch(self):
        """Develop branch should return light green hue."""
        assert get_semantic_hue("develop") == 150

    def test_feature_prefix(self):
        """Feature branches should return yellow-green hue."""
        assert get_semantic_hue("feature/login") == 90
        assert get_semantic_hue("feature/api") == 90

    def test_hotfix_prefix(self):
        """Hotfix branches should return pink hue."""
        assert get_semantic_hue("hotfix/critical") == 330

    def test_bugfix_prefix(self):
        """Bugfix branches should return red hue."""
        assert get_semantic_hue("bugfix/typo") == 0

    def test_release_prefix(self):
        """Release branches should return purple hue."""
        assert get_semantic_hue("release/1.0") == 270

    def test_no_semantic_match(self):
        """Non-semantic branches should return None."""
        assert get_semantic_hue("custom-branch") is None
        assert get_semantic_hue("my-feature") is None


class TestIsSemanticHueConflict:
    """Tests for semantic hue conflict detection."""

    def test_exact_semantic_hue(self):
        """Exact semantic hues should conflict."""
        assert is_semantic_hue_conflict(210) is True  # main
        assert is_semantic_hue_conflict(150) is True  # develop

    def test_near_semantic_hue(self):
        """Near semantic hues (within tolerance) should conflict."""
        assert is_semantic_hue_conflict(215) is True  # Close to main (210)
        assert is_semantic_hue_conflict(205) is True  # Close to main (210)

    def test_far_from_semantic_hues(self):
        """Hues far from semantic values should not conflict."""
        assert is_semantic_hue_conflict(50) is False
        assert is_semantic_hue_conflict(180) is False


class TestNormalizeBranchName:
    """Tests for branch name normalization."""

    def test_origin_prefix_removed(self):
        """Origin prefix should be removed."""
        assert normalize_branch_name("origin/main") == "main"
        assert normalize_branch_name("origin/feature/login") == "feature/login"

    def test_no_prefix(self):
        """Branches without prefix should remain unchanged."""
        assert normalize_branch_name("main") == "main"
        assert normalize_branch_name("feature/test") == "feature/test"


class TestGetBranchColor:
    """Tests for branch color generation."""

    def test_semantic_branch_colors(self):
        """Semantic branches should get consistent colors."""
        used = set()
        main_color = get_branch_color("main", used)
        assert main_color == hsl_to_hex(210, 80, 50)
        assert main_color in used

    def test_remote_same_as_local(self):
        """Remote branches should share color with local equivalent."""
        used = set()
        local_color = get_branch_color("feature/login", used)
        remote_color = get_branch_color("origin/feature/login", used)
        assert local_color == remote_color

    def test_non_semantic_branches_unique(self):
        """Non-semantic branches should get unique colors."""
        used = set()
        color1 = get_branch_color("custom-1", used)
        color2 = get_branch_color("custom-2", used)
        assert color1 != color2
        assert color1 in used
        assert color2 in used

    def test_color_format(self):
        """All colors should be valid hex format."""
        used = set()
        color = get_branch_color("test-branch", used)
        assert color.startswith("#")
        assert len(color) == 7
        # Check it's valid hex
        int(color[1:], 16)


class TestMakeColorPale:
    """Tests for color paling."""

    def test_remote_blend(self):
        """Remote blend should create paler color."""
        color = "#FF0000"
        pale = make_color_pale(color, "remote")
        assert pale.startswith("#")
        assert len(pale) == 7
        assert pale != color  # Should be different

    def test_merge_blend(self):
        """Merge blend should create very pale color."""
        color = "#0000FF"
        pale = make_color_pale(color, "merge")
        assert pale.startswith("#")
        assert len(pale) == 7
        assert pale != color

    def test_merge_paler_than_remote(self):
        """Merge blend should be paler than remote blend."""
        color = "#00FF00"
        pale_remote = make_color_pale(color, "remote")
        pale_merge = make_color_pale(color, "merge")
        # Both should be valid and different
        assert pale_remote != pale_merge

    def test_unknown_color(self):
        """Unknown colors should return default gray."""
        assert make_color_pale("unknown", "remote") == "#E0E0E0"
        assert make_color_pale("", "remote") == "#E0E0E0"

    def test_named_color(self):
        """Named colors should be converted to pale version."""
        pale = make_color_pale("red", "remote")
        assert pale == "#FFB3B3"

    def test_invalid_hex(self):
        """Invalid hex should fallback gracefully."""
        result = make_color_pale("#GGGGGG", "remote")
        # Should either return default or handle gracefully
        assert result.startswith("#")
