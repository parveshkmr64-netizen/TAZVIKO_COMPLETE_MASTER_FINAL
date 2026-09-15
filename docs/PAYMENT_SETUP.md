# Payment setup

TAZVIKO supports two launch modes:

**COD mode:** works immediately; no gateway keys required. Earnings are recorded in the admin ledger but cash settlement is operational/manual.

**Online mode:** set Razorpay merchant keys on the server. The backend creates the provider order using the amount stored in TAZVIKO's database and verifies the returned payment signature before marking an order PAID.

Real bank settlement timing, fees, refunds, KYC and limits are governed by the payment provider and your merchant account. The starter does not pretend to send money without a verified gateway account.

For later marketplace automation, add linked partner accounts and split transfers after completing provider onboarding/KYC.
