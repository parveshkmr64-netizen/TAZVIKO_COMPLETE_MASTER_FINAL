# TAZVIKO Security Baseline

No internet-facing application can honestly be guaranteed "unhackable". This starter is hardened against common mistakes and is designed to move to stronger managed infrastructure as the business grows.

## Included now
- Password/PIN hashing with PBKDF2 + random salt
- Cryptographically random session tokens
- Server-side Razorpay secret and server-side payment signature verification
- Admin secret accepted only through a request header, never URL query parameters
- Basic IP rate limiting
- Maximum API request-body size
- Same-origin checks for state-changing API calls
- Security response headers (nosniff, frame denial, referrer policy, permissions policy, COOP)
- HSTS when deployed with an HTTPS public base URL
- Parameterized SQL queries
- Input length limits on key fields
- Refusal to start a declared public deployment with the default admin key

## Required before accepting real public traffic
1. Deploy only behind HTTPS on a managed host/reverse proxy.
2. Set a long random `TAZVIKO_ADMIN_KEY`; never share it in chat, source code or screenshots.
3. Use PostgreSQL on a managed database with private networking, backups and encryption at rest.
4. Replace PIN login with verified OTP/passwordless auth or a managed identity provider; require MFA for admins.
5. Move customer/admin sessions to Secure + HttpOnly + SameSite cookies and add CSRF tokens where appropriate.
6. Put Cloudflare/AWS WAF or equivalent in front of the site; enable bot and DDoS protection.
7. Never store card numbers/CVV. Use hosted checkout from a PCI-compliant payment provider.
8. Validate prices, discounts, commission and merchant payable on the server from trusted catalog data. Never trust totals sent by the browser.
9. Add audit logs for admin actions, payout changes, partner approvals and payment events.
10. Enable automated dependency/security updates, vulnerability scanning, monitoring and alerting.
11. Encrypt sensitive partner KYC/bank data and collect only what is necessary.
12. Test backups and incident recovery; keep separate production and test credentials.

## Important pilot limitation
The current launch starter still uses browser-side demo catalog/pricing. Before real online payments or merchant settlements are enabled, move the catalog/pricing/fee rules into the server/database so a customer cannot alter prices in the browser.


## Server-side pricing (implemented)
- Browser-sent prices, totals, discounts, commission and merchant payable values are ignored.
- `/api/v1/quote` rebuilds totals from the server catalog.
- `/api/v1/orders` recalculates the same quote before saving the order.
- Product prices live in the server database (`products` table), not in trusted client state.
- Coupon rules live in the server database (`coupons` table).
- Razorpay order amount is created from the saved server-calculated order total.
- Quantity is constrained server-side and unknown/inactive products are rejected.

For production, replace the demo SQLite catalog with your managed database and merchant-specific tax/commission rules.
