from pathlib import Path
from typing import List

from .models import Task


CONFIG_PATH = Path.home() / ".config" / "jos-daily-brief" / "extra-taken.txt"


def fetch_extra_tasks(path: Path = CONFIG_PATH) -> List[Task]:
    if not path.exists():
        return []
    tasks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        title = line.strip()
        if not title or title.startswith("#"):
            continue
        tasks.append(Task(title))
    return tasks
