# billing_api
Read charges and issue refunds through the billing service.

## Connection

Base URL is `$BILLING_API_URL`. Authenticate with the `X-Billing-Key` header.
All amounts are in cents.

## Endpoints

`GET /charges?user_id=...` — list charges for a user.
`POST /refunds` — issue a refund. Body: `{"charge_id": ..., "amount_cents": ...}`

## Rules

Refunds are irreversible. Always confirm with the user before issuing one,
including the charge id and the exact amount.

A charge older than 120 days cannot be refunded through the API and has to go
through support.
