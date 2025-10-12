"""Color utilities for visualization components."""

import colorsys
from utils.logging_config import get_logger

logger = get_logger(__name__)


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Převede HSL hodnoty na hex barvu."""
    import colorsys

    # Převést na RGB (0-1 rozsah)
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)

    # Převést na 0-255 rozsah a hex
    r = int(r * 255)
    g = int(g * 255)
    b = int(b * 255)

    return f"#{r:02x}{g:02x}{b:02x}"


def get_semantic_hue(branch_name: str) -> float:
    """Vrací sémantický HSL hue pro známé názvy/prefixy větví."""
    # Hlavní větve (všechny posunuty o -30° pro hezčí azurovou main/master)
    if branch_name in ["main", "master"]:
        return 210  # Azurová modrá (240° - 30°)
    elif branch_name == "develop":
        return 150  # Světle zelená (180° - 30°)
    elif branch_name == "staging":
        return 240  # Modrá (270° - 30°)

    # Prefixové větve (všechny posunuty o -30°)
    elif branch_name.startswith("feature/"):
        return 90   # Žluto-zelená (120° - 30°)
    elif branch_name.startswith("hotfix/"):
        return 330  # Růžová (0° - 30° + 360°)
    elif branch_name.startswith("bugfix/"):
        return 0    # Červená (30° - 30°)
    elif branch_name.startswith("release/"):
        return 270  # Fialová (300° - 30°)

    return None  # Žádná sémantika


def is_semantic_hue_conflict(hue: float, tolerance: float = 15) -> bool:
    """Zkontroluje zda hue koliduje se sémantickými barvami."""
    semantic_hues = [210, 150, 240, 90, 330, 0, 270]

    for semantic_hue in semantic_hues:
        # Vypočítat nejkratší vzdálenost na kruhu (0-360°)
        diff = abs(hue - semantic_hue)
        if diff > 180:
            diff = 360 - diff

        if diff <= tolerance:
            return True

    return False


def get_branch_color(branch_name: str, used_colors: set) -> str:
    """
    Generuje barvu pro větev pomocí sémantického mapování + HSL algoritmu.
    Priorita: sémantické barvy → sekvenční procházka (přeskakuje kolize).
    """
    # Normalizovat název větve pro sémantické mapování
    normalized_name = normalize_branch_name(branch_name)

    # Zkusit sémantickou barvu pro normalizovaný název
    semantic_hue = get_semantic_hue(normalized_name)
    if semantic_hue is not None:
        color = hsl_to_hex(semantic_hue, 80, 50)
        # Sémantické barvy ignorují used_colors check - mohou být sdílené
        # mezi lokální/remote variantami (např. feature/login a origin/feature/login)
        used_colors.add(color)
        return color

    # Pro ostatní větve - použít normalizovaný název pro jedinečnost
    # Takže origin/custom-branch a custom-branch budou mít stejnou barvu
    normalized_key = normalized_name

    # Sekvenční procházka - počet založený na počtu již přiřazených nesémantických větví
    non_semantic_count = len([key for key in used_colors if not _is_semantic_color(key)])

    branch_index = non_semantic_count  # Začít od počtu již přiřazených nesémantických barev
    while True:
        # Vypočítat HSL hodnoty
        base_hue = (branch_index % 12) * 30  # 12 základních pozic po 30°
        rotation = (branch_index // 12) * 13  # Pootočení o 13° pro každou iteraci
        final_hue = (base_hue + rotation) % 360

        color = hsl_to_hex(final_hue, 80, 50)

        # Dvojí kontrola kolizí:
        # 1. Kolize se sémantickými barvami
        # 2. Barva už není použita
        semantic_conflict = is_semantic_hue_conflict(final_hue)
        already_used = color in used_colors

        if not semantic_conflict and not already_used:
            used_colors.add(color)
            return color

        # Pokud kolize, zkusit další index
        branch_index += 1

        # Bezpečnostní pojistka
        if branch_index > 1000:
            # Fallback - prostě použij vypočítanou barvu
            color = hsl_to_hex(final_hue, 80, 50)
            used_colors.add(color)
            return color


def _is_semantic_color(color: str) -> bool:
    """Zkontroluje zda je barva sémantická (jedna ze 7 pevných sémantických barev)."""
    semantic_colors = [
        hsl_to_hex(210, 80, 50),  # main/master - azurová modrá
        hsl_to_hex(150, 80, 50),  # develop - světle zelená
        hsl_to_hex(240, 80, 50),  # staging - modrá
        hsl_to_hex(90, 80, 50),   # feature - žluto-zelená
        hsl_to_hex(330, 80, 50),  # hotfix - růžová
        hsl_to_hex(0, 80, 50),    # bugfix - červená
        hsl_to_hex(270, 80, 50),  # release - fialová
    ]
    return color in semantic_colors


def normalize_branch_name(branch_name: str) -> str:
    """Normalizuje název větve pro sémantické mapování (odstraní remote prefixy)."""
    if branch_name.startswith('origin/'):
        return branch_name[7:]  # Odstranit "origin/"
    return branch_name


def make_color_pale(color: str, blend_type: str = "remote") -> str:
    """Creates paler version of color using HSL manipulation.

    Args:
        color: Color to make pale (hex format like '#FF0000' or named color)
        blend_type: Type of blending - "remote" for mild fading, "merge" for strong fading

    Returns:
        Paler version of color in hex format

    Examples:
        >>> make_color_pale('#FF0000', 'remote')
        '#ffb3b3'
        >>> make_color_pale('#0000FF', 'merge')
        '#b3b3ff'
    """
    if not color or color == 'unknown':
        return '#E0E0E0'

    if color.startswith('#'):
        try:
            # Convert hex to RGB
            hex_color = color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0

                # Convert RGB to HSL
                h, l, s = colorsys.rgb_to_hls(r, g, b)

                # Apply fading according to type
                if blend_type == "remote":
                    # Remote: milder fading to preserve distinguishability
                    s = s * 0.8  # Reduce saturation to 80% of original (65% from 80%)
                    l = min(0.9, l + 0.15)  # Increase lightness by 15% (approx 65%)
                elif blend_type == "merge":
                    # Merge: strong fading - least saturated of all
                    s = s * 0.6  # Reduce saturation to 60% of original (less than remote)
                    l = min(0.85, l + 0.20)  # Significantly increase lightness by 20%
                else:
                    # Fallback to remote behavior
                    s = s * 0.8
                    l = min(0.9, l + 0.15)

                # Convert back to RGB
                r, g, b = colorsys.hls_to_rgb(h, l, s)

                # Convert to hex
                r = int(r * 255)
                g = int(g * 255)
                b = int(b * 255)

                return f'#{r:02x}{g:02x}{b:02x}'
        except Exception as e:
            logger.warning(f"Failed to make color {color} pale: {e}")
            pass

    # For named colors - simple mappings
    color_map = {
        'red': '#FFB3B3',
        'blue': '#B3B3FF',
        'green': '#B3FFB3',
        'orange': '#FFE0B3',
        'purple': '#E0B3FF',
        'brown': '#D9C6B3',
        'pink': '#FFB3E0',
        'gray': '#D9D9D9',
        'cyan': '#B3FFFF',
        'yellow': '#FFFFE0'
    }

    return color_map.get(color.lower(), '#E0E0E0')
