# Testing Strategy - Git Visualizer

## Přehled testování

Tento dokument obsahuje kompletní strategii testování projektu Git Visualizer, včetně aktuálního stavu pokrytí a dlouhodobého plánu pro robustní testovací suite.

**Aktuální stav**: 224 testů, **100% pass rate** ✅

**Poslední update**: 2025-10-12 (Phase 3 komponenty dokončeny)

**Aktuální fokus**: FÁZE 2 - Utils managers (ThemeManager, TranslationManager)

## Aktuální stav pokrytí testů

### ✅ Dobře pokryto (Phase 1, 2 & 3)

#### Phase 3 - GUI komponenty (100% pokrytí)

- ✅ `test_repo_manager.py` (32 testů, 451 ř. zdrojového kódu) - repository operations, OAuth, temp cleanup
- ✅ `test_theme_switcher.py` (26 testů, 204 ř.) - theme switching, regression testy pro visibility bug
- ✅ `test_language_switcher.py` (19 testů, 154 ř.) - language switching, flag positioning
- ✅ `test_stats_display.py` (13 testů, 136 ř.) - stats formatting, pluralization
- ✅ `test_main_window.py` (13 testů, 500 ř.) - component orchestration, event propagation

**Pokrytí**: 5/5 komponent = **100%** ✅
**Total Phase 3 tests**: 103 (plánováno 60) - **+72% nad plán**

#### Phase 2 - Repository komponenty (100% pokrytí)

- ✅ `test_commit_parser.py` (268 řádků) - parsing commitů, truncation, formátování
- ✅ `test_branch_analyzer.py` - analýza větví, divergence
- ✅ `test_tag_parser.py` - parsing tagů (local/remote)
- ✅ `test_merge_detector.py` - detekce merge větví
- ✅ `test_repository.py` (integration) - facade orchestrace

**Pokrytí**: 5/5 komponent = **100%**

#### Phase 1 - Visualization komponenty (50% pokrytí)

- ✅ `test_colors.py` - HSL manipulace, branch colors
- ✅ `test_tooltip_manager.py` (110 řádků) - tooltip lifecycle
- ✅ `test_text_formatter.py` - truncation, DPI scaling
- ✅ `test_graph_drawer.py` (158 řádků) - integration orchestrace

**Pokrytí**: 4/8 komponent = **50%**

### ❌ Chybí pokrytí

#### Phase 1 - Drawing komponenty (0% pokrytí)

- ❌ `ConnectionDrawer` (384 řádků) - MEDIUM
- ❌ `CommitDrawer` (396 řádků) - MEDIUM
- ❌ `TagDrawer` (241 řádků) - MEDIUM
- ❌ `BranchFlagDrawer` (335 řádků) - MEDIUM

**Pokrytí**: 0/4 komponent = **0%**

#### Phase 1 - UI komponenty (0% pokrytí)

- ❌ `ColumnManager` (430 řádků) - HIGH

#### Utils (0% pokrytí)

- ❌ `theme_manager.py` - **KRITICKÉ** (globální state)
- ❌ `translations.py` - **KRITICKÉ** (globální state)

#### Ostatní GUI (0% pokrytí)

- ❌ `GraphCanvas` - LOW
- ❌ `DragDropFrame` - LOW
- ❌ `AuthDialog` - MEDIUM

---

## Testovací priority

### P0 - KRITICKÉ (Globální state managers) - **AKTUÁLNÍ PRIORITA** 🎯

**Odůvodnění**: Singleton komponenty s globálním state a persistence. Phase 3 business logic je dokončena.

1. **ThemeManager** (singleton) ⬆️ NOVĚ P0
   - **Důvod**: Globální state, persistence do ~/.gitvys/settings.json, callback systém, TTK styling
   - **Risk**: State corruption, race conditions, UI corruption
   - **Test cases**: 15+ testů
   - **Status**: ❌ TODO - **AKTUÁLNÍ PRIORITA**

