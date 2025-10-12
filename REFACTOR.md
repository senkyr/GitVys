# Refactoring Plan - Git Visualizer v1.5.0

> **Cíl:** Rozdělit velké monolitické soubory na menší, lépe spravovatelné komponenty podle principu Single Responsibility.

## 📊 Motivace

### Problém

Aplikace má rychle zaplněné kontextové okno při práci s AI asistenty (Claude Code) kvůli velkým souborům:

| Soubor | Řádky | Velikost | % celku |
|--------|-------|----------|---------|
| `graph_drawer.py` | 1889 | 87.8 KB | 26.5% |
| `main_window.py` | 1225 | 49.1 KB | 17.2% |
| `repository.py` | 1090 | 47.8 KB | 15.3% |
| **CELKEM** | **4204** | **184.7 KB** | **59.1%** |

### Řešení: Varianta 1 - Split by Responsibility

Rozdělit třídy podle odpovědností do menších, soudržných komponent:

- **Největší soubor: 1889 řádků → 8 souborů po ~200-400 řádcích**
- **Postupná implementace** bez breaking changes
- **Jasné odpovědnosti** každého souboru

---

## 🎯 FÁZE 1: Rozdělení graph_drawer.py

**Priorita:** VYSOKÁ (největší benefit)
**Odhadovaný čas:** 2-3 hodiny
**Velikost:** 1889 řádků → 8 souborů

### Současná struktura

```python
class GraphDrawer:
    # 40 metod, 1889 řádků
    # Odpovědnosti:
    # - Vykreslování spojnic a křivek
    # - Vykreslování commit nodů
    # - Vykreslování tagů
    # - Vykreslování branch flags
    # - Column resizing
    # - Tooltip management
    # - Text formatting
```

### Cílová struktura

```
src/visualization/
├── graph_drawer.py              # Orchestrator (200 řádků)
├── drawing/                     # Subpackage pro vykreslování
│   ├── __init__.py
│   ├── connection_drawer.py     # Spojnice a křivky (300 řádků)
│   ├── commit_drawer.py         # Commit nodes (300 řádků)
│   ├── tag_drawer.py            # Tagy a emoji (200 řádků)
│   └── branch_flag_drawer.py    # Branch flags (250 řádků)
└── ui/                          # Subpackage pro UI komponenty
    ├── __init__.py
    ├── column_manager.py        # Column resizing (400 řádků)
    ├── tooltip_manager.py       # Tooltip systém (100 řádků)
    └── text_formatter.py        # Text handling (200 řádků)
```

### Detailní rozdělení

#### 1. `visualization/drawing/connection_drawer.py` (300 řádků)

**Odpovědnost:** Vykreslování všech spojnic mezi commity (čáry, křivky, rozvětvení)

**Metody k přesunu:**

- `_draw_connections()`
- `_draw_line()`
- `_draw_bezier_curve()`
- `_calculate_rounded_corner_arc()`

**Závislosti:**

- `utils.data_structures.Commit`
- `utils.constants` (LINE_WIDTH, NODE_RADIUS)
- `utils.theme_manager` (barvy)

**Interface:**

```python
class ConnectionDrawer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()

    def draw_connections(self, commits: List[Commit], branch_lanes: Dict,
                        merge_branches: List[MergeBranch]) -> None:
        """Vykreslí všechny spojnice mezi commity."""
        pass

    def _draw_line(self, x1, y1, x2, y2, color, width) -> int:
        """Vykreslí přímou čáru."""
        pass

    def _draw_bezier_curve(self, points, color, width) -> int:
        """Vykreslí Bézier křivku."""
        pass
```

---

#### 2. `visualization/drawing/commit_drawer.py` (300 řádků)

**Odpovědnost:** Vykreslování commit nodů (kroužky, text, metadata)

**Metody k přesunu:**

- `_draw_commits()`
- `_create_circle_polygon()`
- `_draw_branch_flag()` (základní vykreslení, bez tooltip logiky)

**Závislosti:**

- `utils.data_structures.Commit`
- `utils.constants` (NODE_RADIUS, FONT_SIZE)
- `utils.theme_manager`
- `utils.translations` (pro překlad textů)

**Interface:**

```python
class CommitDrawer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()

    def draw_commits(self, commits: List[Commit], column_widths: Dict,
                     on_tooltip_callback: Callable) -> None:
        """Vykreslí všechny commit nodes s metadaty."""
        pass

    def _create_circle_polygon(self, x: float, y: float, radius: float,
                              num_points: int = 20) -> List[float]:
        """Vytvoří polygon aproximující kruh."""
        pass
```

---

#### 3. `visualization/drawing/tag_drawer.py` (200 řádků)

