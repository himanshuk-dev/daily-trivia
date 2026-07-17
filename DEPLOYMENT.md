# Deploy Daily Trivia on Render and Neon

This repository includes a Render Blueprint for a free Django web service and a free React static site. PostgreSQL runs on Neon so the database does not expire after Render's 30-day free database period.

> This free-tier setup is intended for demos and light internal testing. Do not use it for protected or sensitive government information without completing your organization's security, privacy, accessibility, records-management, and cloud-hosting approvals.

## 1. Create the Neon database

1. Create a free project at [Neon](https://console.neon.tech/).
2. Open **Connect** and copy the PostgreSQL connection string.
3. Keep the complete query string, including `sslmode=require` and `channel_binding=require` when Neon supplies them.
4. Save this value securely for Render's `DATABASE_URL` prompt.

## 2. Choose an SMTP service

Production authentication sends one-time login codes by email. Obtain approved SMTP settings before deploying:

- SMTP hostname and port
- SMTP username and password
- TLS requirement
- Verified sender address

The console email backend used locally is not suitable for deployment because users cannot see Render's server logs.

## 3. Create the Render Blueprint

1. Sign in to [Render](https://dashboard.render.com/) and connect the GitHub repository.
2. Select **Blueprints → New Blueprint Instance**.
3. Select this repository. Render detects `render.yaml` and creates:
   - `daily-trivia-api`: free Django web service
   - `daily-trivia-web`: free React static site
4. Enter the prompted environment variables:

| Service | Variable | Value |
| --- | --- | --- |
| API | `DATABASE_URL` | Complete Neon connection string |
| API | `PLATFORM_ADMIN_EMAILS` | Comma-separated platform-admin emails |
| API | `GROQ_API_KEY` | Groq API key |
| API | `DJANGO_CORS_ALLOWED_ORIGINS` | Frontend origin, such as `https://daily-trivia-web.onrender.com` |
| API | `DJANGO_CSRF_TRUSTED_ORIGINS` | Same HTTPS frontend origin |
| API | `EMAIL_HOST` | Approved SMTP hostname |
| API | `EMAIL_HOST_USER` | SMTP username |
| API | `EMAIL_HOST_PASSWORD` | SMTP password |
| API | `DEFAULT_FROM_EMAIL` | Verified sender address |
| Web | `VITE_API_BASE_URL` | API URL ending in `/api`, such as `https://daily-trivia-api.onrender.com/api` |
| Web | `VITE_AUTH_TOKEN_STORAGE_KEY` | Browser storage key, such as `daily-trivia-auth-token` |

Render generates `DJANGO_SECRET_KEY`. Never copy local `.env` secrets into source control.

Service names must be globally unique on Render. If Render adds a suffix, update the frontend/backend URL variables with the actual generated `.onrender.com` domains and redeploy both services.

## 4. Verify the deployment

The backend build installs dependencies, collects Django admin static assets, and applies migrations to Neon. After both services finish deploying:

1. Open `https://<api-host>/api/health/` and confirm `{"status":"ok"}`.
2. Open the frontend URL.
3. Register with an address in `PLATFORM_ADMIN_EMAILS`.
4. Confirm the login code arrives by email.
5. Create a test team, sprint, and AI trivia question.
6. Confirm a second account receives the notification and can submit an answer.

## 5. Free-tier behavior

Render's free backend sleeps after 15 minutes without inbound traffic. The first request after sleep can take about a minute. The React static site remains available, but API actions wait for Django to wake up. Neon also suspends idle compute and reconnects automatically.

## Deployment files

- `render.yaml`: backend and frontend service definitions
- `backend/build.sh`: dependency installation, static collection, and migrations
- `backend/requirements.txt`: production server, static-file, and database URL dependencies
- `backend/trivia_backend/settings.py`: Neon, Render hostname, HTTPS, CORS, CSRF, and WhiteNoise configuration
