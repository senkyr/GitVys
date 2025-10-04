"""
Konstanty pro GitVisualizer aplikaci
"""

# Layout constants - visualization/layout.py
COMMIT_VERTICAL_SPACING = 30  # Vertikální rozestup mezi commity (px)
COMMIT_START_Y = 50  # Y offset prvního commitu od vrcholu (px)
COMMIT_START_X = 160  # X pozice pro první větev (lane 0) (px)
BRANCH_LANE_SPACING = 20  # Horizontální rozestup mezi větvemi/lanes (px)

# Repository constants - repo/repository.py
MESSAGE_MAX_LENGTH = 50  # Maximální délka commit zprávy pro zkrácení (znaky)
AUTHOR_NAME_MAX_LENGTH = 15  # Maximální délka jména autora pro zkrácení (znaky)
DESCRIPTION_MAX_LENGTH = 80  # Maximální délka description pro zkrácení (znaky)

# Color constants - visualization/colors.py
COLOR_HUE_TOLERANCE = 15  # Tolerance pro detekci kolize barev (stupně HSL)
COLOR_SATURATION = 80  # Sytost barev pro větve (%)
COLOR_LIGHTNESS = 50  # Světlost barev pro větve (%)

# Graph drawer constants - visualization/graph_drawer.py
NODE_RADIUS = 8  # Poloměr kruhů commit nodes (px)
LINE_WIDTH = 2  # Šířka čar spojujících commity (px)
FONT_SIZE = 10  # Velikost fontu pro text (pt)
SEPARATOR_HEIGHT = 25  # Výška separátorů mezi sloupci (px)
HEADER_HEIGHT = 25  # Výška záhlaví/separátoru (px)
BASE_MARGIN = 25  # Základní margin (stejný jako výška záhlaví) (px)

# Column width constants
MIN_COLUMN_WIDTH_TEXT = 50  # Minimální šířka textového sloupce (px)
MIN_COLUMN_WIDTH_GRAPH = 100  # Minimální šířka grafového sloupce (px)

# UI constants - gui/main_window.py
DEFAULT_WINDOW_WIDTH = 600  # Výchozí šířka okna (px)
DEFAULT_WINDOW_HEIGHT = 400  # Výchozí výška okna (px)
WINDOW_WIDTH_BUFFER = 40  # Buffer pro výpočet optimální šířky okna (px)