**Odpovědnost:** Vykreslování Git tagů s emoji ikonami a tooltips

**Metody k přesunu:**

- `_draw_tags()`
- `_draw_tag_emoji()`
- `_draw_tag_label()`
- `_add_tag_tooltip()`
- `_calculate_required_tag_space()`

**Závislosti:**

- `utils.data_structures.Tag`
- `utils.constants`
- `utils.theme_manager`

**Interface:**

```python
class TagDrawer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.tag_tooltips = {}

    def draw_tags(self, commits: List[Commit], graph_column_width: int) -> None:
        """Vykreslí všechny tagy u commitů."""
        pass

    def calculate_required_tag_space(self, commits: List[Commit]) -> int:
        """Vypočítá potřebný prostor pro tagy."""
        pass
```

---

#### 4. `visualization/drawing/branch_flag_drawer.py` (250 řádků)

**Odpovědnost:** Vykreslování branch flags (vlajky) a jejich propojení s commity

**Metody k přesunu:**

- `_draw_branch_flag()` (pokročilá verze s tooltips)
- `_add_tooltip_to_flag()`
- `_draw_flag_connection()`
- `_truncate_branch_name()`
- `_calculate_flag_width()`
- `_calculate_horizontal_line_extent()`

**Závislosti:**

- `utils.data_structures.Commit`
- `utils.constants`
- `utils.theme_manager`

**Interface:**

```python
class BranchFlagDrawer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.flag_tooltips = {}

    def draw_branch_flags(self, commits: List[Commit],
                         graph_column_width: int) -> None:
        """Vykreslí branch flags pro všechny commity."""
        pass

    def calculate_flag_width(self, commits: List[Commit]) -> int:
        """Vypočítá šířku pro branch flags."""
        pass
```

---

#### 5. `visualization/ui/column_manager.py` (400 řádků)

**Odpovědnost:** Správa sloupců - resizing, separátory, drag & drop events

**Metody k přesunu:**

- `_draw_column_separators()`
- `setup_column_resize_events()`
- `_start_drag()`
- `_on_separator_drag()`
- `_on_separator_release()`
- `_throttled_redraw()`
- `_move_separators_to_scroll_position()`

**Závislosti:**

- tkinter Canvas
- `utils.constants` (MIN_COLUMN_WIDTH_*)
- `utils.theme_manager`

**Interface:**

```python
class ColumnManager:
    def __init__(self, canvas):
        self.canvas = canvas
        self.column_widths = {}
        self.separators = []
        self.dragging = False

    def setup_column_separators(self, column_widths: Dict) -> None:
        """Vytvoří separátory mezi sloupci."""
        pass

    def setup_resize_events(self, on_resize_callback: Callable) -> None:
        """Nastaví event handlers pro resizing."""
        pass

    def get_column_widths(self) -> Dict:
        """Vrátí aktuální šířky sloupců."""
        return self.column_widths
```

---

#### 6. `visualization/ui/tooltip_manager.py` (100 řádků)

**Odpovědnost:** Správa všech tooltips (show/hide, pozicování)

**Metody k přesunu:**

- `_show_tooltip()`
- `_hide_tooltip()`

**Závislosti:**

- tkinter Canvas
- `utils.theme_manager`

**Interface:**

```python
class TooltipManager:
    def __init__(self, canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.tooltip_id = None
        self.tooltip_text_id = None

    def show_tooltip(self, x: int, y: int, text: str) -> None:
        """Zobrazí tooltip na dané pozici."""
        pass

    def hide_tooltip(self) -> None:
        """Skryje aktuální tooltip."""
        pass
```

---

#### 7. `visualization/ui/text_formatter.py` (200 řádků)

**Odpovědnost:** Formátování textu - truncation, DPI handling, měření šířky

**Metody k přesunu:**

- `_truncate_text_to_width()`
- `_truncate_description_for_dpi()`
- `_detect_scaling_factor()`
- `_adjust_descriptions_for_scaling()`
- `_recalculate_descriptions_for_width()`

**Závislosti:**

- tkinter Font
- `utils.constants`

**Interface:**

```python
class TextFormatter:
    def __init__(self, canvas):
        self.canvas = canvas
        self.scaling_factor = self._detect_scaling_factor()

    def truncate_text_to_width(self, text: str, font, max_width: int,
                               suffix: str = "...") -> str:
        """Zkrátí text na danou šířku."""
        pass

    def adjust_descriptions_for_dpi(self, commits: List[Commit]) -> None:
        """Upraví délku popisů podle DPI."""
        pass

    def detect_scaling_factor(self) -> float:
        """Detekuje DPI scaling factor."""
        pass
```

---

