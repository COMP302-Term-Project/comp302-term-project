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

## Project Structure
- `app/main.py` — FastAPI app
- `app/services.py` — service layer (stubs)
- `tests/` — team tests
- `instructor_tests/` — reserved for instructor tests
