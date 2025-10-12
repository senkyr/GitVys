"""ConnectionDrawer - handles drawing connections between commits."""

import tkinter as tk
from typing import List, Dict, Tuple
import math
from utils.data_structures import Commit
from utils.constants import LINE_WIDTH, NODE_RADIUS
from utils.theme_manager import get_theme_manager
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionDrawer:
    """Handles drawing all connections (lines and curves) between commits."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.line_width = LINE_WIDTH
        self.node_radius = NODE_RADIUS
        self.curve_intensity = 0.8  # Intensity of curve rounding (0-1)

    def draw_connections(self, commits: List[Commit], make_color_pale_callback) -> None:
        """Draws all connections between commits.

        Args:
            commits: List of commits to draw connections for
            make_color_pale_callback: Function to make colors pale (for remote/merge connections)
        """
        commit_positions = {commit.hash: (commit.x, commit.y) for commit in commits}
        commit_info = {commit.hash: commit for commit in commits}

        for commit in commits:
            if commit.parents:
                child_pos = commit_positions.get(commit.hash)
                if child_pos:
                    # Detect merge commit (multiple parents)
                    is_merge_commit = len(commit.parents) >= 2

                    for parent_index, parent_hash in enumerate(commit.parents):
                        parent_pos = commit_positions.get(parent_hash)
                        if parent_pos:
                            # Use remote status and uncommitted status of child for drawing connection
                            # Start from parent, draw to child
                            is_uncommitted = getattr(commit, 'is_uncommitted', False)

                            # Determine connection type
                            parent_commit = commit_info.get(parent_hash)

                            # Branching: parent and child in different branches (but not merge connection)
                            is_branching = parent_commit and parent_commit.branch != commit.branch and not is_merge_commit

                            # Merge connection: second+ parent of merge commit
                            is_merge_connection = is_merge_commit and parent_index > 0

                            # For merge connections use color of parent (merged branch), not child (merge commit)
                            if is_merge_connection:
                                line_color = parent_commit.branch_color if parent_commit else commit.branch_color
                            else:
                                line_color = commit.branch_color

                            self._draw_line(parent_pos, child_pos, line_color, commit.is_remote,
                                          is_uncommitted, is_merge_connection, is_branching, make_color_pale_callback)

    def _draw_line(self, start: Tuple[int, int], end: Tuple[int, int], color: str,
                   is_remote: bool = False, is_uncommitted: bool = False,
                   is_merge_connection: bool = False, is_branching: bool = False,
                   make_color_pale_callback=None) -> int:
        """Draws a straight or curved line between two points.

        Args:
            start: Starting position (x, y)
            end: Ending position (x, y)
            color: Line color
            is_remote: Whether this is a remote connection
            is_uncommitted: Whether this is an uncommitted connection
            is_merge_connection: Whether this is a merge connection
            is_branching: Whether this is a branching connection
            make_color_pale_callback: Function to make color pale

        Returns:
            Canvas item ID
        """
        start_x, start_y = start
        end_x, end_y = end

        # Determine color and stipple pattern for connections
        if is_uncommitted:
            line_color = color  # Full branch color for WIP commits
            stipple_pattern = 'gray50'  # Same stipple as WIP circle
        elif is_merge_connection:
            line_color = color  # Use color as is (already pale from parent, don't add more fading)
            stipple_pattern = None
        elif is_remote:
            line_color = make_color_pale_callback(color) if make_color_pale_callback else color  # Paler color for remote
            stipple_pattern = None
        else:
            line_color = color  # Normal color for local commits
            stipple_pattern = None

        # If commits are in different columns (branching), draw smooth curve
        if start_x != end_x:
            self._draw_bezier_curve(start_x, start_y, end_x, end_y, line_color,
                                   stipple_pattern, is_merge_connection, is_branching)
        else:
            # Straight vertical line for commits in same column
            line_kwargs = {
                'fill': line_color,
                'width': self.line_width
            }
            if stipple_pattern:
                line_kwargs['stipple'] = stipple_pattern

            return self.canvas.create_line(start_x, start_y, end_x, end_y, **line_kwargs)

    def _draw_bezier_curve(self, start_x: int, start_y: int, end_x: int, end_y: int,
                           color: str, stipple_pattern=None, is_merge_connection: bool = False,
                           is_branching: bool = False):
        """Draws smooth L-shaped connection with rounded corners.

        For merge connections: horizontal part at end (merge commit) height
        For branching: horizontal part at start (parent commit) height
        For normal connection: straight or minimal arc
        """

        # Distances WITH SIGN to determine direction
        dx_signed = end_x - start_x  # Positive = right, negative = left
        dy_signed = end_y - start_y  # Positive = down, negative = up
        dx = abs(dx_signed)
        dy = abs(dy_signed)

        # Special case: vertical or horizontal straight line
        if dx == 0 or dy == 0:
            line_kwargs = {
                'fill': color,
                'width': self.line_width
            }
            if stipple_pattern:
                line_kwargs['stipple'] = stipple_pattern
            self.canvas.create_line(start_x, start_y, end_x, end_y, **line_kwargs)
            return

        # Rounding radius - small so curve stays in bounds
        radius = min(dx, dy, 20) * self.curve_intensity  # Max 20px radius
        radius = max(3, min(radius, 15))  # Limit between 3-15px

        # Determine connection direction by positions (4 quadrants)
        # Quadrant 1: right up (dx>0, dy<0)
        # Quadrant 2: left up (dx<0, dy<0)
        # Quadrant 3: left down (dx<0, dy>0)
        # Quadrant 4: right down (dx>0, dy>0)

        # Determine corner position by connection type
        if is_merge_connection:
            # Merge: horizontal part at end (merge commit) height
            corner_y = end_y
            corner_x = start_x
        else:  # is_branching
            # Branching: horizontal part at start (parent commit) height
            corner_y = start_y
            corner_x = end_x

        # Determine arc type by direction
        if dx_signed > 0 and dy_signed > 0:
            # Right down
            arc_type = "right_down"
        elif dx_signed > 0 and dy_signed < 0:
            # Right up
            arc_type = "right_up"
        elif dx_signed < 0 and dy_signed > 0:
            # Left down
            arc_type = "left_down"
        else:  # dx_signed < 0 and dy_signed < 0
            # Left up
            arc_type = "left_up"

        # Draw according to arc_type
        line_kwargs = {
            'fill': color,
            'width': self.line_width
        }
        if stipple_pattern:
            line_kwargs['stipple'] = stipple_pattern

        # 1) First segment (from start to corner - radius)
        if is_merge_connection:
            # Merge: vertical first segment
            if arc_type == "right_down":
                if dy > radius:
                    self.canvas.create_line(start_x, start_y, start_x, corner_y - radius, **line_kwargs)
            elif arc_type == "right_up":
                if dy > radius:
                    self.canvas.create_line(start_x, start_y, start_x, corner_y + radius, **line_kwargs)
            elif arc_type == "left_down":
                if dy > radius:
                    self.canvas.create_line(start_x, start_y, start_x, corner_y - radius, **line_kwargs)
            elif arc_type == "left_up":
                if dy > radius:
                    self.canvas.create_line(start_x, start_y, start_x, corner_y + radius, **line_kwargs)
        else:
            # Branching: horizontal first segment
            if arc_type == "right_down":
                if dx > radius:
                    self.canvas.create_line(start_x, start_y, corner_x - radius, corner_y, **line_kwargs)
            elif arc_type == "right_up":
                if dx > radius:
                    self.canvas.create_line(start_x, start_y, corner_x - radius, corner_y, **line_kwargs)
            elif arc_type == "left_down":
                if dx > radius:
                    self.canvas.create_line(start_x, start_y, corner_x + radius, corner_y, **line_kwargs)
            elif arc_type == "left_up":
                if dx > radius:
                    self.canvas.create_line(start_x, start_y, corner_x + radius, corner_y, **line_kwargs)

        # 2) Rounded corner
        if dx > radius and dy > radius:
            corner_points = self._calculate_rounded_corner_arc(
                start_x, start_y, end_x, end_y,
                corner_x, corner_y,
                radius,
                arc_type=arc_type,
                is_merge=is_merge_connection
            )

            if len(corner_points) > 2:
                corner_kwargs = {
                    'fill': color,
                    'width': self.line_width,
                    'smooth': True
                }
                if stipple_pattern:
                    corner_kwargs['stipple'] = stipple_pattern
                self.canvas.create_line(corner_points, **corner_kwargs)

        # 3) Last segment (from corner + radius to end)
        if is_merge_connection:
            # Merge: horizontal last segment
            if arc_type == "right_down":
                if dx > radius:
                    self.canvas.create_line(corner_x + radius, corner_y, end_x, end_y, **line_kwargs)
            elif arc_type == "right_up":
                if dx > radius:
                    self.canvas.create_line(corner_x + radius, corner_y, end_x, end_y, **line_kwargs)
            elif arc_type == "left_down":
                if dx > radius:
                    self.canvas.create_line(corner_x - radius, corner_y, end_x, end_y, **line_kwargs)
            elif arc_type == "left_up":
                if dx > radius:
                    self.canvas.create_line(corner_x - radius, corner_y, end_x, end_y, **line_kwargs)
        else:
            # Branching: vertical last segment
            if arc_type == "right_down":
                if dy > radius:
                    self.canvas.create_line(corner_x, corner_y + radius, end_x, end_y, **line_kwargs)
            elif arc_type == "right_up":
                if dy > radius:
                    self.canvas.create_line(corner_x, corner_y - radius, end_x, end_y, **line_kwargs)
            elif arc_type == "left_down":
                if dy > radius:
                    self.canvas.create_line(corner_x, corner_y + radius, end_x, end_y, **line_kwargs)
            elif arc_type == "left_up":
                if dy > radius:
                    self.canvas.create_line(corner_x, corner_y - radius, end_x, end_y, **line_kwargs)

        # For very short distances - fallback to simple line
        if dx <= radius or dy <= radius:
            self.canvas.create_line(start_x, start_y, end_x, end_y, **line_kwargs)

    def _calculate_rounded_corner_arc(self, start_x: int, start_y: int, end_x: int, end_y: int,
                                       corner_x: int, corner_y: int, radius: int,
                                       arc_type: str = "right_down", is_merge: bool = False):
        """Calculates points for rounded corner using circular arc by type."""
        points = []
        steps = 8

        # New arc_types by direction (4 quadrants)
        if is_merge:
            # Merge: vertical→horizontal, interpolation from horizontal to vertical point
            if arc_type == "right_down":
                arc_center_x = corner_x + radius
                arc_center_y = corner_y - radius
                start_angle = math.pi / 2  # 90° - horizontal point (bottom)
                end_angle = math.pi  # 180° - vertical point (left)
            elif arc_type == "right_up":
                arc_center_x = corner_x + radius
                arc_center_y = corner_y + radius
                start_angle = 3 * math.pi / 2  # 270° - horizontal point (top)
                end_angle = math.pi  # 180° - vertical point (left)
            elif arc_type == "left_down":
                arc_center_x = corner_x - radius
                arc_center_y = corner_y - radius
                start_angle = math.pi / 2  # 90° - horizontal point (bottom)
                end_angle = 2 * math.pi  # 360° - vertical point (right)
            elif arc_type == "left_up":
                arc_center_x = corner_x - radius
                arc_center_y = corner_y + radius
                start_angle = 3 * math.pi / 2  # 270° - horizontal point (top)
                end_angle = 2 * math.pi  # 360° - vertical point (right)
        else:
            # Branching: horizontal→vertical, arc center shifted inside L-shape
            if arc_type == "right_down":
                arc_center_x = corner_x - radius
                arc_center_y = corner_y + radius
                start_angle = 3 * math.pi / 2  # 270° - from top
                end_angle = 2 * math.pi  # 360°/0° - to right
            elif arc_type == "right_up":
                arc_center_x = corner_x - radius
                arc_center_y = corner_y - radius
                start_angle = math.pi / 2  # 90° - from bottom
                end_angle = 0  # 0° - to right
            elif arc_type == "left_down":
                arc_center_x = corner_x + radius
                arc_center_y = corner_y + radius
                start_angle = 3 * math.pi / 2  # 270° - from top
                end_angle = math.pi  # 180° - to left
            elif arc_type == "left_up":
                arc_center_x = corner_x + radius
                arc_center_y = corner_y - radius
                start_angle = math.pi / 2  # 90° - from bottom
                end_angle = math.pi  # 180° - to left
            # Backward compatibility with old names
            elif arc_type == "branching":
                arc_center_x = corner_x - radius
                arc_center_y = corner_y - radius
                start_angle = 0
                end_angle = math.pi / 2
            elif arc_type == "merge":
                arc_center_x = corner_x - radius
                arc_center_y = corner_y + radius
                start_angle = 3 * math.pi / 2
                end_angle = 2 * math.pi
            else:
                raise ValueError(f"Unknown arc_type: {arc_type}")

        # Ensure interpolation goes short way around circle
        angle_diff = end_angle - start_angle
        if angle_diff < 0 and abs(angle_diff) > math.pi:
            # Add 2π to end_angle for interpolation through 360°/0°
            end_angle += 2 * math.pi
        elif angle_diff > 0 and angle_diff > math.pi:
            # Subtract 2π from end_angle
            end_angle -= 2 * math.pi

        for i in range(steps + 1):
            # Interpolation between start_angle and end_angle (short way)
            angle = start_angle + (i / steps) * (end_angle - start_angle)

            # Calculate point on circle relative to arc center
            x = arc_center_x + radius * math.cos(angle)
            y = arc_center_y + radius * math.sin(angle)

            points.extend([int(x), int(y)])

        return points