#### 8. `visualization/graph_drawer.py` (200 řádků) - ORCHESTRATOR

**Odpovědnost:** Koordinace všech drawing a UI komponent, veřejné API

**Zachované metody:**

- `__init__()`
- `reset()`
- `draw_graph()` - deleguje na komponenty
- `_calculate_column_widths()` - orchestrace výpočtu
- `_calculate_graph_column_width()` - deleguje na komponenty
- `_get_table_start_position()`
- `_update_branch_lanes()`
- `_make_color_pale()` - utility

**Nová struktura:**

```python
class GraphDrawer:
    """Hlavní orchestrátor pro vykreslování grafu."""

    def __init__(self):
        self.connection_drawer = None
        self.commit_drawer = None
        self.tag_drawer = None
        self.branch_flag_drawer = None
        self.column_manager = None
        self.tooltip_manager = None
        self.text_formatter = None

    def reset(self):
        """Reset stavu všech komponent."""
        if self.tooltip_manager:
            self.tooltip_manager.hide_tooltip()
        # ...

    def draw_graph(self, canvas, commits, merge_branches, ...):
        """
        Hlavní entry point - orchestruje celé vykreslení grafu.

        Deleguje na jednotlivé komponenty v tomto pořadí:
        1. ConnectionDrawer - spojnice
        2. CommitDrawer - commit nodes
        3. TagDrawer - tagy
        4. BranchFlagDrawer - branch flags
        5. ColumnManager - separátory
        """
        # Initialize components if needed
        if not self.connection_drawer:
            self._initialize_components(canvas)

        # Calculate layout
        column_widths = self._calculate_column_widths(canvas, commits, ...)

        # Delegate drawing to components
        self.connection_drawer.draw_connections(commits, ...)
        self.commit_drawer.draw_commits(commits, column_widths, ...)
        self.tag_drawer.draw_tags(commits, ...)
        self.branch_flag_drawer.draw_branch_flags(commits, ...)
        self.column_manager.setup_column_separators(column_widths)

    def _initialize_components(self, canvas):
        """Inicializuje všechny drawing a UI komponenty."""
        self.connection_drawer = ConnectionDrawer(canvas)
        self.commit_drawer = CommitDrawer(canvas)
        self.tag_drawer = TagDrawer(canvas)
        self.branch_flag_drawer = BranchFlagDrawer(canvas)
        self.column_manager = ColumnManager(canvas)
        self.tooltip_manager = TooltipManager(canvas)
        self.text_formatter = TextFormatter(canvas)
```

---

### Implementační checklist - Fáze 1

- [x] **Krok 1: Příprava**
  - [x] Vytvořit `src/visualization/drawing/__init__.py`
  - [x] Vytvořit `src/visualization/ui/__init__.py`
  - [x] Commit: "Prepare directory structure for graph_drawer refactoring"

- [x] **Krok 2: ConnectionDrawer**
  - [x] Vytvořit `src/visualization/drawing/connection_drawer.py`
  - [x] Přesunout metody: `_draw_connections`, `_draw_line`, `_draw_bezier_curve`, `_calculate_rounded_corner_arc`
  - [x] Aktualizovat imports v `graph_drawer.py`
  - [x] Otestovat vykreslování spojnic
  - [x] Commit: "Extract ConnectionDrawer from GraphDrawer"

- [x] **Krok 3: CommitDrawer**
  - [x] Vytvořit `src/visualization/drawing/commit_drawer.py`
  - [x] Přesunout metody: `_draw_commits`, `_create_circle_polygon`
  - [x] Aktualizovat `graph_drawer.py` pro použití CommitDrawer
  - [x] Otestovat vykreslování commitů
  - [x] Commit: "Extract CommitDrawer from GraphDrawer"

- [x] **Krok 4: TagDrawer**
  - [x] Vytvořit `src/visualization/drawing/tag_drawer.py`
  - [x] Přesunout metody pro tagy
  - [x] Aktualizovat `graph_drawer.py`
  - [x] Otestovat vykreslování tagů
  - [x] Commit: "Extract TagDrawer from GraphDrawer"

- [x] **Krok 5: BranchFlagDrawer**
  - [x] Vytvořit `src/visualization/drawing/branch_flag_drawer.py`
  - [x] Přesunout metody pro branch flags
  - [x] Aktualizovat `graph_drawer.py`
  - [x] Otestovat branch flags
  - [x] Commit: "Extract BranchFlagDrawer from GraphDrawer"

- [x] **Krok 6: TooltipManager**
  - [x] Vytvořit `src/visualization/ui/tooltip_manager.py`
  - [x] Přesunout `_show_tooltip`, `_hide_tooltip`
  - [x] Aktualizovat všechny komponenty pro použití TooltipManager
  - [x] Otestovat tooltips
  - [x] Commit: "Extract TooltipManager from GraphDrawer"

