# Brakwater expediting assistant (version 1)

A small assistant that helps a purchasing team follow up open purchase orders. It reads the open
orders from an ERP, suggests what to do with each one, drafts the emails and proposes the ERP
updates, and a buyer approves or rejects every suggestion on a simple page.

**It never sends an email and never writes to the ERP.** It only suggests; a human decides.

This is a learning project. It rebuilds a client case (a fictional shipyard, Brakwater Boats B.V.)
step by step. All companies, people and data are fictional. The client brief is in
[PROJECT_BRIEF.md](PROJECT_BRIEF.md), the working rules in [CLAUDE.md](CLAUDE.md), and the plan for
the next version in [ROADMAP_V2.md](ROADMAP_V2.md).

<!-- TODO: add a screenshot of the page here, for example docs/screenshot.png:
![The review page: timeline of the open orders and a card per suggestion](docs/screenshot.png)
-->
> _Screenshot: to be added._

## Versions

| Version | Status | Where |
|---|---|---|
| **v1** | done: the pipeline, the page, reviews, draft emails, ERP proposals, fake and real mode | branch `master` |
| **v2** | in progress: evaluation, orchestration, tracing, retrieval, data pipelines, monitoring, deployment | branch `v2`, plan in [ROADMAP_V2.md](ROADMAP_V2.md), one pull request per step |

What changed in each version: [CHANGELOG.md](CHANGELOG.md).

## The problem

The purchasing team spends hours each week tracking open purchase orders: they run an export, read the
memos buyers wrote in the ERP (Dutch, German, English) and write reminders to suppliers one by one.
Now and then something slips through, with consequences for the delivery of a boat. The export
(`export_open_orders.py`, part of the original kit) lists orders by date flags only; it cannot read
the memos, so it misses things like a price increase, a delivery that already arrived, or an order
that will probably be cancelled.

## What it does

For each of the 60 open orders of the sandbox ERP:

1. **Reads** the open orders, suppliers and projects from the (read-only) Keelson ERP API.
2. **Flags** them with plain code: `NO_CONFIRMATION`, `DUE_WITHIN_14_DAYS`, `OVERDUE`.
3. **Triage:** an order with a flag or a memo goes to the LLM. An order without both gets the action
   `none` straight from code.
4. **Suggests an action** (LLM), with a reason of at most 20 words: `escalate`, `chase_supplier`,
   `book_in`, `wait` or `none`.
5. **Proposes ERP updates:** the LLM reads the memo and reports what it states (a confirmation was
   received, a delivery date or week is named). Plain code turns that into dates, compares it with
   the ERP and keeps only what the ERP does not have yet (two fields: confirmed delivery date and
   order confirmation received).
6. **Drafts emails** for `chase_supplier` and `escalate`. Plain code decides who gets the email and in
   which language; the LLM writes the text.
7. **Shows it on a page:** a timeline of all orders, and a card per suggestion with the reason, the
   memo, the ERP proposal, the draft email, a comment box and **Approve / Reject**.

## How to run

You need **Docker Desktop** (with an up-to-date WSL on Windows: `wsl --update`). You do not need
Python on your computer. All commands run in the folder `software (original)` (PowerShell shown;
in bash use `export` instead of `$env:`).

```powershell
cd "software (original)"
docker compose build

# 1. Tests (no network, no key)
docker compose run --rm agent pytest -q

# 2. Build the decisions in fake mode (no key) and open the page
$env:LLM_MODE = "fake"
docker compose run --rm agent python build_decisions.py
docker compose up -d app          # then open http://localhost:8501
```

