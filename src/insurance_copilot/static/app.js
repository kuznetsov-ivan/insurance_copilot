const transcriptEl = document.getElementById("transcript");
const manualInputEl = document.getElementById("manualInput");
const fieldsOutput = document.getElementById("fieldsOutput");
const missingOutput = document.getElementById("missingOutput");
const promptOutput = document.getElementById("promptOutput");
const observerOutput = document.getElementById("observerOutput");
const resultOutput = document.getElementById("resultOutput");
const smsOutput = document.getElementById("smsOutput");
const micStatus = document.getElementById("micStatus");
const policyCard = document.getElementById("policyCard");
const coverageCard = document.getElementById("coverageCard");
const mapCanvas = document.getElementById("mapCanvas");
const providerList = document.getElementById("providerList");
const assistantReply = document.getElementById("assistantReply");
const assistantVoicePlayer = document.getElementById("assistantVoicePlayer");
const recordVoiceButton = document.getElementById("recordVoice");
const stopVoiceButton = document.getElementById("stopVoice");
const recordingBadge = document.getElementById("recordingBadge");
const evaluateClaimButton = document.getElementById("evaluateClaim");
const processTranscriptButton = document.getElementById("processTranscript");
const resetSessionButton = document.getElementById("resetSession");
const coverageLoading = document.getElementById("coverageLoading");
const coverageOverlay = document.getElementById("coverageOverlay");
const intakePanel = document.getElementById("intakePanel");
const coveragePanel = document.getElementById("coveragePanel");
const intakeLoading = document.getElementById("intakeLoading");
const intakeLoadingTitle = document.getElementById("intakeLoadingTitle");
const intakeLoadingText = document.getElementById("intakeLoadingText");

let currentTranscript = "";
let mediaRecorder = null;
let activeStream = null;
let audioChunks = [];

function asJson(value) {
  return JSON.stringify(value, null, 2);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {}
    throw new Error(detail);
  }
  return response.json();
}

async function postVoiceTurn(blob) {
  const formData = new FormData();
  formData.append("session_id", "default");
  formData.append("audio", blob, "voice-turn.webm");
  const response = await fetch("/api/voice/turn", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {}
    throw new Error(detail);
  }
  return response.json();
}

function appendToTranscript(chunk) {
  currentTranscript = `${currentTranscript} ${chunk}`.trim();
  transcriptEl.value = currentTranscript;
}

function renderPolicy(policy) {
  if (!policy) {
    policyCard.className = "detail-card empty";
    policyCard.innerHTML = "No policy matched yet.";
    return;
  }

  policyCard.className = "detail-card";
  policyCard.innerHTML = `
    <div class="metric-row"><span>Customer</span><strong>${policy.customer_name}</strong></div>
    <div class="metric-row"><span>Policy</span><strong>${policy.policy_reference}</strong></div>
    <div class="metric-row"><span>Status</span><strong>${policy.status}</strong></div>
    <div class="metric-row"><span>Phone</span><strong>${policy.phone || "N/A"}</strong></div>
    <div class="tag-row">
      <span class="tag ${policy.roadside_assistance ? "ok" : "warn"}">Roadside ${policy.roadside_assistance ? "Included" : "Excluded"}</span>
      <span class="tag ${policy.tow_covered ? "ok" : "warn"}">Tow ${policy.tow_covered ? "Covered" : "Excluded"}</span>
      <span class="tag ${policy.repair_van_covered ? "ok" : "warn"}">Repair Van ${policy.repair_van_covered ? "Covered" : "Excluded"}</span>
    </div>
    <div class="note-block">
      <span>Covered Regions</span>
      <strong>${policy.covered_regions.join(", ") || "N/A"}</strong>
    </div>
    <div class="note-block">
      <span>Exclusions</span>
      <strong>${policy.exclusions.join(", ") || "None"}</strong>
    </div>
  `;
}

function renderCoverage(decision, followUps) {
  if (!decision) {
    coverageCard.className = "detail-card empty";
    coverageCard.innerHTML = "No assessment yet.";
    return;
  }

  coverageCard.className = "detail-card";
  coverageCard.innerHTML = `
    <div class="headline-row">
      <span class="pill ${decision.status}">${decision.status.replace("_", " ")}</span>
      <strong>${Math.round(decision.confidence * 100)}% confidence</strong>
    </div>
    <p>${decision.customer_explanation}</p>
    <div class="note-block">
      <span>Rationale</span>
      <strong>${decision.reason}</strong>
    </div>
    <div class="note-block">
      <span>Follow Up</span>
      <strong>${followUps.length ? followUps.join(" ") : "No additional follow-up required."}</strong>
    </div>
  `;
}

function parseClaimCoordinates(location) {
  if (!location) {
    return { lat: 40.74, lon: -73.98 };
  }
  const coords = location.includes(":") ? location.split(":")[1] : location;
  const [lat, lon] = coords.split(",").map((value) => Number.parseFloat(value.trim()));
  if (Number.isNaN(lat) || Number.isNaN(lon)) {
    return { lat: 40.74, lon: -73.98 };
  }
  return { lat, lon };
}

