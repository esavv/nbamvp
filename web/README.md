# NBA MVP Predictor Web App

The web app reads the existing CSV files in `data/` through a FastAPI backend and displays them in a React frontend.

## Local preview

From the repository root, install the backend dependencies:

```bash
source venv/bin/activate
pip install -r web/backend/requirements.txt
```

In one terminal, start the API:

```bash
cd web/backend
../../venv/bin/uvicorn app.main:app --reload
```

In a second terminal, start the frontend:

```bash
cd web/frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally [http://localhost:5173](http://localhost:5173).

## Production build

Build the frontend:

```bash
cd web/frontend
npm ci
npm run build
```

When `web/frontend/dist` exists, FastAPI serves the compiled site as well as the API. Run the complete app from `web/backend`:

```bash
../../venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```
