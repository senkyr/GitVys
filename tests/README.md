# Test Suite - Git Visualizer

Basic test coverage for Git Visualizer application (Phase 1.5 - Refactoring v1.5.0).

## Overview

This test suite provides **foundational coverage** for the refactored components from Phase 1 of the visualization refactoring. The goal is to catch regressions during ongoing refactoring (Phase 2 & 3) while keeping implementation time minimal.

## Running Tests

### Basic Test Run

```bash
pytest tests/
```

### With Verbose Output

```bash
pytest -v tests/
```

### With Coverage Report

```bash
pytest --cov=src --cov-report=term-missing tests/
```

### Run Specific Test File

```bash
pytest tests/unit/test_colors.py -v
pytest tests/integration/test_graph_drawer.py -v
```

## Test Structure

```
tests/
├── conftest.py                         # Shared fixtures (canvas, mock commits)
├── unit/                               # Unit tests (fast, isolated)
│   ├── test_colors.py                 # Color utilities (94% coverage)
│   ├── test_text_formatter.py         # Text formatting (81% coverage)
│   └── test_tooltip_manager.py        # Tooltip management (95% coverage)
└── integration/                        # Integration tests
    ├── test_graph_drawer.py           # GraphDrawer orchestration (82% coverage)
    └── test_repository.py             # GitRepository basics (16% coverage)
```

## Coverage Summary

### Refactored Components (v1.5.0)

| Component | Coverage | Tests | Status |
|-----------|----------|-------|--------|
| **colors.py** | 94% | 24 | ✅ Excellent |
| **text_formatter.py** | 81% | 10 | ✅ Good |
| **tooltip_manager.py** | 95% | 7 | ✅ Excellent |
| **graph_drawer.py** | 82% | 14 | ✅ Good |
| **tag_drawer.py** | 84% | 0* | ⚠️ Indirect |
| **commit_drawer.py** | 54% | 0* | ⚠️ Indirect |
| **branch_flag_drawer.py** | 60% | 0* | ⚠️ Indirect |
| **connection_drawer.py** | 47% | 0* | ⚠️ Indirect |
| **column_manager.py** | 71% | 0* | ⚠️ Indirect |

*\*Tested indirectly through GraphDrawer integration tests*

### Overall Coverage

- **Total Lines:** 3782
- **Covered:** 1193 (32%)
- **63 tests passing**

**Note:** Low overall coverage (32%) is expected at this stage - we're only testing refactored components from Phase 1. GUI layer, auth, and unreferenced modules are untested.

## Test Categories

### Unit Tests (46 tests)

