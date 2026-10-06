# WowRoster

A [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) cog that lets members set their
WoW main/secondary class, role, and spec through Discord dropdown menus. Entries are stored locally
via Red's Config and, once configured, pushed to a Google Sheet.

## Installation

```
[p]repo add wowroster https://github.com/YOURNAME/wowroster
[p]cog install wowroster wowroster
[p]load wowroster
```

## Getting started

1. Post the control panel in a channel:
   ```
   [p]wowroster panel
   ```
   This shows four buttons: **Set Main**, **Set Secondary**, **View Roster**, **Reset**. Clicking
   "Set Main" or "Set Secondary" walks the member through Class → Role → Spec → Save, ephemerally.

2. (Optional) Enable Google Sheets sync — see below.

Without a sheet configured, the cog still works fully; entries just live in the bot's local Config
until you set one up.

## Google Sheets sync setup

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project (or use an
   existing one), enable the **Google Sheets API**, then create a **Service Account** and generate
   a JSON key for it.
2. Create (or pick) a Google Sheet for the roster. Share it with the service account's
   `client_email` (found in the JSON key file) with **Editor** access.
3. Copy the Sheet ID — the long string in its URL between `/d/` and `/edit`.
4. In Discord:
   ```
   [p]wowroster setsheet <SHEET_ID>
   [p]wowroster setcreds        (attach the service account JSON file to this message)
   [p]wowroster sync            (force a full push to confirm it's wired up)
   ```

From then on, every save/reset a member makes through the panel is written to the sheet
automatically (one row per Discord ID). `[p]wowroster sync` can be re-run any time to force a full
rewrite of the sheet from the bot's local data.

## Commands

| Command | Who | What |
|---|---|---|
| `[p]wowroster panel` | Admin | Post the button panel in the current channel |
| `[p]wowroster setsheet <id>` | Admin | Set the target Google Sheet |
| `[p]wowroster setcreds` (+ attachment) | Admin | Upload the service-account JSON key |
| `[p]wowroster sync` | Admin | Force a full push of local data to the sheet |
| `[p]wowroster show [member]` | Everyone | View your entry, or someone else's |

## Sheet columns

```
Discord ID | Discord Name | Main Class | Main Role | Main Spec |
Secondary Class | Secondary Role | Secondary Spec | Last Updated
```

## Notes

- The panel's buttons and dropdowns use fixed `custom_id`s and the view is re-registered with
  `bot.add_view()` on cog load, so it keeps working across bot restarts.
- Sheet writes run in a background thread (`asyncio.to_thread`) so a slow Google API call never
  blocks the bot's event loop.
- Currently covers all 13 retail WoW classes/specs. Edit the `WOW_DATA` dict at the top of
  `wowroster.py` if you need Classic-era classes/specs or a different expansion's spec list.
