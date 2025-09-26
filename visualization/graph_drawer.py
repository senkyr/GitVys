import tkinter as tk
from typing import List, Dict, Tuple
import math
from utils.data_structures import Commit


class GraphDrawer:
    def __init__(self):
        self.node_radius = 8
        self.line_width = 2
        self.font_size = 10
        self.column_widths = {}
        self.tooltip = None
        self.branch_lanes = {}  # Uložit lanes pro výpočet pozice tabulky
        self.scaling_factor = 1.0
        self.max_description_length = 50  # Základní délka

        # Interaktivní změna šířky sloupců
        self.column_separators = {}  # pozice separátorů {column_name: x_position}
        self.dragging_separator = None  # název sloupce jehož separátor se táhne
        self.drag_start_x = 0

        # Šířka grafického sloupce (Branch/Commit)
        self.graph_column_width = None  # Bude vypočítána dynamicky

        self.curve_intensity = 0.8  # Intenzita zakřivení pro rounded corners (0-1)

        # Layout konstanty - jednotný systém marginů
        self.HEADER_HEIGHT = 25  # Výška záhlaví/separátoru
        self.BASE_MARGIN = 25    # Základní margin (stejný jako výška záhlaví)
        self.BRANCH_SPACING = 20 # Vzdálenost mezi větvemi (lanes)

        # Starý název pro zpětnou kompatibilitu
        self.separator_height = self.HEADER_HEIGHT
        self.user_column_widths = {}  # uživatelem nastavené šířky

    def _create_circle_polygon(self, x: int, y: int, radius: int, num_points: int = 20) -> List[float]:
        """Vytvoří body pro kruhový polygon (pro stipple support na Windows)."""
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            points.extend([px, py])
        return points

    def reset(self):
        """Resetuje stav GraphDrawer pro nový repozitář."""
        # Reset šířek sloupců - uživatelem nastavené i vypočítané
        self.graph_column_width = None
        self.user_column_widths = {}
        self.column_widths = {}

        # Reset cached hodnot pro výpočet šířek
        self.flag_width = None
        self.required_tag_space = None

        # Reset interaktivních funkcí
        self.dragging_separator = None
        self.drag_start_x = 0
        self.column_separators = {}

    def draw_graph(self, canvas: tk.Canvas, commits: List[Commit]):
        if not commits:
            return

        # Uložit commity pro případné překreslení
        self._current_commits = commits

        # Detekovat DPI škálování
        self._detect_scaling_factor(canvas)

        # Upravit description_short podle škálování
        self._adjust_descriptions_for_scaling(commits)

        # Uložit informace o lanes pro výpočet pozice tabulky
        self._update_branch_lanes(commits)
        self._calculate_column_widths(canvas, commits)
        self._calculate_flag_width(canvas, commits)
        self._calculate_required_tag_space(canvas, commits)
        self._draw_connections(canvas, commits)
        self._draw_commits(canvas, commits)
        self._draw_tags(canvas, commits)
        self._draw_column_separators(canvas)

    def _draw_connections(self, canvas: tk.Canvas, commits: List[Commit]):
        commit_positions = {commit.hash: (commit.x, commit.y) for commit in commits}
        commit_info = {commit.hash: commit for commit in commits}

        for commit in commits:
            if commit.parents:
                child_pos = commit_positions.get(commit.hash)
                if child_pos:
                    for parent_hash in commit.parents:
                        parent_pos = commit_positions.get(parent_hash)
                        if parent_pos:
                            # Použít remote status a uncommitted status dítěte pro kreslení spojnice
                            # Start from parent, draw to child
                            is_uncommitted = getattr(commit, 'is_uncommitted', False)
                            self._draw_line(canvas, parent_pos, child_pos, commit.branch_color, commit.is_remote, is_uncommitted)

    def _draw_line(self, canvas: tk.Canvas, start: Tuple[int, int], end: Tuple[int, int], color: str, is_remote: bool = False, is_uncommitted: bool = False):
        start_x, start_y = start
        end_x, end_y = end

        # Určit barvu a stipple pattern pro spojnice
        if is_uncommitted:
            line_color = color  # Plná barva větve pro WIP commity
            stipple_pattern = 'gray50'  # Stejné šrafování jako WIP kroužek
        elif is_remote:
            line_color = self._make_color_pale(color)  # Bledší barva pro remote
            stipple_pattern = None
        else:
            line_color = color  # Normální barva pro lokální commity
            stipple_pattern = None

        # Pokud jsou commity v různých sloupcích (větvení), kreslíme hladkou křivku
        if start_x != end_x:
            self._draw_bezier_curve(canvas, start_x, start_y, end_x, end_y, line_color, stipple_pattern)
        else:
            # Přímá svislá linka pro commity ve stejném sloupci
            line_kwargs = {
                'fill': line_color,
                'width': self.line_width
            }
            if stipple_pattern:
                line_kwargs['stipple'] = stipple_pattern

            canvas.create_line(start_x, start_y, end_x, end_y, **line_kwargs)

    def _draw_bezier_curve(self, canvas: tk.Canvas, start_x: int, start_y: int, end_x: int, end_y: int, color: str, stipple_pattern=None):
        """Vykreslí hladké L-shaped spojení se zaoblenými rohy"""

        # Vzdálenosti
        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)

        # Rádius zaoblení - malý, aby křivka zůstala v bounds
        radius = min(dx, dy, 20) * self.curve_intensity  # Max 20px radius
        radius = max(3, min(radius, 15))  # Limit mezi 3-15px

        # Corner point (kde se původně lámala čára)
        corner_x = end_x
        corner_y = start_y

        # Rozdělíme na 3 části: straight horizontal + rounded corner + straight vertical

        # 1) Horizontal line až k corner-radius
        if dx > radius:
            line_kwargs = {
                'fill': color,
                'width': self.line_width
            }
            if stipple_pattern:
                line_kwargs['stipple'] = stipple_pattern
            canvas.create_line(
                start_x, start_y,
                corner_x - radius, corner_y,
                **line_kwargs
            )

        # 2) Rounded corner (malá kvadratická Bezier křivka)
        if dx > radius and dy > radius:
            # Rounded corner pomocí arc místo Bezier (správný tvar)
            corner_points = self._calculate_rounded_corner_arc(
                corner_x - radius, corner_y,    # start point
                corner_x, corner_y - radius,    # end point (NAHORU = minus radius)
                corner_x, corner_y,             # corner point
                radius
            )

            if len(corner_points) > 2:
                corner_kwargs = {
                    'fill': color,
                    'width': self.line_width,
                    'smooth': True
                }
                if stipple_pattern:
                    corner_kwargs['stipple'] = stipple_pattern
                canvas.create_line(
                    corner_points,
                    **corner_kwargs
                )

        # 3) Vertical line od corner-radius až k cíli (NAHORU = minus radius)
        if dy > radius:
            line_kwargs = {
                'fill': color,
                'width': self.line_width
            }
            if stipple_pattern:
                line_kwargs['stipple'] = stipple_pattern
            canvas.create_line(
                corner_x, corner_y - radius,
                end_x, end_y,
                **line_kwargs
            )

        # Pro velmi krátké vzdálenosti - fallback na simple line
        if dx <= radius or dy <= radius:
            line_kwargs = {
                'fill': color,
                'width': self.line_width
            }
            if stipple_pattern:
                line_kwargs['stipple'] = stipple_pattern
            canvas.create_line(
                start_x, start_y, end_x, end_y,
                **line_kwargs
            )

    def _calculate_rounded_corner_arc(self, start_x: int, start_y: int, end_x: int, end_y: int, corner_x: int, corner_y: int, radius: int):
        """Vypočítá body pro zaoblený roh pomocí circular arc - správný tvar pro L-shape"""
        import math
        points = []
        steps = 8

        # Pro L-shaped corner: arc v pravém HORNÍM kvadrantu (jde NAHORU!)
        # Center arc je POSUNUTÝ od corner: (corner_x - radius, corner_y - radius)
        arc_center_x = corner_x - radius
        arc_center_y = corner_y - radius

        for i in range(steps + 1):
            # Arc od 0° do 90° (od horizontal doprava k vertical NAHORU)
            angle = (i / steps) * (math.pi / 2)

            # Vypočítat bod na kružnici relative k arc centru
            x = arc_center_x + radius * math.cos(angle)
            y = arc_center_y + radius * math.sin(angle)

            points.extend([int(x), int(y)])

        return points


    def _calculate_column_widths(self, canvas: tk.Canvas, commits: List[Commit]):
        # Použít standardní font - škálování řešíme délkou textu, ne velikostí fontu
        font = ('Arial', self.font_size)

        max_message_width = 0
        max_description_width = 0
        max_author_width = 0
        max_email_width = 0
        max_date_width = 0

        # Definovat maximální šířky podle DPI škálování
        if self.scaling_factor <= 1.0:
            max_allowed_message_width = 800  # Zvětšeno pro lepší využití prostoru
            max_allowed_author_width = 250
            max_allowed_email_width = 300
        elif self.scaling_factor <= 1.25:
            max_allowed_message_width = 700  # 125% škálování
            max_allowed_author_width = 220
            max_allowed_email_width = 280
        elif self.scaling_factor <= 1.5:
            max_allowed_message_width = 600  # 150% škálování
            max_allowed_author_width = 200
            max_allowed_email_width = 250
        else:
            max_allowed_message_width = 500  # 200%+ škálování
            max_allowed_author_width = 180
            max_allowed_email_width = 220

        for commit in commits:
            # Kombinovaná šířka message + description s mezerou
            message_width = canvas.tk.call("font", "measure", font, commit.message)
            if commit.description_short:
                desc_width = canvas.tk.call("font", "measure", font, commit.description_short)
                combined_width = message_width + 20 + desc_width  # 20px mezera
            else:
                combined_width = message_width

            # Omezit šířku podle škálovacího faktoru
            combined_width = min(combined_width, max_allowed_message_width)
            max_message_width = max(max_message_width, combined_width)

            author_width = canvas.tk.call("font", "measure", font, commit.author)
            author_width = min(author_width, max_allowed_author_width)
            max_author_width = max(max_author_width, author_width)

            email_width = canvas.tk.call("font", "measure", font, commit.author_email)
            email_width = min(email_width, max_allowed_email_width)
            max_email_width = max(max_email_width, email_width)

            date_width = canvas.tk.call("font", "measure", font, commit.date_short)
            max_date_width = max(max_date_width, date_width)

        # Použít uživatelem nastavené šířky nebo vypočítané
        self.column_widths = {
            'message': self.user_column_widths.get('message', max_message_width + 20),
            'author': self.user_column_widths.get('author', max_author_width + 20),
            'email': self.user_column_widths.get('email', max_email_width + 20),
            'date': self.user_column_widths.get('date', max_date_width + 20)
        }

    def _calculate_flag_width(self, canvas: tk.Canvas, commits: List[Commit]):
        """Vypočítá jednotnou šířku vlaječek podle nejdelšího názvu větve s místem pro symboly."""
        font = ('Arial', 8, 'bold')  # Font používaný pro vlaječky (aktualizován na správnou velikost)
        max_text_width = 0

        # Najít všechny unikátní názvy větví pro výpočet šířky
        unique_branches = set()
        for commit in commits:
            if commit.branch == 'unknown':
                continue  # Přeskočit unknown větve

            branch_name = commit.branch
            is_remote = commit.is_remote

            # Upravit název větve pro remote větve
            display_name = branch_name
            if is_remote and branch_name.startswith('origin/'):
                display_name = branch_name[7:]  # Odstranit "origin/"

            unique_branches.add(display_name)

        # Najít nejdelší název větve
        for display_name in unique_branches:
            # Změřit šířku čistého textu názvu větve
            try:
                text_width = canvas.tk.call("font", "measure", font, display_name)
                max_text_width = max(max_text_width, text_width)
            except:
                # Fallback pro případ chyby
                max_text_width = max(max_text_width, len(display_name) * 6)

        # Výpočet celkové šířky vlaječky:
        # - Symboly na krajích: 12px (vlevo) + 12px (vpravo) = 24px
        # - Padding mezi symboly a textem: 12px (vlevo) + 12px (vpravo) = 24px (zvětšeno pro lepší rozestupy)
        # - Šířka textu: max_text_width
        symbol_space = 24  # Místo pro symboly na krajích
        padding = 24       # Padding mezi symboly a textem (zvětšeno z 16 na 24)

        self.flag_width = symbol_space + padding + max_text_width

        # Minimální šířka 90px (aby se vešly symboly s větším paddingem), maximální rozumná šířka 160px
        self.flag_width = max(90, min(self.flag_width, 160))

    def _calculate_required_tag_space(self, canvas: tk.Canvas, commits: List[Commit]):
        """Odhadne prostor potřebný pro tagy (zjednodušená verze - nyní počítáme dynamicky)."""
        # Fixní odhad prostoru pro tagy - skutečný prostor se počítá dynamicky v _draw_tags
        # Tento odhad slouží pouze pro výpočet celkové šířky grafického sloupce
        flag_width = getattr(self, 'flag_width', 80)
        self.required_tag_space = flag_width + self.BASE_MARGIN

    def _calculate_graph_column_width(self) -> int:
        """Vypočítá šířku grafického sloupce (Branch/Commit)."""
        if self.graph_column_width is not None:
            # Použít uživatelem nastavenou šířku
            return self.graph_column_width

        # Vypočítat automatickou šířku na základě obsahu
        flag_width = getattr(self, 'flag_width', 80)
        required_tag_space = getattr(self, 'required_tag_space', flag_width + self.BASE_MARGIN)

        # Šířka: margin + vlaječky + margin + tagy
        auto_width = self.BASE_MARGIN + flag_width + self.BASE_MARGIN + required_tag_space
        return auto_width

    def _draw_commits(self, canvas: tk.Canvas, commits: List[Commit]):
        # Použít standardní font - škálování řešíme délkou textu, ne velikostí fontu
        font = ('Arial', self.font_size)

        # Zkontrolovat, zda máme nějaké branch head commity
        has_branch_heads = any(commit.is_branch_head for commit in commits)

        if has_branch_heads:
            # Nová logika - použít branch head commity
            branch_head_commits = {}  # branch_name -> {'local': commit, 'remote': commit, 'both': commit}

            for commit in commits:
                if commit.is_branch_head:
                    clean_branch_name = commit.branch
                    if commit.branch.startswith('origin/'):
                        clean_branch_name = commit.branch[7:]  # Odstranit "origin/"

                    if clean_branch_name not in branch_head_commits:
                        branch_head_commits[clean_branch_name] = {}

                    branch_head_commits[clean_branch_name][commit.branch_head_type] = commit
        else:
            # Fallback logika - použít první commit každé větve (původní chování)
            drawn_branch_flags = set()
            # Najít posledního commitu každé větve (podle času, ale ignorovat WIP commity)
            last_commits_by_branch = {}
            for commit in commits:
                # Ignorovat WIP commity při hledání posledního skutečného commitu
                if getattr(commit, 'is_uncommitted', False):
                    continue

                if commit.branch not in last_commits_by_branch:
                    last_commits_by_branch[commit.branch] = commit
                elif commit.date > last_commits_by_branch[commit.branch].date:
                    last_commits_by_branch[commit.branch] = commit

        for commit in commits:
            x, y = commit.x, commit.y

            # Vizuální rozlišení pro uncommitted změny, remote commity, nebo normální
            if getattr(commit, 'is_uncommitted', False):
                # WIP commity - šrafovaný polygon v barvě větve s černým obrysem
                fill_color = commit.branch_color
                outline_color = 'black'
                stipple_pattern = 'gray50'  # 50% šrafování pro indikaci nehotovosti

                # Vytvořit kruhový polygon místo ovals (stipple nefunguje s ovals na Windows)
                points = self._create_circle_polygon(x, y, self.node_radius)
                canvas.create_polygon(
                    points,
                    fill=fill_color,
                    outline=outline_color,
                    width=1,
                    stipple=stipple_pattern
                )
            elif commit.is_remote:
                # Bledší verze branch_color (50% transparence simulace)
                fill_color = self._make_color_pale(commit.branch_color)
                outline_color = '#CCCCCC'  # Světlejší obrys
                canvas.create_oval(
                    x - self.node_radius, y - self.node_radius,
                    x + self.node_radius, y + self.node_radius,
                    fill=fill_color,
                    outline=outline_color,
                    width=1
                )
            else:
                # Normální commity
                fill_color = commit.branch_color
                outline_color = 'black'
                canvas.create_oval(
                    x - self.node_radius, y - self.node_radius,
                    x + self.node_radius, y + self.node_radius,
                    fill=fill_color,
                    outline=outline_color,
                    width=1
                )

            # Zobrazit vlaječku podle použitého režimu
            if has_branch_heads:
                # Nová logika - zobrazit vlaječku pro branch head commity
                if commit.is_branch_head and commit.branch != 'unknown':
                    clean_branch_name = commit.branch
                    if commit.branch.startswith('origin/'):
                        clean_branch_name = commit.branch[7:]  # Odstranit "origin/"

                    flag_color = self._make_color_pale(commit.branch_color) if commit.is_remote else commit.branch_color

                    # Určit které symboly zobrazit podle branch_head_type
                    if commit.branch_head_type == "both":
                        # Zobrazit oba symboly (jako doteď)
                        branch_avail = "both"
                    elif commit.branch_head_type == "local":
                        # Jen symbol počítače
                        branch_avail = "local_only"
                    elif commit.branch_head_type == "remote":
                        # Jen symbol obláčku
                        branch_avail = "remote_only"
                    else:
                        branch_avail = commit.branch_availability

                    self._draw_branch_flag(canvas, x, y, clean_branch_name, flag_color, commit.is_remote, branch_avail)

                    # Vykreslit connection line k vlaječce
                    connection_color = self._make_color_pale(commit.branch_color) if commit.is_remote else commit.branch_color
                    self._draw_flag_connection(canvas, x, y, connection_color)
            else:
                # Fallback logika - původní chování (ale ne pro WIP commity)
                if (commit.branch != 'unknown' and
                    commit.branch not in drawn_branch_flags and
                    not getattr(commit, 'is_uncommitted', False)):
                    flag_color = self._make_color_pale(commit.branch_color) if commit.is_remote else commit.branch_color
                    self._draw_branch_flag(canvas, x, y, commit.branch, flag_color, commit.is_remote, commit.branch_availability)
                    drawn_branch_flags.add(commit.branch)

                # Pokud je to posledný commit větve, nakreslit horizontální spojnici k vlaječce (kromě 'unknown' a WIP)
                if (commit.branch != 'unknown' and
                    commit.branch in last_commits_by_branch and
                    last_commits_by_branch[commit.branch] == commit and
                    not getattr(commit, 'is_uncommitted', False)):
                    connection_color = self._make_color_pale(commit.branch_color) if commit.is_remote else commit.branch_color
                    self._draw_flag_connection(canvas, x, y, connection_color)

            # Pevná pozice pro začátek "tabulky" - za všemi větvemi
            table_start_x = self._get_table_start_position()

            # Pevné pozice pro tabulkové sloupce
            text_x = table_start_x

            # Vytvořit kombinovaný text message + description
            if commit.description_short:
                # Určit barvu textu podle typu commitu
                if getattr(commit, 'is_uncommitted', False):
                    message_color = '#555555'  # Tmavě šedá pro WIP commity
                else:
                    message_color = 'black'  # Černá pro normální commity

                # Message v odpovídající barvě + description v šedé
                canvas.create_text(
                    text_x, y,
                    text=commit.message,
                    anchor='w',
                    font=font,
                    fill=message_color,
                    tags="commit_text"
                )

                # Změřit šířku message pro pozici description
                message_width = canvas.tk.call("font", "measure", font, commit.message)
                desc_x = text_x + message_width + 20  # 20px mezera pro lepší rozlišení

                # Vypočítat dostupný prostor pro description
                available_space = self.column_widths['message'] - message_width - 40  # 40px mezery (20 + 20)

                # Zkrátit description aby se vešel do dostupného prostoru
                description_to_display = self._truncate_text_to_width(
                    canvas, font, commit.description_short, available_space
                )

                # Vykreslit description v šedé s tooltip
                desc_item = canvas.create_text(
                    desc_x, y,
                    text=description_to_display,
                    anchor='w',
                    font=font,
                    fill='#666666',
                    tags=("commit_text", f"desc_{commit.hash}")
                )

                # Přidat event handlers pro tooltip pouze pokud má původní description více obsahu
                if commit.description and commit.description.strip() != commit.description_short:
                    canvas.tag_bind(f"desc_{commit.hash}", "<Enter>",
                        lambda e, desc=commit.description: self._show_tooltip(e, desc))
                    canvas.tag_bind(f"desc_{commit.hash}", "<Leave>",
                        lambda e: self._hide_tooltip())
            else:
                # Určit barvu textu podle typu commitu
                if getattr(commit, 'is_uncommitted', False):
                    message_color = '#555555'  # Tmavě šedá pro WIP commity
                else:
                    message_color = 'black'  # Černá pro normální commity

                # Jen message bez description
                canvas.create_text(
                    text_x, y,
                    text=commit.message,
                    anchor='w',
                    font=font,
                    fill=message_color,
                    tags="commit_text"
                )

            text_x += self.column_widths['message']

            # Author - zarovnaný na střed sloupce (pouze pro normální commity)
            if not getattr(commit, 'is_uncommitted', False):
                author_center_x = text_x + self.column_widths['author'] // 2
                canvas.create_text(
                    author_center_x, y,
                    text=commit.author,
                    anchor='center',
                    font=font,
                    fill='#333333',
                    tags="commit_text"
                )
            text_x += self.column_widths['author']

            # Email - zarovnaný na střed sloupce (pouze pro normální commity)
            if not getattr(commit, 'is_uncommitted', False):
                email_center_x = text_x + self.column_widths['email'] // 2
                canvas.create_text(
                    email_center_x, y,
                    text=commit.author_email,
                    anchor='center',
                    font=font,
                    fill='#666666',
                    tags="commit_text"
                )
            text_x += self.column_widths['email']

            # Date - zarovnaný na střed sloupce (pouze pro normální commity)
            if not getattr(commit, 'is_uncommitted', False):
                date_center_x = text_x + self.column_widths['date'] // 2
                canvas.create_text(
                    date_center_x, y,
                    text=commit.date_short,
                    anchor='center',
                    font=font,
                    fill='#666666',
                    tags="commit_text"
                )

    def _show_tooltip(self, event, description_text: str):
        """Zobrazí tooltip s kompletním description textem."""
        if not description_text or not description_text.strip():
            return

        self._hide_tooltip()

        # Vytvořit tooltip okno
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_attributes("-topmost", True)

        # Nastavit pozici tooltip okna
        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # Vytvořit label s textem
        label = tk.Label(
            self.tooltip,
            text=description_text,
            background="#ffffe0",
            foreground="black",
            font=('Arial', 9),
            wraplength=400,
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3
        )
        label.pack()

    def _hide_tooltip(self):
        """Skryje tooltip okno."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def _draw_branch_flag(self, canvas: tk.Canvas, x: int, y: int, branch_name: str, branch_color: str, is_remote: bool = False, branch_availability: str = "local_only"):
        """Vykreslí vlaječku s názvem větve a symboly dostupnosti v pevném levém sloupci."""
        # Použít vypočítanou šířku vlaječky
        flag_width = getattr(self, 'flag_width', 80)  # Fallback na 80 pokud nebyla vypočítána
        flag_height = 20

        # Pozice vlaječky - margin zleva stejný jako margin shora (BASE_MARGIN + polovina šířky vlaječky)
        flag_x = self.BASE_MARGIN + flag_width // 2
        flag_y = y

        # Bledší obrys pro remote větve
        outline_color = '#CCCCCC' if is_remote else 'black'

        # Vytvořit obdélník vlaječky
        canvas.create_rectangle(
            flag_x - flag_width // 2, flag_y - flag_height // 2,
            flag_x + flag_width // 2, flag_y + flag_height // 2,
            fill=branch_color,
            outline=outline_color,
            width=1
        )

        # Přidat text názvu větve - upravit pro remote větve
        display_name = branch_name
        if is_remote and branch_name.startswith('origin/'):
            # Zobrazit jen část po origin/ ale v jiné barvě
            display_name = branch_name[7:]  # Odstranit "origin/"

        # Určit, které symboly zobrazit podle dostupnosti větve
        has_local = branch_availability in ["local_only", "both"]
        has_remote = branch_availability in ["remote_only", "both"]

        local_symbol = "💻"  # Laptop pro lokální
        remote_symbol = "☁"  # Obrysový oblačk pro remote
        local_fallback = "PC"
        remote_fallback = "☁"

        emoji_font = ('Segoe UI Emoji', 10)  # Správný font pro emoji
        text_font = ('Arial', 8, 'bold')     # Font pro text
        text_color = '#E0E0E0' if is_remote else 'white'

        # Vždy vykreslit název větve na středu s černým obrysem
        # Nejdříve černý obrys - vykreslí text posunutý o 1px ve všech směrech
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            canvas.create_text(
                flag_x + dx, flag_y + dy,
                text=display_name,
                anchor='center',
                font=text_font,
                fill='black'
            )

        # Pak bílý text na vrch
        canvas.create_text(
            flag_x, flag_y,
            text=display_name,
            anchor='center',
            font=text_font,
            fill='white'
        )

        # Vykreslit remote symbol vlevo, pokud větev existuje remotely
        if has_remote:
            remote_x = flag_x - flag_width // 2 + 12  # 12px od levého okraje vlaječky (zvětšený padding)
            try:
                # Nejdříve černý obrys pro cloud symbol
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    canvas.create_text(
                        remote_x + dx, flag_y - 1 + dy,
                        text=remote_symbol,
                        anchor='center',
                        font=emoji_font,
                        fill='black'
                    )
                # Pak bílý symbol na vrch
                canvas.create_text(
                    remote_x, flag_y - 1,
                    text=remote_symbol,
                    anchor='center',
                    font=emoji_font,
                    fill='white'
                )
            except:
                # Fallback - také s obrysem
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    canvas.create_text(
                        remote_x + dx, flag_y - 1 + dy,
                        text=remote_fallback,
                        anchor='center',
                        font=text_font,
                        fill='black'
                    )
                canvas.create_text(
                    remote_x, flag_y - 1,
                    text=remote_fallback,
                    anchor='center',
                    font=text_font,
                    fill='white'
                )

        # Vykreslit local symbol vpravo, pokud větev existuje lokálně
        if has_local:
            local_x = flag_x + flag_width // 2 - 12  # 12px od pravého okraje vlaječky (zvětšený padding)
            try:
                # Nejdříve černý obrys pro laptop symbol
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    canvas.create_text(
                        local_x + dx, flag_y - 1 + dy,
                        text=local_symbol,
                        anchor='center',
                        font=emoji_font,
                        fill='black'
                    )
                # Pak bílý symbol na vrch
                canvas.create_text(
                    local_x, flag_y - 1,
                    text=local_symbol,
                    anchor='center',
                    font=emoji_font,
                    fill='white'
                )
            except:
                # Fallback - také s obrysem
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    canvas.create_text(
                        local_x + dx, flag_y - 1 + dy,
                        text=local_fallback,
                        anchor='center',
                        font=text_font,
                        fill='black'
                    )
                canvas.create_text(
                    local_x, flag_y - 1,
                    text=local_fallback,
                    anchor='center',
                    font=text_font,
                    fill='white'
                )

    def _calculate_horizontal_line_extent(self, commit: Commit, commits: List[Commit]) -> int:
        """Vypočítá nejdelší dosah horizontální spojnice od daného commitu."""
        max_extent = commit.x  # Výchozí pozice commitu

        # Vytvořit mapu hash -> commit pro rychlé vyhledání
        commit_map = {c.hash: c for c in commits}

        # Projít všechny child commity tohoto commitu
        for other_commit in commits:
            if commit.hash in other_commit.parents:
                # Tento commit je parent pro other_commit
                child_x = other_commit.x

                if child_x != commit.x:  # Pouze horizontální spojnice (větvení)
                    # Vypočítat dosah horizontální části L-shaped spojnice
                    dx = abs(child_x - commit.x)
                    dy = abs(other_commit.y - commit.y)

                    # Radius zaoblení (stejná logika jako v _draw_bezier_curve)
                    radius = min(dx, dy, 20) * self.curve_intensity
                    radius = max(3, min(radius, 15))

                    # Horizontální část končí na child_x - radius
                    # (corner_x = child_x, takže horizontální část končí na corner_x - radius)
                    horizontal_end = child_x - radius if dx > radius else child_x
                    max_extent = max(max_extent, horizontal_end)

        return max_extent

    def _draw_tags(self, canvas: tk.Canvas, commits: List[Commit]):
        """Vykreslí tag emoji a názvy pro commity s tagy."""
        emoji_font = ('Segoe UI Emoji', 10)  # Font pro emoji
        text_font = ('Arial', 8, 'bold')     # Font pro názvy tagů

        # Získat pozici začátku tabulky
        table_start_x = self._get_table_start_position()

        for commit in commits:
            if not commit.tags:
                continue

            x, y = commit.x, commit.y

            # Detekovat kolizi s horizontálními spojnicemi a dynamicky posunout tagy
            horizontal_line_extent = self._calculate_horizontal_line_extent(commit, commits)

            # Standardní pozice pro tagy
            standard_tag_x = x + self.node_radius + 15  # 15px mezera od kolečka

            # Pokud horizontální spojnice sahá za standardní pozici tagů, posunout tagy
            if horizontal_line_extent > standard_tag_x:
                # Posunout tagy za konec nejdelší horizontální spojnice + bezpečná mezera
                tag_x_start = horizontal_line_extent + 20  # 20px bezpečná mezera
            else:
                # Použít standardní pozici
                tag_x_start = standard_tag_x

            # Spočítat skutečný dostupný prostor pro tagy až do začátku tabulky
            available_tag_space = table_start_x - tag_x_start - self.BASE_MARGIN

            # Spočítat dostupný prostor pro jednotlivé tagy tohoto commitu
            tags_total_space = max(0, available_tag_space)  # Zajistit že není negativní
            tags_count = len(commit.tags)

            if tags_count > 0:
                # Rezervovat prostor pro emoji a mezery
                emoji_and_spacing_width = tags_count * 15 + (tags_count - 1) * 20  # emoji + mezery mezi tagy
                available_text_space = max(0, tags_total_space - emoji_and_spacing_width)

                # Minimální šířka pro text jednoho tagu (aby se vešly alespoň 3 znaky + ellipsis)
                min_text_width_per_tag = 30

                # Vypočítat maximální šířku textu na tag
                if available_text_space > 0 and tags_count > 0:
                    max_text_width_per_tag = max(min_text_width_per_tag, available_text_space // tags_count)
                else:
                    max_text_width_per_tag = min_text_width_per_tag

            current_x = tag_x_start
            for tag in commit.tags:
                # Vykreslit tag emoji
                emoji_x = current_x
                self._draw_tag_emoji(canvas, emoji_x, y, tag.is_remote, emoji_font)

                # Vykreslit název tagu vedle emoji s omezenou šířkou
                text_x = emoji_x + 15  # 15px mezera za emoji
                label_width = self._draw_tag_label(canvas, text_x, y, tag.name, tag.is_remote, text_font, max_text_width_per_tag)

                # Přidat tooltip pro anotované tagy
                if tag.message:
                    self._add_tag_tooltip(canvas, emoji_x, y, tag.message)

                # Přesunout pozici pro další tag
                current_x = text_x + label_width + 20  # 20px mezera mezi tagy

    def _draw_tag_emoji(self, canvas: tk.Canvas, x: int, y: int, is_remote: bool, font):
        """Vykreslí tag emoji 🏷️."""
        # Tag emoji
        tag_emoji = "🏷️"

        # Barevné rozlišení - pro remote tagy použít šedší barvu
        if is_remote:
            # Pro remote použít světlejší/menší emoji nebo jiný approach
            text_color = '#888888'  # Šedší barva
        else:
            text_color = 'black'    # Normální barva

        canvas.create_text(
            x, y - 1,
            text=tag_emoji,
            anchor='center',
            font=font,
            fill=text_color,
            tags="tag_emoji"
        )

    def _draw_tag_label(self, canvas: tk.Canvas, x: int, y: int, tag_name: str, is_remote: bool, font, available_width: int = None):
        """Vykreslí label s názvem tagu a vrátí šířku textu."""
        display_name = tag_name
        needs_tooltip = False

        # Zkrátit název pokud je příliš dlouhý
        if available_width and available_width > 0:
            full_width = canvas.tk.call("font", "measure", font, tag_name)
            if full_width > available_width:
                # Název je příliš dlouhý, zkrátit ho
                display_name = self._truncate_text_to_width(canvas, font, tag_name, available_width)
                needs_tooltip = True

        # Barvy textu - konzistentnější s emoji
        text_color = '#666666' if is_remote else '#333333'  # Šedší pro remote, tmavší pro lokální

        text_item = canvas.create_text(
            x, y,
            text=display_name,
            anchor='w',  # Zarovnat vlevo místo na střed
            font=font,
            fill=text_color,
            tags="tag_label"
        )

        # Přidat tooltip pokud byl text zkrácen
        if needs_tooltip:
            canvas.tag_bind(text_item, "<Enter>",
                lambda e, full_name=tag_name: self._show_tooltip(e, full_name))
            canvas.tag_bind(text_item, "<Leave>",
                lambda e: self._hide_tooltip())

        # Vrátit šířku zobrazovaného textu pro kalkulaci pozice dalšího tagu
        text_width = canvas.tk.call("font", "measure", font, display_name)
        return text_width

    def _add_tag_tooltip(self, canvas: tk.Canvas, x: int, y: int, message: str):
        """Přidá tooltip pro anotované tagy."""
        # Vytvořit neviditelnou oblast pro tooltip
        tooltip_area = canvas.create_oval(
            x - 12, y - 12, x + 12, y + 12,
            fill='',
            outline='',
            tags="tag_tooltip_area"
        )

        # Bindovat tooltip events
        canvas.tag_bind(tooltip_area, "<Enter>",
            lambda e, msg=message: self._show_tooltip(e, msg))
        canvas.tag_bind(tooltip_area, "<Leave>",
            lambda e: self._hide_tooltip())

    def _update_branch_lanes(self, commits: List[Commit]):
        """Aktualizuje informace o lanes pro výpočet pozice tabulky."""
        self.branch_lanes = {}
        flag_width = getattr(self, 'flag_width', 80)
        # Spočítat pozici prvního commitu (lane 0)
        first_commit_x = self.BASE_MARGIN + flag_width + self.BASE_MARGIN  # vlaječka + rozestup

        for commit in commits:
            branch_lane = (commit.x - first_commit_x) // self.BRANCH_SPACING
            self.branch_lanes[commit.branch] = branch_lane

    def _get_table_start_position(self) -> int:
        """Vrátí X pozici kde začíná tabulka (za všemi větvemi)."""
        # Použít celkovou šířku grafického sloupce
        graph_column_width = self._calculate_graph_column_width()
        return graph_column_width

    def _draw_flag_connection(self, canvas: tk.Canvas, commit_x: int, commit_y: int, branch_color: str):
        """Vykreslí horizontální spojnici od commitu k vlaječce."""
        # Použít vypočítanou šířku vlaječky
        flag_width = getattr(self, 'flag_width', 80)

        # Pozice vlaječky (konzistentní s _draw_branch_flag)
        flag_x = self.BASE_MARGIN + flag_width // 2

        # Horizontální linka od commitu k vlaječce
        canvas.create_line(
            flag_x + flag_width // 2 + 1, commit_y,  # Od pravého okraje vlaječky + 1px mimo orámování
            commit_x - self.node_radius, commit_y,  # K levému okraji commitu
            fill=branch_color,
            width=self.line_width
        )

    def _detect_scaling_factor(self, canvas: tk.Canvas):
        """Detekuje DPI škálovací faktor Windows."""
        try:
            dpi = canvas.winfo_fpixels('1i')
            self.scaling_factor = dpi / 96  # 96 je standardní DPI
        except:
            self.scaling_factor = 1.0  # Fallback

    def _adjust_descriptions_for_scaling(self, commits: List[Commit]):
        """Upraví délku description_short podle DPI škálování."""
        # Vypočítat cílovou délku podle škálování
        if self.scaling_factor <= 1.0:
            target_length = 120  # Zvětšeno pro lepší využití prostoru
        elif self.scaling_factor <= 1.25:
            target_length = 100  # 125% škálování
        elif self.scaling_factor <= 1.5:
            target_length = 80  # 150% škálování
        else:
            target_length = 60  # 200%+ škálování

        self.max_description_length = target_length

        # Upravit description_short pro všechny commity podle správné logiky
        for commit in commits:
            commit.description_short = self._truncate_description_for_dpi(commit.description, target_length)

    def _truncate_description_for_dpi(self, description: str, max_length: int) -> str:
        """Zkrátí description podle specifikace s ohledem na DPI škálování."""
        if not description:
            return ""

        # Vzít jen první řádek
        first_line = description.split('\n')[0].strip()
        has_more_lines = '\n' in description

        # Určit, jestli potřebujeme vynechávku
        needs_ellipsis = False

        if has_more_lines:
            # Pokud má více řádků, vždycky potřebujeme vynechávku
            needs_ellipsis = True
        elif len(first_line) > max_length:
            # Pokud je první řádek moc dlouhý
            needs_ellipsis = True
        elif first_line.endswith(':'):
            # Pokud řádek končí dvojtečkou, také potřebujeme vynechávku
            needs_ellipsis = True

        # Zkrátit text pokud je potřeba a přidat vynechávku
        if needs_ellipsis:
            if first_line.endswith(':'):
                # Pokud končí dvojtečkou, nahradit ji třemi tečkami
                # ale ověřit, že se vejde do limitu
                potential_result = first_line[:-1] + '...'
                if len(potential_result) > max_length:
                    # Zkrátit ještě více, aby se vešla vynechávka
                    first_line = first_line[:max_length-3] + '...'
                else:
                    first_line = potential_result
            elif len(first_line) > max_length:
                # Normální zkrácení
                first_line = first_line[:max_length-3] + '...'
            else:
                # Text se vejde, ale má více řádků
                first_line = first_line + '...'

        return first_line

    def _truncate_text_to_width(self, canvas: tk.Canvas, font, text: str, max_width: int) -> str:
        """Zkrátí text tak, aby se vešel do zadané šířky v pixelech."""
        if not text or max_width <= 0:
            return ""

        # Změřit šířku celého textu
        text_width = canvas.tk.call("font", "measure", font, text)

        if text_width <= max_width:
            return text

        # Text je moc široký, zkrátit ho
        ellipsis_width = canvas.tk.call("font", "measure", font, "...")
        available_width = max_width - ellipsis_width

        if available_width <= 0:
            return "..."

        # Binární vyhledávání pro nalezení správné délky
        left, right = 0, len(text)
        result = ""

        while left <= right:
            mid = (left + right) // 2
            test_text = text[:mid]
            test_width = canvas.tk.call("font", "measure", font, test_text)

            if test_width <= available_width:
                result = test_text
                left = mid + 1
            else:
                right = mid - 1

        return result + "..." if result else "..."

    def _make_color_pale(self, color: str) -> str:
        """Vytvoří bledší verzi barvy pro remote větve."""
        if not color or color == 'unknown':
            return '#E0E0E0'

        # Pokud je barva hexadecimální
        if color.startswith('#'):
            try:
                # Převést hex na RGB
                hex_color = color.lstrip('#')
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)

                    # Směsovat s bílou (50% transparence simulace)
                    r = int(r * 0.5 + 255 * 0.5)
                    g = int(g * 0.5 + 255 * 0.5)
                    b = int(b * 0.5 + 255 * 0.5)

                    return f'#{r:02x}{g:02x}{b:02x}'
            except:
                pass

        # Pro pojmenované barvy - jednoduchá mapování
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

    def _move_separators_to_scroll_position(self, canvas: tk.Canvas, new_y: float):
        """Přesune existující separátory na novou Y pozici při scrollování."""
        # Najít všechny objekty se separátory
        separator_items = canvas.find_withtag("column_separator")
        header_items = canvas.find_withtag("column_header")

        for item in separator_items + header_items:
            # Získat současné souřadnice
            coords = canvas.coords(item)
            if not coords:
                continue

            # Určit typ objektu podle tagů
            tags = canvas.gettags(item)

            if "column_bg_" in str(tags) or "graph_header_bg" in tags:
                # Pro pozadí záhlaví - obdélník
                canvas.coords(item, coords[0], new_y, coords[2], new_y + 25)
            elif "graph_header_text" in tags:
                # Pro text grafického záhlaví - centred vertically
                canvas.coords(item, coords[0], new_y + 12)
            elif "header_text_" in str(tags):
                # Pro text záhlaví - centred vertically
                canvas.coords(item, coords[0], new_y + 12)
            elif "column_header" in tags and len(coords) == 2:
                # Pro starý formát text záhlaví
                canvas.coords(item, coords[0], new_y + 12)
            elif len(coords) == 4:  # Obdélník nebo čára (pozadí separátoru, klikací oblast, nebo separátor)
                # Pro obdélník i čáru změnit Y1 a Y2
                canvas.coords(item, coords[0], new_y, coords[2], new_y + self.separator_height)

        # Zajistit správné vrstvení: pozadí záhlaví dolů, separátory nahoru, text záhlaví na vrch
        canvas.tag_lower("graph_header_bg")   # Pozadí grafického záhlaví dolů
        for column in ['message', 'author', 'email', 'date']:
            try:
                canvas.tag_lower(f"column_bg_{column}")  # Pozadí jednotlivých sloupců dolů
            except:
                pass
        canvas.tag_raise("column_separator")  # Separátory nahoru (aby byly klikatelné)
        canvas.tag_raise("column_header")      # Text záhlaví na vrch

    def _draw_column_separators(self, canvas: tk.Canvas):
        """Vykreslí interaktivní separátory sloupců na horním okraji."""
        table_start_x = self._get_table_start_position()

        # Záhlaví musí být vždy na vrchu viditelné oblasti (bez mezery)
        # canvasy(0) převede window souřadnici 0 na canvas souřadnici
        scroll_top = canvas.canvasy(0)
        separator_y = scroll_top  # záhlaví vždy na vrchu viditelné oblasti

        # Vždy vymazat staré separátory a popisky a vykreslit znovu
        canvas.delete("column_separator")
        canvas.delete("column_header")

        current_x = table_start_x

        # Názvy sloupců
        column_names = {
            'message': 'Message / Description',
            'author': 'Author',
            'email': 'Email',
            'date': 'Date'
        }

        columns = ['message', 'author', 'email', 'date']

        # NEJPRVE vykreslit separátor před prvním textovým sloupcem (Branch/Commit | Message)
        graph_separator_x = table_start_x

        # Pozadí separátoru pro grafický sloupec
        canvas.create_rectangle(
            graph_separator_x - 5, separator_y,
            graph_separator_x + 5, separator_y + self.HEADER_HEIGHT,
            outline='',
            fill='#888888',
            tags=("column_separator", "sep_graph_bg")
        )

        # Samotný separátor pro grafický sloupec
        canvas.create_line(
            graph_separator_x, separator_y,
            graph_separator_x, separator_y + self.HEADER_HEIGHT,
            width=3,
            fill='#333333',
            tags=("column_separator", "sep_graph"),
            activefill='#000000'
        )

        # Uložit pozici separátoru pro grafický sloupec
        self.column_separators['graph'] = graph_separator_x

        # Přidat interaktivitu pro grafický separátor
        area_id = canvas.create_rectangle(
            graph_separator_x - 5, separator_y,
            graph_separator_x + 5, separator_y + self.HEADER_HEIGHT,
            outline='',
            fill='',
            tags=("column_separator", "sep_graph_area")
        )

        # Event handlers pro grafický separátor
        canvas.tag_bind("sep_graph", '<Button-1>', lambda e: self._start_drag(e, 'graph'))
        canvas.tag_bind("sep_graph_area", '<Button-1>', lambda e: self._start_drag(e, 'graph'))
        canvas.tag_bind("sep_graph_bg", '<Button-1>', lambda e: self._start_drag(e, 'graph'))

        for tag in ["sep_graph", "sep_graph_area", "sep_graph_bg"]:
            canvas.tag_bind(tag, '<Enter>', lambda e: canvas.config(cursor='sb_h_double_arrow'))
            canvas.tag_bind(tag, '<Leave>', lambda e: canvas.config(cursor='') if not self.dragging_separator else None)

        # POTOM vykreslit separátory mezi textovými sloupci (aby byly pod pozadím)
        temp_current_x = table_start_x
        for i, column in enumerate(columns):
            temp_current_x += self.column_widths[column]

            # Vykreslit separátor (kromě posledního sloupce)
            if i < len(columns) - 1:
                # Pozadí separátoru (tmavě šedé, dobře viditelné)
                background_id = canvas.create_rectangle(
                    temp_current_x - 5, separator_y,
                    temp_current_x + 5, separator_y + self.separator_height,
                    outline='',
                    fill='#888888',  # Tmavě šedá
                    tags=("column_separator", f"sep_{column}_bg")
                )

                # Samotný separátor (tmavý)
                separator_id = canvas.create_line(
                    temp_current_x, separator_y,
                    temp_current_x, separator_y + self.separator_height,
                    width=3,
                    fill='#333333',  # Tmavě šedá
                    tags=("column_separator", f"sep_{column}"),
                    activefill='#000000'  # Černá při hover
                )

                # Uložit pozici separátoru
                self.column_separators[column] = temp_current_x

                # Přidat neviditelnou oblast pro lepší zachytávání myši
                area_id = canvas.create_rectangle(
                    temp_current_x - 5, separator_y,
                    temp_current_x + 5, separator_y + self.separator_height,
                    outline='',
                    fill='',
                    tags=("column_separator", f"sep_{column}_area")
                )

                # Zabindovat kliknutí přímo na separátor a oblast
                def make_handler(col):
                    return lambda e: self._start_drag(e, col)

                canvas.tag_bind(f"sep_{column}", '<Button-1>', make_handler(column))
                canvas.tag_bind(f"sep_{column}_area", '<Button-1>', make_handler(column))
                canvas.tag_bind(f"sep_{column}_bg", '<Button-1>', make_handler(column))

                # Přidat cursor events pro všechny části separátoru
                def set_cursor_enter(e):
                    canvas.config(cursor='sb_h_double_arrow')
                def set_cursor_leave(e):
                    if not self.dragging_separator:
                        canvas.config(cursor='')

                canvas.tag_bind(f"sep_{column}", '<Enter>', set_cursor_enter)
                canvas.tag_bind(f"sep_{column}", '<Leave>', set_cursor_leave)
                canvas.tag_bind(f"sep_{column}_area", '<Enter>', set_cursor_enter)
                canvas.tag_bind(f"sep_{column}_area", '<Leave>', set_cursor_leave)
                canvas.tag_bind(f"sep_{column}_bg", '<Enter>', set_cursor_enter)
                canvas.tag_bind(f"sep_{column}_bg", '<Leave>', set_cursor_leave)

        # POTOM vykreslit pozadí (s výřezy pro separátory)
        # Pozadí pro grafický sloupec - s výřezem pro separátor
        graph_column_bg = canvas.create_rectangle(
            0, separator_y,
            table_start_x - 5, separator_y + 25,  # -5 pro výřez separátoru
            outline='',
            fill='#f0f0f0',
            tags=("column_header", "graph_header_bg")
        )

        # Záhlaví pro grafický sloupec
        graph_header_x = table_start_x // 2
        graph_header_text = canvas.create_text(
            graph_header_x, separator_y + 12,
            text="Branch / Commit / Tag",
            anchor='center',
            font=('Arial', 8, 'bold'),
            fill='#333333',
            tags=("column_header", "graph_header_text")
        )

        # Pozadí a text pro textové sloupce (s mezerami pro separátory)
        for i, column in enumerate(columns):

            # Vykreslit pozadí pro tento sloupec (s výřezem pro separátory)
            if i < len(columns) - 1:
                # Ne poslední sloupec - nechat mezeru pro separátor
                column_bg = canvas.create_rectangle(
                    current_x, separator_y,
                    current_x + self.column_widths[column] - 5, separator_y + 25,  # -5 pro mezeru
                    outline='',
                    fill='#f0f0f0',
                    tags=("column_header", f"column_bg_{column}")
                )
            else:
                # Poslední sloupec - bez mezery
                column_bg = canvas.create_rectangle(
                    current_x, separator_y,
                    current_x + self.column_widths[column], separator_y + 25,
                    outline='',
                    fill='#f0f0f0',
                    tags=("column_header", f"column_bg_{column}")
                )

            # Vykreslit popisek sloupce
            header_x = current_x + self.column_widths[column] // 2
            header_text = canvas.create_text(
                header_x, separator_y + 12,
                text=column_names[column],
                anchor='center',
                font=('Arial', 8, 'bold'),
                fill='#333333',
                tags=("column_header", f"header_text_{column}")
            )

            current_x += self.column_widths[column]

        # Zajistit správné vrstvení: pozadí záhlaví dolů, separátory nahoru, text záhlaví na vrch
        canvas.tag_lower("graph_header_bg")   # Pozadí grafického záhlaví dolů
        for column in ['message', 'author', 'email', 'date']:
            try:
                canvas.tag_lower(f"column_bg_{column}")  # Pozadí jednotlivých sloupců dolů
            except:
                pass
        canvas.tag_raise("column_separator")  # Separátory nahoru (aby byly klikatelné)
        canvas.tag_raise("column_header")      # Text záhlaví na vrch

    def setup_column_resize_events(self, canvas: tk.Canvas):
        """Nastaví event handlery pro změnu velikosti sloupců."""
        # Místo bindování na celý canvas, zabindujeme přímo na separátory
        # To se udělá v _draw_column_separators()

        # Pro drag operation potřebujeme globální handlery
        canvas.bind('<B1-Motion>', self._on_separator_drag)
        canvas.bind('<ButtonRelease-1>', self._on_separator_release)

    def _start_drag(self, event, column):
        """Zahájí tažení separátoru pro daný sloupec."""
        self.dragging_separator = column
        self.drag_start_x = event.x
        event.widget.config(cursor='sb_h_double_arrow')

    def _on_separator_drag(self, event):
        """Táhne separátor a upravuje šířku sloupce."""
        if not self.dragging_separator:
            return

        canvas = event.widget
        delta_x = event.x - self.drag_start_x

        if self.dragging_separator == 'graph':
            # Speciální zpracování pro grafický sloupec
            current_width = self._calculate_graph_column_width()
            new_width = max(100, current_width + delta_x)  # minimální šířka 100px pro grafický sloupec

            # Uložit novou šířku grafického sloupce
            self.graph_column_width = new_width
        else:
            # Standardní zpracování pro textové sloupce
            current_width = self.column_widths[self.dragging_separator]
            new_width = max(50, current_width + delta_x)  # minimální šířka 50px

            self.user_column_widths[self.dragging_separator] = new_width
            self.column_widths[self.dragging_separator] = new_width

        self.drag_start_x = event.x

        # Překreslit graf s novými šířkami
        self._redraw_with_new_widths(canvas)

    def _on_separator_release(self, event):
        """Ukončí tažení separátoru."""
        self.dragging_separator = None
        event.widget.config(cursor='')


    def _redraw_with_new_widths(self, canvas: tk.Canvas):
        """Překreslí graf s novými šířkami sloupců."""
        # Smazat texty commitů, tagy, separátory a popisky
        canvas.delete("commit_text")
        canvas.delete("tag_emoji")
        canvas.delete("tag_label")
        canvas.delete("tag_tooltip_area")
        canvas.delete("column_separator")
        canvas.delete("column_header")

        # Najít commity z canvasu (pokud jsou tam uložené jako data)
        if hasattr(self, '_current_commits') and self._current_commits:
            # Přepočítat description texty podle nové šířky message sloupce
            self._recalculate_descriptions_for_width(canvas, self._current_commits)
            self._draw_commits(canvas, self._current_commits)
            self._draw_tags(canvas, self._current_commits)

        # Překreslit separátory
        self._draw_column_separators(canvas)

    def _recalculate_descriptions_for_width(self, canvas: tk.Canvas, commits):
        """Přepočítá description texty podle aktuální šířky message sloupce."""
        font = ('Arial', self.font_size)

        for commit in commits:
            if not commit.description:
                commit.description_short = ""
                continue

            # Aplikovat původní logiku zkracování podle DPI škálování
            commit.description_short = self._truncate_description_for_dpi(
                commit.description, self.max_description_length
            )

            # Pokud je description prázdný, pokračovat
            if not commit.description_short:
                continue

            # Vypočítat dostupný prostor pro description v message sloupci
            message_width = canvas.tk.call("font", "measure", font, commit.message)
            available_space = self.column_widths['message'] - message_width - 40  # 40px mezery

            # Zkrátit description aby se vešel do dostupného prostoru
            if available_space > 0:
                commit.description_short = self._truncate_text_to_width(
                    canvas, font, commit.description_short, available_space
                )
            else:
                # Pokud není místo, skrýt description
                commit.description_short = ""