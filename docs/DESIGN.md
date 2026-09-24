# Git Visualizer - Design Document

## 1. Přehled projektu

### Cíl

Vytvořit jednoduchou desktop aplikaci pro vizualizaci Git repozitářů určenou především pro studenty. Aplikace umožní přetáhnout složku repozitáře a zobrazí přehledný graf větví a commitů podobný GitKrakenu.

### Cílová skupina

- Studenti programování na Windows
- Uživatelé s minimálními znalostmi příkazové řádky
- Potřeba rychlého vizuálního přehledu o stavu repozitáře

### Klíčové požadavky

- Drag & drop rozhraní
- Vizualizace podobná GitKrakenu
- Scrollovatelné zobrazení
- Jednoduché spuštění (.exe soubor)
- V první fázi neinteraktivní

## 2. Technická architektura

### Technologie

- **Python 3.8+** - hlavní jazyk
- **tkinter** - GUI framework (součást Pythonu, jednoduché nasazení)
- **GitPython** - práce s Git repozitáři
- **tkinterdnd2** - drag & drop (graf se kreslí přímo na tk.Canvas, Pillow se nepoužívá)
- **requests** - OAuth Device Flow s GitHubem
- **PyInstaller** - tvorba .exe souboru

### Alternativní technologie (pro pozdější fáze)

- **PyQt5/6** - pokud bude potřeba složitější GUI
- **CustomTkinter** - modernější vzhled tkinter

## 3. Architektura aplikace

### Komponenty

```
git-visualizer/
├── src/                 # Zdrojový kód
│   ├── main.py          # Vstupní bod aplikace (s Git detekcí)
│   ├── auth/            # GitHub OAuth autentizace
│   │   ├── __init__.py
│   │   ├── github_auth.py    # OAuth Device Flow pro GitHub
│   │   └── token_storage.py  # Ukládání tokenu (~/.gitvys/)
│   ├── gui/                  # GUI komponenty (refaktorováno v1.5.0)
│   │   ├── main_window.py   # Layout manager a orchestrátor (500 řádků)
│   │   ├── repo_manager.py  # Repository operations manager (451 řádků)
│   │   ├── graph_canvas.py  # Canvas pro graf s scrollbary
│   │   ├── drag_drop.py     # Drag & drop pro složky i URL
│   │   ├── auth_dialog.py   # Dialog pro OAuth autorizaci
│   │   └── ui_components/   # UI komponenty
│   │       ├── __init__.py
│   │       ├── language_switcher.py  # Language switching s vlajkami
│   │       ├── theme_switcher.py     # Theme switching s ikonami
│   │       └── stats_display.py      # Repository statistiky
│   ├── repo/                # Git operace (refaktorováno v1.5.0)
│   │   ├── repository.py    # GitRepository facade (281 řádků)
│   │   ├── parsers/         # Parsing komponenty
│   │   │   ├── __init__.py
│   │   │   ├── commit_parser.py    # Parsing commitů
│   │   │   ├── branch_analyzer.py  # Analýza větví
│   │   │   └── tag_parser.py       # Parsing tagů
│   │   └── analyzers/       # Analysis komponenty
│   │       ├── __init__.py
│   │       └── merge_detector.py   # Detekce merge větví
│   ├── visualization/       # Vizualizace grafu (refaktorováno v1.5.0)
│   │   ├── graph_drawer.py  # Hlavní orchestrátor (385 řádků)
│   │   ├── layout.py        # Layout s lane recycling
│   │   ├── colors.py        # Barevné utilities a schéma
│   │   ├── drawing/         # Drawing komponenty
│   │   │   ├── __init__.py
│   │   │   ├── connection_drawer.py  # Spojnice mezi commity
│   │   │   ├── commit_drawer.py      # Commit nodes a metadata
│   │   │   ├── tag_drawer.py         # Git tagy s emoji
│   │   │   └── branch_flag_drawer.py # Branch flags a tooltips
│   │   └── ui/              # UI komponenty
│   │       ├── __init__.py
│   │       ├── column_manager.py     # Column resizing
│   │       ├── tooltip_manager.py    # Tooltip systém
│   │       └── text_formatter.py     # Text handling & DPI
│   └── utils/
│       ├── data_structures.py # Commit, MergeBranch, Tag
│       ├── constants.py       # Konstanty aplikace (layout, barvy, rozměry)
│       ├── logging_config.py  # Centralizované logování (~/.gitvys/)
│       ├── theme_manager.py   # Správa témat (světlý/tmavý režim)
│       └── translations.py    # Správa překladů (CS/EN)
├── build/               # Build skripty a assety
│   ├── build-exe.bat    # Automatizovaný build skript
│   ├── build.py         # Build script pro .exe
│   ├── icon.ico         # Ikona aplikace
│   └── feather.png      # Zdrojový asset ikony
├── docs/                # Dokumentace
├── requirements.txt
└── setup.py
```