2. **TranslationManager** (singleton) ⬆️ NOVĚ P0
   - **Důvod**: Globální state, pluralization logika (Czech: 1, 2-4, 5+), callback systém
   - **Risk**: UI corruption, chybějící překlady, pluralization errors
   - **Test cases**: 12+ testů
   - **Status**: ❌ TODO - **AKTUÁLNÍ PRIORITA**

### P0 - DOKONČENO ✅

3. **RepositoryManager** (451 ř.)
   - **Status**: ✅ HOTOVO - 32 testů (target: 25)
   - **Pokrytí**: OAuth Device Flow, cloning s retry logikou, temp cleanup, Windows readonly files
   - **Datum dokončení**: 2025-10-12

### P1 - DOKONČENO ✅

4. **ThemeSwitcher** (204 ř.)
   - **Status**: ✅ HOTOVO - 26 testů včetně regression testů
   - **Bug fixed**: Visibility bug (ikony se nezobrazovaly v úvodním okně)
   - **Pokrytí**: Positioning, retry logic, window resize, fallback width
   - **Datum dokončení**: 2025-10-12

5. **LanguageSwitcher** (154 ř.)
   - **Status**: ✅ HOTOVO - 19 testů
   - **Pokrytí**: Flag creation, language switching, positioning, visibility
   - **Datum dokončení**: 2025-10-12

6. **StatsDisplay** (136 ř.)
   - **Status**: ✅ HOTOVO - 13 testů
   - **Pokrytí**: Stats UI, pluralization (Czech/English), tooltip
   - **Datum dokončení**: 2025-10-12

### P1 - TODO

7. **ColumnManager** (430 ř.)
   - **Důvod**: Složitá resize logika, throttling (60 FPS), floating headers
   - **Risk**: Performance issues, UI glitches, memory leaks
   - **Test cases**: 20+ testů
   - **Status**: ❌ TODO

### P2 - STŘEDNÍ (Drawing komponenty)

**Odůvodnění**: Komplexní rendering logika, ale primárně visual issues (ne data loss).

8-11. **Drawing komponenty**

- ConnectionDrawer (384 ř.) - Bézier curves, connection routing
- CommitDrawer (396 ř.) - Node rendering, metadata display
- TagDrawer (241 ř.) - Tag icons, tooltips
- BranchFlagDrawer (335 ř.) - Branch flags, local/remote indicators
- **Risk**: Visual glitches, performance issues
- **Test cases**: 12+ testů každá
- **Priority**: Střední

### P3 - NÍZKÁ (Integration, orchestrace)

**Odůvodnění**: Většinou delegace na jiné komponenty, které již mají testy.

12-14. **Integration komponenty**

- MainWindow - Orchestrace GUI komponent
- GraphCanvas - Canvas wrapper
- DragDropFrame - Drag & drop handling
- **Risk**: Integration issues mezi komponentami
- **Test cases**: 8+ testů každá
- **Priority**: Nízká

---

## Plán implementace testů

### ✅ FÁZE 1: Phase 3 komponenty - **DOKONČENO** 🎉

**Cíl**: Konzistentní pokrytí Phase 3 komponent ✅

**Rozsah**: 5 test souborů, 103 testů, ~1400 řádků kódu

**Časový odhad**: 5-7 dní → **Skutečnost**: Dokončeno ✅

**Výsledky**:

- ✅ 103 testů vytvořeno (+72% nad plán)
- ✅ 224 celkem testů v projektu
- ✅ 100% pass rate
- ✅ Regression testy pro ThemeSwitcher visibility bug
- ✅ Pokrytí všech edge cases (OAuth, Windows readonly, temp cleanup)
- ✅ Integration testy pro MainWindow orchestraci

**Datum dokončení**: 2025-10-12

#### Test soubory (DOKONČENO)

1. **`tests/unit/test_repo_manager.py`** ✅ (32 testů, target: 20-25)
   - Initialization & cleanup
   - URL detection (HTTPS, SSH, GitHub, local paths)
   - Repository selection (URL vs local)
   - Cloning (success, failure, auth, cleanup)
   - OAuth authentication (token loading, saving, retry)
   - Temp cleanup (single clone, multiple clones, Windows readonly files)
   - Repository loading & refresh
   - Close repository

