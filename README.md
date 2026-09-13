# TourWatch

Proof-of-concept read-only monitor for Recreation.gov timed-entry / tour availability.

## What this version does

- Checks Mammoth Cave facility `234640` over the date range in `watches.json`.
- Uses Recreation.gov's read-only timed-entry availability endpoint.
- Prints qualifying openings to the GitHub Actions log.
- Does **not** reserve, book, log in, solve CAPTCHAs, or collect customer information.

## First test

1. Upload all files in this starter package to the repository, preserving `.github/workflows/check.yml`.
2. Open the repository's **Actions** tab.
3. Click **Check tour availability**.
4. Click **Run workflow**.
5. Open the completed run and expand **Run TourWatch**.

A good first result is either:

- availability lines; or
- `endpoint responded, but no slots normalized ...`

The second result still proves GitHub can reach the endpoint and gives us the payload shape to adapt the parser.

## Configuration

Edit `watches.json` to change dates, party size, or later add additional facilities.
