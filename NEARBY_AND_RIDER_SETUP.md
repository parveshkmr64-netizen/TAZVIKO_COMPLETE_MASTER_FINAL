# TAZVIKO Nearby Discovery + Rider Flow

## Customer nearby businesses
- Customer taps **Use My Location**.
- `/api/v1/places/nearby` searches nearby restaurants, grocery stores, pharmacies, shops and malls.
- Set `GOOGLE_PLACES_API_KEY` to enable automatic Google Places nearby discovery. Nearby restaurants, grocery stores, pharmacies, malls and local shops then appear directly in the customer food/store sections with name, address, rating, open status and distance.
- A discovered business is labelled **Not yet orderable** until its owner uses **Own it? Register**, completes verification and is approved by admin. The claim form is prefilled with the Google business name, address, coordinates and place ID.
- Real menu/products, prices, stock, photos and the **ADD** button only appear after an approved merchant adds them in Merchant Dashboard.
- Discovered businesses are informational until matched to an approved TAZVIKO partner (`google_place_id` + partner status `LIVE`).
- Only approved/orderable partners should accept TAZVIKO orders.

## Rider flow
1. Rider submits Delivery Partner application.
2. Admin opens `/admin.html` -> Delivery Applications -> **Create/Reset Rider PIN**.
3. Rider logs in at `/rider.html` using mobile + PIN.
4. Admin assigns a TAZVIKO order to the rider from **Orders & Rider Assignment**.
5. Rider sees only assigned orders. Each order is clearly labelled `TAZVIKO ORDER • TZ...`.
6. COD orders show the exact amount to collect.
7. Rider updates Picked Up -> On The Way -> Delivered.

## Important
Nearby discovery does not mean a random Google business is automatically a contractual TAZVIKO merchant. It becomes orderable after TAZVIKO onboarding/approval and matching its place ID.
