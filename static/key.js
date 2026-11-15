// The API key page: tests the pasted Cala key and saves it in this browser.
// app.js reads it from the same place and sends it with every request.

const STORAGE_KEY = "calaApiKey";

const form = document.getElementById("key-form");
const input = document.getElementById("key");
const toggle = document.getElementById("toggle");
const start = document.getElementById("start");
const problem = document.getElementById("problem");
const saved = document.getElementById("saved");
const remove = document.getElementById("remove");

function savedKey() {
  try {
    return localStorage.getItem(STORAGE_KEY) || "";
  } catch (e) {
    return ""; // storage is blocked, e.g. some private windows
  }
}

function showProblem(text) {
  problem.textContent = text;
  problem.hidden = !text;
}

toggle.addEventListener("click", () => {
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  toggle.textContent = show ? "Hide" : "Show";
  toggle.setAttribute("aria-pressed", String(show));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const key = input.value.trim();
  if (!key) return;

  showProblem("");
  start.disabled = true;
  start.textContent = "Checking…";
  try {
    const response = await fetch("/api/check-key", { method: "POST", headers: { "X-Cala-Key": key } });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      showProblem((data && data.error) || "Something went wrong. Try again in a moment.");
      return;
    }
    try {
      localStorage.setItem(STORAGE_KEY, key);
    } catch (e) {
      showProblem("This browser is blocking saved data, so the key can't be remembered. " +
        "Try a normal (not private) window.");
      return;
    }
    location.href = "/";
  } catch (e) {
    showProblem("Couldn't reach the server. Check your internet connection and try again.");
  } finally {
    start.disabled = false;
    start.textContent = "Start";
  }
});

remove.addEventListener("click", () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    // nothing saved to remove
  }
  saved.hidden = true;
  input.focus();
});

saved.hidden = !savedKey();
if (new URLSearchParams(location.search).get("problem")) {
  showProblem("Cala didn't accept your saved key. Paste it again, or use a new one.");
}
