"""Place supplements inline without changing or duplicating the analysis data."""
from __future__ import annotations
import re
from typing import Any


def figure_number(figure: dict[str, Any]) -> tuple[int, str]:
    match = re.search(r'fig(?:ure)?\.?\s*(?:s|ed)?\s*(\d+)', figure['label'], re.I)
    numbers = re.findall(r'\d+', figure['label'])
    return (int(match.group(1)) if match else int(numbers[0]) if numbers else 10**9, figure['label'])


def figure_layout(figures: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    mains = sorted((f for f in figures if f['kind'] == 'main'), key=figure_number)
    supplements = sorted((f for f in figures if f['kind'] == 'supplementary'), key=figure_number)
    placed: set[str] = set()
    slots = []
    for main in mains:
        related = [s for s in supplements if s['id'] in main['related_figures'] or main['id'] in s['related_figures']]
        placed.update(s['id'] for s in related)
        slots.append({'main': main, 'supplements': related})
    return slots, [s for s in supplements if s['id'] not in placed]