## 4. Datové struktury

### Commit objekt

```python
@dataclass
class Commit:
    hash: str
    message: str           # Plná commit zpráva
    short_message: str     # Zkrácená na 50 znaků pro tabulku
    author: str
    author_short: str      # Zkrácené jméno pro tabulku
    date: datetime
    date_relative: str     # "2 dny", "1 týden" pro tabulku
    date_short: str        # "05.03" pro tabulku
    parents: List[str]
    branch: str
    branch_color: str      # Hex barva větve
    x: int                 # pozice na časové ose (graf)
    y: int                 # pozice na ose větví (graf)
    table_row: int         # pozice v tabulce
```

### MergeBranch objekt

```python
@dataclass
class MergeBranch:
    virtual_branch_name: str  # např. "merge-abc123"
    branch_point_hash: str    # kde se větev odbočila
    merge_point_hash: str     # kde se větev sloučila
    commits_in_branch: List[str]  # commity v merge větvi
    original_branch_color: str  # barva původní větve
```

## 5. UI Design

### Hlavní okno

```
[Git Visualizer - Přetáhni složku repozitáře]
+------------------------------------------+
|  [Přetáhni složku sem]                   |
|  nebo                                    |
|  [Procházet...]                          |
+------------------------------------------+
|                                          |
|  [Graf Area - scrollovatelná]            |
|  |                                    |  |
|  | ● master    commit message         |  |
|  | │                                  |  |
|  | ├─● feature  add new feature       |  |
|  | │ │                                |  |
|  | │ ● feature  fix bug               |  |
|  | │ │                                |  |
|  | ●─┤ master   merge feature         |  |
|  | │                                  |  |
|                                          |
+------------------------------------------+
| Status: Ready / Loading / Error          |
+------------------------------------------+
```

### Barevné schéma

- **master/main**: #007acc (modrá)
- **feature větve**: #28a745 (zelená)
- **hotfix větve**: #dc3545 (červená)
- **develop větve**: #ffc107 (žlutá)
- **ostatní**: automatické barevné rozlišení

## 6. Implementační plán

### Fáze 1: Základní funkcionalité (MVP)

1. **Setup projektu**
   - Vytvoření struktury souborů
   - Setup requirements.txt
   - Základní main.py s tkinter oknem

2. **Git backend**
   - Implementace GitRepository třídy
   - Načítání základních dat z repozitáře
   - Parser pro commit historii

3. **Základní GUI**
   - Hlavní okno s drag & drop oblastí
   - Implementace drag & drop funkcionality
   - Základní canvas pro kreslení

4. **Vizualizace**
   - Algoritmus pro rozmístění commitů v 2D prostoru
   - Kreslení základního grafu (čáry + body)
   - Zobrazení commit zpráv a autorů

5. **Testování a balíčkování**
   - Testování na různých repozitářích
   - Vytvoření .exe pomocí PyInstaller
   - Dokumentace pro distribuci

