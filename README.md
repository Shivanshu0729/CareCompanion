# CareCompanion

CareCompanion is an agentic AI health and wellness coach. It keeps long-term memory in PostgreSQL, personalizes advice across separate conversations, and can show labelled measurements from the [PMData Fitbit research dataset](https://datasets.simula.no/pmdata/).

This is a wellness coaching application, not a medical diagnosis or prescribing system.

## Problem

Most chatbots forget everything when a new thread starts. CareCompanion stores goals, obstacles, recommendations, commitments and reported outcomes in Supabase Postgres, then retrieves only the records relevant to the current message.

## Main features

- Email registration, login, logout and password reset through Supabase Auth
- Multi-thread conversations with persisted messages
- Groq-hosted LLM coaching (no fake replies)
- User-level long-term memory shared across conversations
- Goals, recommendations, obstacles and outcomes dashboards
- Interactive Plotly health dashboard from processed PMData summaries
- Clearly labelled demo participant mapping (research data is never treated as a public user's personal Fitbit)
- Automated tests with mocked Groq and an isolated in-memory store

## Architecture

```
Streamlit UI
    -> AuthService (Supabase Auth)
    -> SupabaseCareStore (anon key + user access token, RLS)
    -> WellnessCoach
         -> MemoryManager (structured retrieval)
         -> HealthService (processed PMData CSV)
         -> ContextBuilder
         -> GroqClient (LLMProvider)
         -> MemoryExtractor
```

The database is the source of persistent memory. The model context window is only used for the current turn.

## Technology stack

Python, Streamlit, Groq Python SDK, Supabase Auth and Postgres, Pandas, NumPy, Plotly, Pydantic, python-dotenv, Pytest.

## Folder structure

```
CareCompanion/
  app.py
  requirements.txt
  config/settings.py
  src/auth/
  src/database/
  src/llm/
  src/agent/
  src/data/
  src/services/
  src/ui/
  data/pmdata/raw/
  data/pmdata/processed/
  migrations/001_schema.sql
  scripts/process_pmdata.py
  tests/
```

`src/database/in_memory.py` is a test double with the same store contract. Production traffic uses `SupabaseCareStore` only.

## Installation

Python 3.11 is recommended.

```powershell
cd "C:\Users\shiva\ML projects\CareCompanion"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment configuration

Copy `.env.example` to `.env` and fill in values. Never commit `.env`.

```
GROQ_API_KEY=
GROQ_MODEL=
SUPABASE_URL=
SUPABASE_ANON_KEY=
DATABASE_URL=
APP_URL=http://localhost:8501
AUTH_COOKIE_SECRET=replace-with-a-long-random-secret
```

For Streamlit Community Cloud, put the same keys in **App settings → Secrets**.

After sign-in, CareCompanion stores an encrypted, 30-day browser session cookie
and refreshes the Supabase session when the app reconnects. Set
`AUTH_COOKIE_SECRET` to a long random value in production. If it is omitted,
the configured Supabase anon key is used as a fallback encryption seed; setting
the dedicated secret is recommended so rotating the anon key does not invalidate
login cookies. Logging out removes the cookie.

## Web UI

The project also includes a React frontend in `frontend/`. Start the API and
frontend in separate terminals during development:

```powershell
.\.venv\Scripts\uvicorn.exe api.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The browser UI uses the FastAPI endpoints and
HttpOnly session cookie. To build the frontend for the API to serve:

```powershell
Set-Location frontend
npm run build
```

Then open `http://localhost:8000`.

## Groq API configuration

1. Create an API key at [Groq Console](https://console.groq.com/).
2. Choose a current chat model ID from the Groq dashboard and set `GROQ_MODEL` to that ID. Do not hardcode a retired model.
3. Optional live smoke test (uses the paid/free quota):

```powershell
python scripts/smoke_groq.py
```

Automated tests mock Groq and do not send paid requests.

## Supabase configuration

1. Create a project at [supabase.com](https://supabase.com/).
2. Enable Email auth.
3. Copy Project URL into `SUPABASE_URL`.
4. Copy the **anon public** key into `SUPABASE_ANON_KEY`.
5. Do not put the service-role key in this app or in Streamlit secrets used by the browser-facing process.
6. Optional: copy the Postgres URI into `DATABASE_URL` for applying SQL from the CLI.

## Database setup

In the Supabase SQL editor, run `migrations/001_schema.sql`.

That script creates the required tables, indexes and row-level security policies. Every user-owned row is limited by `auth.uid() = user_id`.

If the existing project was created before conversation-linked memories were
added, also run `migrations/002_conversation_memory_links.sql`. It adds the
`conversation_id` columns and reloads the PostgREST schema cache. Without this
step, memory persistence will fail with a missing-column error.

Run `migrations/003_memory_consent_and_versions.sql` after that migration. It
adds confirmation and current-version fields used by the memory controls,
health-memory consent flow, and historical value tracking.

Run `migrations/004_backfill_memory_keys.sql` once to identify older weight,
height, and age memories created before update tracking was added. This lets
new values supersede those older records instead of leaving two current values.

If `DATABASE_URL` is set to a privileged connection string, you can also run:

```powershell
python -m src.database.migrations
```

Use that only on a trusted machine. Privileged database credentials must not be exposed to users.

## PMData setup

1. Download PMData from [Simula](https://datasets.simula.no/pmdata/) or [Kaggle](https://www.kaggle.com/datasets/vlbthambawita/pmdata-a-sports-logging-dataset).
2. Unzip participant folders into `data/pmdata/raw/` so you have `data/pmdata/raw/p01/fitbit/...`.
3. Process supported files:

```powershell
python scripts/process_pmdata.py
```

The loader inspects actual files. It currently understands Fitbit `dateTime`/`value` JSON, nested resting heart-rate objects, `sleep.json` (`minutesAsleep`, `duration`) and `sleep_score.csv`. Minute-level `steps.json` is aggregated when present. Missing measurements stay missing; they are not filled with zero.

Raw exports are gitignored. Processed CSVs in `data/pmdata/processed/` are small enough to keep.

The dashboard and coach always label this data as research-participant PMData, not as the signed-in user's personal device.

## Local execution

```powershell
streamlit run app.py
```

Open http://localhost:8501

Register two accounts and confirm they cannot see each other's conversations.

## Testing

```powershell
python -m pytest
```

Tests cover Groq error handling, auth validation, conversation CRUD, memory storage and retrieval, user isolation, PMData cleaning, context construction and a three-session personalization flow. Groq and Supabase network calls are mocked or replaced.

## Three-session demonstration

Use a dedicated demo account.

1. New conversation: `I have an inconsistent sleep schedule. I want to improve my sleep routine.`
2. New conversation: `I tried sleeping at 11 PM, but I could not maintain it.`
3. New conversation: `I managed to maintain a more consistent bedtime for the last few days.`

Open **My Memory** after each turn. Session 2 should retrieve the sleep goal and first recommendation. Session 3 should retrieve the obstacle and later record the reported outcome. Responses come from Groq with retrieved memory in the prompt; they are not hardcoded per session.

## Deployment (Streamlit Community Cloud)

The application is prepared for deployment. It is not deployed from this repository until you connect the GitHub repo in Streamlit Cloud.

1. Push the project to GitHub without `.env` or raw PMData.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Select the repository, main branch, and `app.py`.
4. Add secrets: `GROQ_API_KEY`, `GROQ_MODEL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_URL`.
5. Set `APP_URL` to the Streamlit Cloud URL so password-reset emails can return to the app.
6. In Supabase Auth, add that URL to allowed redirect URLs.
7. Confirm `migrations/001_schema.sql` has been applied.
8. Include `data/pmdata/processed/daily_summaries.csv` in the repo, or process PMData in CI before deploy.

## Security and health limitations

- Passwords stay in Supabase Auth. Application tables store only the user id and email.
- Queries use the user access token so Postgres RLS is enforced.
- The Groq API key stays on the server process and is never rendered in the UI.
- CareCompanion does not diagnose conditions, prescribe medicines, or invent measurements.
- Concerning symptoms should be taken to a clinician or emergency service.

## Environment variables you must set

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq secret |
| `GROQ_MODEL` | Current Groq model id |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `DATABASE_URL` | Optional privileged Postgres URI for CLI migrations |
| `APP_URL` | Public app URL for password reset redirects |
