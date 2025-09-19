DEFAULT_COLORS = [
    '#007acc', '#28a745', '#dc3545', '#ffc107', '#6f42c1',
    '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8',
    '#ff6b35', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57',
    '#ff9ff3', '#54a0ff', '#5f27cd', '#00d2d3', '#ff9f43',
    '#a55eea', '#26de81', '#fc5c65', '#fd79a8', '#fdcb6e',
    '#6c5ce7', '#74b9ff', '#00b894', '#e17055', '#ddd'
]


def get_branch_color(branch_name: str, used_colors: set) -> str:
    # Jednoduchý sekvenční výběr - každá větev dostane unikátní barvu
    for color in DEFAULT_COLORS:
        if color not in used_colors:
            used_colors.add(color)
            return color

    # Pokud se vyčerpaly všechny barvy, začni znovu, ale generuj lehce odlišné odstíny
    base_color = DEFAULT_COLORS[len(used_colors) % len(DEFAULT_COLORS)]

    # Generuj mírně odlišný odstín přidáním/odebráním hodnot RGB
    import random
    random.seed(len(used_colors))  # Deterministické generování

    # Převést hex na RGB
    r = int(base_color[1:3], 16)
    g = int(base_color[3:5], 16)
    b = int(base_color[5:7], 16)

    # Přidat malé náhodné variace
    r = max(0, min(255, r + random.randint(-30, 30)))
    g = max(0, min(255, g + random.randint(-30, 30)))
    b = max(0, min(255, b + random.randint(-30, 30)))

    new_color = f"#{r:02x}{g:02x}{b:02x}"
    used_colors.add(new_color)
    return new_color