**colors.py (24 tests):**
- HSL to hex conversion
- Semantic hue mapping (main, develop, feature/*, etc.)
- Semantic hue conflict detection
- Branch name normalization (origin/ removal)
- Branch color generation (semantic + sequential)
- Color paling for remote/merge branches

**text_formatter.py (10 tests):**
- DPI scaling factor detection
- Text truncation to pixel width
- Description truncation for DPI
- Description adjustment for scaling factors
- Width recalculation after column resize
- Empty/None handling

**tooltip_manager.py (7 tests):**
- Initialization
- Show/hide tooltip
- Tooltip positioning
- Multiple tooltip handling
- Content verification

### Integration Tests (17 tests)

**graph_drawer.py (14 tests):**
- Component initialization (lazy loading)
- Canvas item creation
- Column width calculation
- Drawing with tags
- State reset
- Column resize events
- Multiple draws on same canvas
- Color paling wrapper
- Legacy API compatibility (`_draw_column_separators`)
- Table position calculation
- Separator scrolling

**repository.py (3 tests):**
- Initialization
- Loading with mock Git repo
- Handling uncommitted changes
- Merge branch detection

## Key Features

### 1. Shared Fixtures (`conftest.py`)

**`root` fixture:**
- Creates tkinter root window
- Auto-cleanup after tests

**`canvas` fixture:**
- Creates 800x600 test canvas
- Requires `root` fixture

**`mock_commits` fixture:**
- Creates 5 mock commits (3 main, 2 feature)
- Pre-applies layout via GraphLayout
- Includes all required Commit fields

**`mock_commits_with_tags` fixture:**
- Creates 3 tagged commits
- Tags: v1.0.0 (version), release-2.0

### 2. Coverage Highlights

**Excellent Coverage (>80%):**
- `colors.py` - 94% (only fallback paths untested)
- `tooltip_manager.py` - 95% (only error handling untested)
- `tag_drawer.py` - 84% (tested via GraphDrawer)
- `graph_drawer.py` - 82% (orchestrator tested)
- `text_formatter.py` - 81% (core functionality covered)

**Moderate Coverage (50-80%):**
- `column_manager.py` - 71% (resize logic tested indirectly)
- `branch_flag_drawer.py` - 60% (basic rendering tested)
- `commit_drawer.py` - 54% (basic rendering tested)

**Lower Coverage (<50%):**
- `connection_drawer.py` - 47% (complex Bézier logic partially tested)
- `repository.py` - 16% (only basic functionality tested with mocks)

## What's NOT Tested (By Design)

This is a **Phase 1.5 basic coverage** - intentionally omitted:

❌ **GUI Layer** (0% coverage)
- `main_window.py`, `graph_canvas.py`, `drag_drop.py`, `auth_dialog.py`
- Reason: Complex GUI interactions, will test after Phase 3

❌ **Auth System** (0% coverage)
- `github_auth.py`, `token_storage.py`
- Reason: Requires OAuth mock setup, low priority

❌ **Layout Algorithm** (59% coverage, no dedicated tests)
- `layout.py` - lane assignment, branch relationships
- Reason: Tested indirectly, complex to test in isolation

❌ **Complex Drawing Logic** (<50% coverage)
- Bézier curves, merge connections, flag positioning
- Reason: Would require pixel-perfect canvas assertions

## Regression Protection

These tests are designed to catch:

✅ **API Changes**
- Method signature changes (e.g., `truncate_text_to_width`)
- Missing required parameters
- Renamed methods

✅ **Refactoring Breakage**
- Component initialization failures
- Missing dependencies between components
- State management issues

✅ **Logic Errors**
- Color calculation bugs
- Text truncation edge cases
- Tooltip show/hide state bugs

## Future Improvements (Post-Phase 3)

After completing Phase 2 & 3 refactoring, consider:

1. **Increase Coverage to 60%+**
   - Add dedicated tests for drawing components
   - Test layout algorithm with various branch patterns
   - Add column manager interaction tests

2. **GUI Testing**
   - Mock tkinter events for drag & drop
   - Test main window initialization
   - Test keyboard shortcuts (F5, etc.)

3. **Performance Tests**
   - Large repository loading (1000+ commits)
   - Memory leak detection
   - Scrolling performance

4. **End-to-End Tests**
   - Load real Git repository
   - Verify rendering output
   - Test full user workflows

## Continuous Testing

Run tests after any code changes:

```bash
# Quick check
pytest tests/unit/

# Full suite with coverage
pytest --cov=src tests/

# Watch mode (requires pytest-watch)
ptw tests/
```

## Troubleshooting

### Tests Fail with `TypeError: Commit.__init__() missing X arguments`

**Cause:** Mock commits in fixtures don't match Commit dataclass signature.

**Fix:** Update `conftest.py` fixtures to include all required fields.

### Tests Fail with `AttributeError: 'GraphLayout' object has no attribute 'layout_graph_commits'`

**Cause:** Incorrect method name (should be `calculate_positions`).

**Fix:** Update fixture to call `layout.calculate_positions()`.

### Import Errors

**Cause:** `src/` not in Python path.

**Fix:** Run tests from project root, pytest will use `conftest.py` path setup.

## Summary

✅ **63 tests passing**
✅ **32% overall coverage** (expected at Phase 1.5)
✅ **Refactored components well-tested** (colors 94%, tooltip 95%, text 81%, graph 82%)
✅ **Fast execution** (~4 seconds for full suite)
✅ **Foundation for Phase 2 & 3** testing

This test suite successfully provides **regression protection** for the Phase 1 refactoring while keeping implementation time minimal (1-2 hours as planned).
