# Changelog

Všechny významné změny v tomto projektu.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/).

## [1.1.1] - 2025-10-04

### Added

- **Centralizované logování** (`utils/logging_config.py`)
  - Logging do souboru `gitvisualizer.log`
  - File handler: WARNING a výše
  - Console handler: ERROR a výše
- **Paste tlačítko v URL dialogu**
  - Tlačítko 📋 pro vložení URL ze schránky jedním kliknutím
  - Tooltip "Vložit ze schránky" při hover
  - Zvětšený emoji font (14pt) pro lepší viditelnost

### Changed

- **Vylepšení kvality kódu**
  - Robustnější error handling (40+ oprav bare exception)
  - Všechny exceptions jsou logovány s kontextem
  - Refaktoring `_detect_merge_branches()` (160 řádků → ~80 řádků)
  - Rozdělení na 4 helper funkce pro lepší maintainability
  - Magic numbers nahrazeny konstantami (`utils/constants.py`)
  - Pinnuté verze závislostí pro reproducible builds
    - GitPython==3.1.40
    - Pillow==10.1.0
    - tkinterdnd2==0.3.0
- **Oprava URL dialogu**
  - Odstraněno systémové topmost - dialog je topmost jen v rámci aplikace

### Security

- **Bezpečnostní vylepšení URL validace**
  - Whitelist trusted Git hostů (GitHub, GitLab, Bitbucket, Codeberg, sr.ht, gitea.io)
  - Podpora HTTP(S) i SSH formátu
  - Odmítnutí untrusted hostů s logováním

### Documentation

- Aktualizace README.md s novými utils soubory
- Aktualizace CLAUDE.md s error handling & logging sekcí
- Aktualizace DESIGN.md s code quality improvements
- Aktualizace INSTALLATION.md s logováním a troubleshooting

## [1.1.0] - 2025-10-04

### Added

- **URL Support** - načítání remote repozitářů z URL
  - Drag & drop URL z prohlížeče
  - Dialog pro zadání URL
  - Automatické klonování do dočasné složky
  - Cleanup s Windows file handle managementem

### Fixed

- Oprava vykreslování složitých repozitářů
- Opravy načítání z URL

### Documentation

- Aktualizace dokumentace
- Aktualizace buildu aplikace

## [1.0.0] - 2025-10-03

### Added

- **Přepracované úvodní okno** s lepším UX
- **Tooltips** pro dlouhá jména a e-maily autorů
- **Kinetické scrollování** s momentum efektem
- **Plynulejší změny šířky sloupců** s throttlováním

### Fixed

- Úspěšné vykreslování složitých repozitářů
- Oprava vykreslování tooltipů s dlouhými názvy
- Oprava pádu při opětovném otevírání
- Čistší zobrazování (menší clutter)

### Changed

- Upravené vykreslování záhlaví
- Whitespace normalizace

## [0.3.0] - 2025-09-27

### Added

- **Bohatší obarvování větví** s prefixovými barvami
- **Vykreslování mergování větví**
- **Tag system** - zobrazování Git tagů
  - Zkracování dlouhých tagů
  - Tagy se nevykreslují přes větve
- **Remote větve support**
  - Zobrazování remote větví
  - Samostatné vykreslování local a remote větví
  - Symboly pro rozlišení remote/local větví
- **Refresh tlačítko** pro obnovení repozitáře
- **Zobrazování necommitnutých změn** (WIP commits)

### Changed

- Hladké křivky spojnic při větvení (Bézier curves)
- Přepracované automatické šířky sloupců
- Vylepšené přizpůsobování okna obsahu

### Fixed

- Nezobrazování nelokálních refs
- Odstraněné zobrazování "unknown" větví
- Reset výpočtů pro každý repozitář
- Drobné úpravy ve vykreslování

## [0.2.0] - 2025-09-19

### Added

- **Build binární verze aplikace** (PyInstaller)
- **Interaktivní funkce:**
  - Posuvné oddělovače sloupců
  - Oddělovače funkční i během scrollování
  - Tooltipy s kompletními Descriptions
  - Škálování zobrazení
- **Vylepšené vykreslování:**
  - Unikátní barvy větví
  - Spojnice větví se nekříží
  - Zobrazování více větví
- **Performance:**
  - Jemnější scrollování
  - Optimalizace načítání větších repozitářů

### Changed

- Upravené ovládací prvky
- Upravený výpis autora a data
- Předělané scrollování
- Úpravy uživatelského rozhraní

### Fixed

- Oprava zobrazení dlouhých Descriptions
- Kosmetické úpravy zobrazení okna aplikace

## [0.1.0] - 2025-09-18

### Added

- **Základní vizualizace Git repozitářů**
  - Graf větví a commitů
  - Detaily commitů v tabulce
  - Přizpůsobování okna obsahu
- **Dokumentace:**
  - CLAUDE.md
  - Design dokument
  - Implementační dokumentace
- Založení repozitáře

---

**Vývoj projektu:** 18. září 2025 - 4. října 2025