function plotPoint(label, lat, lon, className) {
  const x = ((lon + 74.05) / 0.18) * 100;
  const y = (1 - (lat - 40.66) / 0.18) * 100;
  return `
    <div class="map-point ${className}" style="left:${x}%; top:${y}%;">
      <span>${label}</span>
    </div>
  `;
}

function renderMap(claim, providers) {
  if (!providers.length) {
    mapCanvas.innerHTML = '<div class="map-empty">No dispatch map available for this outcome.</div>';
    providerList.innerHTML = "";
    return;
  }

  const customer = parseClaimCoordinates(claim.location);
  const mapPoints = [
    plotPoint("Client", customer.lat, customer.lon, "client"),
    ...providers.map((provider, index) =>
      plotPoint(`${index + 1}`, provider.lat, provider.lon, provider.selected ? "selected" : "provider")
    ),
  ];

  mapCanvas.innerHTML = `
    <div class="map-grid"></div>
    ${mapPoints.join("")}
  `;

  providerList.innerHTML = providers
    .map(
      (provider, index) => `
        <div class="provider-card ${provider.selected ? "selected" : ""}">
          <div>
            <strong>${index + 1}. ${provider.provider_name}</strong>
            <p>${provider.garage_name}</p>
          </div>
          <div>
            <span>${provider.eta_minutes} min ETA</span>
            <span>${provider.capabilities.join(", ")}</span>
          </div>
        </div>
      `
    )
    .join("");
}

function renderDispatch(dispatchPlan) {
  if (!dispatchPlan || dispatchPlan.action_type === "manual_escalation") {
    resultOutput.className = "detail-card empty";
    resultOutput.innerHTML = "No automatic dispatch. Manual review required.";
    return;
  }

  resultOutput.className = "detail-card";
  resultOutput.innerHTML = `
    <div class="metric-row"><span>Action</span><strong>${dispatchPlan.action_type.replace("_", " ")}</strong></div>
    <div class="metric-row"><span>Provider</span><strong>${dispatchPlan.provider_name}</strong></div>
    <div class="metric-row"><span>Garage</span><strong>${dispatchPlan.garage_name}</strong></div>
    <div class="metric-row"><span>ETA</span><strong>${dispatchPlan.eta_minutes} minutes</strong></div>
    <div class="note-block">
      <span>Ancillary Benefits</span>
      <strong>${dispatchPlan.ancillary_benefits.length ? dispatchPlan.ancillary_benefits.join(", ") : "None"}</strong>
    </div>
  `;
}

function setPanelBusy(panel, isBusy) {
  panel.classList.toggle("panel-busy", isBusy);
}

function setIntakeLoading(isLoading, title = "Working...", message = "Waiting for the model.") {
  intakeLoading.classList.toggle("hidden", !isLoading);
  intakeLoadingTitle.textContent = title;
  intakeLoadingText.textContent = message;
  processTranscriptButton.disabled = isLoading;
  recordVoiceButton.disabled = isLoading;
  stopVoiceButton.disabled = isLoading || !mediaRecorder;
  resetSessionButton.disabled = isLoading;
  setPanelBusy(intakePanel, isLoading);
}

function setCoverageLoading(isLoading) {
  evaluateClaimButton.disabled = isLoading;
  resetSessionButton.disabled = isLoading;
  coverageLoading.classList.toggle("hidden", !isLoading);
  coverageOverlay.classList.toggle("hidden", !isLoading);
  evaluateClaimButton.textContent = isLoading ? "Running Coverage Check..." : "Run Coverage Check";
  setPanelBusy(coveragePanel, isLoading);

  if (isLoading) {
    policyCard.className = "detail-card empty";
    policyCard.innerHTML = "Looking up policy record...";
    coverageCard.className = "detail-card empty";
    coverageCard.innerHTML = "Running coverage checks...";
    resultOutput.className = "detail-card empty";
    resultOutput.innerHTML = "Planning dispatch...";
  }
}

function renderCoverageError(message) {
  const text = `Error: ${message}`;
  policyCard.className = "detail-card empty";
  policyCard.innerHTML = text;
  coverageCard.className = "detail-card empty";
  coverageCard.innerHTML = text;
  resultOutput.className = "detail-card empty";
  resultOutput.innerHTML = text;
  observerOutput.textContent = text;
}

async function processTranscript() {
  const chunk = manualInputEl.value.trim() || transcriptEl.value.trim();
  if (!chunk) {
    assistantReply.textContent = "Add conversation text or record a voice turn first.";
    return;
  }
  setIntakeLoading(true, "Extracting claim details", "Passing the full conversation to gpt-5.1.");
  try {
    const data = await postJson("/api/transcript", { session_id: "default", chunk });
    currentTranscript = data.transcript;
    transcriptEl.value = data.transcript;
    fieldsOutput.textContent = asJson(data.extracted_fields);
    missingOutput.textContent = asJson(data.missing_fields);
    promptOutput.textContent = data.next_prompt;
    assistantReply.textContent = `Processed with ${data.assistant_source.toUpperCase()} extraction.`;
    manualInputEl.value = "";
  } finally {
    setIntakeLoading(false);
  }
}

