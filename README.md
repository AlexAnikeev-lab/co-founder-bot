# Co-founder Bot

Telegram bot for finding co-founders, project partners, and startup teammates. Users complete a compatibility test, browse profiles, match with others, join events, and optionally subscribe for premium features.

**Live demo:** [https://t.me/YOUR_BOT_USERNAME](https://t.me/YOUR_BOT_USERNAME) — replace with your hosted bot before submitting to Horizons.

## Why I built this

Many students and young founders have ideas but struggle to find the right teammate. Co-founder Bot combines profile onboarding, personality/compatibility tests, swipe-based discovery, event matchmaking, and bilingual UI (RU/EN) in one Telegram experience — no separate app install required.

## Features

- Registration with age check (learning mode under 14, full mode 14+)
- Profile with photo, city, strengths, and descriptions
- Compatibility tests and partner matching (likes, super-likes, bookmarks, matches)
- Events: admin-created cards, registration, automatic pair matching
- Co-founder Premium subscription (Telegram Stars payment flow)
- Admin panel: stats, swipe cleanup, demo users, event management
- Bilingual interface (Russian / English) with profile translation in discovery

## How to try the bot (demo)

1. Open the live bot: [https://t.me/YOUR_BOT_USERNAME](https://t.me/YOUR_BOT_USERNAME)
2. Send `/start`
3. Complete registration (age, legal agreement, phone, profile fields)
4. Use the main menu: Events, Dating/Partners, Profile, Premium (14+)

The bot must stay **online and hosted** for reviewers. Do not use the GitHub repo URL as the demo link.

## Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/start` | Everyone | Start or restart the bot, begin registration |
| `/admin` | Admins only | Open admin panel (stats, events, demo users) |
| `/add_test_user` | Admins only | Add demo users for testing (default 10, max 50) |
| `/add_test_user 20` | Admins only | Add a specific number of demo users |
| `/delete_test_users confirm` | Admins only | Remove all demo users |
| `/cancel` | Admins in FSM | Cancel current admin input flow |

Most navigation uses **inline buttons** (main menu, profile, swipes, events). Every screen has **Back** or **Main menu**.

## Screenshots

Add 1–2 screenshots to your Horizons project page (registration flow, swipe screen, or events list). UI assets live in `photos/` and `photos_engls/`.

## Tech stack

- Python 3.10+
- [aiogram](https://docs.aiogram.dev/) 3.20+ (async Telegram Bot API)
- SQLAlchemy 2.0 + aiosqlite
- python-dotenv
- deep-translator (RU↔EN profile translation)

## Project structure

```
├── main.py              # Entry point
├── config.py            # Settings from environment
├── handlers/            # Event handlers (thin layer)
├── keyboards/           # Inline/reply keyboards
├── middlewares/         # Auth, throttling, DB session
├── services/            # Business logic
├── repositories/        # Database access
├── states/              # FSM states
├── texts/               # User-facing copy (i18n)
├── utils/               # Logging, validation, helpers
├── .env.example         # Environment template
└── requirements.txt
```

## Local setup

### 1. Clone and enter the repo

```bash
git clone https://github.com/AlexAnikeev-lab/co-founder-bot.git
cd co-founder-bot
```

### 2. Virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If `pydantic-core` fails to build, install Rust (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`) and retry. See [INSTALL.md](INSTALL.md) and [FIX_RUST.md](FIX_RUST.md).

### 3. Environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_ID=your_telegram_user_id
DATABASE_URL=sqlite+aiosqlite:///cofounder.db
MIN_AGE_FULL=14
LOG_LEVEL=INFO
```

Optional: subscription and OpenRouter keys — see [.env.example](.env.example).

### 4. Run

```bash
python main.py
```

Database tables are created automatically on first start.

### Docker (optional)

```bash
docker build -t co-founder-bot .
docker run -d --name co-founder \
  -e BOT_TOKEN=your_bot_token \
  -e ADMIN_ID=123456789 \
  -v co-founder-data:/app/data \
  co-founder-bot
```

## Hosting (required for approval)

Deploy the bot on a VPS, cloud VM, or any always-on host (Docker recommended). The reviewer must open your **Telegram bot link** and use `/start` without setting up the project themselves.

## Horizons submission checklist

Before submitting on [Horizons](https://horizons.hackclub.com):

- [ ] Public GitHub repo with this README and [MIT License](LICENSE)
- [ ] **Demo URL** = live Telegram bot link (`https://t.me/...`), not the repo
- [ ] **Code URL** = public GitHub repo
- [ ] Bot is hosted and online
- [ ] Project description + screenshot on Horizons
- [ ] Hackatime linked to the project
- [ ] No secrets in the repo (`.env` is gitignored)

## Test scenarios

**Happy path:** `/start` → registration → tests → browse partners → register for an event.

**Error paths:** invalid age input, declined phone access, invalid photo — bot shows a friendly message and does not crash.

## Version

Current version: **1.0.1** (see `config.py`).

## License

[MIT](LICENSE) — Copyright (c) 2026 Alex Nik
