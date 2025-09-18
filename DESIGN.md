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
├── main.py              # Vstupní bod aplikace
├── gui/
│   ├── main_window.py   # Hlavní okno
│   ├── graph_canvas.py  # Graf komponenta (vlevo)
│   ├── commit_table.py  # Tabulka commitů (vpravo)
│   └── drag_drop.py     # Drag & drop funkcionalita
├── git/
│   ├── repository.py    # Práce s Git repozitářem
│   └── parser.py        # Parsování Git dat
├── visualization/
│   ├── graph_drawer.py  # Kreslení grafu
│   ├── table_formatter.py # Formátování tabulky
│   ├── layout.py        # Rozmístění uzlů
│   └── colors.py        # Barevné schéma
├── utils/
│   └── helpers.py       # Pomocné funkce
└── requirements.txt
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

### Branch objekt

```python
@dataclass
class Branch:
    name: str
    color: str
    commits: List[Commit]
    start_commit: str
    end_commit: str
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

### Fáze 2: Vylepšení (budoucí)

1. **Lepší vizualizace**
   - Smooth křivky místo přímých čar
   - Ikony pro různé typy commitů
   - Lepší barevné schéma

2. **Základní interaktivita**
   - Klikání na commit pro detail
   - Zoom in/out
   - Vyhledávání

3. **Export funkcionalita**
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

## 10. Rozšíření do budoucna

### Možné funkce v.2.0

- Podpora více repozitářů najednou (tabs)
- Filtrování podle autora/data přímo v GUI
- Témata a barevné schéma na přání
- Export historie do různých formátů (PDF, HTML)
- Zobrazení více detailů (změny souborů, diff statistiky)
- Podpora pro Git hooks a workflow vizualizace

---

**Priorita implementace**: Fáze 1 je MVP která by měla pokrýt 80% potřeb studentů. Fáze 2 až podle potřeby a zpětné vazby.
