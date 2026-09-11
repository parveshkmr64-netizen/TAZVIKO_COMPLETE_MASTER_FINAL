# TAZVIKO — 1 Month Live Pilot

This package turns the front-end demo into a small persistent COD pilot.

## What is real in this pilot
- Customer checkout saves orders into SQLite (`tazviko.sqlite3`)
- Name, mobile and delivery address are stored with the order
- COD orders get a real order code
- Admin page reads the same database and can change order status
- Customer tracking polls the server for the latest status
- Partner applications are saved and can be approved/rejected in Admin
- English/Hindi, PWA and the existing marketplace UI remain available

## What is intentionally NOT connected yet
- Online UPI/card money collection (requires Razorpay/Cashfree/PhonePe merchant onboarding + API keys)
- SMS/OTP (requires an SMS provider)
- Google Maps billing/API key
- Automatic rider GPS tracking
- Marketplace split settlement to merchant bank accounts

## Run on a Windows PC
1. Install Python 3 if it is not already installed.
2. Edit `start_windows.bat` and replace `ChangeThisStrongAdminKey` with your own strong secret.
3. Double-click `start_windows.bat`.
4. Customer site: `http://localhost:8000`
5. Admin: `http://localhost:8000/admin.html`

## Important for public internet use
Do NOT double-click `index.html` directly. The site must be run through `server.py`, otherwise orders cannot be saved.

For a public 1-month pilot, deploy the whole folder to a Python-capable host. `render.yaml` is included as an example. Use persistent storage/managed database for any serious public deployment because some free hosts can reset local files.

## Admin security
Set environment variable `TAZVIKO_ADMIN_KEY` to a long private value before public deployment. Never share it with customers.

## Pilot recommendation
Use COD only for the first month. Once demand is proven, connect a payment gateway and move SQLite to PostgreSQL/MySQL/Supabase for production-scale reliability.
