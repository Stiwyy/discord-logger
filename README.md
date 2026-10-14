# Discord Logger

A small desktop app that sends every message in a channel/DM to a webhook.

## Installation

Clone the repository.

```bash
git clone https://github.com/Stiwyy/discord-logger.git
```

Install the requirements.

```bash
pip install -r requirements.txt
```

Alternatively you can install them manually.

Run the application.

```bash
python main.py
```

## Setup

To get this working, you need two things:

1. Discord User token
2. A webhook

### Discord User Token

1. Login to Discord's web interface: [DiscordApp](https://discordapp.com/)
2. Go to your browser's Developer Tools. In Chrome, press `F12` or `Ctrl + Shift + J`. Firefox, `Ctrl + Shift + I`.:
3. Find your inspector's `LocalStorage`. In Chrome, click `Application`, then `Local Storage -> https://discordapp`.
4. Copy the `token` variable.

> **Info**: The token will look something like this `token:""....""` ONLY copy the part inside the quotes. Do not copy the quotes.

### Webhook

Preferably you want to create a Discord Webhook for this.

1. Open Server settings
2. Under App go to insertions
3. Select Webhooks
4. Click New Webhook and name it whatever you want and select the channel you want the messages to be posted in.
5. Copy Webhook URL.
