import tkinter as tk
from typing import List, Dict, Tuple
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
        self.separator_height = 25  # výška separátoru v pixelech (odpovídá výšce záhlaví)
        self.user_column_widths = {}  # uživatelem nastavené šířky

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
        self._draw_connections(canvas, commits)
        self._draw_commits(canvas, commits)
        self._draw_column_separators(canvas)

    def _draw_connections(self, canvas: tk.Canvas, commits: List[Commit]):
        commit_positions = {commit.hash: (commit.x, commit.y) for commit in commits}

        for commit in commits:
            if commit.parents:
                start_pos = commit_positions.get(commit.hash)
                if start_pos:
                    for parent_hash in commit.parents:
                        end_pos = commit_positions.get(parent_hash)
                        if end_pos:
                            self._draw_line(canvas, start_pos, end_pos, commit.branch_color)

    def _draw_line(self, canvas: tk.Canvas, start: Tuple[int, int], end: Tuple[int, int], color: str):
        start_x, start_y = start
        end_x, end_y = end

        # Pokud jsou commity v různých sloupcích (větvení), kreslíme L-tvar
        if start_x != end_x:
            # L-tvarová linka: vodorovně pak svisle
            # Nejdříve vodorovná část k středu mezi sloupci
            mid_x = (start_x + end_x) // 2

            # Vodorovná čára od start commitu k mid_x
            canvas.create_line(
                start_x, start_y, mid_x, start_y,
                fill=color,
                width=self.line_width
            )

            # Svislá čára z mid_x dolů k end_y
            canvas.create_line(
                mid_x, start_y, mid_x, end_y,
                fill=color,
                width=self.line_width
            )

            # Vodorovná čára z mid_x k end commitu
            canvas.create_line(
                mid_x, end_y, end_x, end_y,
                fill=color,
                width=self.line_width
            )
        else:
            # Přímá svislá linka pro commity ve stejném sloupci
            canvas.create_line(
                start_x, start_y, end_x, end_y,
                fill=color,
                width=self.line_width
            )

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

    def _draw_commits(self, canvas: tk.Canvas, commits: List[Commit]):
        # Použít standardní font - škálování řešíme délkou textu, ne velikostí fontu
        font = ('Arial', self.font_size)

        # Sledovat, které větve už mají vlaječku
        drawn_branch_flags = set()

        # Najít posledního commitu každé větve (podle času)
        last_commits_by_branch = {}
        for commit in commits:
            if commit.branch not in last_commits_by_branch:
                last_commits_by_branch[commit.branch] = commit
            elif commit.date > last_commits_by_branch[commit.branch].date:
                last_commits_by_branch[commit.branch] = commit

        for commit in commits:
            x, y = commit.x, commit.y

            canvas.create_oval(
                x - self.node_radius, y - self.node_radius,
                x + self.node_radius, y + self.node_radius,
                fill=commit.branch_color,
                outline='black',
                width=1
            )

            # Zobrazit vlaječku s názvem větve pro první commit každé větve
            if commit.branch not in drawn_branch_flags:
                self._draw_branch_flag(canvas, x, y, commit.branch, commit.branch_color)
                drawn_branch_flags.add(commit.branch)

            # Pokud je to posledný commit větve, nakreslit horizontální spojnici k vlaječce
            if last_commits_by_branch[commit.branch] == commit:
                self._draw_flag_connection(canvas, x, y, commit.branch_color)

            # Pevná pozice pro začátek "tabulky" - za všemi větvemi
            table_start_x = self._get_table_start_position()

            # Pevné pozice pro tabulkové sloupce
            text_x = table_start_x

            # Vytvořit kombinovaný text message + description
            if commit.description_short:
                # Message v černé + description v šedé
                canvas.create_text(
                    text_x, y,
                    text=commit.message,
                    anchor='w',
                    font=font,
                    fill='black',
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
                # Jen message bez description
                canvas.create_text(
                    text_x, y,
                    text=commit.message,
                    anchor='w',
                    font=font,
                    fill='black',
                    tags="commit_text"
                )

            text_x += self.column_widths['message']

            # Author - zarovnaný na střed sloupce
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

            # Email - zarovnaný na střed sloupce
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

            # Date - zarovnaný na střed sloupce
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

    def _draw_branch_flag(self, canvas: tk.Canvas, x: int, y: int, branch_name: str, branch_color: str):
        """Vykreslí vlaječku s názvem větve v pevném levém sloupci."""
        # Velikost vlaječky
        flag_width = 60
        flag_height = 20

        # Pozice vlaječky (pevný levý sloupec)
        flag_x = 30  # Pevná pozice vlevo
        flag_y = y

        # Vytvořit obdélník vlaječky
        canvas.create_rectangle(
            flag_x - flag_width // 2, flag_y - flag_height // 2,
            flag_x + flag_width // 2, flag_y + flag_height // 2,
            fill=branch_color,
            outline='black',
            width=1
        )

        # Přidat text názvu větve
        canvas.create_text(
            flag_x, flag_y,
            text=branch_name,
            anchor='center',
            font=('Arial', 8, 'bold'),
            fill='white'
        )

    def _update_branch_lanes(self, commits: List[Commit]):
        """Aktualizuje informace o lanes pro výpočet pozice tabulky."""
        self.branch_lanes = {}
        for commit in commits:
            branch_lane = (commit.x - 100) // 20  # Zpětný výpočet lane z X pozice (20px mezery)
            self.branch_lanes[commit.branch] = branch_lane

    def _get_table_start_position(self) -> int:
        """Vrátí X pozici kde začíná tabulka (za všemi větvemi)."""
        if not self.branch_lanes:
            return 200  # Fallback pozice

        max_lane = max(self.branch_lanes.values())
        return (max_lane + 1) * 20 + 120  # Za posledním sloupcem větví (20px mezery)

    def _draw_flag_connection(self, canvas: tk.Canvas, commit_x: int, commit_y: int, branch_color: str):
        """Vykreslí horizontální spojnici od commitu k vlaječce."""
        # Pozice vlaječky
        flag_x = 30

        # Horizontální linka od commitu k vlaječce
        canvas.create_line(
            flag_x + 30, commit_y,  # Od pravého okraje vlaječky
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
            'message': 'Commit Message / Description',
            'author': 'Author',
            'email': 'Email',
            'date': 'Date'
        }

        columns = ['message', 'author', 'email', 'date']

        # NEJPRVE vykreslit separátory (aby byly pod pozadím)
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
        # Pozadí pro grafický sloupec
        graph_column_bg = canvas.create_rectangle(
            0, separator_y,
            table_start_x, separator_y + 25,
            outline='',
            fill='#f0f0f0',
            tags=("column_header", "graph_header_bg")
        )

        # Záhlaví pro grafický sloupec
        graph_header_x = table_start_x // 2
        graph_header_text = canvas.create_text(
            graph_header_x, separator_y + 12,
            text="Branch / Commit",
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

        # Aktualizovat šířku sloupce
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
        # Smazat texty commitů, separátory a popisky
        canvas.delete("commit_text")
        canvas.delete("column_separator")
        canvas.delete("column_header")

        # Najít commity z canvasu (pokud jsou tam uložené jako data)
        if hasattr(self, '_current_commits') and self._current_commits:
            # Přepočítat description texty podle nové šířky message sloupce
            self._recalculate_descriptions_for_width(canvas, self._current_commits)
            self._draw_commits(canvas, self._current_commits)

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