# 🗳️ Telegram Giveaway & Voting Bot

A feature-packed, high-performance Telegram Giveaway & Voting Bot designed for channel engagement, community contests, and automated monetization. Built using **Kurigram** (asynchronous Telegram MTProto framework) and backed by **MongoDB**, this bot delivers real-time anti-cheat vote verification, automated plan subscriptions with QR payment approvals, custom emoji inline keyboards, and intelligent AI-powered profile moderation.

---

## 🌟 Key Highlights

- **⚡ Native Custom Emoji UI**: Built on Kurigram 2.2.25 with native support for Telegram Premium custom emoji inline buttons (`icon_custom_emoji_id`).
- **🛡️ Real-Time Anti-Cheat & Auto-Deduction**: Automatically detects when a voter leaves or is banned from the host channel and immediately deducts their votes from active giveaways in real-time.
- **🤖 Intelligent Profile Moderation**: Evaluates entrant profiles (name, username) using an OpenAI-compatible AI endpoint with Unicode normalization and multi-language support.
- **💎 Monetization & Subscriptions**: Tiered subscription plans (Free, Standard, Premium, Custom) with simultaneous giveaway limits, QR code payment checkouts, and 1-click owner approval buttons.
- **⏰ Automated Expiry Alerts**: Background tasks alert users 24 hours and 3 hours prior to plan expiration with interactive `Renew Plan` and `Upgrade / Downgrade` buttons.
- **📊 Real-Time Channel Sync**: Updates vote counters on channel posts dynamically without message spam or UI flicker.
- **⚡ Zero-Overhead Indexing**: MongoDB compound indexes ensure negligible CPU utilization on low-spec VPS environments.

