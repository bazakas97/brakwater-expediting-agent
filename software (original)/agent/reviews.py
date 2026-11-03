"""Reviews: what a buyer decided about each suggestion. Loading, saving and matching. Plain code.

A review belongs to ONE build of data/decisions.json (its built_at). When the decisions are
rebuilt, older reviews are "outdated": they stay in the file, but they do not count as done.
This file is the only thing the page writes. Nothing here sends an email or touches the ERP.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from view import sort_orders

REVIEWS_PATH = Path(__file__).parent / "data" / "reviews.json"

NEEDS_REVIEW = ["escalate", "chase_supplier", "book_in", "wait"]  # everything except "none"
VERDICTS = ["approved", "rejected"]

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
OUTDATED = "outdated"


def orders_to_review(orders: list[dict]) -> list[dict]:
    """The orders a buyer must look at: every action except "none", most urgent first, by delivery date."""
    return sort_orders([o for o in orders if o["action"] in NEEDS_REVIEW])


def load_reviews(path: Path = REVIEWS_PATH) -> list[dict]:
    """All reviews ever saved, oldest first. No file yet means no reviews."""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def make_review(order: dict, verdict: str, comment: str, built_at: str, now: datetime | None = None) -> dict:
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}, got {verdict!r}")
    now = now or datetime.now(timezone.utc)
    return {
        "po_number": order["po_number"],
        "action": order["action"],  # the suggestion that was reviewed
        "verdict": verdict,
        "comment": comment.strip(),
        "reviewed_at": now.isoformat(timespec="seconds"),
        "built_at": built_at,  # which build of decisions.json this review is about
    }


def save_review(review: dict, path: Path = REVIEWS_PATH) -> None:
    """Add one review at the end. Earlier reviews stay, so there is a trail. Written in one go."""
    reviews = load_reviews(path) + [review]
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(reviews, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_path, path)


def latest_by_po(reviews: list[dict]) -> dict[str, dict]:
    """The most recent review of each order (the file is in time order, so the last one wins)."""
    return {review["po_number"]: review for review in reviews}


def status_for(order: dict, latest: dict[str, dict], built_at: str) -> str:
    """pending, approved, rejected or outdated (reviewed, but for an older build of the decisions)."""
    review = latest.get(order["po_number"])
    if review is None:
        return PENDING
    if review["built_at"] != built_at or review["action"] != order["action"]:
        return OUTDATED
    return review["verdict"]


def statuses(orders: list[dict], reviews: list[dict], built_at: str) -> dict[str, str]:
    latest = latest_by_po(reviews)
    return {o["po_number"]: status_for(o, latest, built_at) for o in orders}


def progress(to_review: list[dict], status_by_po: dict[str, str]) -> tuple[int, int]:
    """(reviewed, total). Only a valid approved or rejected review counts as reviewed."""
    done = sum(1 for o in to_review if status_by_po[o["po_number"]] in (APPROVED, REJECTED))
    return done, len(to_review)


def describe_review(status: str, review: dict | None) -> str:
    """One line for under the order, e.g. 'Approved on 2026-11-03 14:05:00+00:00 · "ok"'."""
    if review is None:
        return "Not reviewed yet"
    when = review["reviewed_at"].replace("T", " ")
    comment = f' · "{review["comment"]}"' if review["comment"] else ""
    if status == OUTDATED:
        return (f"Outdated: {review['verdict']} on {when}, but the decisions were rebuilt since. "
                f"Please review again.{comment}")
    return f"{review['verdict'].capitalize()} on {when}{comment}"