- [x] **Krok 7: TextFormatter**
  - [x] Vytvořit `src/visualization/ui/text_formatter.py`
  - [x] Přesunout všechny text handling metody
  - [x] Aktualizovat komponenty
  - [x] Otestovat text truncation
  - [x] Commit: "Extract TextFormatter from GraphDrawer"

- [x] **Krok 8: ColumnManager**
  - [x] Vytvořit `src/visualization/ui/column_manager.py`
  - [x] Přesunout všechny column resizing metody
  - [x] Aktualizovat `graph_drawer.py`
  - [x] Otestovat column resizing
  - [x] Commit: "Extract ColumnManager from GraphDrawer"

- [x] **Krok 9: Finalizace**
  - [x] Aktualizovat `graph_drawer.py` jako orchestrátor
  - [x] Zkontrolovat všechny importy
  - [x] Spustit aplikaci a otestovat všechny features
  - [x] Commit: "Finalize GraphDrawer refactoring - now orchestrator only"

- [x] **Krok 10: Dokumentace** ✅ HOTOVO
  - [x] Aktualizovat `docs/DESIGN.md` s novou strukturou ✅
  - [x] Aktualizovat `README.md` strukturu ✅
  - [x] Aktualizovat `CLAUDE.md` strukturu ✅
  - [ ] Commit: "Update documentation for GraphDrawer refactoring" (zatím bez commitů)

---

## 🎯 FÁZE 2: Rozdělení repository.py

**Priorita:** STŘEDNÍ
**Odhadovaný čas:** 1-2 hodiny
**Velikost:** 1090 řádků → 5 souborů

### Cílová struktura

```
src/repo/
├── repository.py                # Facade (200 řádků)
├── parsers/                     # Subpackage pro parsing
│   ├── __init__.py
│   ├── commit_parser.py         # Commit parsing (300 řádků)
│   ├── branch_analyzer.py       # Branch detection (300 řádků)
│   └── tag_parser.py            # Tag parsing (150 řádků)
└── analyzers/                   # Subpackage pro analýzu
    ├── __init__.py
    └── merge_detector.py        # Merge branch detection (350 řádků)
```

### Detailní rozdělení

#### 1. `repo/parsers/commit_parser.py` (300 řádků)

**Odpovědnost:** Parsing commitů z Git repozitáře

**Metody k přesunu:**

- `parse_commits()`
- `parse_commits_with_remote()`
- `_truncate_message()`
- `_truncate_name()`
- `_truncate_description()`
- `_get_relative_date()`
- `_get_short_date()`
- `_get_full_date()`

**Interface:**

```python
class CommitParser:
    def __init__(self, repo: Repo):
        self.repo = repo

    def parse_commits(self, include_remote: bool = False) -> List[Commit]:
        """Parsuje commity z repozitáře."""
        pass

    def _truncate_message(self, message: str, max_length: int) -> str:
        """Zkrátí commit message."""
        pass
```

---

#### 2. `repo/parsers/branch_analyzer.py` (300 řádků)

**Odpovědnost:** Analýza větví a jejich vztahů

**Metody k přesunu:**

- `_build_commit_branch_map()`
- `_build_commit_branch_map_with_remote()`
- `_build_branch_availability_map()`
- `_detect_branch_divergence()`

**Interface:**

```python
class BranchAnalyzer:
    def __init__(self, repo: Repo):
        self.repo = repo

    def build_commit_branch_map(self, include_remote: bool = False) -> Dict[str, str]:
        """Vytvoří mapu commit → branch."""
        pass

    def detect_branch_divergence(self, branch_name: str) -> Dict:
        """Detekuje divergenci větve."""
        pass
```

---

#### 3. `repo/parsers/tag_parser.py` (150 řádků)

**Odpovědnost:** Parsing Git tagů

**Metody k přesunu:**

- `_build_commit_tag_map()`
- `_build_commit_tag_map_with_remote()`

**Interface:**

```python
class TagParser:
    def __init__(self, repo: Repo):
        self.repo = repo

    def build_commit_tag_map(self, include_remote: bool = False) -> Dict[str, List[Tag]]:
        """Vytvoří mapu commit → tagy."""
        pass
```

---

#### 4. `repo/analyzers/merge_detector.py` (350 řádků)

**Odpovědnost:** Detekce a analýza merge větví

**Metody k přesunu:**

- `_detect_merge_branches()`
- `_apply_merge_branch_styling()`
- `_build_full_hash_map()`
- `_trace_merge_branch_commits()`
- `_get_commits_in_branches_with_head()`
- `_extract_branch_name_from_merge()`
- `_make_color_pale()`