2. **`tests/unit/test_theme_switcher.py`** ✅ (26 testů, target: 15-18)
   - Všechny plánované test cases implementovány
   - **Regression testy pro visibility bug** (4 testy)
   - Positioning, retry logic, fallback width

3. **`tests/unit/test_language_switcher.py`** ✅ (19 testů, target: 12-15)
   - Flag creation, language switching, positioning
   - Visibility, click handling

4. **`tests/unit/test_stats_display.py`** ✅ (13 testů, target: 8-10)
   - Stats UI, updates, pluralization (Czech/English)
   - Repository path tooltip

5. **`tests/integration/test_main_window.py`** ✅ (13 testů, target: 8-10)
   - Window init, orchestration, event propagation
   - Language/theme changes, error handling

**Fixtures vytvořené** (v `conftest.py`):

```python
@pytest.fixture
def mock_parent_window():
    """Mock MainWindow instance for component tests."""

@pytest.fixture
def mock_theme_manager():
    """Mock ThemeManager singleton."""

@pytest.fixture
def mock_translation_manager():
    """Mock TranslationManager singleton."""

@pytest.fixture
def temp_settings_dir():
    """Temporary ~/.gitvys/ directory for testing."""
```

---

### FÁZE 2: Utils & managers - **AKTUÁLNÍ PRIORITA** 🎯

**Cíl**: Otestovat kritické singleton komponenty s globálním state

**Rozsah**: 2 test soubory, ~27 testů, ~450 řádků kódu

**Časový odhad**: 2-3 pracovní dny

**Priorita**: **P0 - KRITICKÉ** (globální state, persistence)

1. **`tests/unit/test_theme_manager.py`** (15+ testů, ~250 řádků)
   - Singleton pattern
   - Theme initialization & loading
   - Get/set theme with validation
   - Persistence do ~/.gitvys/settings.json
   - Callback registration & notification
   - TTK styling updates
   - Theme color retrieval
   - Edge cases: corrupt settings file, missing keys

2. **`tests/unit/test_translation_manager.py`** (12+ testů, ~200 řádků)
   - Singleton pattern
   - Language management (cs/en)
   - Translation key lookup
   - Pluralization (Czech rules: 1, 2-4, 5+)
   - Callback system
   - Missing translation handling
   - Persistence

**Fixtures potřebné**:

```python
@pytest.fixture
def temp_settings_file(tmp_path):
    """Temporary ~/.gitvys/settings.json for testing."""

@pytest.fixture
def mock_theme_manager_singleton():
    """Reset ThemeManager singleton between tests."""
```

---

### FÁZE 3: Phase 1 chybějící komponenty - **PLANNED**

**Priorita**: P2 - STŘEDNÍ (drawing komponenty)

**Rozsah**: 5 test souborů, ~60 testů, ~1000 řádků kódu

1. **`tests/unit/test_connection_drawer.py`** (12+ testů)
2. **`tests/unit/test_commit_drawer.py`** (12+ testů)
3. **`tests/unit/test_tag_drawer.py`** (12+ testů)
4. **`tests/unit/test_branch_flag_drawer.py`** (12+ testů)
5. **`tests/unit/test_column_manager.py`** (20+ testů)

---

### FÁZE 4: Ostatní GUI komponenty - **PLANNED**

**Priorita**: P3 - NÍZKÁ (integration komponenty)

**Rozsah**: 3 test soubory, ~24 testů, ~400 řádků kódu

1. **`tests/unit/test_graph_canvas.py`** (8+ testů)
2. **`tests/unit/test_drag_drop.py`** (8+ testů)
3. **`tests/unit/test_auth_dialog.py`** (8+ testů)

---

## Detailní test případy

### 1. RepositoryManager Test Cases

#### TestRepositoryManagerInitialization

