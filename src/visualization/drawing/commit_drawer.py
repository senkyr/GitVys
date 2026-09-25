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

    # Canvas tag všech položek s tooltipem - události se navážou jen jednou na tag
    TOOLTIP_TAG = "has_tooltip"

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.node_radius = NODE_RADIUS
        self.font_size = FONT_SIZE

        # Tooltipy: id položky na canvasu -> text. Místo tag_bind s novou lambdou
        # pro každou položku (každá registruje Tcl příkaz, který se neuvolní ani
        # po smazání položky - při každém překreslení rostla paměť) je jeden
        # handler pro tag TOOLTIP_TAG, který si text najde podle id.
        self._node_tooltips: Dict[int, str] = {}
        self._text_tooltips: Dict[int, str] = {}
        self._show_tooltip = None
        self._hide_tooltip = None
        self._tooltip_events_bound = False

    def _bind_tooltip_events(self):
        if self._tooltip_events_bound:
            return
        self.canvas.tag_bind(self.TOOLTIP_TAG, "<Enter>", self._on_tooltip_enter)
        self.canvas.tag_bind(self.TOOLTIP_TAG, "<Leave>", self._on_tooltip_leave)
        self._tooltip_events_bound = True

    def _on_tooltip_enter(self, event):
        current = self.canvas.find_withtag("current")
        if not current or not self._show_tooltip:
            return
        item = current[0]
        text = self._text_tooltips.get(item) or self._node_tooltips.get(item)
        if text:
            self._show_tooltip(event, text)

    def _on_tooltip_leave(self, event):
        if self._hide_tooltip:
            self._hide_tooltip()

    def _add_tooltip(self, item, text: str, is_node: bool = False):
        """Zaregistruje tooltip pro položku canvasu."""
        (self._node_tooltips if is_node else self._text_tooltips)[item] = text
        self.canvas.addtag_withtag(self.TOOLTIP_TAG, item)

    def draw_commits(self, commits: List[Commit], column_widths: Dict,
                    show_tooltip_callback: Callable,
                    hide_tooltip_callback: Callable,
                    truncate_text_callback: Callable,
                    table_start_position: int,
                    make_color_pale_callback: Callable,
                    branch_flag_drawer,
                    draw_flag_connection_callback: Callable,
                    text_only: bool = False,
                    visible_commits: List[Commit] = None) -> None:
        """Draws all commit nodes with metadata.

        Při text_only=True se kreslí jen texty tabulky (překreslení po změně
        šířky sloupců). Uzly a vlaječky zůstávají na canvasu - dřív se při
        každém snímku tažení oddělovače kreslily znovu přes staré a počet
        položek canvasu rostl bez omezení.

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
            text_only: Draw only table texts (nodes and flags are already on canvas)
            visible_commits: Commits to actually draw (virtualized rendering). Global
                decisions (flags, dominant author) are still made over all `commits`.
        """
        # Use standard font - scaling is handled by text length, not font size
        font = ('Arial', self.font_size)

        self._show_tooltip = show_tooltip_callback
        self._hide_tooltip = hide_tooltip_callback
        self._bind_tooltip_events()
        self._text_tooltips = {}
        if not text_only:
            self._node_tooltips = {}

        # Rozhodnutí, která závisí na celé historii (ne jen na vykreslovaném výřezu)
        analysis = self._analyze(commits)
        has_branch_heads = analysis['has_branch_heads']
        flag_commit_ids = analysis['flag_commit_ids']
        connection_commit_ids = analysis['connection_commit_ids']
        dominant_author = analysis['dominant_author']

        tm = get_theme_manager()
        node_items = []  # (commit, id uzlu na canvasu) pro tooltipy s autorem

        for commit in (commits if visible_commits is None else visible_commits):
            x, y = commit.x, commit.y

            if not text_only:
                # Visual distinction for uncommitted changes, remote commits, or normal
                if getattr(commit, 'is_uncommitted', False):
                    # WIP commits - stippled polygon in branch color with black outline
                    fill_color = commit.branch_color
                    outline_color = tm.get_color('commit_node_outline')
                    stipple_pattern = 'gray50'  # 50% stipple to indicate incompleteness

                    # Create circle polygon instead of ovals (stipple doesn't work with ovals on Windows)
                    points = self._create_circle_polygon(x, y, self.node_radius)
                    node_item = self.canvas.create_polygon(
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
                    node_item = self.canvas.create_oval(
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
                    node_item = self.canvas.create_oval(
                        x - self.node_radius, y - self.node_radius,
                        x + self.node_radius, y + self.node_radius,
                        fill=fill_color,
                        outline=outline_color,
                        width=1,
                        tags=f"node_{commit.hash}"
                    )
                node_items.append((commit, node_item))

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
                    # Fallback logic - flag at first commit of each branch (not for WIP and merge commits)
                    if id(commit) in flag_commit_ids:
                        flag_color = make_color_pale_callback(commit.branch_color) if commit.is_remote else commit.branch_color
                        branch_flag_drawer.draw_branch_flag(x, y, commit.branch, flag_color, commit.is_remote, commit.branch_availability)

                    # If this is last commit of branch, draw horizontal connection to flag (except 'unknown', WIP and merge)
                    if id(commit) in connection_commit_ids:
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
                    self._add_tooltip(message_item, commit.message)

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
                    self._add_tooltip(desc_item, commit.description)
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
                    self._add_tooltip(message_item, commit.message)

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
                    self._add_tooltip(author_item, commit.author)
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
                    self._add_tooltip(email_item, commit.author_email)
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

        # Add tooltips with author only for non-dominant authors
        if not text_only:
            for commit, node_item in node_items:
                if commit.author and commit.author != dominant_author:
                    self._add_tooltip(node_item, commit.author, is_node=True)

    def _analyze(self, commits: List[Commit]) -> Dict:
        """Globální rozbor commitů pro kreslení; výsledek se cachuje pro stejný seznam.

        Při virtualizovaném kreslení se draw_commits volá pro každý výřez
        znovu, ale tato rozhodnutí závisí na celé historii.
        """
        cache_key = (id(commits), len(commits))
        cached = getattr(self, '_analysis_cache', None)
        if cached and cached[0] == cache_key and cached[1] is commits:
            return cached[2]

        has_branch_heads = any(commit.is_branch_head for commit in commits)

        flag_commit_ids = set()
        connection_commit_ids = set()
        if not has_branch_heads:
            # Fallback: vlaječka u prvního commitu větve v pořadí řádků,
            # spojnice k vlaječce u nejnovějšího (podle data) commitu větve
            flagged_branches = set()
            last_commits_by_branch = {}
            for commit in commits:
                if getattr(commit, 'is_uncommitted', False):
                    continue
                if commit.branch == 'unknown' or commit.branch.startswith('merge-'):
                    continue
                if commit.branch not in flagged_branches:
                    flagged_branches.add(commit.branch)
                    flag_commit_ids.add(id(commit))
                last = last_commits_by_branch.get(commit.branch)
                if last is None or commit.date > last.date:
                    last_commits_by_branch[commit.branch] = commit
            connection_commit_ids = {id(commit) for commit in last_commits_by_branch.values()}

        # Detect dominant author (>80% commits)
        dominant_author = None
        author_counts = Counter(commit.author for commit in commits)
        if author_counts and commits:
            most_common_author, count = author_counts.most_common(1)[0]
            if count / len(commits) > 0.8:
                dominant_author = most_common_author

        analysis = {
            'has_branch_heads': has_branch_heads,
            'flag_commit_ids': flag_commit_ids,
            'connection_commit_ids': connection_commit_ids,
            'dominant_author': dominant_author,
        }
        self._analysis_cache = (cache_key, commits, analysis)
        return analysis

    def _create_circle_polygon(self, x: int, y: int, radius: int, num_points: int = 20) -> List[float]:
        """Creates points for circular polygon (for stipple support on Windows)."""
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            points.extend([px, py])
        return points
