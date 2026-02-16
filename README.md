# AquaCharge

A minimal React + Flask starter for **AquaCharge** — an application exploring EV V2G booking and monitoring.

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

## 🤝 How to Contribute (Branch Flow)

1. **Sync main**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Create a feature branch**
   ```bash
   git checkout -b feature/<short-description>
   ```
3. **Commit regularly**
   ```bash
   git add .
   git commit -m "feat: add booking list component"
   ```
4. **Push and open a PR**
   ```bash
   git push -u origin feature/<short-description>
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
│  ├─ app.py                 # Flask app: /api/health, /api/sites
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html
│  ├─ package.json           # Yarn
│  ├─ vite.config.js         # Proxies /api → http://localhost:5050
│  └─ src/
│     ├─ main.jsx
│     └─ App.jsx
├─ .gitignore
└─ README.md
```
