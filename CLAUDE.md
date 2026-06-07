# CLAUDE.md — Diesel Requisition System

A small internal Streamlit web app for diesel fuel requisitions (multi-user, login-gated, not public).
Stack: Python + Streamlit, PostgreSQL on Neon via `st.connection("postgresql", type="sql")`, deployed on Streamlit Community Cloud.

**`BUILD_PLAN.md` is the authoritative spec.** Follow it. Build one stage at a time. At the end of each stage, run that stage's Acceptance Checklist, update `CHANGELOG.md` and `README.md`, then stop and report before starting the next stage.

## Code style — simple and elegant above all
- Favor clarity over cleverness. Write the simplest code that works.
- Small, single-purpose functions; descriptive names.
- No premature abstraction, no patterns the task doesn't need, no extra layers.
- Comment only where intent isn't obvious. No noise comments.
- Keep dependencies minimal (streamlit, pandas, sqlalchemy, psycopg2-binary). Don't add others without asking.
- Match the existing structure; don't reorganize files unprompted.

## Foundation & correctness
- The full database schema is built once in Stage 0 (BUILD_PLAN §5). Don't change it casually; later stages only add UI.
- Don't break working features when adding new ones. Re-check existing screens after a change.
- Handle empty states and nulls gracefully — no data yet must show a friendly message, never a crash.

## Secrets & safety (non-negotiable)
- NEVER hardcode the database URL, passwords, or any secret. Always read from Streamlit secrets.
- NEVER commit secrets. Ensure `.gitignore` includes `.streamlit/secrets.toml`, `.venv/`, `__pycache__/`.
- NEVER run destructive SQL (DROP, DELETE, TRUNCATE) or delete data/files without an explicit instruction.

## Maintain the docs (every meaningful change)
- `CHANGELOG.md` — update whenever behavior changes. Keep a Changelog format: dated section per stage, entries under Added / Changed / Fixed, newest on top.
- `README.md` — keep accurate to the current state (overview, roles, setup, deploy, schema, structure, current status). If a change makes the README wrong, fix it in the same step.

## Working method
1. Before writing code, briefly state your plan and which BUILD_PLAN stage/task it serves.
2. Make the smallest change that accomplishes the task.
3. Double-check before declaring done:
   - Re-read the changed code for errors, leftover/unused code, typos.
   - Confirm it runs (`streamlit run app.py`) with no errors.
   - Walk the relevant flow as each affected role using the dev role switcher.
   - Test edge cases: empty tables, a rejected item, a back-dated draw, a null actual.
   - Check the change against the stage's Acceptance Checklist in BUILD_PLAN.
4. Update `CHANGELOG.md` and `README.md`.
5. Report what changed and confirm the checklist passed. Don't start the next stage until told.

## When unsure
Stop and ask rather than guessing or inventing scope. A small clarifying question beats a wrong assumption.
