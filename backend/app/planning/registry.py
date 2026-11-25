"""Build an SQLite index of the bundled guides. The catalog distinguishes bundled guides from dated facts sourced to official tourism sites."""

import sqlite3
from pathlib import Path

from app.rag.pipeline import parse_frontmatter


def lookup(city: str) -> dict:
    root = Path(__file__).resolve().parents[1] / "rag" / "data"
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE guides (city TEXT, file TEXT, title TEXT)")
        for guide in sorted(root.glob("*.md")):
            meta, _ = parse_frontmatter(guide.read_text(encoding="utf-8"))
            db.execute(
                "INSERT INTO guides VALUES (?,?,?)",
                (
                    meta["destination"].split(",")[0].strip().casefold(),
                    guide.name,
                    meta["source"],
                ),
            )
        guides = [
            {"file": f, "title": t}
            for f, t in db.execute(
                "SELECT file,title FROM guides WHERE city=?",
                (city.split(",")[0].strip().casefold(),),
            )
        ]
        db.executescript(
            Path(__file__).with_name("registry.sql").read_text(encoding="utf-8")
        )
        db.row_factory = sqlite3.Row
        name, _, country = city.casefold().partition(",")
        name = name.strip()
        if name == "delhi":
            name = "new delhi"
        facts = [
            dict(row)
            for row in db.execute(
                "SELECT title,fact,source,checked_on FROM facts WHERE city=? AND country=?",
                (name, country.strip()),
            )
        ]
        return {"records": guides, "facts": facts}
    finally:
        db.close()
