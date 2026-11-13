// Calls the FastAPI backend. Same origin, so no CORS setup is needed.
const form = document.getElementById("ask");
const status = document.getElementById("status");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = document.getElementById("q").value.trim();
  if (!question) return;
  status.textContent = "Thinking...";
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Server returned ${res.status}`);
    document.getElementById("answer").textContent = data.answer;
    document.getElementById("evidence").textContent = data.evidence.join("\n\n") || "No tool was called.";
    document.getElementById("out").hidden = false;
    status.textContent = `${data.model_calls} model call(s)`;
  } catch (err) {
    status.textContent = `Something went wrong: ${err.message}. Check /api/health and the logs.`;
  }
});
