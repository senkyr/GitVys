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
2. Přetáhni složku s Git repozitářem do aplikace nebo klikni na "Procházet..."
3. Aplikace automaticky načte a zobrazí historii commitů

## Testování

Aplikaci můžeš otestovat s jakýmkoliv Git repozitářem, včetně tohoto projektu.

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
