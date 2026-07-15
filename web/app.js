const state = {
  jurisdiction: localStorage.getItem("roadlegal_jurisdiction") || "india_national",
  jurisdictions: [],
  score: Number(localStorage.getItem("roadlegal_score") || "0"),
  quiz: [],
  quizIndex: 0,
  countryProfiles: {
    india_national: {
      title: "India",
      side: "Left-hand traffic",
      coverage: "verified starter",
      focus: "Motor Vehicles Act, challan calculator, helmets, speed, drink driving",
      note: "India has the strongest starter fine coverage in this MVP."
    },
    delhi: {
      title: "Delhi, India",
      side: "Left-hand traffic",
      coverage: "city layer",
      focus: "Delhi traffic enforcement and India national baseline",
      note: "Use Delhi for local demo cases where compounding practice differs from national baseline."
    },
    bangladesh_national: {
      title: "Bangladesh",
      side: "Left-hand traffic",
      coverage: "review needed",
      focus: "Road Transport Act, BRTA/legal review, documents",
      note: "Fine amounts are intentionally cautious until the latest official schedule is reviewed."
    },
    bhutan_national: {
      title: "Bhutan",
      side: "Left-hand traffic",
      coverage: "review needed",
      focus: "RSTA law source, licence and safety reminders",
      note: "Starter law mode is ready; challan values need official schedule review."
    },
    nepal_national: {
      title: "Nepal",
      side: "Left-hand traffic",
      coverage: "review needed",
      focus: "Motor vehicle act, documents, speed safety",
      note: "Use for cautious legal guidance while fine schedules are being verified."
    },
    sri_lanka_national: {
      title: "Sri Lanka",
      side: "Left-hand traffic",
      coverage: "review needed",
      focus: "Motor Traffic Act starter coverage",
      note: "RoadLegal distinguishes spot-fine and court-referred offences once schedules are added."
    },
    thailand_national: {
      title: "Thailand",
      side: "Left-hand traffic",
      coverage: "expanded game mode",
      focus: "Land Traffic Act, helmets, speed signs, drink driving, tourist documents",
      note: "Thailand now has richer law passages, calculator offence types, and scenario quiz content."
    },
    myanmar_national: {
      title: "Myanmar",
      side: "Right-hand traffic",
      coverage: "review needed",
      focus: "Vehicle law starter coverage and cautious safety guidance",
      note: "Fine amounts remain source-needed until current official material is reviewed."
    }
  },
  directory: {
    india_national: [
      ["Parivahan e-Challan", "https://echallan.parivahan.gov.in/"],
      ["MoRTH", "https://morth.nic.in/"],
      ["Emergency", "112"]
    ],
    delhi: [
      ["Delhi Traffic Police", "https://traffic.delhipolice.gov.in/"],
      ["Parivahan e-Challan", "https://echallan.parivahan.gov.in/"],
      ["Emergency", "112"]
    ],
    bangladesh_national: [
      ["BRTA", "https://brta.gov.bd/"],
      ["National emergency service", "999"]
    ],
    nepal_national: [
      ["Department of Transport Management", "https://www.dotm.gov.np/"],
      ["Police emergency", "100"]
    ],
    bhutan_national: [
      ["Road Safety and Transport Authority", "https://www.rsta.gov.bt/"],
      ["Emergency", "113"]
    ],
    sri_lanka_national: [
      ["Sri Lanka Police", "https://www.police.lk/"],
      ["Police emergency", "119"]
    ],
    thailand_national: [
      ["Royal Thai Police", "https://www.royalthaipolice.go.th/"],
      ["Department of Land Transport", "https://www.dlt.go.th/"],
      ["Highway Police", "https://highway.police.go.th/"],
      ["Tourist Police", "1155"],
      ["Medical emergency", "1669"],
      ["Police emergency", "191"]
    ],
    myanmar_national: [
      ["Myanmar law reference", "https://www.myanmar-law-library.org/"],
      ["Emergency", "199"]
    ]
  }
};