```python
def test_initialization(mock_parent_window):
    """Test RepositoryManager initialization."""
    manager = RepositoryManager(mock_parent_window)
    assert manager.git_repo is None
    assert manager.is_remote_loaded is False
    assert manager.is_cloned_repo is False
    assert manager.temp_clones == []

def test_cleanup_old_temp_clones_on_init():
    """Test cleanup of orphaned temp clones from previous sessions."""
    # Vytvořit fake temp clone z předchozí session
    # Verifikovat že je smazán při inicializaci

def test_atexit_handler_registration():
    """Test that atexit handler is registered for cleanup."""
```

#### TestURLDetection

```python
def test_is_git_url_https():
    """Test HTTPS URL detection."""
    manager = RepositoryManager(mock_parent_window)
    assert manager._is_git_url("https://github.com/user/repo.git")
    assert manager._is_git_url("https://gitlab.com/user/repo")

def test_is_git_url_ssh():
    """Test SSH URL detection."""
    assert manager._is_git_url("git@github.com:user/repo.git")

def test_is_git_url_local_path():
    """Test local path detection (should return False)."""
    assert not manager._is_git_url("C:\\Users\\user\\repo")
    assert not manager._is_git_url("/home/user/repo")
```

#### TestCloning

```python
def test_clone_repository_creates_temp_dir(mock_tempfile):
    """Test that cloning creates temp directory."""
    # Mock tempfile.mkdtemp()
    # Verify temp_dir is created and added to temp_clones list

def test_clone_worker_success_no_auth(mock_git_clone):
    """Test successful clone without authentication."""
    # Mock Repo.clone_from() to succeed
    # Verify _on_clone_complete is called

def test_clone_worker_auth_error_shows_dialog(mock_git_clone):
    """Test that auth error shows dialog."""
    # Mock Repo.clone_from() to raise GitCommandError with auth error
    # Verify auth dialog is shown

def test_clone_worker_retry_with_token(mock_git_clone):
    """Test clone retry with saved token."""
    # First clone fails with auth error
    # Token is loaded from storage
    # Clone retried with authenticated URL
    # Verify success

def test_clone_worker_cleanup_on_failure(mock_git_clone):
    """Test temp directory cleanup on clone failure."""
    # Mock clone to fail
    # Verify temp directory is cleaned up

def test_clone_repository_multiple_sequential():
    """Test cloning multiple repositories sequentially."""
    # Clone first repo → verify temp created
    # Clone second repo → verify first temp cleaned, second created
```

#### TestTempCleanup

```python
def test_cleanup_single_clone():
    """Test cleanup of single temp clone."""
    # Create fake temp directory
    # Call _cleanup_single_clone()
    # Verify directory is deleted

def test_cleanup_single_clone_readonly_files():
    """Test cleanup handles Windows readonly files."""
    # Create temp dir with readonly files
    # Call _cleanup_single_clone()
    # Verify readonly flag is cleared and files deleted

def test_cleanup_temp_clones_on_exit():
    """Test cleanup of all temp clones on exit."""
    # Create multiple temp clones
    # Call _cleanup_temp_clones()
    # Verify all are deleted
```

---

### 2. ThemeSwitcher Test Cases (včetně Regression)

#### TestThemeSwitcherVisibility (REGRESSION TESTY)

```python
def test_show_positions_correctly_after_window_init():
    """REGRESSION: Test that show() positions correctly after window init.

    Bug: Přepínač se nezobrazoval v úvodním okně.
    Fix: show() nyní čeká na správnou inicializaci okna.
    """
    # Mock window with proper width
    # Call show()
    # Verify theme_frame is positioned correctly (right-aligned)

def test_show_with_uninitialized_window_retries():
    """REGRESSION: Test retry logic when window not initialized.

    Bug: winfo_width() vrátilo <= 1 při volání show() během init.
    Fix: Retry logika s 50ms delay, až 10 pokusů.
    """
    # Mock window with width = 1 (not initialized)
    # Call show()
    # Verify retry is scheduled with after()
    # After retry, verify positioning succeeds

def test_show_retry_logic_max_attempts():
    """REGRESSION: Test max retry attempts fallback."""
    # Mock window that never initializes (width always 1)
    # Call show()
    # Verify after 10 retries, fallback width (600px) is used

def test_update_position_on_window_resize():
    """REGRESSION: Test position updates on window resize.

    Bug: Při změně velikosti okna se přepínač nepřesunul.
    Fix: <Configure> event binding aktualizuje pozici.
    """
    # Show theme switcher
    # Resize window (trigger <Configure> event)
    # Verify update_position() is called
    # Verify new position is correct
```

