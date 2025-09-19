# Git Visualizer

Jednoduchá desktop aplikace pro vizualizaci Git repozitářů určená především pro studenty.

## Funkce

- **Drag & drop rozhraní** - jednoduše přetáhni složku repozitáře
- **Vizualizace podobná GitKrakenu** - přehledný graf větví a commitů
- **Scrollovatelné zobrazení** - procházej historii repozitáře
- **Barevné rozlišení větví** - každá větev má svou barvu
- **Jednoduché spuštění** - samostatný .exe soubor

## Rychlý start

1. Stáhni a spusť `GitVisualizer.exe`
2. Přetáhni složku Git repozitáře do aplikace
3. Prohlížej si historii commitů graficky

## Vývoj

Viz [INSTALLATION.md](INSTALLATION.md) pro instrukce k instalaci a spuštění ze zdrojového kódu.

## Struktura projektu

```
git-visualizer/
├── main.py              # Vstupní bod aplikace
├── gui/                 # GUI komponenty
│   ├── main_window.py   # Hlavní okno
│   ├── graph_canvas.py  # Graf komponenta
│   └── drag_drop.py     # Drag & drop funkcionalita
├── repo/                # Git operace
│   └── repository.py    # Práce s Git repozitářem
├── visualization/       # Vizualizace
│   ├── graph_drawer.py  # Kreslení grafu
│   ├── layout.py        # Rozmístění uzlů
│   └── colors.py        # Barevné schéma
└── utils/               # Pomocné utility
    └── data_structures.py # Datové struktury
```

## Technologie

- **Python 3.8+** - hlavní jazyk
- **tkinter** - GUI framework
- **GitPython** - práce s Git repozitáři
- **Pillow** - vykreslování grafu