---

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Configuration (.env)](#-configuration-env)
- [Installation Guide](#-installation-guide)
  - [Ubuntu / Linux VPS (Recommended)](#1-ubuntu--debian-linux-vps)
  - [Windows Deployment](#2-windows-deployment)
- [Running as a Background Service](#-running-as-a-background-service)
  - [Using systemd (Linux)](#option-a-using-systemd-recommended)
  - [Using PM2](#option-b-using-pm2)
- [Bot Commands](#-bot-commands)
- [License & Intellectual Property](#-license--intellectual-property)

---

## 🚀 Features

### 1. Giveaway Management
- **One-Click Channel Linkage**: Automatically discovers channels where the bot is an administrator and the user is the channel owner.
- **Deep-Link Entries**: Unique giveaway link generation (`https://t.me/your_bot?start=GA_ID`) for seamless participation.
- **Interactive Voting Posts**: Automatically posts entry announcements with dynamic `Vote - X` buttons directly in your channel.
- **Live Leaderboards**: Beautiful in-bot leaderboard showing Top 10 participants with medals (🥇 🥈 🥉) and total voter statistics.
- **Owner Controls**: Hosts can manually add or deduct votes with built-in pagination for high-participant contests.
- **Automatic Finale**: Generates winner announcements in the channel and private notifications to the giveaway creator upon conclusion.

### 2. Anti-Cheat Engine
- **Membership Enforcement**: Users must be channel members to cast a vote.
- **Leave Auto-Deduction**: If a voter leaves or is removed from the channel, their votes are automatically stripped from all active giveaways, and channel message buttons update immediately.
- **Periodic Background Sync**: Runs every 45 seconds to guarantee vote integrity even during Telegram webhook disconnects.
- **Anti-Self Vote**: Participants cannot vote for themselves.
- **Single Vote Constraint**: Strictly one public vote per participant per user.

### 3. AI Content Moderation
- **Multi-Language Support**: Sanitizes and normalizes fancy unicode fonts, zero-width characters, and non-Latin alphabets (Hindi, Arabic, Japanese, Cyrillic, etc.).
- **Strict Harm Reduction**: Automatically rejects and bans profiles with explicit or illegal content.
- **Multi-Key Failover**: Cycles through multiple API keys dynamically if rate limits or timeouts occur.
- **Fail-Closed Security**: Blocks entry safely if AI moderation endpoints are unreachable, preventing uninspected entries.

### 4. Subscription & Billing Engine
- **Custom Plan Tiers**: Create plans with custom validity periods, max simultaneous giveaway caps, and display pricing.
- **QR Payment Workflow**: Generates personalized payment invoices prompting users to scan your payment QR and upload a screenshot.
- **Cooldown Protection**: Enforces a 24-hour request cooldown to prevent spam.
- **One-Click Owner Actions**: Owners receive the submitted receipt in private chat with inline `Approve` and `Reject` buttons.
- **Redeem System**: Generates secure 12-character alphanumeric activation codes with 12-hour expiration timers.
- **Plan Renewal & Notifications**: Automatically notifies subscribers at 24h and 3h intervals before expiry.

---

## 📁 Project Structure

```text
├── bot.py                  # Core bot entrypoint, event loops & background tasks
├── config.py               # Environment configuration and variable loader
├── database.py             # MongoDB async models, queries, and compound indexes
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── LICENSE                 # Custom Source-Available License
├── qr/
│   ├── README.txt          # Instructions for placing payment QR image
│   └── payment_qr.png      # Your UPI/Crypto/Bank payment QR code
├── handlers/
│   ├── __init__.py
│   ├── start.py            # /start command, deep links, and participant join flow
│   ├── giveaway.py         # Giveaway creation, channel selection, and leaderboards
│   ├── voting.py           # Channel vote buttons and membership validations
│   ├── subscription.py     # Plan purchases, QR receipt submissions, and /redeem
│   └── owner.py            # Admin commands: /createplan, /gencode, /stats, /unban
└── utils/
    ├── __init__.py
    ├── ai_analyser.py      # Unicode sanitizer & multi-key AI moderation engine
    ├── decorators.py       # @owner_only access control decorator
    ├── helpers.py          # String generators, channel permissions, vote sync helpers
    └── keyboards.py        # Inline keyboards with native Telegram custom emoji IDs
```

---

## 📦 Prerequisites

Before deploying the bot, make sure you have:

1. **Python 3.10+**: Python version 3.10, 3.11, or 3.12.
2. **MongoDB**: Local MongoDB instance (`mongodb://localhost:27017`) or a free cloud cluster from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
3. **Telegram Bot Token**: Created via [@BotFather](https://t.me/BotFather).
4. **Telegram API Credentials**: `API_ID` and `API_HASH` obtained from [my.telegram.org](https://my.telegram.org).
5. **AI API Key(s)**: Any OpenAI-compatible chat completions API key (supports multi-key rotation).

---

## ⚙️ Configuration (.env)

Create a `.env` file in the root directory by copying `.env.example`:

```bash
cp .env.example .env
```

Fill in your configuration values:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `API_ID` | Telegram API ID from my.telegram.org | `12345678` |
| `API_HASH` | Telegram API Hash from my.telegram.org | `abcdef1234567890abcdef1234567890` |
| `BOT_TOKEN` | Telegram Bot Token from @BotFather | `1234567890:ABCdefGhIJKlmNoPQRsTUVw` |
| `OWNER_ID` | Numeric Telegram User ID of the bot owner | `987654321` |
| `BOT_USERNAME`| Username of your bot (without `@`) | `MyGiveawayBot` |
| `MONGO_URI` | MongoDB connection URI | `mongodb://localhost:27017` |
| `DB_NAME` | MongoDB database name | `votingbot` |
| `AI_API_URL` | OpenAI-compatible chat completions API URL | `https://api.openai.com/v1/chat/completions` |
| `AI_MODEL` | Model name for moderation checks | `gpt-4o-mini` |
| `AI_API_KEY_1` | Primary AI API key | `sk-...` |
| `AI_API_KEY_2` | Secondary AI API key (optional failover) | `sk-...` |

> [!NOTE]
> You can add unlimited AI keys (`AI_API_KEY_1`, `AI_API_KEY_2`, `AI_API_KEY_3`, etc.). The bot automatically discovers all indexed keys and balances requests across them.

---

## 🛠️ Installation Guide

### 1. Ubuntu / Debian Linux VPS

#### Step 1: Update Packages & Install System Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

#### Step 2: Install MongoDB (If using local database)
```bash
sudo apt install -y mongodb
sudo systemctl enable mongodb
sudo systemctl start mongodb
```
*(Alternatively, use MongoDB Atlas connection URI in your `.env`)*

#### Step 3: Clone the Repository
```bash
git clone https://github.com/sankalpmodz/votingbot.git
cd votingbot
```

#### Step 4: Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 5: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 6: Configure Environment & QR Code
```bash
mv sample.env .env
nano .env   # Fill in your credentials, then press CTRL+O, ENTER, CTRL+X
```

Place your payment QR code image into the `qr/` directory:
```bash
# Rename your image to payment_qr.png and put it in qr/
cp /path/to/your/qr.png qr/payment_qr.png
```

#### Step 7: Run the Bot
```bash
python3 bot.py
```

---

### 2. Windows Deployment

1. **Install Python**: Download and install [Python 3.10+](https://www.python.org/downloads/). Ensure you check **"Add Python to PATH"** during installation.
2. **Open Command Prompt / PowerShell** in the project directory:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your values.
4. Place your payment QR image at `qr\payment_qr.png`.
5. Run the bot:
   ```powershell
   python bot.py
   ```

---

## 🔄 Running as a Background Service

For production servers, keep the bot running 24/7 using either **systemd** or **PM2**.

### Option A: Using systemd (Recommended)

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/votingbot.service
   ```

2. Paste the following configuration (replace `ubuntu` and path with your user/path):
   ```ini
   [Unit]
   Description=Telegram Giveaway Voting Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/votingbot
   ExecStart=/home/ubuntu/votingbot/venv/bin/python3 bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable votingbot
   sudo systemctl start votingbot
   ```

4. Check logs:
   ```bash
   sudo journalctl -u votingbot -f
   ```

---

### Option B: Using PM2

1. Install Node.js and PM2:
   ```bash
   sudo apt install -y nodejs npm
   sudo npm install -g pm2
   ```

2. Start the bot with PM2:
   ```bash
   pm2 start bot.py --name votingbot --interpreter venv/bin/python3
   pm2 save
   pm2 startup
   ```

3. Monitor logs:
   ```bash
   pm2 logs votingbot
   ```

---

## 🎮 Bot Commands

### 👤 Public Commands
| Command | Usage | Description |
| :--- | :--- | :--- |
| `/start` | `/start` | Launches the interactive main menu or opens giveaway deep links. |
| `/redeem`| `/redeem <code>` | Redeems an activation code to start or extend a subscription. |

### 👑 Owner Commands (Admin Only)
| Command | Usage | Description |
| :--- | :--- | :--- |
| `/createplan` | `/createplan <name> <days> <max_ga> <price>` | Creates a new subscription tier. |
| `/deleteplan` | `/deleteplan <name>` | Deletes an existing subscription tier. |
| `/listplans` | `/listplans` | Displays all configured tiers and their attributes. |
| `/gencode` | `/gencode <plan_name>` | Generates a 12-hour single-use redeem code for a plan. |
| `/listcodes` | `/listcodes` | Lists all active, unused redeem codes and remaining validities. |
| `/unban` | `/unban <user_id>` | Unbans a previously restricted user. |
| `/stats` | `/stats` | Shows real-time statistics (users, giveaways, active plans). |

---

## 📄 License & Intellectual Property

This project is licensed under a **Custom Source-Available & Non-Commercial Anti-Plagiarism License**.

**Copyright (c) 2026 SankalpModz ([GitHub: sankalpmodz](https://github.com/sankalpmodz)). All rights reserved.**

### Summary of Rights and Restrictions:
- ✅ **Permitted**: You are welcome to view, study, and analyze this source code for educational and research purposes.
- ✅ **Permitted**: You may self-host your own personal, private instance of this bot.
- ❌ **Prohibited**: You may **NOT** re-distribute, re-upload, mirror, or fork this repository to publicly share copies as your own work.
- ❌ **Prohibited**: You may **NOT** sell, rent, commercialize, or offer white-labeled copies or managed services using this codebase.
- ❌ **Prohibited**: You may **NOT** remove, alter, or obscure the author credits and copyright notices crediting **SankalpModz**.

Unauthorized distribution, attribution removal, or intellectual property theft will be subject to DMCA takedown notices and platform enforcement.