If you change code that the page imports (for example `view.py`), restart it:
`docker compose restart app`. The API starts by itself when the agent needs it
(`docker compose up -d keelson-api` to start it by hand, health check at http://localhost:8000/health).

## Fake mode and real mode

| | Fake mode (default) | Real mode |
|---|---|---|
| Switch | `LLM_MODE` unset, empty or `fake` | `LLM_MODE=real` |
| Needs | nothing | `ANTHROPIC_API_KEY` in your shell |
| Actions | simple rules (an overdue order is escalated, any other flag is chased) | the LLM reads the memo |
| ERP proposals | a few text patterns | the LLM reads the memo |
| Draft emails | fixed templates in English, Dutch, German | the LLM writes them |
| Use it for | tests, demos of the pipeline, working without a key | the real suggestions |

Any other value of `LLM_MODE` stops with an error (no silent fallback). The page shows a banner in fake mode.

```powershell
# Real mode: the key lives only in your shell, never in a file
$env:ANTHROPIC_API_KEY = "..."
$env:LLM_MODE = "real"
docker compose run --rm agent python build_decisions.py   # about 80 model calls
$env:LLM_MODE = "fake"                                    # back to the safe default
```

The default model is `claude-haiku-5-5`; set `ANTHROPIC_MODEL` to change it, and run
`docker compose run --rm agent python check_models.py` to list the models your key can use.
The cost of a build is small but **not measured yet** (measuring it is part of the roadmap).
The page's container has no key and no link to the API, so the page itself cannot call the LLM.

## Design decisions

- **The LLM only does language work.** It reads memos, classifies, and writes text. Everything exact
  is plain, tested Python: dates and flags, week numbers to dates, who receives an email, which
  language, money (amounts are never given to the model).
- **Guardrails in code, around every LLM answer.** The answer is validated (Pydantic). A reason over 20
  words is invalid (not cut). An invalid answer is retried once and the retry says why the first was
  rejected. If it fails again, a decision falls back to `escalate` ("needs a human"), never to `none`;
  a draft is kept as a visible problem so the buyer writes the email himself; and when the memo facts
  stay invalid, no ERP proposal is made. The evidence quoted from a memo must exist in the memo. A draft must contain the PO number and the
  buyer's signature. The PO number of a decision always comes from the order, never from the model.
- **A human approves everything.** Nothing is sent and nothing is written to the ERP (the API is
  read-only). An ERP proposal is text a buyer enters by hand; a draft is text a buyer copies into his
  own email.
- **"Via project manager" suppliers are never written to.** If an order of such a supplier needs a
  reminder, the draft goes to the project manager of the project instead. Suppliers never get
  project, customer or internal information.
- **Reviews belong to one build.** If the decisions are rebuilt, earlier reviews show as "outdated" and
  do not count. A tab that was opened before a rebuild cannot save a review for decisions it never
  showed (the click is refused with a message).
- **The page is read-only, except for one file.** It reads `data/decisions.json` and writes only
  `data/reviews.json`. A test checks that the page imports nothing that can reach the LLM, the ERP or
  email, and does not write files itself.
- **A week without a day becomes the Friday of that ISO week**, with a note that the memo gives no
  day. A date without a year takes the year nearest to today (a week that has just passed stays in
  this year and is marked late; "KW 2" said in December means January next year).
- **Not only color:** every action has its own shape in the timeline, and a hollow dot means reviewed.

## Tests

```powershell
docker compose run --rm agent pytest -q
```

All tests run offline. LLM calls are replaced by mocks, so no key is needed.

## Project layout

```
PROJECT_BRIEF.md       the client brief
CLAUDE.md              the working rules for this project
ROADMAP_V2.md          the plan for version 2
software (original)/
  docker-compose.yml   services: keelson-api (the ERP sandbox), agent (jobs and tests), app (the page)
  keelson-api/         the fictional ERP sandbox (original kit)
  agent/
    keelson_client.py  API client (original kit)         expediting.py   the flags (original kit)
    triage.py          which orders need the LLM         decision.py     the five actions, validation
    llm.py             one decision per order            context.py      supplier policy, customer date
    memo_facts.py      facts a memo states               erp_proposals.py  ERP update proposals
    recipients.py      who gets an email and in which language
    email_drafts.py    the email text                    build_decisions.py  builds data/decisions.json
    reviews.py         Approve / Reject records          view.py         exact logic for the page
    app.py             the page (Streamlit)              paths.py        where the data files live
    tests/             the tests
```

## Known limits

- No login: a review does not record which buyer made it.
- The real-mode output was read by hand on a few orders. There is no systematic evaluation yet.
- Emails to colleagues are in Dutch (one constant in `recipients.py`); the brief names no language for them.
- `book_in` (goods arrived, warehouse must book them in) has no draft email: the warehouse has no contact in the data.
- The sandbox shifts all dates, also those inside memos, with today's date.
- The decisions are built by a command, not on a schedule.
