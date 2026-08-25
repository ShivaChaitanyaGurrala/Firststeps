"""Curation rules deciding which TMDB entities get enriched during a bulk seed.

The daily export files list ~1M+ ids; we only want a manageable local subset,
so we rank by the 'popularity' field already present in the export line itself
(no API calls needed just to decide what to keep).
"""

from typing import Any


def curate_top_n(
    export_rows: list[dict[str, Any]], n: int, *, exclude_adult: bool = True
) -> list[int]:
    rows = [r for r in export_rows if not (exclude_adult and r.get("adult"))]
    rows.sort(key=lambda r: r.get("popularity", 0.0), reverse=True)
    return [r["id"] for r in rows[:n]]
