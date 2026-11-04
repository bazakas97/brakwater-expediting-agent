"""The page with real files in a temporary folder: reviews, a rebuild, and a tab that was opened before it.

The tests never touch the real data folder: paths.DECISIONS_PATH and paths.REVIEWS_PATH are replaced.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import paths
from build_decisions import to_record, write_decisions
from reviews import load_reviews, make_review, save_review

APP = Path(__file__).parent.parent / "app.py"
NOW = datetime.now(timezone.utc)  # recent, so the page does not warn that the data is old


def raw_order(po: str, action: str) -> dict:
    return {"po_number": po, "supplier_name": "Acme", "project": "BB-2604", "requested_delivery_date": "2026-11-10",
            "confirmed_delivery_date": None, "flags": [], "memo": "", "action": action}


ORDERS = [raw_order("E1", "escalate"), raw_order("C1", "chase_supplier"), raw_order("W1", "wait"), raw_order("N1", "none")]


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DECISIONS_PATH", tmp_path / "decisions.json")
    monkeypatch.setattr(paths, "REVIEWS_PATH", tmp_path / "reviews.json")
    return tmp_path


def build(built_at: datetime, orders: list[dict] = ORDERS) -> str:
    """Write decisions.json like build_decisions.py does. Returns the built_at text of that build."""
    records = [to_record(o, o["action"], "a reason", "llm") for o in orders]
    write_decisions(records, date(2026, 11, 3), "fake", paths.DECISIONS_PATH, built_at)
    return built_at.isoformat(timespec="seconds")


def review(po: str, built_at: str, verdict: str = "approved") -> None:
    order = next(o for o in ORDERS if o["po_number"] == po)
    save_review(make_review(order, verdict, "", built_at))


def run_page() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=30).run()


def progress_text(at: AppTest) -> str:
    return at.get("progress")[0].proto.text


def captions(at: AppTest) -> list[str]:
    return [c.value for c in at.caption]


def approve_buttons(at: AppTest) -> list:
    return [b for b in at.button if b.label == "Approve"]


# --- reviews of the current build count ---

def test_reviews_made_on_the_current_build_count(data):
    built = build(NOW)
    review("E1", built)
    review("C1", built)
    at = run_page()
    assert progress_text(at) == "Reviewed 2 of 3"  # E1, C1 and W1 need a review, N1 does not
    assert not at.exception


# --- the case from the roadmap: reviews on older decisions after a rebuild ---

def test_after_a_rebuild_reviews_of_the_older_decisions_are_outdated_and_do_not_count(data):
    first_build = build(NOW - timedelta(minutes=5))
    review("E1", first_build)
    review("C1", first_build)
    assert progress_text(run_page()) == "Reviewed 2 of 3"

    build(NOW)  # rebuilt: the same orders with the same actions, only the build time is new

    at = run_page()
    assert progress_text(at) == "Reviewed 0 of 3"
    assert len([c for c in captions(at) if c.startswith("Outdated:")]) == 2
    assert not [c for c in captions(at) if c.startswith("Approved")]  # nothing shows as a valid approval
    assert not at.exception


def test_a_review_made_after_the_rebuild_counts_again(data):
    review("E1", build(NOW - timedelta(minutes=5)))
    build(NOW)
    at = run_page()
    approve_buttons(at)[0].click().run()  # a fresh tab on the new build: this click is saved
    assert progress_text(at) == "Reviewed 1 of 3"
    assert [r["built_at"] for r in load_reviews()][-1] == NOW.isoformat(timespec="seconds")


# --- a tab that was opened before the rebuild ---

def test_a_click_in_a_tab_opened_before_the_rebuild_is_not_saved(data):
    build(NOW - timedelta(minutes=5))
    at = run_page()                      # the buyer opens the page: he sees the first build
    build(NOW)                           # the decisions are rebuilt while the tab stays open
    approve_buttons(at)[0].click().run()  # he clicks Approve on what he sees

    assert load_reviews() == []          # nothing was saved: he never saw the new decisions
    assert any("NOT saved" in w.value for w in at.warning)
    assert progress_text(at) == "Reviewed 0 of 3"


def test_the_next_click_after_that_warning_is_saved_for_the_new_build(data):
    build(NOW - timedelta(minutes=5))
    at = run_page()
    build(NOW)
    approve_buttons(at)[0].click().run()   # not saved, the tab now shows the new decisions
    approve_buttons(at)[0].click().run()   # saved
    assert [r["built_at"] for r in load_reviews()] == [NOW.isoformat(timespec="seconds")]
    assert progress_text(at) == "Reviewed 1 of 3"


def test_without_a_rebuild_a_click_is_saved_and_there_is_no_warning(data):
    build(NOW)
    at = run_page()
    approve_buttons(at)[0].click().run()
    assert len(load_reviews()) == 1
    assert not any("NOT saved" in w.value for w in at.warning)
    assert not any("rebuilt" in i.value for i in at.info)