### Fáze 2: Vylepšení

✅ **Implementováno:**

- Smooth křivky pomocí Bézier curves
- Ikony pro tagy (emoji: 🏷️ 📌 🚀)
- Barevné schéma s prefixovými větvemi
- Interaktivita: tooltips, column resizing
- Smooth scrolling s momentum
- URL support pro remote repozitáře
- Tag zobrazení s emojis

🔜 **Budoucí vylepšení:**

- Klikání na commit pro detail
- Zoom in/out
- Vyhledávání v commitech
- Export do PNG/SVG
- Print preview

## 7. Technické detaily

### Git příkazy k použití

```bash
git log --all --graph --pretty=format:'%h|%an|%ad|%s|%p' --date=iso
git branch -a
git show-branch --all
```

### Algoritmus pro layout

1. **Časová osa**: Commits seřazené podle data
2. **Větve**: Přiřazení sloupců větvím
3. **Merge detection**: Identifikace merge commitů
4. **Collision avoidance**: Zamezení překrývání čar

### Performance optimalizace

- Lazy loading pro velké repozitáře
- Virtualizace scrollingu
- Cache pro Git operace

## 7.5. Error Handling & Logging

### Logging systém

**Konfigurace** (`utils/logging_config.py`):

- Centralizované nastavení pro celou aplikaci
- File handler: `gitvisualizer.log` v aktuálním adresáři
  - Level: WARNING a výše
  - Format: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`
- Console handler: pouze ERROR a výše (nezahlcovat output)

**Použití v kódu**:

```python
from utils.logging_config import get_logger
logger = get_logger(__name__)

try:
    # nějaká operace
except Exception as e:
    logger.warning(f"Failed to do something: {e}")