**Interface:**

```python
class MergeDetector:
    def __init__(self, commits: List[Commit]):
        self.commits = commits

    def detect_merge_branches(self) -> List[MergeBranch]:
        """Detekuje merge větve."""
        pass

    def apply_merge_branch_styling(self, merge_branches: List[MergeBranch]) -> None:
        """Aplikuje styling na merge větve."""
        pass
```

---

#### 5. `repo/repository.py` (200 řádků) - FACADE

**Odpovědnost:** Veřejné API pro práci s repozitářem

**Zachované metody:**

- `__init__()`
- `load_repository()` - deleguje na parsery
- `get_uncommitted_changes()`
- `_create_uncommitted_commits()`
- `get_merge_branches()` - deleguje na MergeDetector
- `get_repository_stats()`

**Nová struktura:**

```python
class GitRepository:
    """Facade pro práci s Git repozitářem."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo = None
        self.commit_parser = None
        self.branch_analyzer = None
        self.tag_parser = None
        self.merge_detector = None

    def load_repository(self) -> bool:
        """Načte repozitář a inicializuje parsery."""
        try:
            self.repo = Repo(self.repo_path)
            self.commit_parser = CommitParser(self.repo)
            self.branch_analyzer = BranchAnalyzer(self.repo)
            self.tag_parser = TagParser(self.repo)
            return True
        except Exception as e:
            logger.error(f"Failed to load repository: {e}")
            return False

    def parse_commits(self, include_remote: bool = False) -> List[Commit]:
        """Deleguje na CommitParser."""
        commits = self.commit_parser.parse_commits(include_remote)

        # Detect merge branches
        self.merge_detector = MergeDetector(commits)
        merge_branches = self.merge_detector.detect_merge_branches()
        self.merge_detector.apply_merge_branch_styling(merge_branches)

        return commits
```

---

### Implementační checklist - Fáze 2

- [x] **Krok 1: Příprava**
  - [x] Vytvořit `src/repo/parsers/__init__.py`
  - [x] Vytvořit `src/repo/analyzers/__init__.py`
  - [x] Commit: "Prepare directory structure for repository refactoring"

- [x] **Krok 2: CommitParser**
  - [x] Vytvořit `src/repo/parsers/commit_parser.py`
  - [x] Přesunout parsing metody
  - [x] Aktualizovat `repository.py`
  - [x] Otestovat parsing commitů
  - [x] Commit: "Extract CommitParser from GitRepository"

- [x] **Krok 3: BranchAnalyzer**
  - [x] Vytvořit `src/repo/parsers/branch_analyzer.py`
  - [x] Přesunout branch analysis metody
  - [x] Aktualizovat `repository.py`
  - [x] Otestovat branch detection
  - [x] Commit: "Extract BranchAnalyzer from GitRepository"

- [x] **Krok 4: TagParser**
  - [x] Vytvořit `src/repo/parsers/tag_parser.py`
  - [x] Přesunout tag parsing metody
  - [x] Aktualizovat `repository.py`
  - [x] Otestovat tag parsing
  - [x] Commit: "Extract TagParser from GitRepository"

- [x] **Krok 5: MergeDetector**
  - [x] Vytvořit `src/repo/analyzers/merge_detector.py`
  - [x] Přesunout merge detection metody
  - [x] Aktualizovat `repository.py`
  - [x] Otestovat merge detection
  - [x] Commit: "Extract MergeDetector from GitRepository"

- [x] **Krok 6: Finalizace**
  - [x] Aktualizovat `repository.py` jako facade
  - [x] Zkontrolovat všechny importy
  - [x] Spustit aplikaci a otestovat loading repozitářů
  - [x] Commit: "Finalize GitRepository refactoring - now facade only"

- [ ] **Krok 7: Dokumentace**
  - [ ] Aktualizovat dokumentaci
  - [ ] Commit: "Update documentation for GitRepository refactoring"

---

## 🎯 FÁZE 3: Rozdělení main_window.py

**Priorita:** NÍZKÁ
**Odhadovaný čas:** 1-2 hodiny
**Velikost:** 1225 řádků → 5 souborů

### Cílová struktura

```
src/gui/
├── main_window.py               # Layout manager (400 řádků)
├── repo_manager.py              # Repository operations (500 řádků)
└── ui_components/               # Subpackage pro UI komponenty
    ├── __init__.py
    ├── language_switcher.py     # Language switching (100 řádků)
    ├── theme_switcher.py        # Theme switching (100 řádků)
    └── stats_display.py         # Stats display (100 řádků)
```

### Detailní rozdělení

#### 1. `gui/repo_manager.py` (500 řádků)

