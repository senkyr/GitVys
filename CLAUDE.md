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
│   ├── gui/               # UI components (refactored v1.5.0)
│   │   ├── main_window.py # Layout manager and window orchestrator (500 lines)
│   │   ├── repo_manager.py # Repository operations manager (451 lines)
│   │   ├── graph_canvas.py # Canvas component for rendering commit graph
│   │   ├── drag_drop.py   # Drag & drop operations for repository folders
│   │   ├── auth_dialog.py # OAuth authorization dialog
│   │   └── ui_components/ # UI component modules
│   │       ├── language_switcher.py  # Language switching with flags
│   │       ├── theme_switcher.py     # Theme switching with icons
│   │       └── stats_display.py      # Repository statistics display
│   ├── repo/              # Git operations (refactored v1.5.0)
│   │   ├── repository.py  # GitRepository facade (281 lines)
│   │   ├── parsers/       # Parsing components
│   │   │   ├── commit_parser.py    # Parses commits from Git repo
│   │   │   ├── branch_analyzer.py  # Analyzes branches and divergence
│   │   │   └── tag_parser.py       # Parses Git tags
│   │   └── analyzers/     # Analysis components
│   │       └── merge_detector.py   # Detects and styles merge branches
│   ├── visualization/     # Graph rendering logic (refactored v1.5.0)
│   │   ├── graph_drawer.py # Main orchestrator (385 lines)
│   │   ├── layout.py      # Calculates positioning for commits/branches
│   │   ├── colors.py      # Color utilities and branch color schemes
│   │   ├── drawing/       # Drawing components
│   │   │   ├── connection_drawer.py  # Draws connections between commits
│   │   │   ├── commit_drawer.py      # Draws commit nodes and metadata
│   │   │   ├── tag_drawer.py         # Draws Git tags with emojis
│   │   │   └── branch_flag_drawer.py # Draws branch flags and tooltips
│   │   └── ui/            # UI components
│   │       ├── column_manager.py     # Column resizing functionality
│   │       ├── tooltip_manager.py    # Tooltip system
│   │       └── text_formatter.py     # Text handling and DPI scaling
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
- **GUI Layer**: `src/gui/` directory contains all UI components (refactored into 4 specialized components in v1.5.0)
  - **MainWindow** (500 lines) - Layout manager that orchestrates UI components
  - **RepositoryManager** (451 lines) - Handles all repository operations (loading, cloning, OAuth, cleanup)
  - **UI Components** (3 modules) - Language switcher, theme switcher, stats display
- **Git Operations**: `src/repo/` directory contains Git repository operations (refactored into 5 specialized components in v1.5.0)
- **Visualization**: `src/visualization/` directory contains graph rendering logic (refactored into 8 specialized components in v1.5.0)
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

## Visualization Architecture Refactoring (v1.5.0)

### Motivation

The original `graph_drawer.py` had **1889 lines** with multiple responsibilities, causing issues:

- Quickly filled context window when working with AI assistants
- Difficult maintenance and testing
- Unclear interfaces between components

### Solution: Single Responsibility Principle

The monolithic file was split into **8 specialized components**:

#### Drawing Components (`visualization/drawing/`)

1. **ConnectionDrawer** (384 lines) - Draws connections between commits with Bézier curves
2. **CommitDrawer** (396 lines) - Draws commit nodes and metadata (messages, authors, dates)
3. **TagDrawer** (241 lines) - Draws Git tags with emoji icons and tooltips
4. **BranchFlagDrawer** (335 lines) - Draws branch flags with local/remote indicators

#### UI Components (`visualization/ui/`)

5. **ColumnManager** (430 lines) - Column resizing with drag & drop and floating headers
6. **TooltipManager** (55 lines) - Centralized tooltip management (show/hide/positioning)
7. **TextFormatter** (191 lines) - Text truncation, DPI scaling detection, width measurement

#### Orchestrator

8. **GraphDrawer** (385 lines) - Coordinates all components, handles layout calculations

#### Color Utilities

9. **colors.py** (210 lines) - `make_color_pale()` for HSL manipulation, `get_branch_color()` for semantic colors

### Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Largest file | 1889 lines | 430 lines | **-77%** |
| Average size | 1889 lines | 309 lines | **-84%** |
| Context window | 87.8 KB | ~20-40 KB | **-70-80%** |

### Benefits

1. **Faster AI-assisted development** - only relevant components loaded
2. **Better testability** - isolated components can be tested independently
3. **Clear responsibilities** - each file has 1-2 well-defined tasks
4. **Easier maintenance** - changes in one area don't affect others
5. **Parallel development** - multiple developers can work simultaneously

## Repository Architecture Refactoring (v1.5.0)

