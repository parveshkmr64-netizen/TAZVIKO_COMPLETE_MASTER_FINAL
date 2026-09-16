# TAZVIKO COMPLETE MASTER FINAL

This is the single master package. It includes all functionality from the previous LIVE READY FINAL package plus the newer Nearby Business + Rider system.

## Preserved existing features
- English-first customer site with manual Hindi/language selection
- Customer register/login/account
- Catalog and marketplace UI
- COD checkout and persistent order saving
- Coupon/quote pricing flow
- Customer order history and tracking
- Support tickets
- Partner/shop/restaurant applications
- Delivery-partner applications
- Admin dashboard, order status controls, partner approval/rejection
- PWA manifest, service worker and offline page
- Render deployment config and persistent SQLite path support
- Optional Razorpay online-payment integration via environment keys

## Added features
- Customer geolocation button and nearby business discovery
- Optional Google Places API (New) nearby restaurant/shop/mall/pharmacy/grocery discovery
- TAZVIKO-approved/orderable partner distinction
- Rider accounts and PIN login
- Separate rider portal at /rider.html
- Admin rider activation and order assignment
- Rider order queue with TAZVIKO order ID, pickup, customer delivery address and COD amount
- Rider delivery status updates: PICKED_UP, ON_THE_WAY, DELIVERED

## Important behavior
Nearby public businesses appear in the main customer discovery grids when `GOOGLE_PLACES_API_KEY` is configured. They include an owner claim/registration action but remain clearly marked **Not yet orderable**. Discovery does not make an external business automatically accept TAZVIKO orders; menu, price, product photo and ordering remain enabled only for approved TAZVIKO partners.

## COD pilot
The site can launch COD-only. Online payment remains optional and can be activated later with live payment-gateway credentials without rebuilding the website.

## Required production secrets/settings
- TAZVIKO_ADMIN_KEY: strong private admin key
- GOOGLE_PLACES_API_KEY: optional; required for automatic nearby public-business discovery
- RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET: optional; required when online payments are enabled

Do not expose secret keys in frontend code.