**Odpovědnost:** Správa repozitářů - loading, cloning, cleanup

**Metody k přesunu:**

- `on_repository_selected()`
- `_is_git_url()`
- `clone_repository()`
- `_clone_worker()`
- `_show_auth_dialog_sync()`
- `_on_clone_complete()`
- `_cleanup_old_temp_clones()`
- `_cleanup_single_clone()`
- `_cleanup_temp_clones()`
- `load_repository()`
- `refresh_repository()`
- `refresh_local_repository()`
- `fetch_remote_data()`

**Interface:**

```python
class RepositoryManager:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.current_repo = None
        self.temp_clone_path = None

    def load_repository(self, repo_path: str) -> None:
        """Načte lokální repozitář."""
        pass

    def clone_repository(self, url: str) -> None:
        """Naklonuje remote repozitář."""
        pass

    def refresh_repository(self) -> None:
        """Obnoví aktuální repozitář."""
        pass
```

---

#### 2. `gui/ui_components/language_switcher.py` (100 řádků)

**Odpovědnost:** Přepínání jazyků

**Metody k přesunu:**

- `_create_czech_flag()`
- `_create_uk_flag()`
- `_switch_to_language()`
- `_update_flag_appearance()`
- `_on_language_changed()`

**Interface:**

```python
class LanguageSwitcher:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.translation_manager = get_translation_manager()
        self.czech_canvas = None
        self.uk_canvas = None

    def create_switcher_ui(self) -> tk.Frame:
        """Vytvoří UI pro přepínání jazyků."""
        pass

    def switch_to_language(self, language: str) -> None:
        """Přepne na daný jazyk."""
        pass
```

---

#### 3. `gui/ui_components/theme_switcher.py` (100 řádků)

**Odpovědnost:** Přepínání témat

**Metody k přesunu:**

- `_create_sun_icon()`
- `_create_moon_icon()`
- `_switch_to_theme()`
- `_update_theme_icon_appearance()`
- `_on_theme_changed()`

**Interface:**

```python
class ThemeSwitcher:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.theme_manager = get_theme_manager()
        self.sun_canvas = None
        self.moon_canvas = None

    def create_switcher_ui(self) -> tk.Frame:
        """Vytvoří UI pro přepínání témat."""
        pass

    def switch_to_theme(self, theme: str) -> None:
        """Přepne na dané téma."""
        pass
```

---

#### 4. `gui/ui_components/stats_display.py` (100 řádků)

**Odpovědnost:** Zobrazení statistik repozitáře

**Metody k přesunu:**

- `_update_stats_display()`
- `_show_repo_path_tooltip()`
- `_hide_repo_path_tooltip()`

**Interface:**

```python
class StatsDisplay:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.stats_label = None
        self.tooltip_window = None

    def create_stats_ui(self) -> tk.Label:
        """Vytvoří UI pro statistiky."""
        pass

    def update_stats(self, repo_path: str, commits: List[Commit], ...) -> None:
        """Aktualizuje zobrazení statistik."""
        pass
```

---

#### 5. `gui/main_window.py` (400 řádků) - LAYOUT MANAGER

**Odpovědnost:** UI layout, koordinace komponent

**Zachované metody:**

- `__init__()`
- `_center_window()`
- `_resize_window_for_content()`
- `_get_accurate_content_width()`
- `_calculate_table_width()`
- `setup_ui()` - použije komponenty

**Nová struktura:**

```python
class MainWindow:
    """Hlavní okno aplikace - layout manager."""

    def __init__(self):
        self.root = tk.Tk()
        self.repo_manager = RepositoryManager(self)
        self.language_switcher = None
        self.theme_switcher = None
        self.stats_display = None
        # ...

    def setup_ui(self):
        """Nastaví UI pomocí komponent."""
        # Create top bar with switchers
        top_bar = ttk.Frame(self.root)

        self.language_switcher = LanguageSwitcher(top_bar)
        lang_frame = self.language_switcher.create_switcher_ui()

        self.theme_switcher = ThemeSwitcher(top_bar)
        theme_frame = self.theme_switcher.create_switcher_ui()

        # Create stats display
        self.stats_display = StatsDisplay(top_bar)
        stats_label = self.stats_display.create_stats_ui()

        # Create drag & drop area
        self.drag_drop_frame = DragDropFrame(
            self.root,
            on_select=self.repo_manager.on_repository_selected
        )

        # ...
```

---

### Implementační checklist - Fáze 3

- [ ] **Krok 1: Příprava**
  - [ ] Vytvořit `src/gui/ui_components/__init__.py`
  - [ ] Commit: "Prepare directory structure for main_window refactoring"