---

## Testovací nástroje & workflow

### Spuštění testů

```bash
# Všechny testy
pytest tests/ -v

# Pouze Phase 3 testy
pytest tests/unit/test_repo_manager.py \
       tests/unit/test_theme_switcher.py \
       tests/unit/test_language_switcher.py \
       tests/unit/test_stats_display.py \
       tests/integration/test_main_window.py -v

# Coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Pouze konkrétní test třída
pytest tests/unit/test_repo_manager.py::TestCloning -v

# Watch mode (re-run on file changes)
pytest-watch tests/ src/ -v
```

### Coverage cíle

**Aktuální (po Phase 3 testech)**: ✅

- Phase 1 komponenty: **50% coverage**
- Phase 2 komponenty: **100% coverage**
- Phase 3 komponenty: **100% coverage** ✅ (bylo: 0%)
- Utils managers: **0% coverage** 🎯 NEXT
- Celkové pokrytí: **~75%** (bylo: ~65%)

**Po FÁZI 2 (Utils managers)**:

- Utils managers: **90%+ coverage**
- Celkové pokrytí: **~78%**

**Dlouhodobý cíl (po všech fázích)**:

- P0 komponenty: **90%+ coverage**
- P1 komponenty: **85%+ coverage**
- P2 komponenty: **75%+ coverage**
- P3 komponenty: **60%+ coverage**
- **Celkové pokrytí: 80%+**

### CI/CD integrace

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest tests/ --cov=src --cov-fail-under=65
```

---

## Mock strategie

### Tkinter mocking

```python
# Pro GUI testy - mock tkinter widgety
@pytest.fixture
def mock_tk_widget():
    from unittest.mock import MagicMock
    widget = MagicMock()
    widget.winfo_width.return_value = 600
    widget.winfo_height.return_value = 400
    return widget
```

### File system mocking

```python
# Pro RepositoryManager testy
@pytest.fixture
def mock_tempfile(tmp_path):
    """Mock tempfile.mkdtemp() to use pytest tmp_path."""
    import tempfile
    original_mkdtemp = tempfile.mkdtemp

    def mock_mkdtemp(prefix=''):
        temp_dir = tmp_path / prefix
        temp_dir.mkdir()
        return str(temp_dir)

    tempfile.mkdtemp = mock_mkdtemp
    yield
    tempfile.mkdtemp = original_mkdtemp
```

### GitPython mocking

```python
# Pro cloning testy
@pytest.fixture
def mock_git_repo():
    from unittest.mock import MagicMock, patch
    with patch('git.Repo.clone_from') as mock_clone:
        mock_clone.return_value = MagicMock()
        yield mock_clone
```

---

## Testovací best practices

### 1. Test isolation

- Každý test musí být nezávislý
- Použít fixtures pro setup/teardown
- Nepoléhat na pořadí testů

### 2. Descriptive names

```python
# ✅ Dobrý název
def test_clone_worker_retries_with_saved_token_after_auth_failure():
    """Test that clone worker retries with saved token after initial auth failure."""

# ❌ Špatný název
def test_clone_2():
    """Test cloning."""
```

### 3. AAA pattern (Arrange, Act, Assert)

```python
def test_example():
    # Arrange
    manager = RepositoryManager(mock_window)
    url = "https://github.com/user/repo.git"

    # Act
    manager.clone_repository(url)

    # Assert
    assert manager.is_cloned_repo is True
    assert len(manager.temp_clones) == 1