const $ = (id) => document.getElementById(id);
const apiQuery = new URLSearchParams(window.location.search).get("api");
if (apiQuery) localStorage.setItem("roadlegal_api_base", apiQuery.replace(/\/$/, ""));
const sameOriginBackend = ["localhost", "127.0.0.1"].includes(window.location.hostname) || window.location.hostname.endsWith(".hf.space");
const apiBase = (
  apiQuery ||
  (sameOriginBackend ? "" : window.ROADLEGAL_CONFIG?.apiBase) ||
  localStorage.getItem("roadlegal_api_base") ||
  ""
).replace(/\/$/, "");
let backendAvailable = true;
let backendRetryTimer = null;
let staticDataPromise = null;

const offenceAliases = {
  speed: "overspeeding",
  speeding: "overspeeding",
  overspeed: "overspeeding",
  helmet: "no_helmet",
  "no helmet": "no_helmet",
  "seat belt": "no_seatbelt",
  seatbelt: "no_seatbelt",
  drunk: "drink_driving",
  drink: "drink_driving",
  alcohol: "drink_driving",
  license: "no_license",
  licence: "no_license",
  phone: "mobile_phone",
  mobile: "mobile_phone",
  insurance: "no_insurance",
  registration: "no_registration"
};

const retrievalAliases = {
  overspeeding: ["speed", "speeding", "speed limit", "ความเร็ว", "ขับรถเร็ว", "গতি", "द्रुतगति", "तीव्र गति", "වේගය", "အမြန်နှုန်း"],
  no_helmet: ["helmet", "no helmet", "หมวกกันน็อก", "หมวกนิรภัย", "হেলমেট", "हेलमेट", "हेल्मेट", "හිස්වැසුම", "ဦးထုပ်"],
  no_seatbelt: ["seat belt", "seatbelt", "เข็มขัดนิรภัย", "সিটবেল্ট", "सिट बेल्ट", "सीट बेल्ट", "ආසන පටිය", "ထိုင်ခုံခါးပတ်"],
  drink_driving: ["drink driving", "drunk driving", "alcohol", "เมาแล้วขับ", "แอลกอฮอล์", "মদ্যপ", "मादक", "नशे", "බීමත්ව", "အရက်မူးမောင်း"],
  no_license: ["license", "licence", "ใบขับขี่", "ড্রাইভিং লাইসেন্স", "चालक अनुमति", "ड्राइविंग लाइसेंस", "රියදුරු බලපත්‍රය", "ယာဉ်မောင်းလိုင်စင်"],
  mobile_phone: ["mobile phone", "cell phone", "โทรศัพท์", "মোবাইল ফোন", "मोबाइल फोन", "ජංගම දුරකථනය", "မိုဘိုင်းဖုန်း"]
};

const countryBoxes = [
  ["india_national", "India", 6.5, 37.1, 68.0, 97.5],
  ["bangladesh_national", "Bangladesh", 20.5, 26.8, 88.0, 92.8],
  ["bhutan_national", "Bhutan", 26.6, 28.4, 88.7, 92.2],
  ["nepal_national", "Nepal", 26.2, 30.5, 80.0, 88.3],
  ["sri_lanka_national", "Sri Lanka", 5.8, 10.0, 79.5, 82.1],
  ["thailand_national", "Thailand", 5.4, 20.6, 97.3, 105.7],
  ["myanmar_national", "Myanmar", 9.4, 28.6, 92.1, 101.2]
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options = {}) {
  if (backendAvailable) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), path.endsWith("/api/chat") ? 90000 : 5000);
    try {
      const response = await fetch(`${apiBase}${path}`, {
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        ...options
      });
      if (!response.ok) {
        throw new Error(response.statusText);
      }
      return response.json();
    } catch (error) {
      backendAvailable = false;
      scheduleBackendRetry();
      console.info("RoadLegal backend unavailable; using static demo mode.", error);
    } finally {
      clearTimeout(timeout);
    }
  }
  return staticApi(path, options);
}

function renderHealth(health) {
  $("modeText").textContent = health.model.mode;
  $("indexText").textContent = `${health.passages} passages`;
  $("modelText").textContent = health.model.loaded
    ? "Qwen3 ready"
    : health.model.gguf_model || health.model.mode === "model-loading"
      ? "model warming"
      : "extractive fallback";
  $("modelText").title = health.model.note;
}

