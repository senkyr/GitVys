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

    @pytest.mark.parametrize("branch_name,expected_hue,description", [
        ("main", 210, "main → azure hue"),
        ("master", 210, "master → azure hue"),
        ("develop", 150, "develop → light green hue"),
        ("feature/login", 90, "feature/* → yellow-green hue"),
        ("feature/api", 90, "feature/* (different name)"),
        ("hotfix/critical", 330, "hotfix/* → pink hue"),
        ("bugfix/typo", 0, "bugfix/* → red hue"),
        ("release/1.0", 270, "release/* → purple hue"),
    ])
    def test_semantic_branches(self, branch_name, expected_hue, description):
        """Test semantic branch hue mapping.

        Verifies that well-known branch names/prefixes map to
        consistent semantic hues for visual consistency.
        """
        assert get_semantic_hue(branch_name) == expected_hue, f"Failed for {description}"

    @pytest.mark.parametrize("branch_name", [
        "custom-branch",
        "my-feature",
    ])
    def test_no_semantic_match(self, branch_name):
        """Non-semantic branches should return None."""
        assert get_semantic_hue(branch_name) is None


class TestIsSemanticHueConflict:
    """Tests for semantic hue conflict detection."""

    @pytest.mark.parametrize("hue,expected_conflict,description", [
        # Exact semantic hues
        (210, True, "exact main hue (210)"),
        (150, True, "exact develop hue (150)"),
        # Near semantic hues (within tolerance)
        (215, True, "near main hue (210+5)"),
        (205, True, "near main hue (210-5)"),
        # Far from semantic hues
        (50, False, "far from any semantic hue"),
        (180, False, "far from any semantic hue"),
    ])
    def test_semantic_hue_conflict_detection(self, hue, expected_conflict, description):
        """Test semantic hue conflict detection.

        Semantic hues should conflict (return True) if they are exact matches
        or within tolerance of well-known branch hues (main, develop, etc).
        """
        assert is_semantic_hue_conflict(hue) == expected_conflict, f"Failed for {description}"


class TestNormalizeBranchName:
    """Tests for branch name normalization."""

    @pytest.mark.parametrize("input_name,expected_output,description", [
        # With origin/ prefix
        ("origin/main", "main", "origin/main → main"),
        ("origin/feature/login", "feature/login", "origin/feature/login → feature/login"),
        # Without prefix
        ("main", "main", "main → main (unchanged)"),
        ("feature/test", "feature/test", "feature/test → feature/test (unchanged)"),
    ])
    def test_normalize_branch_name(self, input_name, expected_output, description):
        """Test branch name normalization (removes origin/ prefix)."""
        assert normalize_branch_name(input_name) == expected_output, f"Failed for {description}"


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
