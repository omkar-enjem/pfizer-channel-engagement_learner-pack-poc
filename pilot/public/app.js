const $ = (id) => document.getElementById(id);
const SAMPLES = [["CLM-2608-01778", "Clean claim"], ["CLM-2608-02777", "Hold: window + invoice"], ["CLM-2608-04515", "Hold: window + repeat"],
                 ["CLM-2511-01801", "Needs a person"], ["CLM-2609-99999", "Not in file"]];
let answers = [], shown = 0;

function el(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function setStatus(msg, err) { $("status").textContent = msg || ""; $("status").className = err ? "err" : ""; }
const inr = (n) => "₹" + Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function render(a) {
  $("out").hidden = false;
  const b = $("badge"); b.textContent = a.label; b.className = a.recommendation;
  $("explain").textContent = a.explanation || "";
  const rs = $("reasons"); rs.replaceChildren(...a.reasons.map((r) => el("li", r)));
  $("amount").textContent = a.amount_at_issue_inr ? "Amount at issue: " + inr(a.amount_at_issue_inr) + " (largest single flagged amount, not a sum)" : "";
  $("notes").replaceChildren(...(a.notes || []).map((n) => el("li", n)));
  $("checks").tBodies[0].replaceChildren(...a.checks.map((c) => {
    const tr = el("tr"); tr.append(el("td", c.rule), el("td", c.status.replace("_", " "), c.status), el("td", c.summary), el("td", c.clause)); return tr;
  }));
  $("evidence").tBodies[0].replaceChildren(...a.evidence.map((e) => {
    const rows = e.rows.join(", ") + (e.row_count > e.rows.length ? " … (" + e.row_count + " rows)" : "");
    const vals = Object.entries(e.values).map(([k, v]) => k + ": " + v).join("; ");
    const tr = el("tr"); tr.append(el("td", e.fact), el("td", e.file), el("td", rows), el("td", vals)); return tr;
  }));
  $("foot").textContent = "Row numbers are line numbers in the original pack file. Explanation by " + (a.explanation_source === "model" ? "the model, limited to verified numbers" : "a fixed template") + ". The decision above is made by code, not the model.";
}

function tabs() {
  const t = $("tabs"); t.replaceChildren();
  if (answers.length < 2) return;
  answers.forEach((a, i) => { const bt = el("button", "Claim line " + (i + 1) + " of " + answers.length); bt.type = "button"; if (i === shown) bt.className = "on"; bt.onclick = () => { shown = i; tabs(); render(answers[i]); }; t.append(bt); });
}

async function run(text) {
  $("out").hidden = true; $("tabs").replaceChildren(); setStatus("Checking…"); $("go").disabled = true;
  try {
    const r = await fetch("/api/check", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: text, stockist_code: $("stockist").value, received_date: $("received").value }) });
    const j = await r.json();
    if (!r.ok) { setStatus(j.error || "Something went wrong. Try again.", true); return; }
    answers = j.results; shown = 0; setStatus(""); tabs(); render(answers[0]);
  } catch (e) { setStatus("Could not reach the server. Check your connection and try again.", true); }
  finally { $("go").disabled = false; }
}

$("form").addEventListener("submit", (e) => { e.preventDefault(); run($("input").value); });
SAMPLES.forEach(([cn, label]) => { const c = el("button", cn + " · " + label, "chip"); c.type = "button"; c.onclick = () => { $("input").value = cn; run(cn); }; $("chips").append(c); });
$("emails").addEventListener("change", (e) => { if (e.target.value) { $("input").value = e.target.value; run(e.target.value); } });
fetch("/api/emails").then((r) => r.json()).then((list) => list.forEach((m) => { const o = el("option", m.email_id + " · " + m.from + " · " + m.subject); o.value = m.email_id; $("emails").append(o); })).catch(() => {});