- [ ] **Krok 2: LanguageSwitcher**
  - [ ] Vytvořit `src/gui/ui_components/language_switcher.py`
  - [ ] Přesunout metody
  - [ ] Aktualizovat `main_window.py`
  - [ ] Otestovat přepínání jazyka
  - [ ] Commit: "Extract LanguageSwitcher from MainWindow"

- [ ] **Krok 3: ThemeSwitcher**
  - [ ] Vytvořit `src/gui/ui_components/theme_switcher.py`
  - [ ] Přesunout metody
  - [ ] Aktualizovat `main_window.py`
  - [ ] Otestovat přepínání tématu
  - [ ] Commit: "Extract ThemeSwitcher from MainWindow"

- [ ] **Krok 4: StatsDisplay**
  - [ ] Vytvořit `src/gui/ui_components/stats_display.py`
  - [ ] Přesunout metody
  - [ ] Aktualizovat `main_window.py`
  - [ ] Otestovat zobrazení statistik
  - [ ] Commit: "Extract StatsDisplay from MainWindow"

- [ ] **Krok 5: RepositoryManager**
  - [ ] Vytvořit `src/gui/repo_manager.py`
  - [ ] Přesunout všechny repo operations
  - [ ] Aktualizovat `main_window.py`
  - [ ] Otestovat loading a cloning
  - [ ] Commit: "Extract RepositoryManager from MainWindow"

- [ ] **Krok 6: Finalizace**
  - [ ] Aktualizovat `main_window.py` jako layout manager
  - [ ] Zkontrolovat všechny importy
  - [ ] Spustit aplikaci a otestovat všechny features
  - [ ] Commit: "Finalize MainWindow refactoring - now layout manager only"

- [ ] **Krok 7: Dokumentace**
  - [ ] Aktualizovat dokumentaci
  - [ ] Commit: "Update documentation for MainWindow refactoring"

---

## 📈 Očekávané benefity

### Před refaktoringem

```
graph_drawer.py   : 1889 řádků (87.8 KB)
repository.py     : 1090 řádků (47.8 KB)
main_window.py    : 1225 řádků (49.1 KB)
--------------------------------
CELKEM            : 4204 řádků (184.7 KB) - 59% kódové báze
```

### Po refaktoringu

```
visualization/
├── graph_drawer.py           :  200 řádků
├── drawing/
│   ├── connection_drawer.py  :  300 řádků
│   ├── commit_drawer.py      :  300 řádků
│   ├── tag_drawer.py         :  200 řádků
│   └── branch_flag_drawer.py :  250 řádků
└── ui/
    ├── column_manager.py     :  400 řádků
    ├── tooltip_manager.py    :  100 řádků
    └── text_formatter.py     :  200 řádků

repo/
├── repository.py             :  200 řádků
├── parsers/
│   ├── commit_parser.py      :  300 řádků
│   ├── branch_analyzer.py    :  300 řádků
│   └── tag_parser.py         :  150 řádků
└── analyzers/
    └── merge_detector.py     :  350 řádků

gui/
├── main_window.py            :  400 řádků
├── repo_manager.py           :  500 řádků
└── ui_components/
    ├── language_switcher.py  :  100 řádků
    ├── theme_switcher.py     :  100 řádků
    └── stats_display.py      :  100 řádků

--------------------------------
CELKEM                        : ~4200 řádků v 18 souborech
NEJVĚTŠÍ SOUBOR               :  500 řádků (vs. 1889 dříve)
```

### Metriky

| Metrika | Před | Po | Zlepšení |
|---------|------|----|----|
| **Největší soubor** | 1889 řádků | 500 řádků | **-73%** |
| **Průměrná velikost** | 1400 řádků | 233 řádků | **-83%** |
| **Kontextové okno** | 184 KB najednou | ~20-50 KB | **-70-80%** |
| **Počet odpovědností/soubor** | 5-8 | 1-2 | **-75%** |

### Konkrétní přínosy

1. **Rychlejší práce s AI**
   - Claude Code načte jen relevantní soubory (200-500 řádků místo 1889)
   - 70-80% redukce kontextového okna při práci na konkrétní feature

2. **Lepší čitelnost**
   - Každý soubor má jasnou, jednoduchou odpovědnost
   - Snadnější orientace v kódu
   - Méně scrollování

3. **Jednodušší testování**
   - Každá komponenta testovatelná izolovaně
   - Snadnější mockování závislostí
   - Rychlejší unit testy

4. **Lepší maintainability**
   - Změny v jedné oblasti neovlivní ostatní
   - Jasné rozhraní mezi komponentami
   - Snadnější refaktoring jednotlivých částí

5. **Paralelní vývoj**
   - Více lidí může pracovat na různých komponentách bez konfliktů