### Motivation

The original `repository.py` had **1090 lines** with multiple responsibilities:

- Commit parsing from Git
- Branch analysis and divergence detection
- Tag parsing (local and remote)
- Merge branch detection and styling
- Uncommitted changes handling

This made it difficult to understand, maintain, and test individual features.

### Solution: Facade Pattern with Specialized Components

The monolithic file was split into **5 specialized components**:

#### Parsing Components (`repo/parsers/`)

1. **CommitParser** (350 lines) - Parses commits from Git repository
   - Handles local and remote commit parsing
   - Manages message/name/description truncation
   - Formats dates (relative, short, full)

2. **BranchAnalyzer** (279 lines) - Analyzes branches and their relationships
   - Builds commit-to-branch mappings
   - Detects branch divergence (local vs remote)
   - Determines branch availability (local_only/remote_only/both)

3. **TagParser** (107 lines) - Parses Git tags
   - Handles local and remote tags
   - Builds commit-to-tags mappings
   - Supports annotated tags with messages

#### Analysis Components (`repo/analyzers/`)

4. **MergeDetector** (355 lines) - Detects and analyzes merge branches
   - Identifies merge commits (2+ parents)
   - Traces merge branch commits
   - Extracts branch names from merge messages
   - Applies paler colors to merge commits (HSL manipulation)

#### Facade

5. **GitRepository** (281 lines) - Coordinates all components
   - Delegates to specialized parsers and analyzers
   - Manages uncommitted changes (WIP commits)
   - Provides unified API for repository operations

### Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Largest file | 1090 lines | 355 lines | **-67%** |
| Main facade | 1090 lines | 281 lines | **-74%** |
| Average size | 1090 lines | 274 lines | **-75%** |
| Context window | 47.8 KB | ~12-16 KB | **-70-75%** |

### Benefits

1. **Modular architecture** - each component has a single, clear responsibility
2. **Easier testing** - components can be tested in isolation
3. **Better maintainability** - changes to parsing don't affect analysis
4. **Cleaner code** - GitRepository is now a simple facade
5. **Faster development** - work on specific features without loading entire file

## GUI Architecture Refactoring (v1.5.0)

### Motivation

The original `main_window.py` had **1225 lines** with multiple responsibilities:

- Window management and layout
- Repository operations (loading, cloning, OAuth)
- Language switching UI
- Theme switching UI
- Statistics display
- Drag & drop handling

This made it difficult to maintain and understand the UI layer structure.

### Solution: Component Pattern with Clear Separation

The monolithic file was split into **5 specialized components**:

#### UI Component Modules (`gui/ui_components/`)

1. **LanguageSwitcher** (154 lines) - Language switching functionality
   - Creates Czech and UK flag icons in Canvas
   - Handles language switching (CS ⇄ EN)
   - Updates flag appearance (active/inactive overlay)
   - Show/hide functionality for initial screen

2. **ThemeSwitcher** (204 lines) - Theme switching functionality
   - Creates sun icon (☀️) for light mode
   - Creates moon icon (🌙) for dark mode
   - Handles theme switching
   - Updates icon appearance (active/inactive overlay)
   - Dynamic repositioning on window resize
   - Show/hide functionality for initial screen

3. **StatsDisplay** (136 lines) - Repository statistics display
   - Creates UI for repository name and statistics
   - Updates stats with current language pluralization
   - Shows repository path tooltip on hover
   - Formats author/branch/tag/commit counts

#### Repository Manager

4. **RepositoryManager** (451 lines) - All repository operations
   - Repository selection (URL vs local path detection)
   - Repository cloning (with OAuth support)
   - GitHub authentication (OAuth Device Flow)
   - Temporary clone management and cleanup
   - Repository loading (local and remote)
   - Repository refresh operations
   - Remote branch fetching
   - Proper file handle management for Windows

#### Layout Manager

5. **MainWindow** (500 lines) - Coordinates all UI components
   - Window management (centering, resizing)
   - UI layout with component orchestration
   - Callback coordination (_on_language_changed, _on_theme_changed)
   - Graph display management
   - Status updates and progress bar

### Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Largest file | 1225 lines | 500 lines | **-59%** |
| Main window | 1225 lines | 500 lines | **-59%** |
| Average size | 1225 lines | 289 lines | **-76%** |
| Context window | 49.1 KB | ~20-25 KB | **-55-60%** |

### Benefits

1. **Component reusability** - UI components can be used independently
2. **Clear responsibilities** - each component has one specific purpose
3. **Easier testing** - components can be mocked and tested in isolation
4. **Better maintainability** - repository logic separated from UI logic
5. **Faster development** - work on UI without loading repository code

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
