# Git Visualizer - Instalace a spuštění

## Požadavky

- Python 3.8 nebo novější
- Git nainstalovaný v systému
- Windows 10/11 (primární platforma)

## Instalace

### 1. Instalace závislostí

```bash
pip install -r requirements.txt
```

### 2. Spuštění aplikace

```bash
python main.py
```

nebo

```bash
python3 main.py
```

## Vytvoření spustitelného souboru (.exe)

Pro vytvoření standalone .exe souboru:

1. Nainstaluj PyInstaller:

```bash
pip install pyinstaller
```

2. Vytvoř .exe soubor:

```bash
pyinstaller --onefile --windowed --name="GitVisualizer" main.py
```

3. Spustitelný soubor najdeš ve složce `dist/`

## Použití

1. Spusť aplikaci
2. Přetáhni složku s Git repozitářem nebo URL repozitáře do aplikace, nebo klikni na "Otevřít složku" / "Otevřít URL"
3. Pro remote repozitáře (URL): aplikace automaticky naklonuje do dočasné složky
4. Aplikace automaticky načte a zobrazí historii commitů
5. Volitelně: klikni "Načíst remote/větve" pro zobrazení remote větví
6. Pro obnovení použij tlačítko "Refresh" nebo klávesovou zkratku F5

## Testování

Aplikaci můžeš otestovat s jakýmkoliv Git repozitářem, včetně tohoto projektu.

## Pokročilé funkce

### URL support - otevření remote repozitáře

Můžeš otevřít repozitář přímo z URL:

- Přetáhni URL z prohlížeče (např. `https://github.com/user/repo.git`)
- Nebo klikni "Otevřít URL" a zadej URL
- Aplikace automaticky naklonuje repozitář do dočasné složky
- Po zavření repozitáře se temp složka automaticky smaže

### Interaktivní sloupce

- **Změna šířky sloupců**: Táhni separátory mezi sloupci pro změnu šířky
- Šířka se uchová během celé session
- Min. šířka: 50px pro textové sloupce, 100px pro grafický sloupec

### Tooltips

- Najeď myší na zkrácený text pro zobrazení plné verze
- Funguje pro: commit zprávy, autory, branch názvy, tagy

### Smooth scrolling

- Scrolluj kolečkem myši pro plynulý pohyb s momentum efektem
- Rychlejší scrollování = větší akcelerace

### Remote větve

- Klikni "Načíst remote/větve" (lokální repo) nebo "Načíst větve" (klonované repo)
- Zobrazí všechny remote větve s origin/ prefixem

### Klávesové zkratky

- **F5** - Obnovit repozitář
- **Ctrl+C** - Ukončit aplikaci (v příkazové řádce)

### Logování

Aplikace vytváří log soubor pro debugging:

- **Umístění**: `gitvisualizer.log` v aktuálním adresáři
- **Obsah**: Warnings a errors z běhu aplikace
- **Formát**: `YYYY-MM-DD HH:MM:SS - modul - LEVEL - zpráva`
- **Účel**: Pomoc při řešení problémů a debugování

Pokud narazíš na problém, zkontroluj log soubor pro detaily.

## Řešení problémů

### "Vybraná složka neobsahuje Git repozitář"

- Ujisti se, že složka obsahuje `.git` podsložku
- Zkus otevřít nadřazenou složku repozitáře

### Aplikace se nespustí

- Zkontroluj, že máš nainstalován Python 3.8+
- Zkontroluj, že jsou nainstalovány všechny závislosti z requirements.txt

### Prázdný graf

- Repozitář může být prázdný (žádné commity)
- Zkus jiný repozitář s historií commitů

### Chyba při klonování URL

- Zkontroluj, že je URL správná Git URL (začíná `https://`, `http://`, nebo `git@`)
- Zkontroluj internetové připojení
- Některé repozitáře vyžadují autentizaci - použij lokální klon místo URL

### "URL byla odmítnuta" / Untrusted Git host

Aplikace z bezpečnostních důvodů akceptuje pouze důvěryhodné hosty:

**Podporované hosty:**

- GitHub (github.com)
- GitLab (gitlab.com)
- Bitbucket (bitbucket.org)
- Codeberg (codeberg.org)
- SourceHut (sr.ht)
- Gitea (gitea.io)

**Řešení:**

- Použij URL z podporovaného hostu
- Nebo naklonuj repozitář lokálně a otevři složku místo URL
- Pro vlastní Git server: naklonuj manuálně pomocí `git clone` a pak otevři složku

### Horizontální scrollbar se nezmenší po zúžení sloupců

- **OPRAVENO v aktuální verzi**
- Scrollregion se nyní správně aktualizuje při změně šířky sloupců

### Chyby v log souboru

Pokud vidíš warnings v `gitvisualizer.log`:

- **"Failed to..."** warnings jsou normální pro některé operace (např. remote větve u lokálního repo)
- **ERROR** zprávy indikují skutečný problém - nahlásit jako issue
- Log file pomáhá při reportování bugů
