# AquaCharge — Minimal Starter (React + Flask)

A minimal starter for **AquaCharge**, with:

- **frontend/**: React (Vite) using **Yarn**
- **backend/**: Flask API

## Prerequisites

- Node.js 18+ and **Yarn**
- Python 3.10+ (3.11 recommended)

---

## Getting started

### 1) Backend (Flask)

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
flask --app app run --debug --port 5050
```

Your API is now at: http://localhost:5050/api/health

### 2) Frontend (React + Vite with Yarn)

Open a new terminal:

```bash
cd frontend
yarn install
yarn dev
```

Your app is now at: http://localhost:5173

The frontend dev server proxies **/api** to Flask on **http://localhost:5000** (see `vite.config.js`).

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

## Making changes

- Frontend: edit `frontend/src/App.jsx`
- Backend: edit `backend/app.py` and restart Flask (or keep `--debug` for auto-reload)

Have fun!
