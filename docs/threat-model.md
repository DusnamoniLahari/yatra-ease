# YatraEase Threat Model

YatraEase is a student portfolio project: a bilingual (English/Hindi) tourism and transport booking web app built with Flask, SQLAlchemy and pandas. All data is simulated. This document lists what could go wrong and how the app responds.

## 1. What we protect

- **Accounts and sessions** of visitors and staff
- **Bookings and customer details** (name, email, booking history)
- **Inventory accuracy** (seats must never be oversold)
- **Staff functions** (cancelling bookings, editing services, downloading reports)
- **Secrets** (secret key, admin password, database credentials)

## 2. Who might attack

- An anonymous visitor probing the site
- A registered visitor trying to see other people's bookings or reach admin pages
- An attacker guessing passwords or running scripts against the login page
- A malicious website trying to trick a logged-in user (CSRF, clickjacking)
- A customer who enters harmful text into forms (injection, XSS, spreadsheet formulas)

## 3. Threats and mitigations

| # | Threat | Mitigation | Where |
|---|---|---|---|
| 1 | SQL injection through search or forms | All queries use SQLAlchemy parameters; sort and filter values are whitelisted | routes.py, admin.py |
| 2 | Cross-site scripting (XSS) | Jinja2 auto-escapes output; Content Security Policy allows scripts only from the site itself; no inline JavaScript | templates, app/__init__.py |
| 3 | Cross-site request forgery (CSRF) | CSRF token on every POST form; SameSite=Lax cookies; logout, cancel and booking actions are POST only | Flask-WTF, config.py |
| 4 | Password theft from the database | Passwords are stored only as salted hashes (Werkzeug scrypt) | models.py |
| 5 | Password guessing | Minimum 8 characters with a letter and a number; common passwords rejected; 5 failed logins lock that email for 15 minutes | forms.py, auth.py |
| 6 | Account enumeration | Login always says "Invalid email or password"; lockout applies to unknown emails too | auth.py |
| 7 | Visitor reaches admin pages | admin_required checks the role on the server for every admin route (403 otherwise) | admin.py |
| 8 | Reading someone else's booking (IDOR) | Booking pages check ownership and return 404 for other people's bookings | bookings.py |
| 9 | Overbooking from two people booking the last seat | Capacity check and update happen in one atomic SQL statement | bookings.py |
| 10 | Double refund of seats when cancelling twice | Status changes only if still confirmed; seats are returned once | bookings.py, admin.py |
| 11 | Price tampering | Total price is calculated on the server, never read from the form | bookings.py |
| 12 | Open redirect after login | The next address must be a path on this site | auth.py |
| 13 | Clickjacking | frame-ancestors none and X-Frame-Options DENY | app/__init__.py |
| 14 | Spreadsheet formula injection in reports | Cells that start with = + - or @ are prefixed with an apostrophe | dashboard.py |
| 15 | Session theft | HttpOnly cookie, Secure flag in production, 8 hour lifetime, HSTS over HTTPS, no-store caching for logged-in pages | config.py, app/__init__.py |
| 16 | Information leakage | Friendly generic error pages; debug mode off in production; secrets only in .env | errors.py, run.py |
| 17 | Hardcoded or guessable secrets | Admin and demo passwords and the secret key come from .env; production refuses to start with a weak key | seed.py, config.py |
| 18 | Oversized or malformed requests | 1 MB request limit; WTForms length and range checks; date ranges capped | config.py, forms.py |
| 19 | No trace of who did what | Audit log records registrations, logins, failed logins, bookings, cancellations, admin changes and report downloads | auth.py, bookings.py, admin.py |

## 4. Known limitations (honest list)

- **Lockout can be abused.** Limiting by email lets someone lock a victim out on purpose. Limiting by IP address as well needs the real client address behind the production proxy.
- **No email verification, password reset, or two-factor login.** Admin accounts especially should use two-factor login in a real system.
- **Sessions are signed cookies.** Logging out removes the cookie in the browser, but a stolen cookie stays valid until it expires (8 hours).
- **Style attributes are allowed inline** by the Content Security Policy, because the dashboard bars use them. Scripts are fully restricted.
- **The common password list is short.** A real system would check a large breached-password list.
- **Audit log does not record IP addresses** and is not protected against deletion by someone with database access.
- **An early development password** (`Admin@123`) exists in the Git history. It was never used on a deployed system and has been replaced.
- **No automatic backups or monitoring yet.**

## 5. Future work

IP-based rate limiting, two-factor login for staff, email verification and password reset, server-side session revocation, log shipping and alerts, automated dependency scanning, and regular database backups.