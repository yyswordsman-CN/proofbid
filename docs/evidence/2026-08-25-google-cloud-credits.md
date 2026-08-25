# Google Cloud Credits approval and redemption — 2026-08-25

Observed on 2026-08-25 in Asia/Shanghai from the owner-controlled Devpost
approval email and Google Cloud Billing Credits page.

## Verified status

- The All Things Agentic Hackathon request was approved for **USD 150** in
  Google Cloud promotional credits.
- The one-time promotion code was redeemed into the existing Google Cloud
  billing account. The code and billing-account identifier are intentionally
  excluded from this repository.
- The Billing Credits page shows the promotional credit as available with an
  original and remaining localized value of **CNY 1,176.49**, starting
  2026-08-25 and ending **2026-09-24**.
- The same account shows the active Free Trial credit with an original and
  remaining localized value of **CNY 2,350.33**, starting 2026-08-25 and ending
  **2026-11-23**.
- The two active rows therefore showed **CNY 3,526.82** remaining at the time
  of observation. A separate expired Free Trial row reflects the account
  transition and is not counted as another credit grant.
- A read-only `gcloud billing projects describe` check returned
  `billingEnabled=True` for project `proofbid-agentic-yys-260822`.

## Raw evidence boundary

The following screenshots are retained only under the ignored
`.proofbid/evidence-raw/devpost/` directory. They are not version-controlled
because the approval email contains a unique promotion code and the Billing UI
contains account context.

| Local evidence | SHA-256 |
| --- | --- |
| `2026-08-25-google-cloud-credits-approved.png` | `b10c90690764cc073131e37b31b2b804eca38dd144ca3316f1452c6b58c1c734` |
| `2026-08-25-google-cloud-credits-overview.png` | `c4f1e658088e9b28de8b14b7c9a999f4e0f1e0396daff50bf15036a3fb574e29` |
| `2026-08-25-google-cloud-credits-dates.png` | `7ded1161950fb8190b28d6ced5a3afa7815c2f09119035453599878c8bc6c376` |

## Claim boundary

This receipt proves approval, redemption, displayed credit values and dates,
and that Billing remains enabled for the isolated ProofBid project. It does not
prove that every Google Cloud SKU is eligible, attribute any specific task cost,
extend either expiry date, or cap charges after eligible credits are exhausted.
