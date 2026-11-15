// Investor Check front end: sends the founder's input to the JSON API in app.py
// and renders the answers.

const MODES = {
  check: {
    label: "Investor or firm name",
    placeholder: "e.g. Sequoia Capital",
    button: "Check",
  },
  find: {
    label: "Describe the investors you're looking for",
    placeholder: "e.g. Seed fintech investors in Europe",
    button: "Search",
  },
};

const form = document.getElementById("search-form");
const input = document.getElementById("query");
const label = document.getElementById("query-label");
const submit = document.getElementById("submit");
const results = document.getElementById("results");
const tabs = document.querySelectorAll(".tab");

let mode = "check";
let controller = null; // cancels the previous request when a new one starts

// --- Small helpers -----------------------------------------------------------

// Create an element: el("p", { className: "empty" }, "text or child nodes")
function el(tag, props, ...children) {
  const node = Object.assign(document.createElement(tag), props || {});
  node.append(...children);
  return node;
}

// The visitor's Cala API key, saved in this browser by the key page (key.js).
function savedKey() {
  try {
    return localStorage.getItem("calaApiKey") || "";
  } catch (e) {
    return ""; // storage is blocked, e.g. some private windows
  }
}

async function getJSON(url, signal) {
  const key = savedKey();
  const response = await fetch(url, { signal, headers: key ? { "X-Cala-Key": key } : {} });
  if (response.status === 401) {
    // Missing or rejected key: send the visitor to the key page and leave
    // this request pending so no error flashes up first.
    location.href = key ? "/key?problem=1" : "/key";
    return new Promise(() => {});
  }
  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    // not JSON; handled below
  }
  if (!response.ok || data === null) {
    throw new Error((data && data.error) || "Something went wrong (HTTP " + response.status + ").");
  }
  return data;
}

function loading(text) {
  return el("div", { className: "loading" }, el("span", { className: "spinner" }), text);
}

function card(title, ...children) {
  return el("section", { className: "card" }, el("h3", {}, title), ...children);
}

// Fill a card's body with the result of `load`, showing a spinner meanwhile.
async function fill(body, loadingText, load) {
  body.replaceChildren(loading(loadingText));
  try {
    body.replaceChildren(...[].concat(await load()));
  } catch (e) {
    if (e.name === "AbortError") return;
    body.replaceChildren(el("div", { className: "error" }, e.message));
  }
}

// --- Markdown (Cala's briefings are markdown) --------------------------------

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return text.replace(/[&<>"']/g, (c) => map[c]);
}

function inlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
}

// Handles headings, bullet and numbered lists, and paragraphs. Everything is
// HTML-escaped first, so text from the API can never inject markup.
function markdownToHtml(markdown) {
  const html = [];
  let paragraph = [];
  let list = null; // "ul" or "ol" while inside a list

  const closeParagraph = () => {
    if (paragraph.length) html.push("<p>" + inlineMarkdown(paragraph.join(" ")) + "</p>");
    paragraph = [];
  };
  const closeList = () => {
    if (list) html.push("</" + list + ">");
    list = null;
  };

  for (const line of markdown.split("\n")) {
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const item = bullet || numbered;

    if (item) {
      const type = bullet ? "ul" : "ol";
      closeParagraph();
      if (list !== type) {
        closeList();
        html.push("<" + type + ">");
        list = type;
      }
      html.push("<li>" + inlineMarkdown(item[1]) + "</li>");
    } else if (heading) {
      closeParagraph();
      closeList();
      html.push("<h4>" + inlineMarkdown(heading[1]) + "</h4>");
    } else if (!line.trim()) {
      closeParagraph();
      closeList();
    } else {
      closeList();
      paragraph.push(line.trim());
    }
  }
  closeParagraph();
  closeList();
  return html.join("");
}

// --- Tables (Cala decides the columns, so they are built from the data) -------

