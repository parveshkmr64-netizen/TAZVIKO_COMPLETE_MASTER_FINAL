# TAZVIKO API Contract (v1)

Use one backend for Web, Android and iOS. Suggested base path: `/api/v1`.

## Core modules
- Auth: OTP request/verify, refresh token, logout
- Customers: profile, addresses, preferences, wallet, referrals
- Merchants: restaurant/shop/mall profiles, branches, hours, catalog, stock, offers
- Partner onboarding: application, KYC documents, bank/settlement details, approval status
- Catalog: categories, products/menu items, variants, add-ons, inventory/availability
- Cart & pricing: delivery fee, platform fee, taxes, coupon validation, membership benefits
- Orders: create, accept/reject, prepare, rider assignment, dispatch, deliver, cancel/refund
- Payments: create intent/order, verify webhook, refund, payout/settlement ledger
- Delivery: rider availability, assignment, live coordinates, proof of delivery
- Admin: users, merchants, orders, commissions, fees, payouts, coupons, zones, support
- Notifications: push, SMS, WhatsApp/email adapters
- Support: tickets, chat metadata, refund/escalation workflow

## Minimum endpoints
`POST /auth/otp/request`
`POST /auth/otp/verify`
`GET /merchants?lat=&lng=&type=`
`GET /merchants/:id/catalog`
`POST /pricing/quote`
`POST /orders`
`GET /orders/:id`
`GET /orders/:id/tracking`
`POST /payments/create`
`POST /payments/webhook/:provider`
`POST /partners/applications`
`GET /partners/applications/:id`
`POST /admin/partners/:id/approve`
`GET /admin/reports/earnings`
`POST /orders/:id/feedback`
`GET /merchant/feedback`
`GET /rider/feedback`
`GET /admin/feedback`
`GET /admin/backup`
`POST /admin/restore`
`POST /admin/clear-test-data`

Never put payment secret keys, KYC documents or privileged admin operations in browser/mobile code.

## Secure catalog and pricing
- `GET /api/v1/catalog` returns active server-side products and authoritative prices.
- `POST /api/v1/quote` accepts only cart identity/quantity plus an optional coupon and returns server-calculated totals.
- `POST /api/v1/orders` recalculates prices, discount, fees, tax, commission, merchant payable and TAZVIKO earnings before saving. Client-supplied totals are not trusted.
