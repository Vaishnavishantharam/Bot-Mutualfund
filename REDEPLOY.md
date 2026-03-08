# Next steps for redeploying

## 1. Push to GitHub

```bash
git push origin main
```

This triggers an automatic deploy on Vercel (if the repo is connected).

---

## 2. Confirm deployment on Vercel

1. Open [Vercel Dashboard](https://vercel.com/dashboard) → your project (**Bot-Mutualfund**).
2. Check **Deployments**: the latest deployment should show **Ready** (usually 1–2 minutes after push).
3. Open your live app (e.g. `https://bot-mutualfund.vercel.app/`).

---

## 3. (Optional) Refresh data to get “today’s” date

- **Manual run:** GitHub → **Actions** → **Refresh data (Phase 5 scheduler)** → **Run workflow**.
- After it completes, it will push updated `data/schemes.json` and `api/schemes.json`; Vercel will redeploy and “Data last updated” will show the new date.
- **Automatic:** The same workflow runs daily at **10:00 UTC**.

---

## 4. Quick checks after deploy

- Ask: *“What is the expense ratio of HDFC Large Cap?”* → should get **0.98%** and a citation.
- Ask: *“What is the AUM of small cap?”* → should get **₹36941 Cr**.
- Ask: *“Should I invest in HDFC Mid Cap?”* → should get a **refusal** (no advice).
- Ask: *“What is the expense ratio of SBI Bluechip?”* → should say **scheme not available**.
- UI: **Data last updated** should show the date from your corpus.

---

## 5. Check data freshness locally (any time)

```bash
python scripts/check_data_freshness.py
```

Exit 0 = data from today (UTC); exit 1 = older or missing.
