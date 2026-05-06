# Telegram listings scraper

This folder contains a standalone scraper that collects listing data from a Telegram channel.
It uses a user MTProto client (Telethon) to open the contact bot via the first button,
parse contact details, and produce a JSON array that matches the listings table columns.

## Setup

1. Create a virtual environment (optional).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in values.

Optional: set `YANDEX_API_KEY` to geocode addresses into lon/lat. You can tune
`YANDEX_RPS` and `YANDEX_CITY` if needed.

## Run

```bash
python scrape_listings.py
```

The script writes `output/listings.json` and prints a summary count.