function columnLabel(key) {
  const text = key.replace(/_/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function cellText(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map(cellText).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

// The column holding the investor's or company's name, else the first column.
function nameColumn(rows) {
  const keys = Object.keys(rows[0] || {});
  return keys.find((key) => /^(investor|company|firm)?_?name$|^(investor|company|firm)$/i.test(key)) ||
    keys.find((key) => /name/i.test(key)) ||
    keys[0];
}

// The name column is shown first. With `link`, its values become buttons that
// check that investor.
function table(rows, link = false) {
  const nameKey = nameColumn(rows);
  const columns = [nameKey];
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!columns.includes(key)) columns.push(key);
    }
  }

  const head = el("tr", {}, ...columns.map((key) => el("th", { scope: "col" }, columnLabel(key))));
  const body = rows.map((row) =>
    el("tr", {}, ...columns.map((key) => {
      const text = cellText(row[key]);
      if (key !== nameKey) return el("td", {}, text);
      if (link && typeof row[key] === "string" && row[key]) {
        const button = el("button", { className: "link-button", type: "button" }, text);
        button.addEventListener("click", () => run("check", row[key]));
        return el("td", { className: "cell-name" }, button);
      }
      return el("td", { className: "cell-name" }, text);
    }))
  );

  return el("div", { className: "table-scroll" },
    el("table", {}, el("thead", {}, head), el("tbody", {}, ...body)));
}

// --- Worth a call -------------------------------------------------------------

const PHONE_ICON = '<svg aria-hidden="true" width="56" height="56" viewBox="0 0 44 44">' +
  '<path d="M13.5 6.5c-3 1.3-5.300 3.700-5.500 7 .6 12 10.500 22.500 22.500 24 3.200-.2 5.600-2.300 7-5.200-2.300-2.300-4.800-4.200-7.600-5.600' +
  'l-3.600 3.400c-4.600-2.200-8.300-5.900-10.400-10.500l3.300-3.700c-1.400-3.400-3.300-6.600-5.700-9.400z"/>' +
  '<path d="M27 7.500c4.500 1.200 8 4.700 9.300 9.200M26 13.500c2.200.8 3.900 2.500 4.700 4.700"/></svg>';

// "Ann Lee, Bo Chan" or ["Ann Lee", "Bo Chan"] -> ["Ann Lee", "Bo Chan"]
function splitNames(value) {
  if (Array.isArray(value)) return value.map(cellText);
  if (!value) return [];
  return String(value).split(/\s*[,;]\s*/).filter(Boolean);
}

// One row per company: name and year on the left, founders and what happened
// on the right. Falls back to a plain table if Cala's columns are unexpected.
function callList(rows) {
  const keys = Object.keys(rows[0]);
  const companyKey = keys.find((key) => /company|name/i.test(key));
  const foundersKey = keys.find((key) => /founder/i.test(key));
  const yearKey = keys.find((key) => /year|date/i.test(key));
  if (!companyKey || !foundersKey) return table(rows);

  return el("ul", { className: "call-list" }, ...rows.map((row) => {
    const founders = splitNames(row[foundersKey]);
    const details = Object.keys(row)
      .filter((key) => ![companyKey, foundersKey, yearKey].includes(key) && row[key] !== null && row[key] !== "")
      .map((key) => el("p", {}, cellText(row[key])));

    return el("li", { className: "call-row" },
      el("div", { className: "call-company" },
        el("h4", {}, cellText(row[companyKey])),
        yearKey && row[yearKey] ? el("span", { className: "call-year" }, cellText(row[yearKey])) : ""),
      el("div", { className: "call-detail" },
        el("div", { className: "founders" },
          el("span", { className: "founders-label" },
            founders.length === 0 ? "Founders not known" : founders.length === 1 ? "Founder" : "Founders"),
          ...founders.map((name) => el("a", {
            className: "founder",
            href: "https://www.linkedin.com/search/results/people/?keywords=" +
              encodeURIComponent(name + " " + cellText(row[companyKey])),
            target: "_blank",
            rel: "noopener noreferrer",
            title: "Search LinkedIn for " + name,
          }, name))),
        ...details));
  }));
}

// --- Views -------------------------------------------------------------------