```

### 4. Edge cases

- Testovat boundary conditions
- Testovat error paths
- Testovat race conditions (zejména u singleton managerů)

### 5. Regression testy

- Po každém bug fixu přidat regression test
- Dokumentovat bug v docstringu testu
- Označit jako REGRESSION v názvu/docstringu

---

## Metriky & reporting

### Coverage report struktura

```
src/
├── gui/
│   ├── repo_manager.py          85% (target: 90%)
│   ├── ui_components/
│   │   ├── theme_switcher.py    80% (target: 85%)
│   │   ├── language_switcher.py 82% (target: 85%)
│   │   └── stats_display.py     78% (target: 80%)
│   └── main_window.py           65% (target: 70% - orchestrace)
```

### Test execution time

- Unit testy: **< 0.1s každý**
- Integration testy: **< 1s každý**
- Celková suite: **< 30s**

---

## Changelog testů

### v1.5.0 - Phase 3 tests COMPLETED (2025-10-12) ✅

**Shrnutí**: Dokončena kompletní testovací suite pro Phase 3 GUI komponenty

- ✅ Přidány testy pro RepositoryManager (32 testů)
  - OAuth Device Flow authentication
  - Repository cloning s retry logikou
  - Temp directory cleanup (včetně Windows readonly files)
  - URL detection a validace
  - Repository loading & refresh
- ✅ Přidány testy pro ThemeSwitcher (26 testů)
  - Icon creation (sun, moon)
  - Theme switching
  - **REGRESSION testy pro visibility bug**:
    - Retry logic při neinicializovaném okně
    - Fallback width handling
    - Window resize event handling
- ✅ Přidány testy pro LanguageSwitcher (19 testů)
  - Flag creation (Czech, UK)
  - Language switching
  - Visibility & positioning
- ✅ Přidány testy pro StatsDisplay (13 testů)
  - Stats UI creation & updates
  - Pluralization (Czech, English)
  - Repository path tooltip
- ✅ Přidány integration testy pro MainWindow (13 testů)
  - Component orchestration
  - Event propagation (language, theme)
  - Window resize handling

**Metriky**:

- **Tests created**: 103 (plánováno 60) → **+72% nad plán**
- **Total project tests**: 121 → **224**
- **Pass rate**: **100% (224/224)** ✅
- **Coverage Phase 3**: 0% → **100%**
- **Coverage celkem**: ~65% → **~75%**

**Další kroky**: FÁZE 2 - Utils managers (ThemeManager, TranslationManager)

### v1.5.0 - Phase 2 tests (2025-09)

- ✅ Přidány testy pro CommitParser
- ✅ Přidány testy pro BranchAnalyzer
- ✅ Přidány testy pro TagParser
- ✅ Přidány testy pro MergeDetector
- ✅ Přidány integration testy pro GitRepository
- **Coverage Phase 2**: 0% → 100%

### v1.5.0 - Phase 1 tests (2025-09)

- ✅ Přidány testy pro colors utility
- ✅ Přidány testy pro TooltipManager
- ✅ Přidány testy pro TextFormatter
- ✅ Přidány integration testy pro GraphDrawer
- **Coverage Phase 1**: 0% → 50%

---

## Budoucí vylepšení

### Property-based testing

- Použít `hypothesis` pro generování test dat
- Zejména pro parsing, formátování, color utilities

### Performance testing

- Benchmark testy pro GraphDrawer s velkými repozitáři (1000+ commitů)
- Memory profiling pro RepositoryManager (temp cleanup)

### E2E testing

- Selenium/Playwright pro kompletní GUI testing
- Test celého workflow: otevření repo → zobrazení → close → cleanup

### Mutation testing

- Použít `mutmut` pro zjištění kvality testů
- Cíl: 80%+ mutation score

---

## Závěr

Tato testovací strategie zajišťuje:

1. ✅ **Konzistentní pokrytí** refaktorovaných komponent
2. ✅ **Regression prevence** pro opravené bugy
3. ✅ **Prioritizace** kritických komponent (data loss, security)
4. ✅ **Incremental approach** - dokončit Phase 3, pak expandovat
5. ✅ **Dlouhodobý plán** pro dosažení 80%+ coverage

**Aktuální fokus**: Phase 3 testy (5 souborů, ~60 testů, 5-7 dní)
