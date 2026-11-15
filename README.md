# Investor Check

A tool for founders to check investors before they pitch, built on [Cala](https://cala.ai).

## What it does

**Check an investor.** Type an investor or firm name. If Cala knows several with similar names, you pick the right one. You then get:

- **Quick facts** — type of investor, founding year, address, website, straight from Cala's record of the investor.
- **Briefing** — what kind of investor they are, the stages and sectors they back, typical check size and location, with the sources behind it.
- **Investments** — the companies they have backed, with round and year where Cala knows them.
- **Worth a call** — companies they backed that failed or are struggling, and their founders. These are the people who can tell you how the investor behaves when things go wrong. Each founder links to a LinkedIn search.

**Find investors.** Describe who you're looking for (e.g. "seed fintech investors in Europe") and get a table of investors to contact. Select a name to check that investor.

## How to run

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
| `templates/index.html` | The page's HTML |
| `static/style.css` | The page's styling |
| `static/app.js` | The page's JavaScript: calls the JSON API and renders the answers |
| `tests/test_app.py` | Automated tests (`python3 -m unittest`); they never call Cala |
| `corporate-identity.md` | Cala's visual identity, which the design follows |
| `requirements.txt` | The libraries to install |
| `.env` | Your Cala API key (secret, not uploaded) |

## Limits

- **Speed.** Cala takes roughly 20 to 60 seconds to answer a question, so each section of an investor page loads on its own as its answer arrives.
- **Request limit.** Cala's free plan allows 10 requests per minute. One investor check uses 9, so a second check straight after the first may be asked to wait a minute.
- **Saved answers.** Every answer is saved in a `.cache/` folder and reused for 24 hours, so repeating a check or search is instant and uses no credits. Delete the folder to clear it.
- **Accuracy.** Everything shown comes from Cala's knowledge. The briefing lists its sources; the tables do not, so check the facts before acting on them.

## Putting it online

`python3 app.py` runs Flask's development server with debug mode on, which is only safe on your own machine. To host it, run it with a production server instead, for example:

```
python3 -m pip install gunicorn
gunicorn app:app
```