function scheduleBackendRetry(delay = 30000) {
  if (!apiBase || sameOriginBackend || backendRetryTimer) return;
  backendRetryTimer = setTimeout(async () => {
    backendRetryTimer = null;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${apiBase}/api/health`, {signal: controller.signal});
      if (!response.ok) throw new Error(response.statusText);
      const health = await response.json();
      backendAvailable = true;
      renderHealth(health);
    } catch (error) {
      console.info("RoadLegal AI backend is still warming.", error);
      scheduleBackendRetry(60000);
    } finally {
      clearTimeout(timeout);
    }
  }, delay);
}

async function getStaticData() {
  if (!staticDataPromise) {
    staticDataPromise = fetch("static-data.json").then((response) => {
      if (!response.ok) throw new Error("static-data.json is missing");
      return response.json();
    });
  }
  return staticDataPromise;
}

async function staticApi(path, options = {}) {
  const data = await getStaticData();
  const url = new URL(path, window.location.origin);
  const body = options.body ? JSON.parse(options.body) : {};
  if (url.pathname.endsWith("/api/health")) return data.health;
  if (url.pathname.endsWith("/api/jurisdictions")) return { jurisdictions: data.jurisdictions };
  if (url.pathname.endsWith("/api/offences")) {
    const jurisdiction = url.searchParams.get("jurisdiction") || "india_national";
    return { offences: staticOffences(data, jurisdiction) };
  }
  if (url.pathname.endsWith("/api/geofence")) {
    return staticGeofence(Number(url.searchParams.get("lat")), Number(url.searchParams.get("lon")));
  }
  if (url.pathname.endsWith("/api/quiz")) {
    const jurisdiction = url.searchParams.get("jurisdiction") || "india_national";
    return data.quizzes[jurisdiction] || data.quizzes.india_national;
  }
  if (url.pathname.endsWith("/api/calculate-challan")) {
    return staticCalculate(data, body.jurisdiction, body.offence, body.vehicle_class);
  }
  if (url.pathname.endsWith("/api/chat")) {
    return staticChat(data, body.message, body.jurisdiction, body.language);
  }
  if (url.pathname.endsWith("/api/feedback")) {
    const current = JSON.parse(localStorage.getItem("roadlegal_feedback") || "[]");
    current.push({ ...body, saved_static: true });
    localStorage.setItem("roadlegal_feedback", JSON.stringify(current.slice(-50)));
    return { ok: true };
  }
  throw new Error(`No static handler for ${path}`);
}

function staticOffences(data, jurisdiction) {
  const record = staticJurisdictionData(data, jurisdiction);
  return Object.entries(record.offences || {}).map(([id, value]) => ({
    id,
    label: value.label || id,
    vehicle_classes: Object.keys(value.vehicles || {})
  }));
}

function staticJurisdictionData(data, jurisdiction) {
  const aliases = data.fine_schedule.aliases || {};
  const key = aliases[jurisdiction] || jurisdiction || "india_national";
  return data.fine_schedule.jurisdictions[key] || data.fine_schedule.jurisdictions.india_national;
}

function normalizeOffence(value) {
  const key = String(value || "").toLowerCase().replaceAll("_", " ").trim();
  if (offenceAliases[key]) return offenceAliases[key];
  for (const [alias, canonical] of Object.entries(offenceAliases)) {
    if (key.includes(alias)) return canonical;
  }
  return key.replaceAll(" ", "_");
}

function staticCalculate(data, jurisdiction, offence, vehicleClass = "light_motor_vehicle") {
  const jurisdictionKey = data.fine_schedule.aliases?.[jurisdiction] || jurisdiction || "india_national";
  const jurisdictionData = staticJurisdictionData(data, jurisdictionKey);
  const offenceKey = normalizeOffence(offence);
  const vehicleKey = String(vehicleClass || "light_motor_vehicle").toLowerCase().replaceAll(" ", "_");
  const offenceData = jurisdictionData.offences?.[offenceKey];
  if (!offenceData) {
    return {
      jurisdiction: jurisdictionKey,
      offence: offenceKey,
      vehicle_class: vehicleKey,
      status: "unknown_offence",
      amount_display: "No verified fine in the local schedule.",
      legal_basis: "No local structured fine record yet.",
      consequences: [],
      caveats: ["Ask a more specific question or update the source schedule."],
      source: null
    };
  }
  const vehicleData = offenceData.vehicles?.[vehicleKey] || offenceData.vehicles?.any || {};
  let amount = vehicleData.amount_display;
  if (!amount) {
    const currency = vehicleData.currency || "";
    if (vehicleData.fine_min && vehicleData.fine_max && vehicleData.fine_min !== vehicleData.fine_max) {
      amount = `${currency}${vehicleData.fine_min.toLocaleString()} - ${currency}${vehicleData.fine_max.toLocaleString()}`;
    } else if (vehicleData.fine_min) {
      amount = `${currency}${vehicleData.fine_min.toLocaleString()}`;
    } else {
      amount = "Amount requires local verification.";
    }
  }
  return {
    jurisdiction: jurisdictionKey,
    offence: offenceKey,
    vehicle_class: vehicleKey,
    status: vehicleData.status || "verified",
    amount_display: amount,
    legal_basis: offenceData.legal_basis || "",
    consequences: vehicleData.consequences || offenceData.consequences || [],
    caveats: vehicleData.caveats || offenceData.caveats || [],
    source: offenceData.source || null
  };
}

function staticGeofence(lat, lon) {
  const matches = countryBoxes
    .filter(([, , minLat, maxLat, minLon, maxLon]) => minLat <= lat && lat <= maxLat && minLon <= lon && lon <= maxLon)
    .map(([jurisdiction, country, minLat, maxLat, minLon, maxLon]) => ({
      area: (maxLat - minLat) * (maxLon - minLon),
      jurisdiction,
      country
    }))
    .sort((a, b) => a.area - b.area);
  if (matches.length) {
    return {
      matched: true,
      jurisdiction: matches[0].jurisdiction,
      country: matches[0].country,
      confidence: 0.72,
      note: "Country-level geofence from static demo data."
    };
  }
  return {
    matched: false,
    jurisdiction: "india_national",
    country: "Unknown",
    confidence: 0,
    note: "Coordinates are outside the starter BIMSTEC bounding boxes."
  };
}

function tokenize(value) {
  return String(value || "").toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
}

function expandStaticQuery(value) {
  const normalized = String(value || "").toLocaleLowerCase();
  const terms = tokenize(normalized);
  const concepts = [];
  Object.entries(retrievalAliases).forEach(([concept, aliases]) => {
    if (aliases.some((alias) => normalized.includes(alias.toLocaleLowerCase()))) {
      concepts.push(concept);
      terms.push(...tokenize(concept.replaceAll("_", " ")));
      aliases.filter((alias) => /^[\x00-\x7F]+$/.test(alias)).forEach((alias) => terms.push(...tokenize(alias)));
    }
  });
  return { terms: [...new Set(terms)], concepts };
}

function staticSearch(data, message, jurisdiction) {
  const { terms, concepts } = expandStaticQuery(message);
  const allowed = new Set([jurisdiction, "global", "bimstec"]);
  if (jurisdiction === "delhi") allowed.add("india_national");
  return data.passages
    .filter((passage) => allowed.has(passage.jurisdiction))
    .map((passage) => {
      const title = String(passage.title || "").toLocaleLowerCase();
      const body = String(passage.text || "").toLocaleLowerCase();
      const tags = (passage.tags || []).map((tag) => String(tag).toLocaleLowerCase());
      let score = terms.reduce((total, term) => total + (body.includes(term) ? 1 : 0) + (title.includes(term) ? 1.8 : 0), 0);
      score += terms.reduce((total, term) => total + (tags.some((tag) => tag.includes(term)) ? 1.4 : 0), 0);
      score += concepts.reduce((total, concept) => total + (tags.includes(concept) ? 2.4 : 0), 0);
      if (passage.jurisdiction === jurisdiction) score *= 1.38;
      if (passage.jurisdiction === "global") score *= 0.78;
      if (passage.jurisdiction === "bimstec") score *= 0.92;
      score *= passage.verified ? 1.14 : 0.84;
      if (["official_law", "official_government", "official_public_health"].includes(passage.source_type)) score *= 1.16;
      return { ...passage, score };
    })
    .filter((passage) => passage.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
}

function safetyTip(message) {
  const lowered = String(message || "").toLowerCase();
  if (lowered.includes("helmet") || lowered.includes("bike") || lowered.includes("motorcycle") || lowered.includes("scooter")) {
    return "Correct helmet use sharply reduces death and brain-injury risk; replace damaged helmets and fasten the strap.";
  }
  if (lowered.includes("speed")) {
    return "Small speed increases raise both crash likelihood and injury severity, so match speed to road, weather, and pedestrian activity.";
  }
  if (lowered.includes("seat") || lowered.includes("belt")) {
    return "Seat belts reduce fatal injury risk for vehicle occupants and should be used on every trip.";
  }
  if (lowered.includes("drink") || lowered.includes("alcohol") || lowered.includes("drunk")) {
    return "Alcohol impairment begins before a driver feels obviously drunk; use a sober driver or public transport.";
  }
  return "";
}

function staticChat(data, message, jurisdiction = "india_national", language = "English") {
  const retrieved = staticSearch(data, message, jurisdiction);
  const expanded = expandStaticQuery(message);
  const offenceInput = expanded.concepts[0] || message;
  const twoWheeler = expanded.concepts.includes("no_helmet") || message?.toLowerCase().includes("bike") || message?.toLowerCase().includes("scooter");
  const fine = staticCalculate(data, jurisdiction, offenceInput, twoWheeler ? "two_wheeler" : "light_motor_vehicle");
  const lines = [];
  if (fine.status !== "unknown_offence") {
    lines.push(`Challan estimate for ${fine.jurisdiction.replaceAll("_", " ")}: ${fine.amount_display}.`);
    if (fine.legal_basis) lines.push(`Legal basis: ${fine.legal_basis}.`);
    if (fine.consequences?.length) lines.push(`Possible consequences: ${fine.consequences.join("; ")}.`);
    if (fine.caveats?.length) lines.push(`Caveat: ${fine.caveats.join(" ")}`);
  }
  if (retrieved.length) {
    lines.push("Grounded answer:");
    retrieved.slice(0, 3).forEach((item) => {
      const snippet = item.text.length > 260 ? `${item.text.slice(0, 257).trim()}...` : item.text;
      lines.push(`- ${snippet} [${item.source_title}]`);
    });
  } else {
    lines.push("I do not have enough packaged source material to answer that safely yet.");
  }
  const tip = safetyTip(message);
  if (tip) lines.push(`Safety coach: ${tip}`);
  lines.push(`Mode: static GitHub Pages demo. Language selected: ${language}. Verify urgent or disputed matters with the local traffic authority.`);
  return {
    answer: lines.join("\n"),
    mode: "static-rag",
    jurisdiction,
    language,
    citations: retrieved.map((item) => ({
      title: item.source_title,
      url: item.source_url,
      passage: item.title,
      country: item.country,
      verified: item.verified
    })),
    fine,
    model: data.health.model
  };
}

function addMessage(role, text, citations = []) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  if (citations.length) {
    const box = document.createElement("div");
    box.className = "citations";
    citations.slice(0, 5).forEach((citation) => {
      const line = document.createElement("div");
      line.className = "citation";
      const verified = citation.verified ? "verified" : "review";
      line.innerHTML = `<span>${verified}</span><a target="_blank" rel="noreferrer" href="${escapeHtml(citation.url)}">${escapeHtml(citation.title)}</a>`;
      box.appendChild(line);
    });
    node.appendChild(box);
  }
  $("messages").appendChild(node);
  $("messages").scrollTop = $("messages").scrollHeight;
}

async function loadHealth() {
  const health = await api("/api/health");
  renderHealth(health);
}

async function loadJurisdictions() {
  const data = await api("/api/jurisdictions");
  state.jurisdictions = data.jurisdictions;
  if (!data.jurisdictions.some((item) => item.id === state.jurisdiction)) {
    state.jurisdiction = "india_national";
  }
  const groups = data.jurisdictions.reduce((acc, item) => {
    const key = item.country || "Other";
    acc[key] = acc[key] || [];
    acc[key].push(item);
    return acc;
  }, {});
  $("jurisdictionSelect").innerHTML = Object.keys(groups)
    .sort()
    .map((country) => {
      const options = groups[country]
        .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`)
        .join("");
      return `<optgroup label="${escapeHtml(country)}">${options}</optgroup>`;
    })
    .join("");
  $("jurisdictionSelect").value = state.jurisdiction;
}

