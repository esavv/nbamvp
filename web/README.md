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

Prediction browsing works without AWS credentials. To exercise the subscription flow locally, use AWS credentials with SES/SSM access and either create `/nbamvp/subscription-token-secret` or set:

```bash
export SUBSCRIPTION_TOKEN_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export WEBAPP_URL="http://localhost:5173"
```

SES sandbox restrictions still apply to confirmation-email recipients.

Weekly email test sends can run locally without SSM access by using the restricted policy in `deploy/local-dev-iam-policy.json`:

```bash
AWS_PROFILE=nbamvp-dev \
ADMIN_EMAIL=you@example.com \
venv/bin/python src/preview_nba_email.py --season 2026 --week 25 --send
```

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

In production, the backend uses the EC2 instance role and reads its administrator email and subscription signing secret from SSM Parameter Store. See [`ADMIN.md`](../ADMIN.md) and [`deploy/iam-policy.json`](deploy/iam-policy.json).
