import csv
import json
from pathlib import Path

from dynscraper.models import Quote


def save(quotes: list[Quote], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text(
            json.dumps([q.as_dict() for q in quotes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif path.suffix == ".csv":
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["text", "author", "tags"])
            for q in quotes:
                w.writerow([q.text, q.author, ", ".join(q.tags)])
    else:
        raise ValueError("Поддерживаются .csv и .json")
