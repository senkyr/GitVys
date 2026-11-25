# Changelog

Všechny významné změny v tomto projektu.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/).

## [1.6.1] - 2026-11-25

### Security

- Tlačítko „Odhlásit GitHub“ ve stavovém řádku smaže uložený token GitHubu. Dřív token zůstával v profilu Windows bez možnosti odhlášení, takže na sdíleném účtu pracoval další uživatel s GitHubem předchozího. Klonování, které token získalo před odhlášením, se zruší a token neuloží.
- Při klonu z GitHubu přes HTTP(S) se nepoužije přihlášení, které si pamatuje sám Git (credential helper, na Windows Git Credential Manager, ani program askpass). Dřív první pokus o klon takové přihlášení použil, takže soukromý repozitář šel naklonovat i po odhlášení v aplikaci. Kdo má přihlášení ke GitHubu uložené v Gitu, přihlásí se v aplikaci zvlášť; ostatní hosty se klonují jako dřív. Vyžaduje Git 2.31+.

### Changed

- Tlačítko „Načíst remote“ („Načíst větve“) stáhne aktuální stav ze serveru (`git fetch --prune origin`), než remote větve zobrazí. Dřív jen četlo, co už na disku bylo, takže graf ukazoval stav z posledního `git fetch` a tvářil se jako aktuální. Přihlášení ke GitHubu se řeší stejně jako u klonu (jen přihlášení v aplikaci, token jen pro `https://github.com`) a stahuje se jen z povolených hostů. Když se stáhnout nepodaří, graf ukáže naposledy stažený stav a aplikace na to upozorní. Refresh (F5) ze sítě nestahuje.

### Fixed

- Každá větev má vlaječku u commitu, na který ukazuje; ukazuje-li na jeden commit víc větví, stojí vlaječky vedle sebe. Dřív nesl commit jedinou vlaječku, takže větev bez vlastního commitu (čerstvě založená, sloučená fast-forwardem, pozadu za `main`) v grafu chyběla. V pohledu s remote větvemi totéž platí pro větve na serveru.
- Aktuální větev je v grafu označená tučným rámečkem vlaječky (tooltip „aktuální větev“). Dřív nebylo poznat, na které větvi uživatel stojí.
- Rozpracované změny (WIP) navazují na commit, na kterém uživatel opravdu stojí (HEAD). Dřív se hledal nejnovější commit se jménem aktuální větve, takže na čerstvě založené větvi visel WIP uzel bez spojnice.
- Odpojený HEAD (po `git checkout <hash>`) je v grafu vidět jako vlaječka `HEAD` a commity vytvořené v tomto stavu se zobrazí pod ní. Dřív v grafu chyběly a rozpracované změny se nezobrazily vůbec.
- Popis WIP uzlu (počet souborů) je v jazyce rozhraní; dřív byl vždy česky.
- Neošetřená chyba se ukáže v dialogu. Dřív ji okenní `.exe` nemělo kam vypsat: tlačítko po chybě „nic neudělalo“ a chyba při startu aplikaci beze slova zavřela.

## [1.6.0] - 2026-09-27

### Security

- GitHub token se už nevkládá do URL klonu (dřív skončil v `.git/config` klonu a v textu chybového dialogu); Gitu se předává hlavičkou přes proměnné prostředí a jen pro `https://github.com`.
- Token se neposílá na jiné hosty ani přes `http://`; whitelist URL platí i pro text přetažený přímo na graf.
- Uložený token je na Windows šifrovaný přes DPAPI, jinde v souboru s právy 0600; starý plaintext se převede.
- Všechny tokeny vydané přes OAuth App GitVys byly 27. 9. 2026 odvolány; při dalším klonu soukromého repozitáře se uživatel přihlásí znovu.

### Fixed

- Graf: potomek je vždy nad rodičem i při rozjetých hodinách autora; větve už nesdílí sloupec se spojnicí jiné větve.
- Plné SHA-1 místo 8znakových hashů (kolize ve velkých repozitářích).
- Odvolaný uložený token vede k novému přihlášení místo trvalé chyby klonování.
- Zavření OAuth dialogu ukončí polling GitHubu.
- Výsledek pomalého načítání starého repozitáře už nepřepíše graf nově otevřeného.
- Tlačítko „Načíst remote“ se po chybě znovu povolí.
- Detekce neuložených změn (první řádek `git status` se špatně parsoval, nesledované soubory se hlásily jako staged).
- Statistiky nepočítají WIP pseudo-commit ani virtuální merge větve.
- Změna šířky sloupce už nekreslí uzly a vlaječky znovu přes staré.

### Changed

- Rychlejší načítání velkých repozitářů: jeden průchod historií místo průchodu pro každou větev, merge-base a first-parent linie v paměti, žádné O(n²) při kreslení tagů, tooltipy bez registrace Tcl příkazu pro každou položku.
- Odstraněna nepoužívaná závislost Pillow.
- Graf se kreslí virtualizovaně (jen řádky kolem viditelné oblasti); šířky sloupců se u velkých repozitářů odhadují ze šířek znaků.
- Dočasné klony má každá instance ve vlastní složce se zámkem; úklid při startu nemaže klony jiné běžící instance.

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
