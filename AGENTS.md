# AquaCharge — Agent Instructions (tool-agnostic)

Applies to any coding agent (Codex, Claude Code, Cursor agents, etc.).

## Prime directive
Minimize git conflicts. Prefer small, isolated changes per ticket.

## Isolation: one ticket = one branch/worktree
- Create a new branch (and ideally a worktree) per ticket:
  - `ticket/<JIRA_KEY>-<short-slug>`
  - Example: `ticket/SCRUM-158-users-table`
- Never commit directly to `main`.

## Repo layout (actual)
- Backend (Flask): `backend/`
- Frontend (Vite/React): `frontend/`
- Infra (AWS CDK): `infra/`

## Ownership boundaries (edit only your area)
**Frontend owner**
- `frontend/**`

**Backend DB/Infra owner**
- `backend/db/**`
- `infra/**`

**Backend Auth/Monitoring owner**
- `backend/middleware/**`
- `backend/api/auth.py`
- `backend/test/testAuth.py` (if needed)

**Backend Domain/Services owner**
- `backend/api/**` (except `auth.py` unless coordinated)
- `backend/models/**`
- `backend/services/**`

If you must touch outside your owned area:
- Keep it minimal
- Call it out in PR + Jira comment

## Hot files (avoid; common conflict points)
- `backend/app.py`
- `backend/config.py`
- Any central API registration in `backend/api/__init__.py`
Rules:
- Avoid touching hot files if possible
- No refactors or formatting-only commits
- Keep hot-file diffs tiny (<10 lines when possible)

## Contracts first (enables parallel work)
Before implementing logic:
- Add/extend contracts in `docs/api.md` or `docs/contracts.md` (create if missing)
Include:
- endpoint paths + request/response JSON
- model fields (User, Org, Vessel, Booking, DREvent, Contract)
- error shapes

Prefer additive edits (do not rewrite existing docs).

## DB dependency rule (don’t block others)
Backend work must not block on DynamoDB table availability:
- code to repository/service interfaces
- provide an in-memory stub when needed
- keep swap from stub → Dynamo minimal

## Local commands (actual from repo)
### Frontend (from repo root)
- Install: `cd frontend && yarn install`
- Dev: `cd frontend && yarn dev`
- Lint: `cd frontend && yarn lint`
- Test: `cd frontend && yarn test`
- Build: `cd frontend && yarn build`

### Backend (from repo root)
Create venv & install:
- `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Run:
- `cd backend && source .venv/bin/activate && flask --app app run --debug --port 5050`

Test:
- `cd backend && source .venv/bin/activate && pytest`

Lint:
- `cd backend && source .venv/bin/activate && flake8`

### Infra (CDK) (from repo root)
- Install: `cd infra && npm install`
- Build: `cd infra && npm run build`
- Lint: `cd infra && npm run lint`
- Test: `cd infra && npm test`

## Required output for every ticket
- Summarize what changed
- List files touched
- Provide exact test commands + results
- Post a Jira comment with the same info

## Safety rails
- Do not commit secrets. `.env`, `.venv`, `node_modules`, `__pycache__` are ignored (verify they are not tracked).
- Prefer small PRs.
- Avoid changing dependency lockfiles unless required for the ticket.