# Archived: the MVP-0.2 vanilla frontend

Moved here from the repository root on 2026-07-07 (audit QW-2,
`docs/audit-2026-07-07.md`, finding M-OPS-5).

These three files (`index.html`, `app.js`, `style.css`) were the original
MVP-0.2 prototype UI, frozen on 2026-06-10. They were never served by the
backend (no `StaticFiles` mount, no route), never referenced by the README,
and rotted ~15 milestones behind the API while sitting at the repo root
masquerading as a live frontend.

The real operator console is **`frontend/`** (Next.js + Zustand) — see
"Running Locally" in the top-level README.

Kept for the historical record; safe to delete outright whenever the
record stops being interesting.
