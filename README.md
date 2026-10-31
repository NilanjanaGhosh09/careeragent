# CareerAgent

A Telegram bot that helps students and freshers in India get internships and jobs by cold-emailing startup founders.

Bot: @nil_careeragent_bot

## What it does

- Reads your CV (PDF) and builds your profile
- Writes cold emails to founders
- Tracks the startups you emailed
- Reminds you who to follow up with
- Interview practice for a role
- Finds startups that match your profile

## Commands

- `/start` - how to use the bot
- `/email Startup name | what it does | founder name` - write a cold email
- `/track` - see your list
- `/track add Startup name | founder name` - save a startup
- `/track status 1 | replied` - update a startup
- `/followup` - who to follow up with
- `/prep Role` - interview practice
- `/find` - find startups for you
- `/profile` - see your profile
- `/reset` - delete your profile

## Setup

1. Create a bot with @BotFather and copy the token.
2. Get a Gemini API key from Google AI Studio.
3. Set these environment variables:
   - `TELEGRAM_TOKEN`
   - `GEMINI_API_KEY`
4. Install the library: `pip install requests`
5. Run: `python bot.py`

## Privacy

Your CV is sent to Google AI to build your profile. Use `/reset` to delete your data.
Never put your tokens or keys in the code.
