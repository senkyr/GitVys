# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

```bash
python src/main.py
# or
python3 src/main.py
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Building Executable

**Automated build (recommended):**

```bash
build\build-exe.bat
```

This script automatically:

- Checks Python availability
- Installs dependencies from `requirements.txt`
- Installs PyInstaller (build dependency)
- Runs `build.py` to create the executable

**Manual build:**

```bash
pip install -r requirements.txt
pip install pyinstaller
python build/build.py
```

**Direct PyInstaller command:**

```bash
pyinstaller --onefile --windowed --name="GitVisualizer" --icon=build/icon.ico src/main.py
```

The executable will be in the `dist/` folder.

## Project Architecture

This is a Python desktop application that visualizes Git repository history using tkinter. The application follows a modular architecture with clear separation of concerns:

### Project Structure

```
GitVys/
├── src/                    # Source code
│   ├── main.py            # Entry point - initializes the GUI
│   ├── auth/              # GitHub OAuth authentication
│   │   ├── __init__.py    # Auth module exports
│   │   ├── github_auth.py # OAuth Device Flow for GitHub
│   │   └── token_storage.py # Token persistence (~/.gitvys/)
│   ├── gui/               # UI components
│   │   ├── main_window.py # Main application window with drag & drop
│   │   ├── graph_canvas.py # Canvas component for rendering commit graph
│   │   ├── drag_drop.py   # Drag & drop operations for repository folders
│   │   └── auth_dialog.py # OAuth authorization dialog
│   ├── repo/              # Git operations
│   │   └── repository.py  # GitRepository class (uses GitPython)
│   ├── visualization/     # Graph rendering logic
│   │   ├── graph_drawer.py # Draws commit nodes and connections
│   │   ├── layout.py      # Calculates positioning for commits/branches
│   │   └── colors.py      # Branch color schemes
│   └── utils/             # Utilities
│       ├── data_structures.py # Commit and Branch data classes
│       ├── logging_config.py  # Centralized logging (~/.gitvys/)
│       ├── theme_manager.py   # Theme management (light/dark mode)
│       ├── translations.py    # Translation management (CS/EN)
│       └── constants.py   # Application-wide constants
├── build/                 # Build scripts and assets
│   ├── build-exe.bat     # Automated build script (installs deps + builds)
│   ├── build.py          # Python build script for creating .exe
│   ├── icon.ico          # Application icon
│   └── feather.png       # Icon source asset
├── docs/                  # Documentation
├── dist/                  # Build output (ignored by git)
└── [config files]         # setup.py, requirements.txt, etc.
```

### Core Components

- **Main Entry Point**: `src/main.py` - Simple launcher that initializes the GUI and checks Git availability
- **Auth Layer**: `src/auth/` directory contains GitHub OAuth authentication (Device Flow)
- **GUI Layer**: `src/gui/` directory contains all UI components including OAuth dialog
- **Git Operations**: `src/repo/repository.py` - GitRepository class handles all Git operations using GitPython
- **Visualization**: `src/visualization/` directory contains graph rendering logic
- **Data Structures**: `src/utils/data_structures.py` - Defines Commit and Branch data classes
- **Utilities**: `src/utils/` directory contains helper modules (logging, constants)

### Key Technologies

- **Python 3.8+** with tkinter for GUI
- **GitPython** for Git repository operations
- **Pillow** for image processing
- **tkinterdnd2** for drag & drop functionality
- **requests** for OAuth HTTP communication with GitHub API

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
- **Private Repository Support**: OAuth Device Flow authentication for private GitHub repositories
- **Temp Clone Management**: Automatic cleanup of cloned repositories with proper Windows file handle management
- **Theme Support**: Light/dark mode with automatic persistence to settings
- **Multi-language**: Czech/English UI with language switcher
- **Tags**: Display Git tags with emoji icons (🏷️ normal, 📌 release, 🚀 version) and tooltips for annotated tags
- **Remote Branches**: Load remote branches via "Načíst remote/větve" button
- **Git Detection**: Startup check for Git availability with user-friendly error dialog
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
  - `GitPython==3.1.45`
  - `Pillow==11.0.0`
  - `tkinterdnd2==0.4.2`
  - `requests==2.32.3`
- Build dependency (not in requirements.txt):
  - `pyinstaller` (latest version, auto-installed by `build-exe.bat`)

## Multi-language Support (v1.4.0)

The application supports Czech and English languages:

- Language switcher with flag icons (🇨🇿 Czech, 🇬🇧 English)
- Automatic persistence to `~/.gitvys/settings.json`
- Default language: Czech
- Translation management via `utils/translations.py`
- All UI texts, button labels, status messages, and error dialogs are translated
- Plural forms handled correctly for both languages

## Theme Management (v1.5.0)

The application supports light and dark themes:

- Theme switcher with icons (☀️ light, 🌙 dark)
- Automatic persistence to `~/.gitvys/settings.json`
- Default theme: light mode
- Theme management via `utils/theme_manager.py`
- Full TTK widget styling for consistent appearance
- Dynamic color updates for all UI components:
  - Canvas background and text colors
  - Button, label, frame, entry field styling
  - Progress bar colors
  - Tooltip colors
  - Column headers and separators
- Contrasting text colors calculated automatically for readability

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
   - `setup.py` - version field (line 5)
   - `src/utils/translations.py` - app_title in BOTH language dictionaries ('cs' and 'en')
   - **IMPORTANT:** Version number in code MUST match the version in CHANGELOG.md (e.g., if CHANGELOG shows v1.5.0, translations.py must also show v1.5.0)
