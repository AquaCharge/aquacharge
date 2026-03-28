# AquaCharge

AquaCharge is a React + Flask application for managing EV V2G charging, DR event dispatch, contract booking, and live monitoring for vessel operators and power system operators.

---

## 👥 Developers

- Aidan Foster
- Alex Groom
- Lucas Savoie
- Gabe Vadureanu
- Mackenzie Cooper

---

## 🧰 Tech Stack

- **Frontend:** React (Vite), Yarn
- **Backend:** Python, Flask, Flask-CORS
- **Data:** AWS DynamoDB
- **Infrastructure:** AWS CDK
- **Dev Proxy:** Vite → Flask (`/api` proxied to `http://localhost:5050`)
- **Tooling:** Git, virtualenv, Node.js/Yarn

---

## ✅ Preferred Versions

- **Python:** 3.11 (3.10+ OK)
- **Node.js:** 18 or 20 LTS
- **Yarn:** 1.x or 4.x (Berry) — team choice
- **Flask:** 3.0.x
- **React:** 18.x

---

## ▶️ Run the Backend (Flask) & Create Your Virtual Environment

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug --port 5050
```

Now available at **http://localhost:5050/api/health**

### Windows (PowerShell)

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app app run --debug --port 5050
```

---

## ▶️ Run the Frontend (React + Vite with Yarn)

```bash
cd frontend
yarn install
yarn dev
```

Open **http://localhost:5173**.  
Vite proxies **/api** to **http://localhost:5050** (configured in `frontend/vite.config.js`).

---

## 🎬 Demo Data Seeding

For presentation rehearsal and dashboard population, the repo includes shared demo-data setup commands for both `-dev` and `-prod` tables. Both commands use the same seed logic and produce the same curated station/charger/vessel/history dataset.

### Preview the dev-table mutations

```bash
make demo-data-dev
```

### Apply the reseed

```bash
make demo-data-dev ARGS="--apply"
```

### Preview the prod-table mutations

```bash
make demo-data-prod
```

### Apply the prod reseed

```bash
make demo-data-prod ARGS="--apply --confirm-production"
```

### What the demo seed does

- Creates demo stations in Moncton, Saint John, and Halifax
- Creates chargers for each seeded station
- Sets Sarah Chen’s current vessel to the Halifax demo vessel
- Seeds six finalized historical DR events across the previous week (`Completed` / `Archived`) with bookings, contracts, and measurements
- Leaves a clean live-demo path so you can create, dispatch, accept, book, start, monitor, and end a new DR event manually
- Fills the PSO Analytics aggregate 7-day view with enough historical activity to make the charts readable without hand-entering data

### Safety notes

- Dry-run is the default behavior
- Cleanup is item-level only; it does not recreate or truncate tables
- It treats the shared demo operational tables (`stations`, `chargers`, `drevents`, `contracts`, `bookings`, `measurements`) as seed-owned for rehearsal consistency
- `make demo-data-dev` runs with `ENVIRONMENT=dev`
- `make demo-data-prod` runs with `ENVIRONMENT=prod`
- Production apply is blocked unless `--confirm-production` is provided
- Dev seed expects existing users:
  - VO: `sarah.chen@bayshipping.com`
  - PSO: `robert.wilson@gridoperator.com`
- Prod seed expects existing users:
  - VO: `sarah.chen@aquacharge.demo`
  - PSO: `alex.rivera@aquacharge.demo`
- Full rehearsal instructions are in `docs/dev_demo_runbook.md`

## 🧪 Demo-Critical Flow

The current presentation-ready flow is:

1. PSO reviews seeded history on `Dashboard` and `Analytics`
2. PSO creates and dispatches a new DR event
3. VO accepts the contract and books a charger
4. PSO starts the committed event from the PSO dashboard
5. Live measurements stream to the PSO and VO dashboards
6. PSO can end the active event manually for demo timing control

---

## 🤝 How to Contribute (Branch Flow)

1. **Sync main**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Create a feature branch**
   ```bash
   git checkout -b ticket/<short-description>
   ```
3. **Commit regularly**
   ```bash
   git add .
   git commit -m "feat: add booking list component"
   ```
4. **Push and open a PR**
   ```bash
   git push -u origin ticket/<short-description>
   # then open a Pull Request in GitHub from your branch → main
   ```
5. **Reviews & merge**
   - Keep PRs small and focused.
   - Address comments, then squash/merge.

---

## 📂 Directory Structure

```
aquacharge/
├─ backend/
│  ├─ app.py                 # Flask app entrypoint
│  ├─ api/                   # Backend API routes
│  ├─ services/              # Domain services and dispatch logic
│  ├─ models/                # Data models
│  ├─ test/                  # Backend test suite
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html
│  ├─ package.json           # Yarn
│  ├─ vite.config.js         # Proxies /api → http://localhost:5050
│  └─ src/
│     ├─ components/
│     ├─ contexts/
│     └─ pages/
├─ infra/                    # AWS CDK infrastructure
├─ docs/                     # Contracts, runbooks, and implementation notes
├─ .gitignore
└─ README.md
```