async function evaluateClaim() {
  if (!transcriptEl.value.trim()) {
    renderCoverageError("No conversation available. Record or send a transcript first.");
    return;
  }
  setCoverageLoading(true);
  const data = await postJson("/api/claims/evaluate", {
    session_id: "default",
    transcript: transcriptEl.value,
  });

  renderPolicy(data.matched_policy);
  renderCoverage(data.coverage_decision, data.follow_up_questions);
  renderDispatch(data.dispatch_plan);
  renderMap(data.claim, data.provider_candidates);

  observerOutput.textContent = asJson(data.observer_state);
  smsOutput.textContent = data.customer_notification.message;
  setCoverageLoading(false);
}

function stopActiveStream() {
  if (activeStream) {
    activeStream.getTracks().forEach((track) => track.stop());
    activeStream = null;
  }
}

async function startVoiceTurn() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("Audio recording is not supported in this browser.");
  }
  activeStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(activeStream, { mimeType: "audio/webm" });
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };
  mediaRecorder.start();
  recordVoiceButton.classList.add("recording");
  stopVoiceButton.disabled = false;
  recordingBadge.classList.remove("hidden");
  micStatus.textContent = "Recording voice turn for backend STT.";
}

async function stopVoiceTurn() {
  if (!mediaRecorder) {
    return;
  }
  const recorder = mediaRecorder;
  recordVoiceButton.classList.remove("recording");
  recordingBadge.classList.add("hidden");
  setIntakeLoading(true, "Processing voice turn", "Transcribing audio and extracting claim fields.");
  try {
    const data = await new Promise((resolve, reject) => {
      recorder.onstop = async () => {
        try {
          const blob = new Blob(audioChunks, { type: "audio/webm" });
          stopActiveStream();
          resolve(await postVoiceTurn(blob));
        } catch (error) {
          reject(error);
        }
      };
      recorder.stop();
    });
    mediaRecorder = null;
    currentTranscript = data.transcript;
    transcriptEl.value = data.transcript;
    fieldsOutput.textContent = asJson(data.extracted_fields);
    missingOutput.textContent = asJson(data.missing_fields);
    promptOutput.textContent = data.next_prompt;
    assistantReply.textContent = data.assistant_text;
    if (data.assistant_audio_base64) {
      assistantVoicePlayer.src = `data:${data.assistant_audio_mime_type};base64,${data.assistant_audio_base64}`;
      assistantVoicePlayer.play().catch(() => {});
    }
    micStatus.textContent = `Voice turn processed with ${data.assistant_source.toUpperCase()}.`;
  } finally {
    mediaRecorder = null;
    setIntakeLoading(false);
  }
}

async function resetSession() {
  await fetch("/api/reset?session_id=default", { method: "POST" });
  currentTranscript = "";
  transcriptEl.value = "";
  manualInputEl.value = "";
  fieldsOutput.textContent = "No data yet.";
  missingOutput.textContent = "[]";
  promptOutput.textContent = "Start voice capture to begin.";
  observerOutput.textContent = "No evaluation yet.";
  smsOutput.textContent = "No messages yet.";
  assistantReply.textContent = "The voice agent will reply here after each recorded turn.";
  assistantVoicePlayer.removeAttribute("src");
  assistantVoicePlayer.load();
  recordVoiceButton.classList.remove("recording");
  stopVoiceButton.disabled = true;
  recordingBadge.classList.add("hidden");
  setIntakeLoading(false);
  renderPolicy(null);
  renderCoverage(null, []);
  renderDispatch(null);
  renderMap({}, []);
  setCoverageLoading(false);
}

recordVoiceButton.addEventListener("click", () => {
  if (mediaRecorder) {
    return;
  }
  startVoiceTurn().catch((error) => {
    setIntakeLoading(false);
    assistantReply.textContent = `Error: ${error.message}`;
  });
});

stopVoiceButton.addEventListener("click", () => {
  if (!mediaRecorder) {
    return;
  }
  stopVoiceTurn().catch((error) => {
    setIntakeLoading(false);
    assistantReply.textContent = `Error: ${error.message}`;
  });
});

document.getElementById("processTranscript").addEventListener("click", () => {
  processTranscript().catch((error) => {
    setIntakeLoading(false);
    promptOutput.textContent = `Error: ${error.message}`;
    assistantReply.textContent = `Error: ${error.message}`;
  });
});

evaluateClaimButton.addEventListener("click", () => {
  evaluateClaim().catch((error) => {
    setCoverageLoading(false);
    renderCoverageError(error.message);
  });
});

resetSessionButton.addEventListener("click", () => {
  resetSession().catch((error) => {
    setCoverageLoading(false);
    promptOutput.textContent = `Error: ${error.message}`;
  });
});

document.querySelectorAll(".scenarioButton").forEach((button) => {
  button.addEventListener("click", () => {
    const transcript = button.getAttribute("data-transcript");
    if (transcript) {
      currentTranscript = transcript;
      transcriptEl.value = transcript;
      manualInputEl.value = transcript;
    }
  });
});

stopVoiceButton.disabled = true;
setIntakeLoading(false);
setCoverageLoading(false);
renderMap({}, []);
