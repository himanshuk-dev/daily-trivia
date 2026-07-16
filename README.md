# Daily Trivia

Daily Trivia is a team-based trivia platform where a designated trivia master creates or generates multiple-choice quizzes, team members submit answers, and correct participants earn digital trophies.

The application supports passwordless email-code authentication, multiple teams, team administration, invite-based membership, public leaderboards, notifications, and AI-assisted question generation.

## Features

- Passwordless registration with first name, last name, username, email, and short-lived email codes
- Multiple teams with isolated members, trivia, trophies, and leaderboards
- Team invite codes with optional administrator approval
- Platform administrator, team administrator, trivia master, and member roles
- Platform-admin team editing and confirmed deletion
- Two-week master sprints with a same-day suggested-topic picker for each trivia
- Manual trivia creation or a one-question AI daily challenge
- Draft review, editing, publishing, closing, and answer evaluation
- Trophy awards for users who answer correctly
- Team leaderboards, trivia history, notifications, and basic analytics
- Automatic dashboard refresh for notifications, new trivia, submissions, teams, and leaderboards
- Platform-wide publish notifications for every active platform administrator
- Automatic publication with a configurable, server-enforced answer window

See [PLANNING.md](PLANNING.md) for the product requirements, role model, delivery plan, and implementation status.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design, data model, request flows, API map, permissions, and contributor reading guide.

## Technology stack

- Frontend: React 18, Vite 5, and Material UI
- Backend: Python 3.12, Django 5, and Django REST Framework
- Database: PostgreSQL
- Authentication: Django REST Framework token authentication with email one-time codes
- AI integration: Groq API with GPT-OSS 20B (API key required)

## Project structure

```text
daily-trivia/
├── backend/                 # Django API and application logic
│   ├── trivia_app/          # Models, views, serializers, tests, and migrations
│   ├── trivia_backend/      # Django settings and root URL configuration
│   ├── manage.py
│   └── requirements.txt
├── frontend/                # React/Vite web application
│   ├── src/
│   └── package.json
├── .env.example             # Environment-variable template
├── PLANNING.md              # Product and implementation plan
└── README.md
```

## Prerequisites

Install the following before running the project:

- Python 3.12 (Django 5 requires Python 3.10 or newer)
- Node.js 18 or newer and npm
- PostgreSQL

## Local setup

### 1. Configure the environment

From the project root, create a local environment file:

```bash
cp .env.example .env
```

Update the PostgreSQL values in `.env` to match your local database. At minimum:

```dotenv
POSTGRES_DB=daily_trivia
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Create the database if it does not already exist:

```bash
createdb daily_trivia
```

The exact database command may differ depending on how PostgreSQL is installed and which database user you use.

### 2. Set up the backend

From the project root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend API runs at `http://localhost:8000/api/`. Django's administration site is available at `http://localhost:8000/admin/`.

On a machine where `python3.12` is not on `PATH`, use the full path to its executable. On the original development machine that command is:

```bash
/Users/Himanshu.Kumar/.local/bin/python3.12 -m venv .venv
```

Always confirm that the environment is using the expected interpreter:

```bash
python --version
```

### 3. Set up the frontend

Open a second terminal and run:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173/` and uses `http://localhost:8000/api` by default.

## Authentication during development

Local development uses Django's console email backend. When the application requests a login or registration code, the email and its one-time code appear in the backend terminal instead of being sent through SMTP.

The initial platform administrator is configured with:

```dotenv
PLATFORM_ADMIN_EMAILS=himanshu.kumar@ssc-spc.gc.ca
```

Change this value in `.env` if a different account should receive platform-administrator access.

## AI trivia generation

AI generation requires a Groq API key. The master selects a cycle whose topic has already been set, and GPT-OSS 20B creates exactly one multiple-choice question. The question is published immediately and remains open for the configured answer window:

```dotenv
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
TRIVIA_ANSWER_WINDOW_HOURS=24
```

Set a valid key in `.env`. Without it, the API returns a clear configuration error instead of generating placeholder content. Do not commit `.env` or API keys to source control.

## Useful commands

Run these backend commands from `backend/` with the virtual environment active:

```bash
# Validate Django configuration
python manage.py check

# Apply database migrations
python manage.py migrate

# Create new migrations after model changes
python manage.py makemigrations

# Run backend tests
python manage.py test
```

Run these frontend commands from `frontend/`:

```bash
# Start the development server
npm run dev

# Create a production build
npm run build

# Preview the production build locally
npm run preview
```

## Environment variables

The complete template is in [.env.example](.env.example). Important settings include:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django cryptographic signing key |
| `DJANGO_DEBUG` | Enables or disables Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | Hosts accepted by Django |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Frontend origins allowed to call the API |
| `POSTGRES_*` | PostgreSQL connection settings |
| `PLATFORM_ADMIN_EMAILS` | Initial platform-administrator email addresses |
| `LOGIN_CODE_EXPIRY_MINUTES` | Lifetime of email login codes |
| `EMAIL_*` | Console or production SMTP configuration |
| `GROQ_API_KEY` | Optional Groq key for AI trivia generation |
| `GROQ_MODEL` | Groq model used to generate trivia questions |
| `TRIVIA_ANSWER_WINDOW_HOURS` | Answer-window duration; accepts decimals such as `0.25` for 15 minutes |
| `VITE_API_BASE_URL` | Backend API URL used by the frontend |

## Main workflow

1. A user registers with their first name, last name, unique username, and email address.
2. The user verifies the email code printed by the development backend.
3. A platform administrator creates a team and assigns its initial team administrator.
4. Members join using the team's invite code.
   Platform and team administrators can also add an existing active user directly as an approved member or team administrator.
5. A team administrator assigns themselves or another approved member as master for a two-week sprint without preselecting daily topics.
6. Each day, the master chooses a suggested topic from a dropdown and asks AI to generate one question; it is published immediately.
7. Approved team members submit their answers during the configured answer window.
8. After the deadline, the master evaluates the session.
9. Correct answers produce trophies.
10. Correct participants receive trophies reflected in the sprint leaderboard, whose leader is announced as the sprint winner when the two weeks end.
11. Team members can reopen completed trivia to review the correct answer, explanation, and their own submission.

## Troubleshooting

### Pip cannot install Django 5

If pip reports that Django requires a different Python version, the virtual environment was probably created with Python 3.9 or older. Recreate it explicitly with Python 3.12:

```bash
cd backend
deactivate 2>/dev/null || true
mv .venv .venv-old
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Pip reports `Invalid requirement: '-'`

Use the `-r` flag immediately before the requirements filename:

```bash
python -m pip install -r requirements.txt
```

### Login email does not arrive

With the default development configuration, no email is delivered. Look for the one-time code in the terminal running `python manage.py runserver`.

### Database connection fails

Confirm that PostgreSQL is running, the database exists, and the `POSTGRES_*` values in `.env` match your local PostgreSQL credentials.
