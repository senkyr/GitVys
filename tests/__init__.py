"""Tests for Git Visualizer.

TCL/TK environment initialization - ensures environment variables are set
before pytest collects test modules that import tkinter.
"""
import tests.setup_tcl  # noqa: F401
