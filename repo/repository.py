import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
import git
from git import Repo, InvalidGitRepositoryError
from utils.data_structures import Commit, Branch, Tag, MergeBranch
from visualization.colors import get_branch_color


class GitRepository:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo: Optional[Repo] = None
        self.commits: List[Commit] = []
        self.branches: Dict[str, Branch] = {}
        self.merge_branches: List[MergeBranch] = []  # Posledně detekované merge větve

    def load_repository(self) -> bool:
        try:
            self.repo = Repo(self.repo_path)
            return True
        except InvalidGitRepositoryError:
            return False

    def parse_commits(self) -> List[Commit]:
        if not self.repo:
            return []

        # Předpočítání map commit -> větev a commit -> tagy pro optimalizaci
        commit_to_branch = self._build_commit_branch_map()
        commit_to_tags = self._build_commit_tag_map()
        branch_availability = self._build_branch_availability_map(include_remote=False)

        commits = []
        used_colors = set()
        branch_colors = {}
        seen_commits = set()

        # Iterovat pouze přes lokální větve, ne přes all=True
        for head in self.repo.heads:
            try:
                for commit in self.repo.iter_commits(head):
                    if commit.hexsha in seen_commits:
                        continue
                    seen_commits.add(commit.hexsha)

                    branch_name = commit_to_branch.get(commit.hexsha, 'unknown')

                    if branch_name not in branch_colors:
                        branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

                    full_message = commit.message.strip()
                    message_lines = full_message.split('\n', 1)
                    subject = message_lines[0]
                    description = message_lines[1].strip() if len(message_lines) > 1 else ""

                    # Získat tagy pro tento commit
                    commit_tags = commit_to_tags.get(commit.hexsha, [])

                    # Určit dostupnost větve
                    branch_avail = branch_availability.get(branch_name, 'local_only')

                    commit_obj = Commit(
                        hash=commit.hexsha[:8],
                        message=subject,
                        short_message=self._truncate_message(subject, 50),
                        author=commit.author.name,
                        author_short=self._truncate_name(commit.author.name),
                        author_email=commit.author.email,
                        date=commit.committed_datetime,
                        date_relative=self._get_relative_date(commit.committed_datetime),
                        date_short=self._get_full_date(commit.committed_datetime),
                        parents=[parent.hexsha[:8] for parent in commit.parents],
                        branch=branch_name,
                        branch_color=branch_colors[branch_name],
                        tags=commit_tags,
                        branch_availability=branch_avail
                    )
                    commit_obj.description = description
                    commit_obj.description_short = self._truncate_description(description)
                    commits.append(commit_obj)
            except:
                continue

        # Přidat uncommitted změny na začátek (nejnovější)
        uncommitted_info = self.get_uncommitted_changes()
        uncommitted_commits = self._create_uncommitted_commits(uncommitted_info, commits)

        # Kombinovat commity s uncommitted změnami
        all_commits = uncommitted_commits + commits

        # Detekovat merge větve a aplikovat jejich styling
        merge_branches = self._detect_merge_branches(commits)
        self.merge_branches = merge_branches  # Uložit pro GraphLayout
        self._apply_merge_branch_styling(all_commits, merge_branches)

        all_commits.sort(key=lambda c: c.date, reverse=True)

        self.commits = all_commits
        return all_commits

    def _build_commit_branch_map(self) -> Dict[str, str]:
        """Vytvořuje mapu commit_hash -> branch_name pro rychlé vyhledávání."""
        commit_to_branch = {}

        try:
            # Nejdříve zpracujeme hlavní větve s prioritou
            main_branches = ['main', 'master']
            other_branches = []

            # Pracovat s lokálními heads (větve)
            for head in self.repo.heads:
                branch_name = head.name
                if branch_name in main_branches:
                    # Okamžitě zpracujeme hlavní větve
                    try:
                        for commit in self.repo.iter_commits(head):
                            commit_to_branch[commit.hexsha] = branch_name
                    except:
                        continue
                else:
                    other_branches.append((head, branch_name))

            # Poté zpracujeme ostatní větve, ale pouze commity co ještě nemají větev
            for head, branch_name in other_branches:
                try:
                    for commit in self.repo.iter_commits(head):
                        commit_hash = commit.hexsha
                        if commit_hash not in commit_to_branch:
                            commit_to_branch[commit_hash] = branch_name
                except:
                    continue

        except Exception:
            pass

        return commit_to_branch

    def parse_commits_with_remote(self) -> List[Commit]:
        """Načte commity včetně remote větví z origin s podporou divergence."""
        if not self.repo:
            return []

        # Předpočítání map pro lokální i remote větve a tagy
        local_commit_map, remote_commit_map = self._build_commit_branch_map_with_remote()
        commit_to_tags = self._build_commit_tag_map_with_remote()
        branch_availability = self._build_branch_availability_map()

        # Detekovat divergence pro všechny větve
        branch_divergences = {}
        all_branch_names = set()
        if hasattr(self.repo, 'heads'):
            for head in self.repo.heads:
                all_branch_names.add(head.name)
        if hasattr(self.repo, 'remotes') and self.repo.remotes:
            try:
                for ref in self.repo.remotes.origin.refs:
                    if not ref.name.endswith('/HEAD'):
                        branch_name = ref.name.replace('origin/', '')
                        all_branch_names.add(branch_name)
            except:
                pass

        for branch_name in all_branch_names:
            branch_divergences[branch_name] = self._detect_branch_divergence(branch_name)

        commits = []
        used_colors = set()
        branch_colors = {}

        # Collect all branch heads for identification
        branch_heads = {}  # branch_name -> {'local': commit_hash, 'remote': commit_hash}
        for branch_name, div_info in branch_divergences.items():
            branch_heads[branch_name] = {
                'local': div_info.get('local_head'),
                'remote': div_info.get('remote_head')
            }

        for commit in self.repo.iter_commits(all=True):
            # Prioritně lokální větev
            if commit.hexsha in local_commit_map:
                branch_name = local_commit_map[commit.hexsha]
                is_remote = False
            elif commit.hexsha in remote_commit_map:
                branch_name = remote_commit_map[commit.hexsha]
                is_remote = True
            else:
                branch_name = 'unknown'
                is_remote = False

            if branch_name not in branch_colors:
                branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

            full_message = commit.message.strip()
            message_lines = full_message.split('\n', 1)
            subject = message_lines[0]
            description = message_lines[1].strip() if len(message_lines) > 1 else ""

            # Získat tagy pro tento commit
            commit_tags = commit_to_tags.get(commit.hexsha, [])

            # Určit dostupnost větve (pro remote větve může být branch_name s origin/ prefixem)
            clean_branch_name = branch_name
            if branch_name.startswith('origin/'):
                clean_branch_name = branch_name[7:]  # Odstranit "origin/"

            branch_avail = branch_availability.get(clean_branch_name, 'local_only')

            # Zjistit zda je tento commit HEAD nějaké větve
            is_branch_head = False
            branch_head_type = "none"

            if clean_branch_name in branch_heads:
                heads = branch_heads[clean_branch_name]
                local_head = heads.get('local')
                remote_head = heads.get('remote')

                is_local_head = local_head and commit.hexsha == local_head.hexsha
                is_remote_head = remote_head and commit.hexsha == remote_head.hexsha

                if is_local_head and is_remote_head:
                    is_branch_head = True
                    branch_head_type = "both"
                elif is_local_head:
                    is_branch_head = True
                    branch_head_type = "local"
                elif is_remote_head:
                    is_branch_head = True
                    branch_head_type = "remote"


            commit_obj = Commit(
                hash=commit.hexsha[:8],
                message=subject,
                short_message=self._truncate_message(subject, 50),
                author=commit.author.name,
                author_short=self._truncate_name(commit.author.name),
                author_email=commit.author.email,
                date=commit.committed_datetime,
                date_relative=self._get_relative_date(commit.committed_datetime),
                date_short=self._get_full_date(commit.committed_datetime),
                parents=[parent.hexsha[:8] for parent in commit.parents],
                branch=branch_name,
                branch_color=branch_colors[branch_name],
                is_remote=is_remote,
                tags=commit_tags,
                branch_availability=branch_avail,
                is_branch_head=is_branch_head,
                branch_head_type=branch_head_type
            )
            commit_obj.description = description
            commit_obj.description_short = self._truncate_description(description)
            commits.append(commit_obj)

        # Přidat uncommitted změny na začátek (nejnovější)
        uncommitted_info = self.get_uncommitted_changes()
        uncommitted_commits = self._create_uncommitted_commits(uncommitted_info, commits)

        # Kombinovat commity s uncommitted změnami
        all_commits = uncommitted_commits + commits

        # Detekovat merge větve a aplikovat jejich styling
        merge_branches = self._detect_merge_branches(commits)
        self.merge_branches = merge_branches  # Uložit pro GraphLayout
        self._apply_merge_branch_styling(all_commits, merge_branches)

        all_commits.sort(key=lambda c: c.date, reverse=True)

        self.commits = all_commits
        return all_commits

    def _build_commit_branch_map_with_remote(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Vytvořuje mapy commit_hash -> branch_name pro lokální a remote větve."""
        local_commit_map = {}
        remote_commit_map = {}

        try:
            # 1. Prioritně lokální větve
            main_branches = ['main', 'master']
            other_local_branches = []

            for head in self.repo.heads:
                branch_name = head.name
                if branch_name in main_branches:
                    try:
                        for commit in self.repo.iter_commits(head):
                            local_commit_map[commit.hexsha] = branch_name
                    except:
                        continue
                else:
                    other_local_branches.append((head, branch_name))

            for head, branch_name in other_local_branches:
                try:
                    for commit in self.repo.iter_commits(head):
                        if commit.hexsha not in local_commit_map:
                            local_commit_map[commit.hexsha] = branch_name
                except:
                    continue

            # 2. Remote větve - jen pro commity bez lokální větve
            try:
                remote_refs = list(self.repo.remote().refs)
                for remote_ref in remote_refs:
                    # Přeskočit HEAD ref
                    if remote_ref.name.endswith('/HEAD'):
                        continue

                    try:
                        for commit in self.repo.iter_commits(remote_ref):
                            if commit.hexsha not in local_commit_map:
                                remote_commit_map[commit.hexsha] = remote_ref.name
                    except:
                        continue
            except:
                # Pokud remote neexistuje, pokračovat jen s lokálními větvemi
                pass

        except Exception:
            pass

        return local_commit_map, remote_commit_map

    def _build_branch_availability_map(self, include_remote: bool = True) -> Dict[str, str]:
        """Vytvoří mapu branch_name -> availability (local_only/remote_only/both)."""
        local_branches = set()
        remote_branches = set()

        # Získat lokální větve
        try:
            for head in self.repo.heads:
                local_branches.add(head.name)
        except:
            pass

        # Získat remote větve pouze pokud je to požadováno
        if include_remote:
            try:
                remote_refs = list(self.repo.remote().refs)
                for remote_ref in remote_refs:
                    if remote_ref.name.endswith('/HEAD'):
                        continue
                    # Extrahovat název větve z origin/branch_name
                    if remote_ref.name.startswith('origin/'):
                        branch_name = remote_ref.name[7:]  # Odstranit "origin/"
                        remote_branches.add(branch_name)
            except:
                pass

        # Vytvořit mapu dostupnosti
        availability_map = {}
        all_branches = local_branches | remote_branches

        for branch in all_branches:
            if branch in local_branches and branch in remote_branches:
                availability_map[branch] = 'both'
            elif branch in local_branches:
                availability_map[branch] = 'local_only'
            elif branch in remote_branches:
                availability_map[branch] = 'remote_only'

        return availability_map

    def _detect_branch_divergence(self, branch_name: str) -> Dict:
        """Detekuje divergenci mezi lokální a remote větví."""
        try:
            # Získat lokální a remote reference
            local_head = None
            remote_head = None

            # Lokální větev
            try:
                local_head = self.repo.heads[branch_name].commit
            except:
                pass

            # Remote větev
            try:
                remote_head = self.repo.remotes.origin.refs[branch_name].commit
            except:
                pass

            # Pokud některá neexistuje, není divergence
            if not local_head or not remote_head:
                return {
                    'diverged': False,
                    'local_head': local_head,
                    'remote_head': remote_head,
                    'merge_base': None
                }

            # Pokud ukazují na stejný commit, není divergence
            if local_head == remote_head:
                return {
                    'diverged': False,
                    'local_head': local_head,
                    'remote_head': remote_head,
                    'merge_base': local_head
                }

            # Najít merge base
            merge_bases = self.repo.merge_base(local_head, remote_head)
            if not merge_bases:
                # Žádný společný předek - divergence definitivně existuje
                return {
                    'diverged': True,
                    'local_head': local_head,
                    'remote_head': remote_head,
                    'merge_base': None
                }

            merge_base = merge_bases[0]

            # Zkontrolovat zda skutečně divergovaly (oba jsou ahead of merge base)
            local_is_ahead = local_head != merge_base
            remote_is_ahead = remote_head != merge_base

            return {
                'diverged': local_is_ahead and remote_is_ahead,
                'local_head': local_head,
                'remote_head': remote_head,
                'merge_base': merge_base,
                'local_ahead': local_is_ahead,
                'remote_ahead': remote_is_ahead
            }

        except Exception as e:
            return {
                'diverged': False,
                'local_head': None,
                'remote_head': None,
                'merge_base': None,
                'error': str(e)
            }

    def _build_commit_tag_map(self) -> Dict[str, List[Tag]]:
        """Vytvořuje mapu commit_hash -> List[Tag] pro lokální tagy."""
        commit_to_tags = {}

        try:
            for tag in self.repo.tags:
                try:
                    # Získat commit na který tag ukazuje
                    tag_commit = tag.commit
                    tag_obj = Tag(
                        name=tag.name,
                        is_remote=False,
                        message=tag.tag.message if hasattr(tag, 'tag') and tag.tag else ""
                    )

                    if tag_commit.hexsha not in commit_to_tags:
                        commit_to_tags[tag_commit.hexsha] = []
                    commit_to_tags[tag_commit.hexsha].append(tag_obj)
                except:
                    continue
        except:
            pass

        return commit_to_tags

    def _build_commit_tag_map_with_remote(self) -> Dict[str, List[Tag]]:
        """Vytvořuje mapu commit_hash -> List[Tag] pro lokální i remote tagy."""
        commit_to_tags = {}

        # Nejprve lokální tagy (mají prioritu)
        local_tags = self._build_commit_tag_map()
        commit_to_tags.update(local_tags)

        # Poté remote tagy (jen pokud commit ještě nemá lokální tag)
        try:
            # Remote tagy jsou v refs/remotes/origin/tags/* nebo se načítají přes remote
            # Pro zjednodušení použijeme GitPython API, který umí rozlišit remote tagy
            remote_refs = []
            try:
                remote_refs = list(self.repo.remote().refs)
            except:
                pass

            for remote_ref in remote_refs:
                # Přeskočit branch refs, hledáme jen tagy
                if not remote_ref.name.endswith('/tags/') and '/tags/' not in remote_ref.name:
                    continue

                try:
                    # Extrahovat název tagu z remote ref
                    tag_name = remote_ref.name.split('/')[-1]
                    if '/tags/' in remote_ref.name:
                        tag_name = remote_ref.name.split('/tags/')[-1]

                    tag_commit = remote_ref.commit
                    tag_obj = Tag(
                        name=f"origin/{tag_name}",
                        is_remote=True,
                        message=""
                    )

                    if tag_commit.hexsha not in commit_to_tags:
                        commit_to_tags[tag_commit.hexsha] = []

                    # Přidat jen pokud už není lokální tag se stejným názvem
                    existing_names = [t.name for t in commit_to_tags[tag_commit.hexsha]]
                    if tag_name not in existing_names:
                        commit_to_tags[tag_commit.hexsha].append(tag_obj)
                except:
                    continue
        except:
            pass

        return commit_to_tags

    def _truncate_message(self, message: str, max_length: int) -> str:
        if len(message) <= max_length:
            return message
        return message[:max_length-3] + '...'

    def _truncate_name(self, name: str) -> str:
        if len(name) <= 15:
            return name
        parts = name.split()
        if len(parts) > 1:
            return f"{parts[0][0]}. {parts[-1]}"
        return name[:12] + '...'

    def _truncate_description(self, description: str, max_length: int = 80) -> str:
        """Zkrátí description na první řádek s maximální délkou a přidá vynechávku."""
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

        # Zkrátit text pokud je potřeba
        if len(first_line) > max_length:
            first_line = first_line[:max_length-3]

        # Přidat vynechávku
        if needs_ellipsis:
            # Pokud končí dvojtečkou, nahradit ji vynechávkou
            if first_line.endswith(':'):
                first_line = first_line[:-1] + '...'
            else:
                first_line = first_line + '...'

        return first_line

    def _get_relative_date(self, date: datetime) -> str:
        now = datetime.now(timezone.utc)
        diff = now - date.replace(tzinfo=timezone.utc)

        if diff.days > 7:
            return f"{diff.days // 7} týdnů"
        elif diff.days > 0:
            return f"{diff.days} dní" if diff.days > 1 else "1 den"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hodin" if hours > 1 else "1 hodina"
        else:
            minutes = diff.seconds // 60
            return f"{minutes} minut" if minutes > 1 else "před chvílí"

    def _get_short_date(self, date: datetime) -> str:
        return date.strftime("%d.%m")

    def _get_full_date(self, date: datetime) -> str:
        return date.strftime("%d.%m.%Y @ %H:%M")

    def get_uncommitted_changes(self) -> Dict[str, any]:
        """Detekuje uncommitted změny (staged a working directory)."""
        if not self.repo:
            return {"has_changes": False}

        try:
            # Získat status repozitáře
            status = self.repo.git.status(porcelain=True)

            if not status.strip():
                return {"has_changes": False}

            # Analyzovat status výstup
            staged_files = []
            working_files = []

            for line in status.strip().split('\n'):
                if len(line) >= 3:
                    staged_status = line[0]
                    working_status = line[1]
                    filename = line[3:]

                    if staged_status != ' ':
                        staged_files.append(filename)
                    if working_status != ' ':
                        working_files.append(filename)

            has_staged = len(staged_files) > 0
            has_working = len(working_files) > 0

            if not has_staged and not has_working:
                return {"has_changes": False}

            # Určit typ změn
            if has_staged and has_working:
                uncommitted_type = "both"
                change_desc = f"{len(staged_files)} staged, {len(working_files)} working"
            elif has_staged:
                uncommitted_type = "staged"
                change_desc = f"{len(staged_files)} staged"
            else:
                uncommitted_type = "working"
                change_desc = f"{len(working_files)} working"

            return {
                "has_changes": True,
                "uncommitted_type": uncommitted_type,
                "staged_files": staged_files,
                "working_files": working_files,
                "change_description": change_desc
            }

        except Exception as e:
            return {"has_changes": False, "error": str(e)}

    def _detect_merge_branches(self, commits: List[Commit]) -> List[MergeBranch]:
        """Detekuje merge patterns a vytvoří virtuální merge větve."""
        if not commits:
            return []

        merge_branches = []
        commit_map = {commit.hash: commit for commit in commits}

        # Rozšířený commit map pro plné hashe (může být nutné pro GitPython)
        full_hash_map = {}
        if self.repo:
            try:
                for commit in self.repo.iter_commits(all=True):
                    short_hash = commit.hexsha[:8]
                    full_hash_map[short_hash] = commit.hexsha
            except:
                pass

        # Najít merge commity (více než 1 parent)
        merge_commits = [commit for commit in commits if len(commit.parents) >= 2]

        for merge_commit in merge_commits:
            try:
                if len(merge_commit.parents) < 2:
                    continue

                # První parent = hlavní větev, druhý parent = mergovaná větev
                main_parent_hash = merge_commit.parents[0]
                merge_parent_hash = merge_commit.parents[1]

                # Najít branch point (společný ancestor) pomocí GitPython
                if self.repo and merge_parent_hash in full_hash_map and main_parent_hash in full_hash_map:
                    try:
                        full_merge_parent = full_hash_map[merge_parent_hash]
                        full_main_parent = full_hash_map[main_parent_hash]

                        # Najít merge base (společný ancestor)
                        merge_base = self.repo.merge_base(full_merge_parent, full_main_parent)
                        if merge_base:
                            branch_point_hash = merge_base[0].hexsha[:8]

                            # Získat všechny commity v merge branch (od branch point k merge parent)
                            merge_branch_commits = []

                            # Trasovat zpětně od merge parent k branch point
                            current = merge_parent_hash
                            visited = set()

                            while current and current != branch_point_hash and current not in visited:
                                visited.add(current)
                                if current in commit_map:
                                    commit = commit_map[current]
                                    merge_branch_commits.append(current)

                                    # Pokračovat k prvnímu parentu (lineární path)
                                    if commit.parents:
                                        current = commit.parents[0]
                                    else:
                                        break
                                else:
                                    break

                            # Pokud jsme našli nějaké commity v merge branch
                            if merge_branch_commits:
                                # Vytvořit virtuální název větve
                                virtual_name = f"merge-{merge_commit.hash}"

                                # Určit původní barvu (z hlavní větve)
                                main_parent = commit_map.get(main_parent_hash)
                                original_color = main_parent.branch_color if main_parent else '#666666'

                                merge_branch = MergeBranch(
                                    branch_point_hash=branch_point_hash,
                                    merge_point_hash=merge_commit.hash,
                                    commits_in_branch=merge_branch_commits,
                                    virtual_branch_name=virtual_name,
                                    original_color=original_color
                                )

                                merge_branches.append(merge_branch)
                    except Exception as e:
                        # Pokud selže GitPython approach, přeskočit tento merge
                        continue

            except Exception as e:
                # Pokud selže zpracování tohoto merge commitu, pokračovat
                continue

        return merge_branches

    def _apply_merge_branch_styling(self, commits: List[Commit], merge_branches: List[MergeBranch]):
        """Aplikuje styling na commity v merge větvích - světlejší barvy, virtuální branch names."""
        if not merge_branches:
            return

        # Vytvořit mapu commit hash -> merge branch pro rychlé vyhledávání
        commit_to_merge_branch = {}
        for merge_branch in merge_branches:
            for commit_hash in merge_branch.commits_in_branch:
                commit_to_merge_branch[commit_hash] = merge_branch

        # Aplikovat styling na commity v merge větvích
        styled_count = 0
        for commit in commits:
            if commit.hash in commit_to_merge_branch:
                merge_branch = commit_to_merge_branch[commit.hash]

                # Změnit branch na virtuální název
                old_branch = commit.branch
                commit.branch = merge_branch.virtual_branch_name

                # Aplikovat světlejší barvu (podobně jako _make_color_pale v graph_drawer)
                old_color = commit.branch_color
                commit.branch_color = self._make_color_pale(merge_branch.original_color, blend_type="merge")

                # Označit jako merge branch commit (pro případné budoucí funkce)
                commit.is_merge_branch = True
                styled_count += 1


    def _make_color_pale(self, color: str, blend_type: str = "merge") -> str:
        """Vytvoří světlejší variantu barvy pro merge větve pomocí HSL manipulace."""
        if not color or color == 'unknown':
            return '#CCCCCC'

        if color.startswith('#'):
            try:
                # Převést hex na RGB
                hex_color = color.lstrip('#')
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16) / 255.0
                    g = int(hex_color[2:4], 16) / 255.0
                    b = int(hex_color[4:6], 16) / 255.0

                    # Převést RGB na HSL
                    import colorsys
                    h, l, s = colorsys.rgb_to_hls(r, g, b)

                    # Aplikovat vyblednutí podle typu
                    if blend_type == "remote":
                        # Remote: mírnější vyblednutí pro zachování rozlišitelnosti
                        s = s * 0.8  # Snížit sytost na 80% originální
                        l = min(0.9, l + 0.15)  # Zvýšit lightness o 15%
                    elif blend_type == "merge":
                        # Merge: výrazné vyblednutí - nejméně saturované ze všech
                        s = s * 0.6  # Snížit sytost na 60% originální (méně než remote)
                        l = min(0.85, l + 0.20)  # Výrazně zvýšit lightness o 20%
                    else:
                        # Fallback na merge chování
                        s = s * 0.6
                        l = min(0.85, l + 0.20)

                    # Převést zpět na RGB
                    r, g, b = colorsys.hls_to_rgb(h, l, s)

                    # Převést na hex
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)

                    return f'#{r:02x}{g:02x}{b:02x}'
            except:
                pass

        # Fallback na světle šedou
        return "#CCCCCC"

    def _create_uncommitted_commits(self, uncommitted_info: Dict[str, any], existing_commits: List[Commit] = None) -> List[Commit]:
        """Vytvoří pseudo-commity pro uncommitted změny pro každou větev."""
        if not uncommitted_info.get("has_changes", False):
            return []

        uncommitted_commits = []
        try:
            # Získat aktuální větev
            current_branch = self.repo.active_branch.name if self.repo.active_branch else "HEAD"

            # Zjistit který typ změn máme
            uncommitted_type = uncommitted_info["uncommitted_type"]
            staged_files = uncommitted_info.get("staged_files", [])
            working_files = uncommitted_info.get("working_files", [])

            # Spočítat celkový počet dotčených souborů (bez duplikátů)
            all_files = set(staged_files + working_files)
            file_count = len(all_files)

            # Vytvořit description podle počtu souborů
            if file_count == 1:
                description = "1 soubor"
            elif file_count < 5:
                description = f"{file_count} soubory"
            else:
                description = f"{file_count} souborů"

            # Vytvořit pseudo-commit pro aktuální větev
            now = datetime.now(timezone.utc)

            # Hash pro uncommitted změny - použijeme speciální prefix
            full_hash = f"uncommit_{current_branch}_{int(now.timestamp())}"
            uncommitted_hash = full_hash[:8]

            # Najít HEAD commit aktuální větve pro parent a barvu
            head_commit = None
            branch_color = '#CCCCCC'  # Defaultní šedá fallback

            # Najít nejnovější commit v aktuální větvi (ne uncommitted)
            commits_to_search = existing_commits if existing_commits else self.commits
            for commit in sorted(commits_to_search, key=lambda c: c.date, reverse=True):
                if commit.branch == current_branch and not getattr(commit, 'is_uncommitted', False):
                    head_commit = commit
                    branch_color = commit.branch_color
                    break

            uncommitted_commit = Commit(
                hash=uncommitted_hash,
                message="WIP (Work In Progress)",
                short_message="WIP (Work In Progress)",
                author="",  # Prázdné pole
                author_short="",  # Prázdné pole
                author_email="",  # Prázdné pole
                date=now,
                date_relative="",  # Prázdné pole
                date_short="",  # Prázdné pole
                parents=[head_commit.hash] if head_commit else [],  # Parent je HEAD commit větve
                branch=current_branch,
                branch_color=branch_color,
                is_uncommitted=True,
                uncommitted_type=uncommitted_type,
                description=description,
                description_short=description
            )

            uncommitted_commits.append(uncommitted_commit)

        except Exception as e:
            # V případě chyby vrátit prázdný seznam
            pass

        return uncommitted_commits

    def get_merge_branches(self) -> List[MergeBranch]:
        """Vrátí posledně detekované merge větve."""
        return self.merge_branches

    def get_repository_stats(self) -> Dict[str, int]:
        if not self.repo or not self.commits:
            return {"authors": 0, "branches": 0, "commits": 0, "tags": 0, "local_tags": 0, "remote_tags": 0}

        authors = set()
        branches = set()
        all_tags = set()
        local_tags = set()
        remote_tags = set()

        for commit in self.commits:
            authors.add(commit.author)
            branches.add(commit.branch)

            # Spočítat tagy z commitů
            for tag in commit.tags:
                all_tags.add(tag.name)
                if tag.is_remote:
                    remote_tags.add(tag.name)
                else:
                    local_tags.add(tag.name)

        return {
            "authors": len(authors),
            "branches": len(branches),
            "commits": len(self.commits),
            "tags": len(all_tags),
            "local_tags": len(local_tags),
            "remote_tags": len(remote_tags)
        }