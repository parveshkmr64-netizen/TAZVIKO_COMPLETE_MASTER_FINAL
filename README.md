# TAZVIKO — Launch-Ready Starter

This package is designed to start small and grow without rebuilding the whole product.

## What works immediately
- Customer account registration/login using mobile + PIN (server database)
- Restaurant/shop self-registration and admin approval
- Cart, checkout and real COD order storage
- Admin order view, status updates, earnings ledger and partner approvals
- Customer order tracking
- Verified post-delivery shop, rider and delivery feedback
- Merchant product/stock dashboard and rider self-registration/portal
- Admin logout, duplicate-registration protection, JSON backup/restore and test-data cleanup
- Original TAZVIKO marketplace hero artwork and eight professional category item-photo icons
- English/Hindi front-end and PWA structure

## Online payment / money to your account
Online checkout is already wired for Razorpay Standard Checkout. It is intentionally **OFF until you add your own Razorpay merchant API keys**. This is necessary because real money can only settle to the bank account linked to your verified payment-gateway merchant account.

When `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are set, UPI/Card/Wallet selections create a Razorpay order on the backend, open checkout, verify the payment signature on the backend, and mark the TAZVIKO order as PAID.

For the first test, all online customer payments can settle to the TAZVIKO merchant account and the site records TAZVIKO commission vs merchant payable. Merchant payouts can remain manual. Later, marketplace split settlements can be added using a product such as Razorpay Route/Cashfree Easy Split after partner KYC.

## Run locally
Windows: double-click `start_windows.bat`.
Mac/Linux: run `./start_mac_linux.sh`.
Then open `http://localhost:8000` and admin at `http://localhost:8000/admin.html`.

Before public deployment, set `TAZVIKO_ADMIN_KEY` to a strong private value.

For the complete launch, backup, cleanup and free-to-paid migration steps, read `FINAL_MARKETPLACE_GUIDE.md`.

## Enable online payment
1. Create/verify your Razorpay merchant account.
2. Generate Test keys first.
3. Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` as server environment variables.
4. Restart server and test payment.
5. After successful testing and gateway approval, replace Test keys with Live keys.

Never put `RAZORPAY_KEY_SECRET` inside HTML or JavaScript.

## Production upgrade path
Keep the same API contract and replace SQLite with PostgreSQL, deploy the backend to a managed server, add SMS/OTP, maps/rider tracking, marketplace payouts, webhooks, backups and monitoring. Android/iOS apps can reuse the same backend APIs.


## Secure checkout update
This build includes server-side catalog pricing and order totals. The browser no longer controls the authoritative price, discount, fees, commission, merchant payable or Razorpay amount. Use `/api/v1/catalog` for the current server catalog and `/api/v1/quote` for checkout quotes.
