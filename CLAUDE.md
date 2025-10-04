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
