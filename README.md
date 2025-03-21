# BiciCare Automation — Booqable to Reeleezee Sync

This project automates the daily synchronization of **paid orders from Booqable** into **Reeleezee** to streamline financial tracking for BiciCare Amsterdam.

---

## 🚀 Features

- Retrieves all **paid orders** from Booqable (`payment_status=paid`)
- Filters orders based on **successful payments made today**
- Transforms order data into Reeleezee-compatible format
- Creates and books **Sales Invoices** in Reeleezee
- Creates **Receipts** linked to the invoices
- Fully automated via **GitHub Actions**

---

## 🗂️ Project Structure

```
📁/
├── main.py                     # Entrypoint script
├── lib/
│   ├── booqable.py             # Fetch & transform Booqable orders
│   ├── reeleezee.py            # Interact with Reeleezee API
│   └── __init__.py
├── requirements.txt            # Python dependencies
└── .github/
    └── workflows/
        └── sync.yml            # GitHub Actions workflow
```

---

## 🔐 Secrets & Environment

Secrets are configured via **GitHub Actions > Secrets**:

| Name                   | Description                          |
|------------------------|--------------------------------------|
| `BOOQABLE_API_KEY`     | Booqable API key                     |
| `REELEEZEE_USERNAME`   | Reeleezee username (`bicicare`)      |
| `REELEEZEE_PASSWORD`   | Reeleezee password                   |

For local testing, use environment variables or a `.env` file with [python-dotenv](https://pypi.org/project/python-dotenv/).

---

## 🧪 Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Export your secrets as environment variables:
   ```bash
   export BOOQABLE_API_KEY=your_key_here
   export REELEEZEE_USERNAME=bicicare
   export REELEEZEE_PASSWORD=your_password
   ```

3. Run the script:
   ```bash
   python main.py
   ```

---

## 🔁 Automation (GitHub Actions)

This project includes a GitHub Actions workflow that can be triggered manually and (optionally) scheduled daily.

To manually run:

- Go to the **Actions** tab
- Select **"Sync Booqable to Reeleezee"**
- Click **Run workflow**

To enable daily sync, uncomment the `schedule` block in `.github/workflows/sync.yml`.

---

## 📝 Roadmap / Future Improvements

- [ ] Add retry logic for API robustness
- [ ] Optional `.env` support with fallback
- [ ] Dry-run mode for testing without pushing to Reeleezee
- [ ] Slack or email alerts for failures/success summaries
- [ ] Auto-check if receipt is already created (Reeleezee logic)

---

## 👤 Maintainer

Developed by [@vladpke](https://github.com/vladpke) for BiciCare Amsterdam 🚴‍♂️

---
