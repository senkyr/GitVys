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

1. User drags Git repository folder into application
2. GitRepository class loads and parses commit history
3. GraphLayout calculates positions for commits based on timeline and branches
4. GraphDrawer renders the visualization on canvas
5. UI displays commit graph with branch colors and commit details

### Data Model

The main data structure is the Commit class which includes:

- Basic Git data (hash, message, author, date, parents)
- UI-specific data (truncated messages, relative dates, branch colors)
- Layout data (x/y positions for rendering)

### Threading

Repository loading runs in background threads to prevent UI blocking, with results passed back to main thread for display.

## Czech Language Support

The application uses Czech language for UI text and date formatting. User-facing messages and labels are in Czech.
