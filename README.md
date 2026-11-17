# Git Visualizer

Desktopová aplikace pro studenty: zobrazí historii Git repozitáře jako graf větví a commitů. Otevře lokální složku i repozitář z URL (naklonuje si ho do dočasné složky) a u soukromých repozitářů na GitHubu se přihlásí přes OAuth.

Je napsaná v Pythonu (tkinter, GitPython) a pro Windows se vydává jako samostatný `GitVisualizer.exe`. Zdrojový kód je v `src/`, testy v `tests/`, skripty pro build .exe v `build/`, dokumentace v `docs/`.

## Spuštění

### Hotový program (Windows)

1. Nainstaluj [Git](https://git-scm.com/downloads) tak, aby byl v `PATH` (aplikace bez něj nefunguje a při startu to ohlásí). Pro klonování **soukromých** repozitářů z GitHubu je potřeba Git 2.31 nebo novější (token se předává přes `GIT_CONFIG_COUNT`).
2. Stáhni `GitVisualizer.exe` z [Releases](https://github.com/senkyr/GitVys/releases) a spusť ho. Python není potřeba, je zabalený v .exe.
3. Přetáhni do okna složku s Git repozitářem nebo URL repozitáře, případně použij tlačítka „Otevřít složku“ / „Otevřít URL“.

### Ze zdrojového kódu

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

## Upozornění

- **Přihlášení ke GitHubu zůstává po zavření aplikace uložené.** Po prvním klonu soukromého repozitáře se token uloží do `~/.gitvys/github_token` (na Windows zašifrovaný přes DPAPI vázané na účet Windows) a použije ho každý, kdo pod stejným účtem Windows aplikaci spustí. Na sdíleném školním účtu by tak další žák klonoval soukromé repozitáře předchozího. Než od počítače odejdeš, klikni vpravo dole na **„Odhlásit GitHub“**: token se smaže a další klon soukromého repozitáře si vyžádá nové přihlášení.
- **Verze 1.6.0 a starší tlačítko „Odhlásit GitHub“ nemají.** V nich se odhlásíš jen smazáním souboru `%USERPROFILE%\.gitvys\github_token`.
- **Odhlášení token na GitHubu neodvolá,** smaže jen jeho kopii v počítači. Kdo si token stihl zkopírovat, může ho používat dál. Při podezření ho odvolej na GitHubu: Settings → Applications → Authorized OAuth Apps → Revoke.
- **Odhlášení se netýká přihlášení, které si pamatuje sám Git.** První pokus o klon běží s běžným nastavením Gitu včetně jeho credential helperu (na Windows obvykle Git Credential Manager). Má-li Git pro účet Windows uložené přihlášení ke GitHubu, soukromý repozitář se naklonuje bez přihlášení v aplikaci, a to i po odhlášení. Takové přihlášení aplikace nezná a nemaže; odebírá se tam, kam ho Git uložil (u Git Credential Manageru ve Správci pověření Windows).
- **Token má OAuth scope `repo`,** tedy plný zápis do všech soukromých repozitářů přihlášeného uživatele, i když aplikace repozitáře jen čte. Užší oprávnění by šlo jen přes GitHub App. Na počítači, kterému nevěříš, se proto nepřihlašuj a na sdíleném se vždy odhlas.
- **Naklonovaný repozitář leží na disku, dokud ho nezavřeš.** Klon z URL (i soukromého repozitáře) je v dočasné složce `%TEMP%\gitvys_instance_*` a smaže se při zavření repozitáře nebo aplikace; odhlášení ho nezavírá. Když aplikace spadne, zůstane tam do jejího příštího spuštění. Na sdíleném počítači proto před odchodem aplikaci zavři.
- **Verze do 1.5.0 včetně nepoužívat.** Vkládají token do URL klonu (skončí v `.git/config` klonu a v textu chyb), ukládají ho jako čitelný text a přetažením URL na graf v nich jde obejít seznam povolených hostů.
- **„Načíst remote“ nestahuje nic ze sítě.** Tlačítko čte lokální remote-tracking refy, nedělá `git fetch`. Ukáže tedy stav z posledního fetch/pull; pro aktuální stav nejdřív v repozitáři spusť `git fetch` a pak repozitář načti znovu (repozitář otevřený z URL zavři a otevři znovu).
- **Se starším Gitem než 2.31 soukromý repozitář nenaklonuješ.** Git token od aplikace nepřevezme, klon skončí chybou autentizace i po úspěšném přihlášení a hláška na verzi Gitu neupozorní. Aktualizuj Git.
- **Překlep v adrese repozitáře na GitHubu vypadá jako chybějící přihlášení.** GitHub u neexistujícího repozitáře odpovídá stejně jako u soukromého, takže aplikace otevře přihlašovací dialog a uložené přihlášení smaže. Zkontroluj adresu a přihlas se znovu.

## Funkce

- **Lokální repozitář:** přetažením složky nebo přes dialog.
- **Repozitář z URL:** HTTPS nebo SSH (`git@host:user/repo.git`) z povolených hostů: GitHub, GitLab, Bitbucket, Codeberg, gitea.io, sr.ht (i jejich subdomény). Klonuje se do dočasné složky (každá spuštěná instance má vlastní `%TEMP%/gitvys_instance_*` se zámkem), která se smaže při zavření repozitáře nebo aplikace. Po pádu aplikace se zbytky uklidí při dalším startu; klony jiné běžící instance zůstanou. URL s přihlašovacími údaji (`https://user:heslo@...`) se odmítají.
- **Soukromé repozitáře na GitHubu:** když klon selže kvůli přihlášení, aplikace otevře přihlášení přes GitHub (OAuth Device Flow). Token:
  - se používá jen pro `https://github.com`, nikdy pro jiné hosty ani přes `http://`;
  - se Gitu předává hlavičkou přes proměnné prostředí, takže se neobjeví v URL, v `.git/config` klonu ani v chybových hláškách;
  - se ukládá do `~/.gitvys/github_token`: na Windows zašifrovaný přes DPAPI (vázaný na účet uživatele), jinde jako soubor s právy 0600;
  - pokud ho GitHub odmítne (odvolaný, vypršelý), smaže se a aplikace požádá o nové přihlášení;
  - smaže tlačítko „Odhlásit GitHub“ ve stavovém řádku. Klonování, které token získalo před odhlášením, se zruší a token neuloží.
- **Graf:** commity seřazené podle času, ale potomek je vždy nad rodičem (jako `git log --date-order`), takže graf nerozbijí ani rozjeté hodiny autora. Každá větev má vlastní barvu a sloupec; sloupce se recyklují, až skončí větev i její spojnice.
- **Velké repozitáře:** na canvas se kreslí jen řádky kolem viditelné části (při scrollování se dokreslují), takže ani desetitisíce commitů nevytvoří statisíce položek canvasu. Šířky sloupců se nad 2000 commitů odhadují ze šířek znaků.
- **Merge větve:** větve, které po sloučení zmizely, se kreslí jako světlejší samostatná odbočka.
- **Tagy** s emoji ikonou; u anotovaných tagů tooltip se zprávou.
- **Neuložené změny** (staged/working/untracked) jako pseudo-commit „WIP“ nad aktuální větví.
- **Remote větve:** tlačítko „Načíst remote“ (u repozitáře z URL „Načíst větve“) zobrazí i větve `origin/*` z lokálních remote-tracking refů; `git fetch` nedělá (viz Upozornění).
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

Většina testů je jednotková s mocky GitPythonu a tkinteru. `tests/integration/test_real_repository.py` staví skutečné repozitáře přes `git` v dočasné složce a ověřuje celé načtení i vlastnosti grafu (hrany vedou jen dolů, větve se v jednom sloupci nepřekrývají). `tests/integration/test_large_repository.py` vyrobí přes `git fast-import` repozitář s ~12 000 commity a ověří virtualizované kreslení (běží řádově deset sekund). Testy vytvářejí skrytá okna Tk, takže potřebují funkční tkinter; když je stroj zároveň vytížený něčím jiným, občas některý test spadne už na startu Tk (`TclError: Can't find a usable init.tcl`) a opakované spuštění projde. Strategie testování: [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md).

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
│   ├── repo_manager.py       # načítání, klonování, refresh ve vláknech, odhlášení
│   ├── temp_clones.py        # dočasné složky klonů, zámek instance
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
