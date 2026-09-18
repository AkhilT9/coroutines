# coroutines

A small X-style social network: Django 6, HTMX, Tailwind, PostgreSQL.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000. Locally the app uses SQLite and writes emails to `sent_emails/`
instead of sending them — open the newest file there to find your verification link.

Run tests: `python manage.py test`

## Deploy to Render (free)

1. Push this folder to a GitHub repository.
2. Supabase: create a project in the **Singapore** region (same region as the Render service).
   Copy the **Session pooler** connection string from *Connect* (the one on port 5432 that
   starts with `postgresql://postgres.xxxx:`), and put your DB password in it.
3. Render: *New → Blueprint*, pick the repo. `render.yaml` creates the web service. Fill in:
   - `DATABASE_URL` — the Supabase pooler URL from step 2
   - `APPS_SCRIPT_URL` + `APPS_SCRIPT_SECRET` — Render's free plan blocks SMTP, so mail is sent
     by a Google Apps Script web app in your Gmail account. Deploy `scripts/apps_script_mailer.gs`
     (Execute as: Me, access: Anyone) and paste its `/exec` URL and the secret you set in it.
     (Alternative: `BREVO_API_KEY` from a Brevo account with a verified sender.)
   - `DEFAULT_FROM_EMAIL` — e.g. `coroutines <yourapp@gmail.com>`
4. After the first deploy, open the Render *Shell* tab and run `python manage.py createsuperuser`
   so you can log in to `/admin/` for moderation.

When you buy a domain: add it under *Settings → Custom Domains* on Render, then add the
hostname to an `ALLOWED_HOSTS` env var (comma-separated).
