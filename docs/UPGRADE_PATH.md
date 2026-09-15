# TAZVIKO Upgrade Path

## Stage A — Free/low-cost validation
- COD orders
- SQLite database
- Manual partner approval
- Manual rider assignment/phone coordination
- One city/area

## Stage B — Paid services after traction
Keep the same `/api/v1` interface and replace infrastructure behind it:
- PostgreSQL managed database
- OTP authentication
- Razorpay/Cashfree/PhonePe payments
- Google Maps/Mapbox
- SMS/WhatsApp/push notifications
- Cloud object storage for product/menu images

## Stage C — Mobile apps
Build Flutter or React Native customer, merchant and rider apps against the same backend endpoints. The website remains usable as a PWA.

## Stage D — Scale
Add queues, caching, CDN, autoscaling, observability, settlement automation, accounting exports, fraud/risk controls and city-wise operations.