```

### Exception handling pattern

**Pravidla**:

- ❌ **Nikdy** `except:` (bare except)
- ✅ **Vždy** `except Exception as e:` s logováním
- Všechny exceptions jsou logovány s kontextem
- User-friendly zprávy v GUI (messagebox)
- Debug informace v log souboru

### Konstanty

**Organizace** (`utils/constants.py`):

- Layout konstanty: spacing, rozměry, pozice
- Barvy: tolerance, sytost, světlost
- UI: velikosti fontů, radiusy, šířky
- Vyhnutí se "magic numbers" v kódu

## 8. Nasazení

### Požadavky

- Windows 10/11
- Python 3.8+ (pro vývoj)
- Git nainstalovaný v systému

### Distribuce

- PyInstaller pro vytvoření standalone .exe
- Možnost portable verze (zip s .exe)
- Velikost cíl: < 50MB

### Instalace pro koncové uživatele

1. Stáhnutí .exe souboru
2. Spuštění (žádná instalace potřeba)
3. První spuštění: drag & drop složky repozitáře

## 9. Testovací scénáře

### Testovací repozitáře

1. **Jednoduchý**: Linear historie, jedna větev
2. **Střední**: Několik feature větví s merge
3. **Komplexní**: Mnoho větví, merge konflikty, tag
4. **Velký**: 1000+ commitů, 10+ větví

### Test cases

- Přetažení neplatné složky
- Repozitář bez .git složky
- Prázdný repozitář
- Velmi velký repozitář
- Repozitář s nestandarními znaky

## 10. Implementované funkce (v1.1)

### URL Support & Temp Clone Management

- Drag & drop URL z prohlížeče (GitHub, GitLab, Bitbucket)
- Automatické klonování do temp složky (`tempfile.mkdtemp()`)
- Cleanup s Windows file handle managementem
  - `GitPython repo.close()` před mazáním
  - `onerror` handler pro readonly files
  - Cleanup při: otevření nového repo, zavření repo, zavření aplikace (atexit)
- Display name extraction z URL (místo temp folder názvu)

### Tag System

- Emoji ikony podle typu tagu:
  - 🏷️ normal tags
  - 📌 release tags (release/*, v*.*.*)
  - 🚀 version tags (v*, ver*)
- Tooltips s plnou zprávou anotovaných tagů
- Intelligent placement (vpravo od commit node)
- Multiple tags per commit support

### Interactive UI

- **Column resizing** by dragging separators
  - Throttled redraw (60 FPS)
  - Min width constraints (50px text, 100px graph)
  - User preferences preserved during session
- **Floating headers** (stay visible while scrolling)
  - Dynamic calculation of header fill
  - Selective bbox (excludes headers from scrollregion)
- **Smooth scrolling** with momentum and acceleration
  - Velocity-based scrolling
  - Deceleration (85% per frame)
  - Scroll bounds checking
- **Tooltips** for all truncated text
  - Commits, authors, branch names, tags
  - Auto-show on hover, auto-hide on leave
  - Positioned smartly (避免截断)

### Performance Optimizations

- **Lane recycling** for better space utilization
  - Reuse lanes from ended branches
  - Reduces horizontal width for complex repos
- **Background threading** for Git operations
  - Repository loading in separate thread
  - UI stays responsive during heavy operations
- **Selective rendering** during column resize
  - Delete only necessary canvas items
  - Keep graph structure intact
- **Smart bbox calculation**
  - Excludes floating headers
  - Accurate scrollregion sizing

### Remote Branches Support

- "Načíst remote/větve" button (for local repos)
- "Načíst větve" button (for cloned repos)
- Remote branch visualization with origin/ prefix
- Remote tag support (显示远程标签)

### Code Quality Improvements (v1.1)

**Refactoring:**

- `_detect_merge_branches()` (160 řádků) → rozděleno na 4 helper funkce:
  - `_build_full_hash_map()` - vytvoření hash mapy
  - `_trace_merge_branch_commits()` - trasování commitů
  - `_get_commits_in_branches_with_head()` - hlavní linie větví
  - `_extract_branch_name_from_merge()` - extrakce názvu z merge message
- Zlepšená čitelnost a testovatelnost

**Error Handling:**

- 40+ bare `except:` nahrazeno `except Exception as e:` + logging
- Centralizovaný logging systém (`utils/logging_config.py`)
- Konzistentní error reporting

**Security:**

- URL validace s whitelist trusted hosts:
  - GitHub, GitLab, Bitbucket, Codeberg, sr.ht, gitea.io
  - Podpora HTTP(S) i SSH (git@) formátu
  - Odmítnutí untrusted hostů s logováním

**Maintainability:**

- Magic numbers nahrazeny konstantami (`utils/constants.py`)
- Pinnuté verze závislostí (reproducible builds)
- Lepší type hints a dokumentace

## 7.6. Visualization Refactoring (v1.5.0)

### Motivace

Původní `graph_drawer.py` měl **1889 řádků** s mnoha odpovědnostmi, což způsobovalo problémy:

- Rychle zaplněné kontextové okno při práci s AI asistenty
- Obtížná údržba a testování
- Nejasné rozhraní mezi komponentami

### Řešení: Single Responsibility Principle

Rozdělení monolitického souboru na **8 specializovaných komponent**:

#### Drawing komponenty (`visualization/drawing/`)

1. **ConnectionDrawer** (384 řádků)
   - Vykreslování spojnic mezi commity
   - Bézierovy křivky pro smooth connections
   - Handling merge a branching connections

2. **CommitDrawer** (396 řádků)
   - Vykreslování commit nodů (kroužky)
   - Metadata (zprávy, autoři, datumy)
   - WIP commits s stipple pattern

3. **TagDrawer** (241 řádků)
   - Git tagy s emoji ikonami
   - Tooltips pro anotované tagy
   - Dynamic tag spacing

4. **BranchFlagDrawer** (335 řádků)
   - Branch flags (vlajky) s názvy větví
   - Local/remote indikace (💻/☁)
   - Tooltips pro dlouhé názvy

#### UI komponenty (`visualization/ui/`)

5. **ColumnManager** (430 řádků)
   - Column resizing with drag & drop
   - Floating headers
   - Throttled redraw (60 FPS)

6. **TooltipManager** (55 řádků)
   - Centralizovaná správa tooltipů
   - Show/hide s pozicováním
   - Wrapping dlouhého textu

7. **TextFormatter** (191 řádků)
   - Text truncation
   - DPI scaling detection
   - Width measurement utilities

#### Orchestrátor

8. **GraphDrawer** (385 řádků)
   - Koordinace všech komponent
   - Layout calculations
   - Veřejné API

#### Color utilities

9. **colors.py** (210 řádků)
   - `make_color_pale()` - HSL manipulace
   - `get_branch_color()` - sémantické barvy
   - Branch color generation

### Výsledky refaktoringu

| Metrika | Před | Po | Zlepšení |
|---------|------|-----|----------|
| Největší soubor | 1889 ř. | 430 ř. | **-77%** |
| Průměrná velikost | 1889 ř. | 309 ř. | **-84%** |
| Počet souborů | 1 | 8 | +700% (lepší modularita) |
| Kontextové okno | 87.8 KB | ~20-40 KB | **-70-80%** |

### Benefity

1. **Rychlejší vývoj s AI** - načítání jen relevantních komponent
2. **Lepší testovatelnost** - izolované komponenty
3. **Jasné odpovědnosti** - každý soubor má 1-2 úkoly
4. **Snadnější údržba** - změny v jedné oblasti neovlivní ostatní
5. **Paralelní vývoj** - více vývojářů může pracovat současně

## 7.7. Repository Architecture Refactoring (v1.5.0)

### Motivace

Původní `repository.py` měl **1090 řádků** s mnoha odpovědnostmi:

- Parsing commitů z Git
- Analýza větví a divergence
- Parsing tagů (local a remote)
- Detekce merge větví a styling
- Správa uncommitted změn

To způsobovalo obtížné porozumění, údržbu a testování jednotlivých funkcí.

### Řešení: Facade Pattern se specializovanými komponentami

Rozdělení monolitického souboru na **5 specializovaných komponent**:

#### Parsing komponenty (`repo/parsers/`)

1. **CommitParser** (350 řádků)
   - Parsing commitů z Git repozitáře
   - Handling local a remote commit parsing
   - Truncation zpráv/jmen/popisů
   - Formátování dat (relativní, zkrácené, plné)

2. **BranchAnalyzer** (279 řádků)
   - Analýza větví a jejich vztahů
   - Vytváření commit-to-branch map
   - Detekce divergence větví (local vs remote)
   - Určení dostupnosti větve (local_only/remote_only/both)

3. **TagParser** (107 řádků)
   - Parsing Git tagů
   - Handling local a remote tags
   - Vytváření commit-to-tags map
   - Podpora anotovaných tagů se zprávami

#### Analysis komponenty (`repo/analyzers/`)

4. **MergeDetector** (355 řádků)
   - Detekce a analýza merge větví
   - Identifikace merge commitů (2+ rodiče)
   - Trasování commitů v merge větvi
   - Extrakce názvů větví z merge zpráv
   - Aplikace světlejších barev na merge commity (HSL manipulace)

#### Facade

5. **GitRepository** (281 řádků)
   - Koordinace všech komponent
   - Delegace na specializované parsery a analyzéry
   - Správa uncommitted změn (WIP commits)
   - Jednotné API pro operace s repozitářem

### Výsledky refaktoringu

| Metrika | Před | Po | Zlepšení |
|---------|------|-----|----------|
| Největší soubor | 1090 ř. | 355 ř. | **-67%** |
| Hlavní facade | 1090 ř. | 281 ř. | **-74%** |
| Průměrná velikost | 1090 ř. | 274 ř. | **-75%** |
| Kontextové okno | 47.8 KB | ~12-16 KB | **-70-75%** |

### Benefity

1. **Modulární architektura** - každá komponenta má jednu jasnou odpovědnost
2. **Snadnější testování** - komponenty lze testovat izolovaně
3. **Lepší údržba** - změny v parsingu neovlivní analýzu
4. **Čistší kód** - GitRepository je nyní jednoduchý facade
5. **Rychlejší vývoj** - práce na konkrétních funkcích bez načítání celého souboru

## 7.8. GUI Architecture Refactoring (v1.5.0)

### Motivace

Původní `main_window.py` měl **1225 řádků** s mnoha odpovědnostmi:

- Window management a layout orchestrace
- Repository operace (loading, cloning, OAuth autentizace)
- Language switching UI
- Theme switching UI
- Statistics display
- Drag & drop handling

To způsobovalo obtížnou údržbu, testování a rychlé zaplnění kontextového okna při vývoji.

### Řešení: Component Pattern se jasným rozdělením odpovědností

Rozdělení monolitického souboru na **5 specializovaných komponent**:

#### UI komponenty (`gui/ui_components/`)

1. **LanguageSwitcher** (154 řádků)
   - Language switching functionality
   - Czech (🇨🇿) a UK (🇬🇧) flag ikony v Canvasu
   - Handling přepínání jazyků (CS ⇄ EN)
   - Visual feedback (active/inactive overlay)
   - Show/hide pro initial screen

2. **ThemeSwitcher** (204 řádků)
   - Theme switching functionality
   - Sun icon (☀️) pro light mode
   - Moon icon (🌙) pro dark mode
   - Handling přepínání tématu
   - Visual feedback (active/inactive overlay)
   - Dynamic repositioning při window resize
   - Show/hide pro initial screen

3. **StatsDisplay** (136 řádků)
   - Repository statistics display
   - UI pro název repozitáře a statistiky
   - Update stats s aktuální language pluralization
   - Repository path tooltip on hover
   - Formátování počtu autorů/větví/tagů/commitů

#### Repository Manager

4. **RepositoryManager** (451 řádků)
   - Veškeré operace s repozitáři
   - Repository selection (URL vs local path detection)
   - Repository cloning (s OAuth supportem)
   - GitHub autentizace (OAuth Device Flow)
   - Temporary clone management a cleanup
   - Repository loading (local a remote)
   - Repository refresh operations
   - Remote branch fetching
   - Správná file handle management pro Windows
   - Token storage integration

**Klíčové metody:**

- `on_repository_selected(repo_path)` - Entry point pro loading (URL nebo local)
- `_is_git_url(text)` - Detekce URL vs local path
- `clone_repository(url)` - Klonování remote repozitářů do temp složky
- `_clone_worker(url, path)` - Background thread pro klonování s OAuth retry
- `load_repository(repo_path)` - Načtení repozitáře a parsing commitů
- `refresh_repository()` - Obnovení podle stavu (local/remote)
- `fetch_remote_data()` - Načtení remote větví
- `close_repository()` - Zavření a cleanup temp souborů
- `_cleanup_temp_clones()` - Automatické mazání temp složek (atexit handler)

#### Layout Manager

5. **MainWindow** (500 řádků)
   - Koordinace všech UI komponent
   - Window management (centrování, resizing)
   - UI layout s component orchestration
   - Callback coordination:
     - `_on_language_changed()` - propagace změny jazyka
     - `_on_theme_changed()` - propagace změny tématu
     - `_on_repository_path_changed()` - validace repozitáře
   - Graph display management
   - Status updates a progress bar
   - Error dialogs a uživatelská zpětná vazba

**Data Flow:**

```
MainWindow (orchestrator)
    ↓
    ├─→ RepositoryManager (repository operations)
    │       ├─→ GitRepository.load_repository()
    │       ├─→ GitRepository.parse_commits()
    │       └─→ GraphLayout.calculate_positions()
    │
    ├─→ LanguageSwitcher (UI component)
    │       └─→ callback → MainWindow._on_language_changed()
    │
    ├─→ ThemeSwitcher (UI component)
    │       └─→ callback → MainWindow._on_theme_changed()
    │
    └─→ StatsDisplay (UI component)
            └─→ update_stats(repo_path, counts, lang)