---

## ⚠️ Rizika a mitigace

### Riziko 1: Breaking changes

**Mitigace:** Zachovat původní veřejné API, změnit jen interní implementaci

### Riziko 2: Chyby při přesunu kódu

**Mitigace:**

- Postupná implementace s testy po každém kroku
- Commit po každé extrahované komponentě
- Možnost rychlého rollbacku

### Riziko 3: Zvýšená složitost importů

**Mitigace:**

- Použít `__init__.py` pro re-export běžně používaných tříd
- Zachovat jednoduché importy pro koncové uživatele

### Riziko 4: Zvýšení build času

**Mitigace:**

- PyInstaller by neměl být ovlivněn (stejný počet modulů)
- Možné mírné zpomalení (< 5%)

---

## 🧪 Testovací strategie

### Před začátkem refaktoringu

- [ ] Spustit aplikaci a otestovat všechny základní features
- [ ] Otestovat loading lokálního repozitáře
- [ ] Otestovat cloning remote repozitáře
- [ ] Otestovat přepínání jazyka
- [ ] Otestovat přepínání tématu
- [ ] Otestovat column resizing
- [ ] Otestovat tooltips
- [ ] Otestovat zobrazení tagů
- [ ] Vytvořit screenshot reference

### Po každé fázi refaktoringu

- [ ] Spustit aplikaci
- [ ] Otestovat všechny features z minulé sekce
- [ ] Porovnat s reference screenshoty
- [ ] Zkontrolovat console na warnings/errors
- [ ] Zkontrolovat log soubor

### Po dokončení všech fází

- [ ] Kompletní manuální testing všech features
- [ ] Performance test (load velkého repozitáře)
- [ ] Memory leak test (load/unload repozitáře opakovaně)
- [ ] Build .exe a otestovat
- [ ] Otestovat na čistém systému

---

## 📝 Poznámky k implementaci

### Import conventions

```python
# Doporučené importy po refaktoringu:

# Namísto:
from visualization.graph_drawer import GraphDrawer

# Použít:
from visualization import GraphDrawer  # re-export v __init__.py

# Pro interní komponenty:
from visualization.drawing.connection_drawer import ConnectionDrawer
```

### **init**.py soubory

```python
# visualization/__init__.py
from .graph_drawer import GraphDrawer
from .layout import GraphLayout
from .colors import get_branch_color

__all__ = ['GraphDrawer', 'GraphLayout', 'get_branch_color']

# visualization/drawing/__init__.py
from .connection_drawer import ConnectionDrawer
from .commit_drawer import CommitDrawer
from .tag_drawer import TagDrawer
from .branch_flag_drawer import BranchFlagDrawer

__all__ = [
    'ConnectionDrawer',
    'CommitDrawer',
    'TagDrawer',
    'BranchFlagDrawer'
]
```

### Zpětná kompatibilita

```python
# Pro zachování zpětné kompatibility (pokud by někdo importoval interní metody):

# graph_drawer.py (legacy support)
from visualization.drawing.connection_drawer import ConnectionDrawer

class GraphDrawer:
    # ... nová implementace ...

    # Legacy methods (deprecated)
    def _draw_connections(self, *args, **kwargs):
        """DEPRECATED: Use self.connection_drawer.draw_connections()"""
        warnings.warn("_draw_connections is deprecated", DeprecationWarning)
        return self.connection_drawer.draw_connections(*args, **kwargs)
```

---

## 🎯 Success Criteria

Refaktoring je úspěšný, pokud:

- [ ] ✅ Všechny soubory jsou menší než 500 řádků
- [ ] ✅ Každý soubor má max. 2 hlavní odpovědnosti
- [ ] ✅ Aplikace funguje identicky jako před refaktoringem
- [ ] ✅ Všechny tests procházejí (pokud existují)
- [ ] ✅ .exe build funguje bez problémů
- [ ] ✅ Dokumentace je aktualizována
- [ ] ✅ Kontextové okno při práci s AI je o 70%+ menší

---

## 📚 Reference

- **Principy:**
  - [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)
  - [Separation of Concerns](https://en.wikipedia.org/wiki/Separation_of_concerns)
  - [Facade Pattern](https://refactoring.guru/design-patterns/facade)
  - [Composition over Inheritance](https://en.wikipedia.org/wiki/Composition_over_inheritance)

- **Související dokumenty:**
  - `docs/DESIGN.md` - Aktuální architektura
  - `CLAUDE.md` - Development guide
  - `docs/CHANGELOG.md` - Historie změn

---

**Autor:** Claude Code + User
**Datum vytvoření:** 2025-01-12
**Verze:** 1.0
**Status:** 📋 Ready for Implementation
