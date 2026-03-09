const transcriptEl = document.getElementById("transcript");
const manualInputEl = document.getElementById("manualInput");
const fieldsOutput = document.getElementById("fieldsOutput");
const missingOutput = document.getElementById("missingOutput");
const promptOutput = document.getElementById("promptOutput");
const observerOutput = document.getElementById("observerOutput");
const resultOutput = document.getElementById("resultOutput");
const smsOutput = document.getElementById("smsOutput");
const micStatus = document.getElementById("micStatus");

let recognition = null;
let currentTranscript = "";

const asJson = (value) => JSON.stringify(value, null, 2);

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function appendToTranscript(chunk) {
  currentTranscript = `${currentTranscript} ${chunk}`.trim();
  transcriptEl.value = currentTranscript;
}

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micStatus.textContent = "Browser speech API unavailable. Use manual input.";
    return null;
  }
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (event) => {
    let finalChunk = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalChunk += ` ${transcript}`;
      }
    }
    if (finalChunk.trim()) {
      appendToTranscript(finalChunk.trim());
    }
  };

  recognition.onerror = () => {
    micStatus.textContent = "Microphone error. Use manual input.";
  };

  return recognition;
}

async function processTranscript() {
  const chunk = manualInputEl.value.trim() || transcriptEl.value.trim();
  if (!chunk) {
    return;
  }
  const data = await postJson("/api/transcript", { session_id: "default", chunk });
  currentTranscript = data.transcript;
  transcriptEl.value = data.transcript;
  fieldsOutput.textContent = asJson(data.extracted_fields);
  missingOutput.textContent = asJson(data.missing_fields);
  promptOutput.textContent = data.next_prompt;
  manualInputEl.value = "";
}

async function evaluateClaim() {
  const data = await postJson("/api/claims/evaluate", {
    session_id: "default",
    transcript: transcriptEl.value,
  });
  resultOutput.textContent = asJson({
    claim: data.claim,
    coverage_decision: data.coverage_decision,
    dispatch_plan: data.dispatch_plan,
  });
  observerOutput.textContent = asJson(data.observer_state);
  smsOutput.textContent = data.customer_notification.message;
}

async function resetSession() {
  await fetch("/api/reset?session_id=default", { method: "POST" });
  currentTranscript = "";
  transcriptEl.value = "";
  manualInputEl.value = "";
  fieldsOutput.textContent = "No data yet.";
  missingOutput.textContent = "[]";
  promptOutput.textContent = "Start voice capture to begin.";
  resultOutput.textContent = "No evaluation yet.";
  observerOutput.textContent = "No evaluation yet.";
  smsOutput.textContent = "No messages yet.";
}

document.getElementById("startMic").addEventListener("click", () => {
  if (!recognition) {
    recognition = setupSpeechRecognition();
  }
  if (!recognition) {
    return;
  }
  recognition.start();
  micStatus.textContent = "Voice capture running.";
});

document.getElementById("stopMic").addEventListener("click", () => {
  if (recognition) {
    recognition.stop();
  }
  micStatus.textContent = "Voice capture stopped.";
});

document.getElementById("processTranscript").addEventListener("click", () => {
  processTranscript().catch((error) => {
    promptOutput.textContent = `Error: ${error.message}`;
  });
});

document.getElementById("evaluateClaim").addEventListener("click", () => {
  evaluateClaim().catch((error) => {
    resultOutput.textContent = `Error: ${error.message}`;
  });
});

document.getElementById("resetSession").addEventListener("click", () => {
  resetSession().catch((error) => {
    promptOutput.textContent = `Error: ${error.message}`;
  });
});

document.querySelectorAll(".scenarioButton").forEach((button) => {
  button.addEventListener("click", () => {
    const transcript = button.getAttribute("data-transcript");
    if (transcript) {
      currentTranscript = transcript;
      transcriptEl.value = transcript;
    }
  });
});
