# Investor Check

A tool for founders to check investors before they pitch, built on [Cala](https://cala.ai).

## What it does

**Check an investor.** Type an investor or firm name. If Cala knows several with similar names, you pick the right one. You then get:

- **Quick facts** — type of investor, founding year, address, website, straight from Cala's record of the investor.
- **Briefing** — what kind of investor they are, the stages and sectors they back, typical check size and location, with the sources behind it.
- **Investments** — the companies they have backed, with round and year where Cala knows them.
- **Worth a call** — companies they backed that failed or are struggling, and their founders. These are the people who can tell you how the investor behaves when things go wrong. Each founder links to a LinkedIn search.

**Find investors.** Describe who you're looking for (e.g. "seed fintech investors in Europe") and get a table of investors to contact. Select a name to check that investor.

## Use it online

Hosted, nobody needs to install anything. There are two ways to run the site:

- **With your Cala key on the server.** Visitors open the site and it works, with no sign-up and no key. Every request spends your credits and counts against your request limit.
- **Without a key on the server.** Each visitor is asked once for their own Cala API key, which is saved in their browser only, and uses their own credits.

To host your own copy on [Render](https://render.com) (free plan):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/seaningman/investor-check)

1. Press the button and sign in to Render with GitHub.
2. Render asks for `CALA_API_KEY`. Paste your key for a site that just works, or leave it empty to have visitors bring their own.
3. Press Deploy. Render builds the app from `render.yaml` and gives you a web address.

Sequoia Capital, Thiel Fellowship and the search "Seed fintech investors in Europe" are saved in `seed/`, so they load instantly on a fresh site and spend no credits.

On the free plan the site pauses after 15 minutes without visitors; the next visit takes up to a minute to wake it.

## Run it on your own machine

You need Python 3.9+ and a Cala API key from [console.cala.ai](https://console.cala.ai).

```
python3 -m pip install -r requirements.txt
```

Put your key in the `.env` file:

```
CALA_API_KEY=your-key-here
```

Start the app:

```
python3 app.py
```

Then open http://127.0.0.1:5001.

## How it's organised

| File | What it does |
| :- | :- |
| `app.py` | The web server (Flask): serves the page and a small JSON API for it |
| `cala.py` | All communication with Cala's API, plus the answer cache |
| `prompts.py` | The questions sent to Cala, kept in one place |
| `templates/index.html` | The main page's HTML |
| `templates/key.html`, `static/key.js` | The page where a visitor pastes their Cala API key |
| `static/style.css` | The page's styling |
| `static/app.js` | The page's JavaScript: calls the JSON API and renders the answers |
| `tests/test_app.py` | Automated tests (`python3 -m unittest`); they never call Cala |
| `corporate-identity.md` | Cala's visual identity, which the design follows |
| `requirements.txt` | The libraries to install |
| `render.yaml` | Hosting settings for Render |
| `seed/` | Saved Cala answers for the demo investors, shipped with the app |
| `.env` | Your Cala API key (secret, not uploaded) |

## Limits

- **Speed.** Cala takes roughly 20 to 60 seconds to answer a question, so each section of an investor page loads on its own as its answer arrives.
- **Request limit.** Cala's free plan allows 10 requests per minute per key. One investor check uses 9, so a second check straight after the first may be asked to wait a minute.
- **Saved answers.** Every answer is saved in a `.cache/` folder and reused for 24 hours, so repeating a check or search is instant and uses no credits. On a hosted site the saved answers are shared by all visitors. Delete the folder to clear it.
- **Accuracy.** Everything shown comes from Cala's knowledge. The briefing lists its sources; the tables do not, so check the facts before acting on them.
