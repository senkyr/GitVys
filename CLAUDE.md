# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

```bash
python main.py
# or
python3 main.py
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Building Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="GitVisualizer" main.py
```

The executable will be in the `dist/` folder.

## Project Architecture

This is a Python desktop application that visualizes Git repository history using tkinter. The application follows a modular architecture with clear separation of concerns:

### Core Components

- **Main Entry Point**: `main.py` - Simple launcher that initializes the GUI
- **GUI Layer**: `gui/` directory contains all UI components
  - `main_window.py` - Main application window with drag & drop functionality
  - `graph_canvas.py` - Canvas component for rendering the commit graph
  - `drag_drop.py` - Handles drag & drop operations for repository folders
- **Git Operations**: `repo/repository.py` - GitRepository class handles all Git operations using GitPython
- **Visualization**: `visualization/` directory contains graph rendering logic
  - `graph_drawer.py` - Draws commit nodes and connections on canvas
  - `layout.py` - Calculates positioning for commits and branches
  - `colors.py` - Manages branch color schemes
- **Data Structures**: `utils/data_structures.py` - Defines Commit and Branch data classes
- **Utilities**: `utils/` directory contains helper modules
  - `logging_config.py` - Centralized logging configuration
  - `constants.py` - Application-wide constants (layout, colors, UI dimensions)

### Key Technologies

- **Python 3.8+** with tkinter for GUI
- **GitPython** for Git repository operations
- **Pillow** for image processing
- **tkinterdnd2** for drag & drop functionality

### Application Flow

1. User drags Git repository folder OR Git URL into application
2. For URLs: Repository is cloned to temporary directory with automatic cleanup
3. GitRepository class loads and parses commit history
4. GraphLayout calculates positions for commits based on timeline and branches (with lane recycling)
5. GraphDrawer renders the visualization on canvas with:
   - Interactive column resizing
   - Tooltips for truncated text
   - Tag display with emojis
   - Smooth scrolling with momentum
6. UI displays commit graph with branch colors and commit details

### Features

- **URL Support**: Clone remote repositories (GitHub, GitLab, Bitbucket) to temp directory
- **Temp Clone Management**: Automatic cleanup of cloned repositories with proper Windows file handle management
- **Tags**: Display Git tags with emoji icons (🏷️ normal, 📌 release, 🚀 version) and tooltips for annotated tags
- **Remote Branches**: Load remote branches via "Načíst remote/větve" button
- **Interactive Columns**: Resize column widths by dragging separators
- **Smooth Scrolling**: Momentum-based scrolling with acceleration
- **Tooltips**: Hover tooltips for truncated text (commits, authors, branch names, tags)
- **Column Headers**: Floating headers that stay visible while scrolling

### Data Model

The main data structures:

**Commit class:**

- Basic Git data (hash, message, author, date, parents)
- UI-specific data (truncated messages, relative dates, branch colors)
- Layout data (x/y positions for rendering)
- Tag information (attached tags with emoji)
- Uncommitted changes support (WIP commits)

**MergeBranch class:**

- Virtual branches for merge commits
- Branch point and merge point hashes
- List of commits in the merge branch

### Threading

Repository loading runs in background threads to prevent UI blocking, with results passed back to main thread for display.

### Error Handling & Logging

The application uses centralized logging for error tracking and debugging:

**Logging System** (`utils/logging_config.py`):

- File logging: `gitvisualizer.log` in current directory
- Log level: WARNING and above for file handler
- Log level: ERROR and above for console handler
- Format: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`

**Exception Handling Pattern**:

- All exceptions are caught with `except Exception as e:`
- Logged with context: `logger.warning(f"Failed to X: {e}")`
- Never silently swallowed - always logged for debugging
- User-friendly error messages shown in GUI when appropriate

**Constants** (`utils/constants.py`):

- Layout constants: `COMMIT_VERTICAL_SPACING`, `BRANCH_LANE_SPACING`, `COMMIT_START_X/Y`
- Repository constants: `MESSAGE_MAX_LENGTH`, `AUTHOR_NAME_MAX_LENGTH`
- Color constants: `COLOR_HUE_TOLERANCE`, `COLOR_SATURATION`, `COLOR_LIGHTNESS`
- Graph drawer constants: `NODE_RADIUS`, `LINE_WIDTH`, `FONT_SIZE`, `SEPARATOR_HEIGHT`
- UI constants: `DEFAULT_WINDOW_WIDTH/HEIGHT`, `MIN_COLUMN_WIDTH_*`

### Code Quality

**Refactored Functions**:

- `_detect_merge_branches()` split into helper functions:
  - `_build_full_hash_map()` - Maps short hashes to full hashes
  - `_trace_merge_branch_commits()` - Traces commits in merge branch
  - `_get_commits_in_branches_with_head()` - Gets commits in main line
  - `_extract_branch_name_from_merge()` - Extracts branch name from merge message

**URL Security**:

- Whitelist of trusted Git hosts (GitHub, GitLab, Bitbucket, Codeberg, sr.ht, gitea.io)
- Validates both HTTP(S) and SSH (git@) URLs
- Rejects untrusted hosts with logged warning
- Supports subdomains of trusted hosts

**Dependencies**:

- Pinned versions in `requirements.txt` for reproducibility:
  - `GitPython==3.1.40`
  - `Pillow==10.1.0`
  - `tkinterdnd2==0.3.0`

## Czech Language Support

The application uses Czech language for UI text and date formatting. User-facing messages and labels are in Czech.

## Versioning & Changelog

This project uses Git tags for versioning.

### Updating CHANGELOG

**IMPORTANT:** When creating a new version tag, update `docs/CHANGELOG.md`:

1. **Extract changes from Git history** between the previous tag and current HEAD:

   ```bash
   git log --pretty=format:"%h|%ad|%s" --date=short vPREVIOUS_TAG..HEAD
   ```

2. **Create new version section** in `docs/CHANGELOG.md` following Keep a Changelog format:

   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD

   ### Added
   - New features from commits

   ### Changed
   - Changes to existing functionality

   ### Fixed
   - Bug fixes

   ### Documentation
   - Documentation updates
   ```

3. **Categorize commits** into appropriate sections (Added/Changed/Fixed/Documentation/etc.)

4. **Update version in code:**
   - `setup.py` - version field
   - `gui/main_window.py` - default_title with version number
   - **IMPORTANT:** Version number in code MUST match the version in CHANGELOG.md (e.g., if CHANGELOG shows v1.1.1, gui/main_window.py must also show v1.1.1)
