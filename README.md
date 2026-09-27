# Git Visualizer

Desktopová aplikace pro studenty: zobrazí historii Git repozitáře jako graf větví a commitů.

## Upozornění

- **Token GitHubu zůstává uložený v profilu Windows** (`~/.gitvys/github_token`, šifrovaný přes DPAPI vázané na účet). Na sdíleném školním účtu proto další žák pracuje s GitHubem předchozího. Tlačítko pro odhlášení chybí, po práci je potřeba soubor `~/.gitvys/github_token` smazat.
- **Token má OAuth scope `repo`,** tedy plný zápis do všech soukromých repozitářů přihlášeného uživatele. Užší oprávnění by šlo jen přes GitHub App.
- **Verze do 1.5.0 včetně nepoužívat.** Vkládaly token do URL klonu (token skončil v `.git/config` klonu a v textu chyb) a přetažením URL na graf šlo obejít whitelist hostů. Aktuální build je v [Releases](https://github.com/senkyr/GitVys/releases) (v1.6.0). Všechny tokeny vydané přes OAuth App GitVys byly 27. 9. 2026 odvolány — při dalším klonu soukromého repa se uživatel přihlásí znovu.
- **Neověřeno:** GUI po revizi, klon soukromého repa proti GitHubu přes OAuth a plynulost scrollování ve skutečném okně. Revize to ověřila jen testy.

## Rychlý start

1. Nainstaluj [Git](https://git-scm.com/downloads) (aplikace bez něj nefunguje).
2. Spusť `GitVisualizer.exe`.
3. Přetáhni do okna složku s Git repozitářem nebo URL repozitáře, případně použij tlačítka „Otevřít složku“ / „Otevřít URL“.

## Požadavky

### Spuštění .exe

- **Git** v `PATH`. Pro klonování **soukromých** repozitářů z GitHubu je potřeba Git 2.31 nebo novější (token se předává přes `GIT_CONFIG_COUNT`).
- Python není potřeba, je zabalený v .exe.

### Spuštění ze zdrojového kódu

- Python 3.8+ (syntaxe ověřená pro 3.8, testy běží na 3.14)
- Git

```bash
pip install -r requirements.txt
python src/main.py
```

### Build .exe

```bash
build\build-exe.bat
```

Skript nainstaluje závislosti a PyInstaller a spustí `build/build.py`. Výsledek je v `dist/`. Podrobnosti v [docs/BUILD-INSTRUCTIONS.md](docs/BUILD-INSTRUCTIONS.md).

## Funkce

- **Lokální repozitář:** přetažením složky nebo přes dialog.
- **Repozitář z URL:** HTTPS nebo SSH (`git@host:user/repo.git`) z povolených hostů: GitHub, GitLab, Bitbucket, Codeberg, gitea.io, sr.ht (i jejich subdomény). Klonuje se do dočasné složky (každá spuštěná instance má vlastní `%TEMP%/gitvys_instance_*` se zámkem), která se smaže při zavření repozitáře nebo aplikace. Po pádu aplikace se zbytky uklidí při dalším startu; klony jiné běžící instance zůstanou. URL s přihlašovacími údaji (`https://user:heslo@...`) se odmítají.
- **Soukromé repozitáře na GitHubu:** když klon selže kvůli přihlášení, aplikace otevře přihlášení přes GitHub (OAuth Device Flow). Token:
  - se používá jen pro `https://github.com`, nikdy pro jiné hosty ani přes `http://`;
  - se Gitu předává hlavičkou přes proměnné prostředí, takže se neobjeví v URL, v `.git/config` klonu ani v chybových hláškách;
  - se ukládá do `~/.gitvys/github_token`: na Windows zašifrovaný přes DPAPI (vázaný na účet uživatele), jinde jako soubor s právy 0600;
  - pokud ho GitHub odmítne (odvolaný, vypršelý), smaže se a aplikace požádá o nové přihlášení.
- **Graf:** commity seřazené podle času, ale potomek je vždy nad rodičem (jako `git log --date-order`), takže graf nerozbijí ani rozjeté hodiny autora. Každá větev má vlastní barvu a sloupec; sloupce se recyklují, až skončí větev i její spojnice.
- **Velké repozitáře:** na canvas se kreslí jen řádky kolem viditelné části (při scrollování se dokreslují), takže ani desetitisíce commitů nevytvoří statisíce položek canvasu. Šířky sloupců se nad 2000 commitů odhadují ze šířek znaků.
- **Merge větve:** větve, které po sloučení zmizely, se kreslí jako světlejší samostatná odbočka.
- **Tagy** s emoji ikonou; u anotovaných tagů tooltip se zprávou.
- **Neuložené změny** (staged/working/untracked) jako pseudo-commit „WIP“ nad aktuální větví.
- **Remote větve:** tlačítko „Načíst remote“ zobrazí i větve `origin/*`. Pozor: čte je z lokálních remote-tracking refů, **nedělá `git fetch`**; ukáže tedy stav z posledního fetch/pull.
- **Refresh (F5)** znovu načte repozitář.
- **Sloupce tabulky** (zpráva, autor, e-mail, datum) jdou roztáhnout tažením oddělovače; tooltipy u zkrácených textů.
- **Čeština/angličtina** a **světlý/tmavý režim**; volby se ukládají do `~/.gitvys/settings.json`.
- **Kontrola Gitu při startu** s návodem, když chybí.

## Screenshot

![Git Visualizer](docs/screenshot.png)

## Testy

```bash
pytest tests/ -q
pytest tests/ --cov=src --cov-report=html   # coverage (potřebuje pytest-cov)
```

Většina testů je jednotková s mocky GitPythonu a tkinteru. `tests/integration/test_real_repository.py` staví skutečné repozitáře přes `git` v dočasné složce a ověřuje celé načtení i vlastnosti grafu (hrany vedou jen dolů, větve se v jednom sloupci nepřekrývají). `tests/integration/test_large_repository.py` vyrobí přes `git fast-import` repozitář s ~12 000 commity a ověří virtualizované kreslení (běží asi 20 s). Testy vytvářejí skrytá okna Tk, takže potřebují funkční tkinter. Strategie testování: [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md).

## Struktura projektu

```
src/
├── main.py                   # vstupní bod, kontrola Gitu
├── auth/
│   ├── github_auth.py        # OAuth Device Flow (GitHub)
│   ├── token_storage.py      # uložení tokenu (DPAPI / 0600)
│   └── git_credentials.py    # whitelist URL, předání tokenu Gitu, čištění tajemství z textů
├── gui/
│   ├── main_window.py        # hlavní okno a rozvržení
│   ├── repo_manager.py       # načítání, klonování, refresh ve vláknech
│   ├── graph_canvas.py       # canvas s grafem, scrollování
│   ├── drag_drop.py          # úvodní obrazovka, drag & drop, dialog URL
│   ├── auth_dialog.py        # dialog přihlášení ke GitHubu
│   └── ui_components/        # přepínač jazyka a tématu, statistiky
├── repo/
│   ├── repository.py         # fasáda GitRepository
│   ├── parsers/              # commity, přiřazení větví, tagy
│   └── analyzers/            # detekce merge větví
├── visualization/
│   ├── layout.py             # pořadí řádků a přidělení sloupců větvím
│   ├── graph_drawer.py       # orchestrace kreslení
│   ├── drawing/              # spojnice, uzly, tagy, vlaječky větví
│   ├── ui/                   # sloupce, tooltipy, práce s textem
│   └── colors.py
└── utils/                    # datové struktury, konstanty, logování, témata, překlady
build/                        # build skripty (PyInstaller), ikona
docs/                         # instalace, build, design, changelog, testovací strategie
tests/                        # unit/ a integration/
```

## Technologie

- Python + tkinter (graf se kreslí na `tk.Canvas`)
- GitPython (čtení repozitáře; volá `git`)
- tkinterdnd2 (drag & drop)
- requests (komunikace s GitHub OAuth)

## Další dokumentace

- [docs/INSTALLATION.md](docs/INSTALLATION.md) – instalace ze zdrojového kódu
- [docs/BUILD-INSTRUCTIONS.md](docs/BUILD-INSTRUCTIONS.md) – build .exe
- [docs/DESIGN.md](docs/DESIGN.md) – architektura
- [docs/CHANGELOG.md](docs/CHANGELOG.md) – historie verzí
- [CLAUDE.md](CLAUDE.md) – instrukce pro Claude Code
- [LICENSE.md](LICENSE.md) – licence
