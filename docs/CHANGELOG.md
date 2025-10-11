# Changelog

Všechny významné změny v tomto projektu.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/).

## [1.5.0] - 2025-01-12

### Added

- **Podpora světlého/tmavého tématu**
  - Přepínač témat pomocí ikon slunce ☀️ a měsíce 🌙 v pravém horním rohu
  - Automatické ukládání volby tématu do `~/.gitvys/settings.json`
  - Defaultní téma: light mode
  - Nový modul: `utils/theme_manager.py` pro správu barevných schémat
  - Kompletní TTK widget styling (Button, Label, Frame, Entry, Progressbar)
  - Dynamické barvy pro všechny UI komponenty (záhlaví, separátory, tooltipy, canvas)

### Changed

- **Vylepšený URL dialog**
  - Pozadí dialogu se přizpůsobuje aktuálnímu tématu
  - Entry pole pro URL má správné barvy v dark módu (#3a3a3a pozadí, #e0e0e0 text)
  - Konzistentní styling napříč celou aplikací

### Fixed

- **Inteligentní skrývání scrollbarů**
  - Scrollbary se správně skrývají když se obsah vejde do viewportu
  - Zmenšen buffer v scrollregion z 50px na 20px (60px úspora celkem)
  - Přidán threshold 10px pro zobrazení scrollbarů (eliminuje zbytečné zobrazování)
  - Scrollbary se aktualizují při změně velikosti okna

## [1.4.0] - 2025-10-08

### Added

- **Dvojjazyčné rozhraní (čeština/angličtina)**
  - Přepínač jazyka pomocí vykreslených vlajek (🇨🇿 česká a 🇬🇧 britská) v levém horním rohu
  - Automatické ukládání volby jazyka do `~/.gitvys/settings.json`
  - Defaultní jazyk: čeština
  - Kompletní překlad všech UI prvků: tlačítka, statusy, dialogy, záhlaví sloupců
  - Nový modul: `utils/translations.py` pro správu překladů
- **Tooltip s autorem commitu**
  - Zobrazení plného jména autora při najetí myší na zkrácené jméno v tabulce

### Changed

- **Vylepšená dokumentace**
  - Aktualizace README.md s jasnějšími instrukcemi
  - Rozšíření CLAUDE.md o development informace
  - Vylepšené build skripty (`build-exe.bat`)

### Fixed

- **Oprava rozšiřování okna při refreshi**
  - Okno se již nerozšiřuje nechtěně při obnovení repozitáře
  - Lepší handling změny velikosti okna

## [1.3.0] - 2025-10-07

### Added

- **OAuth Device Flow autentizace pro GitHub**
  - Podpora pro private GitHub repozitáře
  - Automatická autorizace přes GitHub OAuth Device Flow
  - Uložení tokenu do `~/.gitvys/github_token`
  - User-friendly dialog s device code a progress barem
  - Automatické otevření GitHubu v prohlížeči
  - Nové moduly: `auth/github_auth.py`, `auth/token_storage.py`, `gui/auth_dialog.py`
- **Detekce chybějícího Gitu při startu**
  - Kontrola dostupnosti Gitu při spuštění aplikace
  - User-friendly dialog s odkazem na stažení Git
  - Elegantní ukončení místo crashe s chybovou hláškou
- **Tooltip s cestou k repozitáři**
  - Zobrazení plné cesty při hover nad názvem repozitáře
  - Funguje i pro klonované remote repozitáře (temp složka)

### Changed

- **Dynamické zkracování commit message**
  - Message se zkracuje podle skutečné šířky sloupce (ne pevných 50 znaků)
  - Tooltip zobrazí plný text při hover nad zkráceným textem
  - Optimální využití prostoru i u složitých repozitářů s dlouhými zprávami
- **Vylepšení šířky grafického sloupce**
  - Automatický výpočet podle nejvíce napravo vykreslené větve
  - Optimální mezera mezi větvemi a textem (právě na jednu větev)
  - Eliminace zbytečně velkých prázdných mezer
- **Centralizované umístění log souboru**
  - Log soubor se vytváří v `~/.gitvys/gitvisualizer.log` (místo CWD)
  - Windows: `%USERPROFILE%\.gitvys\gitvisualizer.log`
  - Linux/Mac: `~/.gitvys/gitvisualizer.log`
  - Konzistentní s GitHub token storage
  - Žádné "špinění" různých složek v systému
- **Aktualizace dependencies na nejnovější verze**
  - GitPython 3.1.40 → 3.1.45 (oprava CVE-2024-22190)
  - Pillow 10.1.0 → 11.0.0
  - tkinterdnd2 0.3.0 → 0.4.2
  - Přidán requests==2.32.3 (pro OAuth komunikaci)
- **Vylepšení README.md**
  - Upřesnění požadavků pro .exe vs. development vs. build
  - Jasně uvedeno, že .exe nevyžaduje Python (je zabalený)
  - Přímé odkazy na instalace Git a Pythonu

### Fixed

- **Build proces opravy**
  - `.spec` soubor se nyní generuje do `build/temp/` (ne root)
  - `*.spec` přidán do `.gitignore`
  - Přidány chybějící `--hidden-import` pro OAuth moduly
  - `--collect-all=git` a `--collect-all=gitdb` pro kompletní Git dependencies
  - Oprava zabalení všech potřebných modulů do .exe
- **Oprava překrývání textu**
  - Commit message se už nepřekrývají u složitých repozitářů
  - Správné zkracování podle dostupného prostoru

### Security

- **Aktualizace GitPython na 3.1.45**
  - Oprava CVE-2024-22190 (High Severity - Untrusted search path)
  - Bezpečnostní záplata pro Windows systémy

## [1.2.0] - 2025-10-05

### Added

- **Centralizované logování** (`utils/logging_config.py`)
  - Logging do souboru `gitvisualizer.log`
  - File handler: WARNING a výše
  - Console handler: ERROR a výše
- **Paste tlačítko v URL dialogu**
  - Tlačítko 📋 pro vložení URL ze schránky jedním kliknutím
  - Tooltip "Vložit ze schránky" při hover
  - Zvětšený emoji font (14pt) pro lepší viditelnost
- **Ikona aplikace**
  - Custom ikona pro .exe (feather/pírko logo)
  - PNG formát uvnitř ICO (5 velikostí: 16, 24, 32, 48, 256px)
  - Správné zobrazení v Průzkumníku Windows
  - Ikona umístěna v `build/icon.ico`

### Changed

- **Refaktoring struktury projektu**
  - Přesun zdrojového kódu do `src/` složky
  - Přesun build assets (ikona, feather.png) do `build/` složky
  - Čistší root repozitáře (pouze config soubory a dokumentace)
  - Aktualizace všech build skriptů pro novou strukturu
  - Aktualizace `setup.py` pro src-based layout
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
- **Logging jen v dev módu**
  - Produkční .exe nevytváří prázdný gitvisualizer.log
  - Debug logging v .exe jen s `GITVIS_DEBUG=1` env proměnnou

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