// A typed name can match several investors. If it does, ask which one is meant.
// If there is one match, or the top match has exactly the typed name, go
// straight to it, unless `alwaysAsk` (the founder asked to see the other matches).
function chooseInvestor(typed, signal, alwaysAsk = false) {
  const body = el("div");
  results.replaceChildren(body);

  fill(body, "Looking up this name.", async () => {
    const data = await getJSON("/api/entities?name=" + encodeURIComponent(typed), signal);
    const top = data.entities[0];
    const clear = data.entities.length < 2 ||
      top.name.trim().toLowerCase() === typed.trim().toLowerCase();
    if (!top || (clear && !alwaysAsk)) {
      // Replace the URL so the back button doesn't return to this lookup step.
      openInvestor(top ? top.name : typed, top ? top.description : "", top ? top.id : "", true);
      return [];
    }

    const choice = (title, type, description, onPick, className = "choice") => {
      const button = el("button", { className, type: "button" },
        el("span", { className: "choice-heading" },
          el("span", { className: "choice-name" }, title),
          type ? el("span", { className: "choice-type" }, type) : ""),
        description ? el("span", { className: "choice-description" }, description) : "");
      button.addEventListener("click", onPick);
      return el("li", {}, button);
    };

    return [
      el("h2", { className: "result-title" },
        el("small", {}, "Matches for “" + typed + "”"), "Which one do you mean?"),
      el("ul", { className: "choices" },
        ...data.entities.map((entity) =>
          choice(entity.name, entity.type, entity.description,
            () => openInvestor(entity.name, entity.description, entity.id))),
        choice("None of these", "", "Search for “" + typed + "” as typed.",
          () => openInvestor(typed, ""), "choice choice-none")),
    ];
  });
}

// Quick facts from the investor's Cala record. They arrive in under a second,
// long before the briefing. The page works without them, so errors are ignored.
function showFacts(id, badge, facts, signal) {
  getJSON("/api/facts?id=" + encodeURIComponent(id), signal).then((data) => {
    if (data.type) {
      badge.textContent = data.type;
      badge.hidden = false;
    }
    if (data.facts.length) {
      facts.replaceChildren(...data.facts.map((fact) =>
        el("div", {},
          el("dt", {}, fact.label),
          el("dd", {}, fact.url
            ? el("a", { href: fact.url, target: "_blank", rel: "noopener noreferrer" }, fact.value)
            : fact.value))));
      facts.hidden = false;
    }
  }).catch(() => {});
}

// Cala's briefing often opens with a heading that repeats the investor's name,
// which the page title already shows.
function withoutTitle(briefing, name) {
  const first = briefing.trimStart().split("\n", 1)[0];
  const repeatsName = /^#{1,6}\s/.test(first) && first.toLowerCase().includes(name.toLowerCase());
  return repeatsName ? briefing.trimStart().slice(first.length) : briefing;
}

// `about` is the picked investor's description; it tells Cala which one is meant.
// `id` is its Cala entity id, if it was picked from Cala's matches.
function showInvestor(name, about, id, signal) {
  const briefing = el("div");
  const portfolio = el("div");
  const worthACall = el("div");
  const sources = el("div");
  const sourcesCard = card("Sources", sources);
  sourcesCard.classList.add("sources-card");
  sourcesCard.hidden = true;
  worthACall.className = "call-body";

  const badge = el("span", { className: "badge", hidden: true });
  const facts = el("dl", { className: "facts", hidden: true });
  const otherMatches = el("button", { className: "link-button", type: "button" },
    "Not the right one? See other matches");
  otherMatches.addEventListener("click", () => {
    start("check", name);
    setUrl({ mode: "check", q: name, choose: "1" });
    chooseInvestor(name, controller.signal, true);
  });
  if (id) showFacts(id, badge, facts, signal);

  results.replaceChildren(
    el("div", { className: "investor-head" },
      el("h2", { className: "result-title" }, el("small", { className: "kicker" }, "Investor", badge), name,
        about ? el("small", {}, about) : ""),
      facts,
      el("p", {}, otherMatches)),
    el("div", { className: "split" }, card("Briefing", briefing), sourcesCard),
    card("Investments", portfolio),
    el("section", { className: "call" },
      el("div", { className: "call-head", innerHTML: PHONE_ICON },
        el("div", {},
          el("h3", {}, "Worth a call"),
          el("p", {},
            "Founders of companies this investor backed that failed or are struggling. " +
            "They can tell you how the investor behaves when things go wrong."),
          el("p", { className: "call-note" },
            "Select a founder to search for them on LinkedIn. This list is generated " +
            "from Cala's knowledge, so check the facts before you reach out."))),
      worthACall)
  );

  const query = "?" + new URLSearchParams({ name, about });

  fill(briefing, "Asking Cala about this investor. This can take up to two minutes.", async () => {
    const data = await getJSON("/api/investor" + query, signal);
    if (data.sources.length) {
      sources.replaceChildren(el("ol", { className: "sources" }, ...data.sources.map((source) =>
        el("li", {},
          el("a", { href: source.url, target: "_blank", rel: "noopener noreferrer" }, source.title),
          source.publisher ? el("span", {}, " · " + source.publisher) : "")
      )));
      sourcesCard.hidden = false;
    }
    if (!data.briefing.trim()) return el("p", { className: "empty" }, "Cala has no briefing for this investor.");
    return el("div", { className: "prose", innerHTML: markdownToHtml(withoutTitle(data.briefing, name)) });
  });

  fill(portfolio, "Looking up investments.", async () => {
    const data = await getJSON("/api/portfolio" + query, signal);
    if (!data.rows.length) return el("p", { className: "empty" }, "No investments found.");
    return table(data.rows);
  });

  fill(worthACall, "Looking for failed or struggling companies.", async () => {
    const data = await getJSON("/api/worth-a-call" + query, signal);
    if (!data.rows.length) return el("p", { className: "empty" }, "No failed or struggling companies found.");
    return callList(data.rows);
  });
}

