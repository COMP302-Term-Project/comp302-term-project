# COMP302 Term Project — InClass Platform

Software Engineering term project for the InClass Platform.

## Tech Stack
- Python
- FastAPI
- Supabase (PostgreSQL)

## Required Environment Variables
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- DATABASE_URL
- GOOGLE_CLIENT_ID
- GOOGLE_AUTH_SESSION_SECRET

## Google Auth Demo Flow
- Frontend sends the Google ID token to `POST /auth/google-login` as JSON using `id_token` or `credential`.
- On success, the response includes `email`, `role`, `user`, and `session_token`.
- Existing protected endpoints stay Phase-1 compatible: send the Google email as `email` and the returned `session_token` as `password`.
- If no frontend exists, start the backend and open `/auth/google-test-page` to get a real Google credential for demo testing.

## Demo Runbook
- Install dependencies: `python -m pip install -r requirements.txt`
- Run tests: `python -m pytest tests/`
- Start the API: `python -m uvicorn app.main:app --reload`
- Open the interactive API demo UI at `http://127.0.0.1:8000/docs`.
- Keep the official demo data from `resources/term_project_documents/Student_Demo_Doc.md` loaded before the demo starts.

Notes:
- FastAPI Swagger UI at `/docs` is an interactive browser UI for black-box API execution, but it is not a custom product frontend.
- The Google helper page at `/auth/google-test-page` is only for obtaining a real Google credential during demo preparation.
- Do not print or commit `.env`; use `.env.example` for required variable names.

## Project Structure
- `app/main.py` — FastAPI app
- `app/services.py` — service layer (stubs)
- `tests/` — team tests
- `instructor_tests/` — reserved for instructor tests