```

### Výsledky refaktoringu

| Metrika | Před | Po | Zlepšení |
|---------|------|-----|----------|
| Největší soubor | 1225 ř. | 500 ř. | **-59%** |
| Main window | 1225 ř. | 500 ř. | **-59%** |
| Průměrná velikost | 1225 ř. | 289 ř. | **-76%** |
| Počet souborů | 1 | 5 | +400% (lepší modularita) |
| Kontextové okno | 49.1 KB | ~20-25 KB | **-55-60%** |

### Benefity

1. **Modulární architektura** - každá komponenta má jednu jasnou odpovědnost
2. **Lepší testovatelnost** - komponenty lze testovat izolovaně
3. **Repository operace odděleny** - RepositoryManager jako facade pro veškeré Git operace
4. **Čistější MainWindow** - pouze orchestrace a layout, bez implementačních detailů
5. **Reusable komponenty** - LanguageSwitcher, ThemeSwitcher lze použít v jiných projektech
6. **Rychlejší vývoj s AI** - menší soubory → rychlejší načítání kontextu

### Component Pattern

**Společné rozhraní všech UI komponent:**

```python
class UIComponent:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.root = parent_window.root
        # ... component-specific initialization

    def show(self):
        """Show the component"""
        pass

    def hide(self):
        """Hide the component"""
        pass

    def update(self, *args):
        """Update component state"""
        pass
