# Návod pro vytvoření .exe souboru

## Rychlý způsob (doporučený)

1. **Otevři složku projektu** v Explorer
2. **Poklikej na `build\build-exe.bat`**
3. **Počkej** až se build dokončí (1-2 minuty)
4. **Hotovo!** - nový .exe je v složce `dist\GitVisualizer.exe`

## Ruční způsob (pro pokročilé)

1. Otevři terminál/příkazovou řádku v root složce projektu
2. Spusť: `python build/build.py`
3. Počkaj až se build dokončí
4. Výsledek je v `dist\GitVisualizer.exe`

## Co build script dělá

- ✅ Automaticky nainstaluje PyInstaller 6.x+ (pokud chybí nebo je starý)
- ✅ Vymaže předchozí buildy
- ✅ Vytvoří optimalizovaný .exe soubor (~14MB s plným GUI supportem)
- ✅ Zahrnuje všechny tkinter, Git a PIL moduly
- ✅ Otestuje že se .exe spouští
- ✅ Oznámí kde najdeš výsledek

## Řešení problémů

### "Python není rozpoznán jako příkaz"

- Ujisti se, že máš Python nainstalovaný a přidaný do PATH

### Build selže kvůli chybějícím modulům

- Spusť: `pip install -r requirements.txt`
- Pak zkus build znovu

### .exe se nespustí s chybou "ModuleNotFoundError: No module named 'tkinter'"

- **OPRAVENO** - build script teď automaticky:
  - Kontroluje PyInstaller verzi a aktualizuje na 6.x+ pro správný tkinter support
  - Zahrnuje všechny potřebné tkinter moduly a hooks
  - Používá správnou verzi Pythonu (3.12+)

### .exe se nespustí z jiných důvodů

- Zkontroluj že máš všechny dependencies: `pip install -r requirements.txt`
- Zkus spustit `python src/main.py` - pokud to nefunguje, oprav chyby a pak buildni znovu

### Build selže s "Permission denied" chybou

- Zavři všechny běžící instance GitVisualizer.exe
- Smaž složku `dist/` ručně pokud potřeba
- Zkus build znovu

## Tip: Při vývoji

**Pokaždé když změníš kód a chceš nový .exe:**

1. Poklikej na `build\build-exe.bat`
2. Hotovo!

Je to tak jednoduché! 🚀
