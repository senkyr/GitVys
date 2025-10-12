"""Initialize TCL/TK environment variables before any tkinter imports.

This module MUST be imported before any module that uses tkinter.
It sets up the TCL_LIBRARY and TK_LIBRARY environment variables to prevent
"Can't find a usable tk.tcl" errors on some systems.
"""
import os
import sys
from pathlib import Path

# Set TCL/TK library paths BEFORE any tkinter import
python_root = Path(sys.executable).parent
tcl_dir = python_root / "tcl"
if tcl_dir.exists():
    os.environ.setdefault("TCL_LIBRARY", str(tcl_dir / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_dir / "tk8.6"))
