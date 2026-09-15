# TAZVIKO Final Marketplace Flow

## Customer
- Register/login with mobile and PIN.
- Browse default and approved-partner products.
- Place COD orders now.
- Track order status from PLACED through DELIVERED.
- Razorpay code is included but stays disabled until live keys are added.

## Business owner
1. Open the customer site and submit **Register Business**.
2. Wait for admin approval.
3. Admin creates a temporary merchant PIN.
4. Login at `/partner.html` using registered mobile + PIN.
5. Manage business profile, pickup address, opening hours and delivery radius.
6. Add/edit products, price, image URL, stock and live status.
7. Accept and progress incoming orders through CONFIRMED, PREPARING and READY.

## Admin
- Login at `/admin.html` with `TAZVIKO_ADMIN_KEY`.
- Review partner applications and press Approve.
- Set a temporary merchant PIN and share the mobile + PIN privately with the owner.
- Review delivery applications and create rider PINs.
- Assign READY orders to active riders.
- Monitor orders, sales, platform earnings, partners and riders.

## Rider
- Login at `/rider.html` using mobile + rider PIN.
- View assigned orders.
- Update PICKED_UP, ON_THE_WAY and DELIVERED.

## Razorpay later
When the business is ready after the pilot/100-order milestone, add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in Render Environment and redeploy. COD remains active.

## Production note
Keep `TAZVIKO_ADMIN_KEY`, merchant PINs, rider PINs and Razorpay secrets private. A persistent Render disk/database is required so orders and accounts survive restarts/redeployments.
