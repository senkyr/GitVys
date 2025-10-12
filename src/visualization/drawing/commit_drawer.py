"""CommitDrawer - handles drawing commit nodes and metadata."""

import tkinter as tk
from typing import List, Dict, Callable
import math
from collections import Counter
from utils.data_structures import Commit
from utils.constants import NODE_RADIUS, FONT_SIZE
from utils.theme_manager import get_theme_manager
from utils.logging_config import get_logger

logger = get_logger(__name__)


class CommitDrawer:
    """Handles drawing commit nodes (circles) with text and metadata."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.node_radius = NODE_RADIUS
        self.font_size = FONT_SIZE

    def draw_commits(self, commits: List[Commit], column_widths: Dict,
                    show_tooltip_callback: Callable,
                    hide_tooltip_callback: Callable,
                    truncate_text_callback: Callable,
                    table_start_position: int,
                    make_color_pale_callback: Callable,
                    branch_flag_drawer,
                    draw_flag_connection_callback: Callable) -> None:
        """Draws all commit nodes with metadata.

        Args:
            commits: List of commits to draw
            column_widths: Dictionary with column widths
            show_tooltip_callback: Callback to show tooltip
            hide_tooltip_callback: Callback to hide tooltip
            truncate_text_callback: Callback to truncate text to width
            table_start_position: X position where table starts
            make_color_pale_callback: Callback to make colors pale
            branch_flag_drawer: BranchFlagDrawer instance to draw branch flags
            draw_flag_connection_callback: Callback to draw flag connections
        """
        # Use standard font - scaling is handled by text length, not font size
        font = ('Arial', self.font_size)

        # Check if we have any branch head commits
        has_branch_heads = any(commit.is_branch_head for commit in commits)

        if has_branch_heads:
            # New logic - use branch head commits
            branch_head_commits = {}  # branch_name -> {'local': commit, 'remote': commit, 'both': commit}

            for commit in commits:
                if commit.is_branch_head:
                    clean_branch_name = commit.branch
                    if commit.branch.startswith('origin/'):
                        clean_branch_name = commit.branch[7:]  # Remove "origin/"

                    if clean_branch_name not in branch_head_commits:
                        branch_head_commits[clean_branch_name] = {}

                    branch_head_commits[clean_branch_name][commit.branch_head_type] = commit
        else:
            # Fallback logic - use first commit of each branch (original behavior)
            drawn_branch_flags = set()
            # Find last commit of each branch (by time, but ignore WIP commits)
            last_commits_by_branch = {}
            for commit in commits:
                # Ignore WIP commits when finding last real commit
                if getattr(commit, 'is_uncommitted', False):
                    continue

                if commit.branch not in last_commits_by_branch:
                    last_commits_by_branch[commit.branch] = commit
                elif commit.date > last_commits_by_branch[commit.branch].date:
                    last_commits_by_branch[commit.branch] = commit

        tm = get_theme_manager()

        for commit in commits:
            x, y = commit.x, commit.y

            # Visual distinction for uncommitted changes, remote commits, or normal
            if getattr(commit, 'is_uncommitted', False):
                # WIP commits - stippled polygon in branch color with black outline
                fill_color = commit.branch_color
                outline_color = tm.get_color('commit_node_outline')
                stipple_pattern = 'gray50'  # 50% stipple to indicate incompleteness

                # Create circle polygon instead of ovals (stipple doesn't work with ovals on Windows)
                points = self._create_circle_polygon(x, y, self.node_radius)
                self.canvas.create_polygon(
                    points,
                    fill=fill_color,
                    outline=outline_color,
                    width=1,
                    stipple=stipple_pattern,
                    tags=f"node_{commit.hash}"
                )
            elif commit.is_remote:
                # Paler version of branch_color (50% transparency simulation)
                fill_color = make_color_pale_callback(commit.branch_color)
                outline_color = tm.get_color('commit_node_outline')
                self.canvas.create_oval(
                    x - self.node_radius, y - self.node_radius,
                    x + self.node_radius, y + self.node_radius,
                    fill=fill_color,
                    outline=outline_color,
                    width=1,
                    tags=f"node_{commit.hash}"
                )
            else:
                # Normal commits
                fill_color = commit.branch_color
                outline_color = tm.get_color('commit_node_outline')
                self.canvas.create_oval(
                    x - self.node_radius, y - self.node_radius,
                    x + self.node_radius, y + self.node_radius,
                    fill=fill_color,
                    outline=outline_color,
                    width=1,
                    tags=f"node_{commit.hash}"
                )

            # Display flag according to used mode
            if has_branch_heads:
                # New logic - display flag for branch head commits (but not for virtual merge branches)
                if (commit.is_branch_head and commit.branch != 'unknown' and
                    not commit.branch.startswith('merge-')):
                    clean_branch_name = commit.branch
                    if commit.branch.startswith('origin/'):
                        clean_branch_name = commit.branch[7:]  # Remove "origin/"

                    flag_color = make_color_pale_callback(commit.branch_color) if commit.is_remote else commit.branch_color

                    # Determine which symbols to display according to branch_head_type
                    if commit.branch_head_type == "both":
                        # Display both symbols (as before)
                        branch_avail = "both"
                    elif commit.branch_head_type == "local":
                        # Only computer symbol
                        branch_avail = "local_only"
                    elif commit.branch_head_type == "remote":
                        # Only cloud symbol
                        branch_avail = "remote_only"
                    else:
                        branch_avail = commit.branch_availability

                    branch_flag_drawer.draw_branch_flag(x, y, clean_branch_name, flag_color, commit.is_remote, branch_avail)

                    # Draw connection line to flag
                    connection_color = make_color_pale_callback(commit.branch_color) if commit.is_remote else commit.branch_color
                    draw_flag_connection_callback(x, y, connection_color)
            else:
                # Fallback logic - original behavior (but not for WIP and merge commits)
                if (commit.branch != 'unknown' and
                    commit.branch not in drawn_branch_flags and
                    not getattr(commit, 'is_uncommitted', False) and
                    not commit.branch.startswith('merge-')):
                    flag_color = make_color_pale_callback(commit.branch_color) if commit.is_remote else commit.branch_color
                    branch_flag_drawer.draw_branch_flag(x, y, commit.branch, flag_color, commit.is_remote, commit.branch_availability)
                    drawn_branch_flags.add(commit.branch)

                # If this is last commit of branch, draw horizontal connection to flag (except 'unknown', WIP and merge)
                if (commit.branch != 'unknown' and
                    commit.branch in last_commits_by_branch and
                    last_commits_by_branch[commit.branch] == commit and
                    not getattr(commit, 'is_uncommitted', False) and
                    not commit.branch.startswith('merge-')):
                    connection_color = make_color_pale_callback(commit.branch_color) if commit.is_remote else commit.branch_color
                    draw_flag_connection_callback(x, y, connection_color)

            # Fixed position for "table" start - behind all branches
            text_x = table_start_position

            # Create combined text message + description
            # Determine text color by commit type
            if getattr(commit, 'is_uncommitted', False):
                message_color = tm.get_color('commit_text_wip')  # Dark gray for WIP commits
            else:
                message_color = tm.get_color('commit_text')  # Black for normal commits

            # First truncate message according to available column width
            if commit.description_short:
                # With description - reserve space for description
                # Try to use full message if it fits
                full_message_width = self.canvas.tk.call("font", "measure", font, commit.message)
                min_desc_space = 100  # Minimal space for description

                # Available space for message is full column width - margins - minimal space for description
                available_message_space = column_widths['message'] - 40 - min_desc_space

                # Truncate message if too long
                message_to_display = truncate_text_callback(
                    self.canvas, font, commit.message, available_message_space
                )

                # Message in corresponding color
                message_item = self.canvas.create_text(
                    text_x, y,
                    text=message_to_display,
                    anchor='w',
                    font=font,
                    fill=message_color,
                    tags=("commit_text", f"msg_{commit.hash}")
                )

                # Add tooltip if truncated
                if message_to_display != commit.message:
                    self.canvas.tag_bind(f"msg_{commit.hash}", "<Enter>",
                        lambda e, msg=commit.message: show_tooltip_callback(e, msg))
                    self.canvas.tag_bind(f"msg_{commit.hash}", "<Leave>",
                        lambda e: hide_tooltip_callback())

                # Measure width of displayed message for description position
                message_width = self.canvas.tk.call("font", "measure", font, message_to_display)
                desc_x = text_x + message_width + 20  # 20px space for better distinction

                # Calculate available space for description
                available_space = column_widths['message'] - message_width - 40  # 40px margins (20 + 20)

                # Truncate description to fit available space
                description_to_display = truncate_text_callback(
                    self.canvas, font, commit.description_short, available_space
                )

                # Draw description in gray with tooltip
                desc_item = self.canvas.create_text(
                    desc_x, y,
                    text=description_to_display,
                    anchor='w',
                    font=font,
                    fill=tm.get_color('description_text'),
                    tags=("commit_text", f"desc_{commit.hash}")
                )

                # Add event handlers for tooltip only if original description has more content
                if commit.description and commit.description.strip() != commit.description_short:
                    self.canvas.tag_bind(f"desc_{commit.hash}", "<Enter>",
                        lambda e, desc=commit.description: show_tooltip_callback(e, desc))
                    self.canvas.tag_bind(f"desc_{commit.hash}", "<Leave>",
                        lambda e: hide_tooltip_callback())
            else:
                # Without description - message can take full column width
                available_message_space = column_widths['message'] - 20  # 20px padding

                # Truncate message if too long
                message_to_display = truncate_text_callback(
                    self.canvas, font, commit.message, available_message_space
                )

                # Message without description
                message_item = self.canvas.create_text(
                    text_x, y,
                    text=message_to_display,
                    anchor='w',
                    font=font,
                    fill=message_color,
                    tags=("commit_text", f"msg_{commit.hash}")
                )

                # Add tooltip if truncated
                if message_to_display != commit.message:
                    self.canvas.tag_bind(f"msg_{commit.hash}", "<Enter>",
                        lambda e, msg=commit.message: show_tooltip_callback(e, msg))
                    self.canvas.tag_bind(f"msg_{commit.hash}", "<Leave>",
                        lambda e: hide_tooltip_callback())

            text_x += column_widths['message']

            # Author - centered in column (only for normal commits)
            if not getattr(commit, 'is_uncommitted', False):
                author_center_x = text_x + column_widths['author'] // 2

                # Truncate author according to available width
                author_to_display = truncate_text_callback(
                    self.canvas, font, commit.author, column_widths['author']
                )

                # Draw with tag
                author_item = self.canvas.create_text(
                    author_center_x, y,
                    text=author_to_display,
                    anchor='center',
                    font=font,
                    fill=tm.get_color('author_text'),
                    tags=("commit_text", f"author_{commit.hash}")
                )

                # Add tooltip if truncated
                if author_to_display != commit.author:
                    self.canvas.tag_bind(f"author_{commit.hash}", "<Enter>",
                        lambda e, author=commit.author: show_tooltip_callback(e, author))
                    self.canvas.tag_bind(f"author_{commit.hash}", "<Leave>",
                        lambda e: hide_tooltip_callback())
            text_x += column_widths['author']

            # Email - centered in column (only for normal commits)
            if not getattr(commit, 'is_uncommitted', False):
                email_center_x = text_x + column_widths['email'] // 2

                # Truncate email according to available width
                email_to_display = truncate_text_callback(
                    self.canvas, font, commit.author_email, column_widths['email']
                )

                # Draw with tag
                email_item = self.canvas.create_text(
                    email_center_x, y,
                    text=email_to_display,
                    anchor='center',
                    font=font,
                    fill=tm.get_color('email_text'),
                    tags=("commit_text", f"email_{commit.hash}")
                )

                # Add tooltip if truncated
                if email_to_display != commit.author_email:
                    self.canvas.tag_bind(f"email_{commit.hash}", "<Enter>",
                        lambda e, email=commit.author_email: show_tooltip_callback(e, email))
                    self.canvas.tag_bind(f"email_{commit.hash}", "<Leave>",
                        lambda e: hide_tooltip_callback())
            text_x += column_widths['email']

            # Date - centered in column (only for normal commits)
            if not getattr(commit, 'is_uncommitted', False):
                date_center_x = text_x + column_widths['date'] // 2
                self.canvas.create_text(
                    date_center_x, y,
                    text=commit.date_short,
                    anchor='center',
                    font=font,
                    fill=tm.get_color('date_text'),
                    tags="commit_text"
                )

        # Detect dominant author (>80% commits)
        author_counts = Counter(commit.author for commit in commits)
        total_commits = len(commits)
        dominant_author = None
        if author_counts and total_commits > 0:
            most_common_author, count = author_counts.most_common(1)[0]
            if count / total_commits > 0.8:
                dominant_author = most_common_author

        # Add tooltips with author only for non-dominant authors
        for commit in commits:
            if commit.author != dominant_author:
                self.canvas.tag_bind(f"node_{commit.hash}", "<Enter>",
                    lambda e, author=commit.author: show_tooltip_callback(e, author))
                self.canvas.tag_bind(f"node_{commit.hash}", "<Leave>",
                    lambda e: hide_tooltip_callback())

    def _create_circle_polygon(self, x: int, y: int, radius: int, num_points: int = 20) -> List[float]:
        """Creates points for circular polygon (for stipple support on Windows)."""
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            points.extend([px, py])
        return points