```

**Callback Pattern:**

Komponenty neznají detaily parent window - komunikují jen přes callbacks:

```python
# In LanguageSwitcher:
if self.callback:
    self.callback(new_language)  # Notify parent

# In MainWindow:
self.lang_switcher = LanguageSwitcher(self, callback=self._on_language_changed)
```

## 7.9. Theme Management (v1.5.0)

### Theme systém

**Implementace** (`utils/theme_manager.py`):

- Singleton pattern pro globální správu tématu
- Podpora light/dark módu
- Persistence preference do `~/.gitvys/settings.json`
- Callback systém pro notifikaci o změně tématu

**Barevné schéma:**

Light mode:

- Window background: `#f0f0f0`
- Canvas: `#ffffff`
- Text: `#000000`
- Buttons: `#e0e0e0`
- Entry fields: `#ffffff`

Dark mode:

- Window background: `#2b2b2b`
- Canvas: `#1e1e1e`
- Text: `#e0e0e0`
- Buttons: `#3a3a3a`
- Entry fields: `#3a3a3a`

**TTK Widget Styling:**

Automatická konfigurace všech TTK widgetů:

- TFrame, TLabel, TButton
- TEntry (field background, text, selection colors)
- TProgressbar
- Kontrastní barvy pro čitelnost

**UI Komponenty:**

- Přepínač pomocí ikon (☀️ světlý / 🌙 tmavý)
- Vizuální indikace aktivního tématu (overlay na neaktivní ikoně)
- Dynamické aktualizace všech komponent při změně

## 11. Rozšíření do budoucna

### Možné funkce v2.0

- Podpora více repozitářů najednou (tabs)
- Filtrování podle autora/data přímo v GUI
- Témata a barevné schéma na přání
- Export historie do různých formátů (PDF, HTML)
- Zobrazení více detailů (změny souborů, diff statistiky)
- Podpora pro Git hooks a workflow vizualizace
- Kliknutí na commit pro diff view
- Zoom in/out functionality
- Search & filter UI

---

**Priorita implementace**: Fáze 1 (MVP) a většina Fáze 2 jsou implementovány. v2.0 funkce podle potřeby a zpětné vazby.
