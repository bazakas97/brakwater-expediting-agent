import json
from datetime import datetime, timezone

import pytest

import reviews
from reviews import (APPROVED, OUTDATED, PENDING, REJECTED, describe_review, latest_by_po, load_reviews,
                     make_review, orders_to_review, progress, save_review, status_for, statuses)

BUILD_1 = "2026-11-03T12:00:00+00:00"
BUILD_2 = "2026-11-04T09:00:00+00:00"
NOW = datetime(2026, 11, 3, 14, 5, tzinfo=timezone.utc)


def order(po: str, action: str = "escalate", delivery_date: str = "2026-11-10") -> dict:
    return {"po_number": po, "action": action, "delivery_date": delivery_date}


# --- which orders need a review ---

def test_every_action_except_none_needs_review_most_urgent_first():
    orders = [order("N", "none"), order("W", "wait", "2026-11-02"), order("B", "book_in", "2026-11-03"),
              order("C", "chase_supplier", "2026-11-01"), order("E", "escalate", "2026-12-01")]
    assert [o["po_number"] for o in orders_to_review(orders)] == ["E", "C", "B", "W"]


# --- making and saving reviews ---

def test_review_has_all_the_fields():
    review = make_review(order("PO1", "chase_supplier"), "approved", "  looks fine \n", BUILD_1, NOW)
    assert review == {"po_number": "PO1", "action": "chase_supplier", "verdict": "approved",
                      "comment": "looks fine", "reviewed_at": "2026-11-03T14:05:00+00:00", "built_at": BUILD_1}


def test_verdict_must_be_approved_or_rejected():
    with pytest.raises(ValueError, match="verdict"):
        make_review(order("PO1"), "maybe", "", BUILD_1)


def test_no_file_means_no_reviews(tmp_path):
    assert load_reviews(tmp_path / "reviews.json") == []


def test_saving_adds_to_the_end_and_keeps_the_trail(tmp_path):
    path = tmp_path / "reviews.json"
    save_review(make_review(order("PO1"), "rejected", "no", BUILD_1, NOW), path)
    save_review(make_review(order("PO1"), "approved", "ok after all", BUILD_1, NOW), path)
    saved = load_reviews(path)
    assert [r["verdict"] for r in saved] == ["rejected", "approved"]


def test_saving_writes_only_the_reviews_file(tmp_path):
    path = tmp_path / "data" / "reviews.json"
    save_review(make_review(order("PO1"), "approved", "", BUILD_1, NOW), path)
    assert [p.name for p in path.parent.iterdir()] == ["reviews.json"]  # no temp file left behind
    assert json.loads(path.read_text(encoding="utf-8"))[0]["po_number"] == "PO1"


def test_the_default_path_is_data_reviews_json():
    assert reviews.REVIEWS_PATH.name == "reviews.json"
    assert reviews.REVIEWS_PATH.parent.name == "data"


# --- matching reviews to the current decisions ---

def review(po: str, verdict: str, built_at: str = BUILD_1, action: str = "escalate") -> dict:
    return {"po_number": po, "action": action, "verdict": verdict, "comment": "", "reviewed_at": "x",
            "built_at": built_at}


def test_order_without_review_is_pending():
    assert status_for(order("PO1"), {}, BUILD_1) == PENDING


def test_review_of_the_current_build_gives_its_verdict():
    latest = latest_by_po([review("PO1", "approved"), review("PO2", "rejected")])
    assert status_for(order("PO1"), latest, BUILD_1) == APPROVED
    assert status_for(order("PO2"), latest, BUILD_1) == REJECTED


def test_review_of_an_older_build_is_outdated_not_valid():
    latest = latest_by_po([review("PO1", "approved", built_at=BUILD_1)])
    assert status_for(order("PO1"), latest, BUILD_2) == OUTDATED


def test_review_of_a_different_action_is_outdated():
    latest = latest_by_po([review("PO1", "approved", action="chase_supplier")])
    assert status_for(order("PO1", "escalate"), latest, BUILD_1) == OUTDATED


def test_the_latest_review_wins():
    latest = latest_by_po([review("PO1", "rejected"), review("PO1", "approved")])
    assert status_for(order("PO1"), latest, BUILD_1) == APPROVED


def test_a_new_review_after_a_rebuild_makes_it_valid_again():
    old, new = review("PO1", "approved", BUILD_1), review("PO1", "rejected", BUILD_2)
    assert status_for(order("PO1"), latest_by_po([old, new]), BUILD_2) == REJECTED


# --- progress ---

def test_progress_counts_only_valid_reviews():
    to_review = [order("A"), order("B"), order("C"), order("D")]
    reviews_list = [review("A", "approved"), review("B", "rejected"), review("C", "approved", built_at=BUILD_1)]
    by_po = statuses(to_review, reviews_list, BUILD_2)          # after a rebuild: all three are outdated
    assert progress(to_review, by_po) == (0, 4)
    by_po = statuses(to_review, reviews_list, BUILD_1)          # same build: A, B, C count, D is pending
    assert progress(to_review, by_po) == (3, 4)


def test_reviews_of_orders_that_are_gone_are_ignored():
    to_review = [order("A")]
    by_po = statuses(to_review, [review("GONE", "approved"), review("A", "approved")], BUILD_1)
    assert progress(to_review, by_po) == (1, 1)


# --- the line under an order ---

def test_describe_review_texts():
    approved = {**review("PO1", "approved"), "comment": "ok", "reviewed_at": "2026-11-03T14:05:00+00:00"}
    assert describe_review(PENDING, None) == "Not reviewed yet"
    assert describe_review(APPROVED, approved) == 'Approved on 2026-11-03 14:05:00+00:00 · "ok"'
    assert describe_review(OUTDATED, approved).startswith("Outdated: approved on")
    assert "review again" in describe_review(OUTDATED, approved)
