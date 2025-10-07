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
- **Pillow (PIL)** - vykreslování grafu
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
│   ├── gui/
│   │   ├── main_window.py   # Hlavní okno s drag & drop a URL support
│   │   ├── graph_canvas.py  # Canvas pro graf s scrollbary
│   │   ├── drag_drop.py     # Drag & drop pro složky i URL
│   │   └── auth_dialog.py   # Dialog pro OAuth autorizaci
│   ├── repo/
│   │   └── repository.py    # Git operace pomocí GitPython
│   ├── visualization/
│   │   ├── graph_drawer.py  # Kreslení grafu, tagů, tooltipů, column resizing
│   │   ├── layout.py        # Layout s lane recycling
│   │   └── colors.py        # Barevné schéma s prefixovými větvemi
│   └── utils/
│       ├── data_structures.py # Commit, MergeBranch
│       ├── constants.py       # Konstanty aplikace (layout, barvy, rozměry)
│       └── logging_config.py  # Centralizované logování (~/.gitvys/)
├── build/               # Build skripty a assety
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
