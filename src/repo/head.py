"""Stav HEAD repozitáře: na které větvi a na kterém commitu uživatel stojí.

HEAD je v jednom ze tří stavů:

- **na větvi** - ``branch`` je jméno větve, ``commit`` její poslední commit;
- **odpojený (detached)** - po ``git checkout <hash|tag>``: ``branch`` je None,
  ``commit`` je commit, na kterém uživatel stojí. Commity vytvořené v tomto
  stavu nepatří žádné větvi;
- **nenarozená větev** - čerstvý ``git init`` bez commitu: ``branch`` je jméno
  budoucí větve, ``commit`` je None.
"""

from dataclasses import dataclass
from typing import Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Jméno, pod kterým se v grafu vedou commity a rozpracované změny odpojeného HEAD.
# Skutečná větev se tak jmenovat nemůže (Git jméno HEAD pro větev odmítá).
DETACHED_HEAD = 'HEAD'


@dataclass(frozen=True)
class HeadState:
    branch: Optional[str] = None  # Jméno aktuální větve; None při odpojeném HEAD
    commit: Optional[str] = None  # Plný hash commitu pod HEAD; None bez commitu

    @property
    def is_detached(self) -> bool:
        return self.branch is None and self.commit is not None

    @property
    def branch_label(self) -> str:
        """Jméno větve pro graf (u odpojeného HEAD zástupné ``DETACHED_HEAD``)."""
        return self.branch or DETACHED_HEAD


def read_head_state(repo) -> HeadState:
    """Přečte stav HEAD z GitPython repozitáře; při chybě vrátí prázdný stav."""
    if repo is None:
        return HeadState()

    try:
        head = repo.head
        branch = None
        # is_detached je u GitPythonu bool; cokoli jiného (např. Mock v testech)
        # neznamená nic a bere se jako "nevíme"
        detached = head.is_detached
        if detached is False:
            branch = head.reference.name
            if not isinstance(branch, str):
                branch = None
        elif detached is not True:
            return HeadState()

        try:
            commit = head.commit.hexsha
        except ValueError:
            commit = None  # Nenarozená větev: ref existuje, commit ještě ne
        if not isinstance(commit, str):
            commit = None

        return HeadState(branch=branch, commit=commit)
    except Exception as e:
        logger.warning(f"Failed to read HEAD state: {e}")
        return HeadState()
