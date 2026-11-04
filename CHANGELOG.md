# Changelog

What changed in each version. The plan for version 2 is in [ROADMAP_V2.md](ROADMAP_V2.md); every
step there is one pull request into the `v2` branch.

## v2 (in progress)

Nothing released yet. Steps are added here as their pull requests are merged.

## v1 (2026-11)

The first working version: a read-only assistant that suggests, and a human decides.

- Reads the open orders, suppliers and projects from the read-only Keelson ERP API.
- Flags orders with plain code (`NO_CONFIRMATION`, `DUE_WITHIN_14_DAYS`, `OVERDUE`) and a triage that
  decides which orders need the LLM.
- One decision per order, with a reason of at most 20 words: `escalate`, `chase_supplier`, `book_in`,
  `wait` or `none`. Answers are validated, retried once, and fall back to `escalate`.
- ERP update proposals: the LLM reads the memo, plain code turns weeks and dates into days and keeps
  only what the ERP does not have yet.
- Draft emails: plain code decides the recipient and the language (a "Via project manager" supplier is
  never written to); the LLM writes the text; the code checks it.
- A Streamlit page: timeline, one card per suggestion, comment and Approve / Reject.
- Reviews are tied to a build: after a rebuild they show as outdated, and a tab opened before a rebuild
  cannot save a review.
- Fake mode (no key) and real mode (Anthropic API), a read-only page enforced by tests, README.
