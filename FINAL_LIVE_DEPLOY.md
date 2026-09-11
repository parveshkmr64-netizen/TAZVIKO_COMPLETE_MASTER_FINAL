# TAZVIKO — Final Live Deployment

This package has been checked as a self-contained launch build.

## Verified in this final build
- Customer website loads with **English as the default language**.
- User can switch to Hindi from the language selector after the site opens.
- Account registration/login API works.
- Server-side catalog pricing and coupon validation work.
- COD order creation and order tracking work.
- Support tickets save to the database.
- Partner applications save to the database.
- Delivery-partner applications save to the database.
- Admin dashboard reads real server data and can update workflow statuses.
- Render deployment includes a persistent disk for SQLite data.
- PWA manifest, icons, service worker and offline page are included.
- Server and JavaScript syntax checks pass.

## Live deployment settings
The included `render.yaml` is the easiest deployment path.

Required for public deployment:
1. Deploy the repository/package on Render using `render.yaml`.
2. Set `PUBLIC_BASE_URL` to the final HTTPS site URL/domain.
3. Render generates `TAZVIKO_ADMIN_KEY`; keep it private and use it on `/admin.html`.

Optional for online payments:
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`

If Razorpay keys are blank, **COD remains operational** and UPI/Card are not enabled.

## Before taking real paid orders
Confirm your business-specific GST/tax rate, commission, delivery fee and platform fee environment values. Also complete payment-gateway KYC/merchant approval and your customer-facing legal policies for the jurisdiction/business model in which TAZVIKO operates.

## Important security note
Do not publish a manually configured server with the default admin key. Render's included configuration generates a secure admin key automatically.
