
# AquaCharge — Minimal Starter (React + Flask)

A minimal starter for **AquaCharge**, with:
- **frontend/**: React (Vite) using **Yarn**
- **backend/**: Flask API

This guide includes **Windows & macOS/Linux** setup and how to avoid committing your virtual environment (venv).

---

## Prerequisites
- Node.js 18+ and **Yarn**
- Python 3.10+ (3.11 recommended)

---

## Getting started

### 1) Backend (Flask)

#### macOS / Linux
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug --port 5050
```

#### Windows (PowerShell)
```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app app run --debug --port 5050
```

Your API should be available at: **http://localhost:5050/api/health**

### 2) Frontend (React + Vite with Yarn)
Open a new terminal:

```bash
cd frontend
yarn install
yarn dev
```
Your app is now at: **http://localhost:5173**

The Vite dev server proxies **/api** to Flask on **http://localhost:5050** (see `frontend/vite.config.js`).

---

## Directory structure
```
.
├─ backend/
│  ├─ app.py
│  └─ requirements.txt
└─ frontend/
   ├─ index.html
   ├─ package.json
   ├─ vite.config.js
   └─ src/
      ├─ main.jsx
      └─ App.jsx
```

---

## Avoid committing virtual environments and node_modules

**Do NOT commit your local Python venv or node_modules; they are OS-specific and huge.**  
We've added these to `.gitignore`, but if you already pushed them once, remove them from Git history.

### Ensure ignored going forward
These entries are in `.gitignore`:
```
.venv/
venv/
node_modules/
```

### If you accidentally committed a venv
```bash
git rm -r --cached .venv  # or 'venv' if that's your folder name
git commit -m "Remove local venv from repo and ignore it"
git push
```

> Need to purge it from the entire history? Consider `git filter-repo` or BFG Repo-Cleaner (history rewrite — coordinate with your team).

---

## Making changes
- Frontend: edit `frontend/src/App.jsx`
- Backend: edit `backend/app.py` and restart Flask (or keep `--debug` for auto-reload)

---

## Troubleshooting
- **Frontend says "loading..."**: Make sure Flask is running on **port 5050** and you can GET `http://localhost:5050/api/health`.
- **Proxy issues**: Check `frontend/vite.config.js` → proxy target is `http://localhost:5050`.
- **Windows execution policy**: If activation is blocked, run PowerShell as admin and `Set-ExecutionPolicy RemoteSigned` (then retry activation).