function showSearch(description, signal) {
  const matches = el("div");
  results.replaceChildren(
    el("h2", { className: "result-title" }, el("small", {}, "Investors matching"), description),
    card("Investors to contact", matches)
  );

  fill(matches, "Searching Cala for investors. This can take up to two minutes.", async () => {
    const data = await getJSON("/api/search?q=" + encodeURIComponent(description), signal);
    if (!data.rows.length) return el("p", { className: "empty" }, "No investors found. Try describing them differently.");
    return [
      el("p", { className: "card-note" }, "Select an investor's name to check them."),
      table(data.rows, true),
    ];
  });
}

// --- Wiring ------------------------------------------------------------------

function setMode(newMode) {
  mode = newMode;
  tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.mode === mode)));
  label.textContent = MODES[mode].label;
  input.placeholder = MODES[mode].placeholder;
  submit.textContent = MODES[mode].button;
}

// Reset the page for a new check or search, cancelling the one in progress.
function start(newMode, text) {
  setMode(newMode);
  input.value = text;
  if (controller) controller.abort();
  controller = new AbortController();
  document.body.classList.add("has-results"); // hides the home headline and feature blocks
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setUrl(params, replace) {
  history[replace ? "replaceState" : "pushState"](null, "", "?" + new URLSearchParams(params));
}

// Run a check or a search. `updateUrl` is false when reacting to the URL itself.
function run(newMode, text, updateUrl = true) {
  start(newMode, text);
  if (updateUrl) setUrl({ mode: newMode, q: text });
  if (newMode === "check") chooseInvestor(text, controller.signal);
  else showSearch(text, controller.signal);
}

// Show one specific investor, skipping the "which one do you mean?" step.
function openInvestor(name, about, id = "", replaceUrl = false) {
  start("check", name);
  setUrl({ mode: "check", q: name, about, id, picked: "1" }, replaceUrl);
  showInvestor(name, about, id, controller.signal);
}

// Show whatever the URL says, so links and the back button work.
function showFromUrl() {
  const params = new URLSearchParams(location.search);
  const text = (params.get("q") || "").trim();
  const urlMode = params.get("mode") === "find" ? "find" : "check";
  if (text && urlMode === "check" && params.get("picked")) {
    start("check", text);
    showInvestor(text, params.get("about") || "", params.get("id") || "", controller.signal);
  } else if (text && urlMode === "check" && params.get("choose")) {
    start("check", text);
    chooseInvestor(text, controller.signal, true);
  } else if (text) {
    run(urlMode, text, false);
  } else {
    if (controller) controller.abort();
    setMode(urlMode);
    input.value = "";
    results.replaceChildren();
    document.body.classList.remove("has-results");
  }
}

tabs.forEach((tab) => tab.addEventListener("click", () => {
  setMode(tab.dataset.mode);
  input.focus();
}));

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (text) run(mode, text);
});

// With no key saved here and none on the server, nothing can work: ask for one first.
async function boot() {
  if (!savedKey()) {
    try {
      const status = await (await fetch("/api/key-status")).json();
      if (!status.server_key) {
        location.replace("/key");
        return;
      }
    } catch (e) {
      // carry on; a request will report the problem
    }
  }
  showFromUrl();
}

window.addEventListener("popstate", showFromUrl);
boot();