async function loadOffences() {
  const data = await api(`/api/offences?jurisdiction=${encodeURIComponent(state.jurisdiction)}`);
  if (!data.offences.length) {
    $("offenceSelect").innerHTML = `<option value="overspeeding">Overspeeding</option>`;
    return;
  }
  $("offenceSelect").innerHTML = data.offences
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`)
    .join("");
}

function renderDirectory() {
  const items = state.directory[state.jurisdiction] || state.directory.india_national;
  $("directoryBox").innerHTML = items
    .map(([label, url]) => {
      const isUrl = /^https?:/.test(url);
      const link = isUrl
        ? `<a target="_blank" rel="noreferrer" href="${escapeHtml(url)}">${escapeHtml(label)}</a>`
        : `<strong>${escapeHtml(label)}</strong>`;
      return `<div class="directory-item">${link}<span>${escapeHtml(url)}</span></div>`;
    })
    .join("");
}

function selectedJurisdiction() {
  return state.jurisdictions.find((item) => item.id === state.jurisdiction) || {
    id: state.jurisdiction,
    name: state.jurisdiction.replaceAll("_", " "),
    country: ""
  };
}

function renderCountryProfile() {
  const selected = selectedJurisdiction();
  const profile = state.countryProfiles[state.jurisdiction] || {
    title: selected.name,
    side: "Check local rule",
    coverage: "starter",
    focus: "Cautious legal guidance, calculator, quiz, and local directory",
    note: "This country mode uses available local law records and marks unverified fines clearly."
  };
  $("countryTitle").textContent = profile.title;
  $("coveragePill").textContent = profile.coverage;
  $("countryBox").innerHTML = `
    <div class="country-grid">
      <span>Traffic side<strong>${escapeHtml(profile.side)}</strong></span>
      <span>Law mode<strong>${escapeHtml(profile.coverage)}</strong></span>
    </div>
    <p><strong>Focus:</strong> ${escapeHtml(profile.focus)}</p>
    <p>${escapeHtml(profile.note)}</p>
  `;
}

function updateQuickPrompts() {
  const selected = selectedJurisdiction();
  const country = selected.country || selected.name;
  const prompts = [
    [`${country} speed`, `What should I know about overspeeding in ${country}?`],
    [`${country} helmet`, `What are the helmet rules in ${country}?`],
    [`${country} documents`, `What driving documents should I carry in ${country}?`],
    [`${country} quiz`, `Give me a ${country} road safety scenario.`]
  ];
  document.querySelectorAll("[data-prompt]").forEach((button, index) => {
    const item = prompts[index];
    if (!item) return;
    button.textContent = item[0];
    button.dataset.prompt = item[1];
  });
}

async function ask(message) {
  addMessage("user", message);
  $("messageInput").value = "";
  const button = document.querySelector(".send-button");
  button.disabled = true;
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        jurisdiction: state.jurisdiction,
        language: $("languageSelect").value
      })
    });
    addMessage("bot", data.answer, data.citations);
  } catch (error) {
    addMessage("bot", `RoadLegal could not answer: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function calculateFine() {
  const data = await api("/api/calculate-challan", {
    method: "POST",
    body: JSON.stringify({
      jurisdiction: state.jurisdiction,
      offence: $("offenceSelect").value,
      vehicle_class: $("vehicleSelect").value
    })
  });
  const caveats = data.caveats?.length ? `<p>${escapeHtml(data.caveats.join(" "))}</p>` : "";
  const consequences = data.consequences?.length ? `<p>${escapeHtml(data.consequences.join("; "))}</p>` : "";
  $("fineResult").innerHTML = `
    <strong>${escapeHtml(data.amount_display)}</strong>
    <p>${escapeHtml(data.legal_basis || data.status)}</p>
    ${consequences}
    ${caveats}
  `;
}

async function loadQuiz() {
  const data = await api(`/api/quiz?jurisdiction=${encodeURIComponent(state.jurisdiction)}`);
  state.quiz = data.questions || [];
  state.quizIndex = 0;
  renderQuiz();
}

function renderQuiz() {
  $("scorePill").textContent = `${state.score} pts`;
  const question = state.quiz[state.quizIndex % Math.max(1, state.quiz.length)];
  if (!question) {
    $("quizBox").textContent = "No quiz questions available.";
    return;
  }
  $("quizBox").innerHTML = `
    <strong>${escapeHtml(question.question)}</strong>
    <div class="quiz-options">
      ${question.options.map((option, index) => `<button data-answer="${index}">${escapeHtml(option)}</button>`).join("")}
    </div>
    <p id="quizExplanation"></p>
  `;
  document.querySelectorAll("[data-answer]").forEach((button) => {
    button.addEventListener("click", () => answerQuiz(Number(button.dataset.answer), question));
  });
}

function answerQuiz(index, question) {
  const buttons = [...document.querySelectorAll("[data-answer]")];
  buttons.forEach((button, idx) => {
    button.disabled = true;
    if (idx === question.answer) button.classList.add("correct");
    if (idx === index && idx !== question.answer) button.classList.add("incorrect");
  });
  if (index === question.answer) {
    state.score += 10;
    localStorage.setItem("roadlegal_score", String(state.score));
  }
  $("scorePill").textContent = `${state.score} pts`;
  $("quizExplanation").textContent = question.explanation;
  setTimeout(() => {
    state.quizIndex += 1;
    renderQuiz();
  }, 2400);
}

async function submitFeedback(event) {
  event.preventDefault();
  const text = $("feedbackInput").value.trim();
  if (!text) return;
  await api("/api/feedback", {
    method: "POST",
    body: JSON.stringify({
      text,
      jurisdiction: state.jurisdiction,
      at: new Date().toISOString()
    })
  });
  $("feedbackInput").value = "";
  addMessage("bot", "Feedback saved locally for legal-data review.");
}

function useLocation() {
  if (!navigator.geolocation) {
    addMessage("bot", "Geolocation is not available in this browser.");
    return;
  }
  navigator.geolocation.getCurrentPosition(async (position) => {
    const { latitude, longitude } = position.coords;
    const data = await api(`/api/geofence?lat=${latitude}&lon=${longitude}`);
    if (data.jurisdiction) {
      state.jurisdiction = data.jurisdiction;
      $("jurisdictionSelect").value = state.jurisdiction;
      await loadOffences();
      await loadQuiz();
      renderCountryProfile();
      updateQuickPrompts();
      renderDirectory();
    }
    addMessage("bot", `${data.note} Selected: ${data.country}.`);
  }, () => addMessage("bot", "Location permission was not granted."));
}

function bindEvents() {
  $("chatForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const message = $("messageInput").value.trim();
    if (message) ask(message);
  });
  $("clearChatButton").addEventListener("click", () => {
    $("messages").innerHTML = "";
    addMessage("bot", "Ready. Ask about fines, enforcement, documents, or safer driving choices.");
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => ask(button.dataset.prompt));
  });
  $("jurisdictionSelect").addEventListener("change", async (event) => {
    state.jurisdiction = event.target.value;
    localStorage.setItem("roadlegal_jurisdiction", state.jurisdiction);
    await loadOffences();
    await loadQuiz();
    renderCountryProfile();
    updateQuickPrompts();
    renderDirectory();
    const selected = selectedJurisdiction();
    addMessage("bot", `Switched to ${selected.name}. Calculator, quiz, directory, and chat context are now using this country mode.`);
  });
  $("calculateButton").addEventListener("click", calculateFine);
  $("feedbackForm").addEventListener("submit", submitFeedback);
  $("geoButton").addEventListener("click", useLocation);
}

async function init() {
  bindEvents();
  await loadHealth();
  await loadJurisdictions();
  await loadOffences();
  await loadQuiz();
  renderCountryProfile();
  updateQuickPrompts();
  renderDirectory();
  addMessage("bot", "Ready. Ask about fines, enforcement, documents, or safer driving choices.");
}

init().catch((error) => {
  console.error(error);
  addMessage("bot", `Startup error: ${error.message}`);
});
