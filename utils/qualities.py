"""Разбор и проверка трёх сильных качеств профиля."""

from __future__ import annotations


def parse_qualities_to_slots(user_qualities: str | None) -> list[tuple[str, str]]:
    """До 3 слотов (emoji, text). Формат 'emoji|text\\n' или старый текст в одной строке."""
    if not user_qualities or not user_qualities.strip():
        return [("•", ""), ("•", ""), ("•", "")]
    lines = [ln.strip() for ln in user_qualities.strip().split("\n") if ln.strip()]
    slots: list[tuple[str, str]] = []
    for line in lines[:3]:
        if "|" in line:
            emoji, text = line.split("|", 1)
            slots.append((emoji.strip() or "•", text.strip()))
        else:
            slots.append(("•", line))
    while len(slots) < 3:
        slots.append(("•", ""))
    return slots[:3]


def is_quality_slot_filled(user_qualities: str | None, index: int) -> bool:
    """Заполнен ли слот качества (0, 1 или 2)."""
    if index < 0 or index > 2:
        return False
    slots = parse_qualities_to_slots(user_qualities)
    return bool((slots[index][1] or "").strip())


def all_qualities_filled(user_qualities: str | None) -> bool:
    """Все три сильных качества указаны."""
    return all(is_quality_slot_filled(user_qualities, i) for i in range(3))
