BRANCH_COLORS = {
    'master': '#007acc',
    'main': '#007acc',
    'develop': '#ffc107',
    'dev': '#ffc107',
}

FEATURE_COLOR = '#28a745'
HOTFIX_COLOR = '#dc3545'

DEFAULT_COLORS = [
    '#007acc', '#28a745', '#dc3545', '#ffc107', '#6f42c1',
    '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8'
]


def get_branch_color(branch_name: str, used_colors: set) -> str:
    branch_lower = branch_name.lower()

    if branch_lower in BRANCH_COLORS:
        return BRANCH_COLORS[branch_lower]

    if 'feature' in branch_lower or 'feat' in branch_lower:
        return FEATURE_COLOR

    if 'hotfix' in branch_lower or 'fix' in branch_lower:
        return HOTFIX_COLOR

    for color in DEFAULT_COLORS:
        if color not in used_colors:
            used_colors.add(color)
            return color

    return DEFAULT_COLORS[len(used_colors) % len(DEFAULT_COLORS)]