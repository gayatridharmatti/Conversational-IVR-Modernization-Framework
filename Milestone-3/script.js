/**
 * ============================================================
 * FILE        : static/script.js
 * PROJECT     : IRCTC Smart IVR — Conversational AI Interface
 * DESCRIPTION : Frontend JavaScript — TTS, STT, chat,
 *               DTMF key presses, NLU API calls, activity log
 * ============================================================
 */

// ── STATE ────────────────────────────────────────────────────
let sessionId    = null;
let currentFlow  = 'idle';
let logCount     = 0;
let ttsEnabled   = true;
let lastPrompt   = '';
let recognition  = null;
let isRecording  = false;
const speechSynth = window.speechSynthesis;

// ============================================================
// TTS — Text to Speech
// ============================================================
function speak(text) {
  if (!ttsEnabled || !text) return;
  speechSynth.cancel();
  const utt    = new SpeechSynthesisUtterance(text);
  utt.lang     = 'en-IN';
  utt.rate     = 0.92;
  utt.pitch    = 1.0;
  utt.volume   = 1.0;
  const voices   = speechSynth.getVoices();
  const indVoice = voices.find(v => v.lang === 'en-IN') ||
                   voices.find(v => v.lang.startsWith('en'));
  if (indVoice) utt.voice = indVoice;
  utt.onstart = () => {
    setNLUBox('tts-status', 'SPEAKING', 'var(--amber)');
    setNLUBox('tts-preview', text.slice(0, 55) + (text.length > 55 ? '…' : ''), null);
    const btn = document.getElementById('btn-last-tts');
    if (btn) btn.classList.add('speaking');
  };
  utt.onend = () => {
    setNLUBox('tts-status', 'READY', 'var(--teal)');
    const btn = document.getElementById('btn-last-tts');
    if (btn) btn.classList.remove('speaking');
  };
  speechSynth.speak(utt);
  addLog('tts', 'TTS SPEAK', text.slice(0, 65) + (text.length > 65 ? '…' : ''));
}

function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  const btn = document.getElementById('btn-tts-toggle');
  if (btn) {
    btn.textContent = ttsEnabled ? '🔊' : '🔇';
    btn.title       = ttsEnabled ? 'TTS ON — click to mute' : 'TTS OFF — click to enable';
  }
  addLog('tts', 'TTS TOGGLE', ttsEnabled ? 'Auto-speak enabled' : 'Auto-speak muted');
}

function speakLast() {
  if (lastPrompt) speak(lastPrompt);
}

// ============================================================
// STT — Speech to Text
// ============================================================
function toggleMic() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    addLog('err', 'STT ERROR', 'Speech recognition not supported. Use Chrome or Edge.');
    appendBotMsg('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
    return;
  }
  if (isRecording) {
    if (recognition) recognition.stop();
    return;
  }
  const SpeechRec              = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition                  = new SpeechRec();
  recognition.lang             = 'en-IN';
  recognition.continuous       = false;
  recognition.interimResults   = true;
  recognition.maxAlternatives  = 1;

  recognition.onstart = () => {
    isRecording = true;
    const btn = document.getElementById('btn-mic');
    if (btn) { btn.classList.add('recording'); btn.title = 'Recording — click to stop'; }
    const input = document.getElementById('chat-input');
    if (input) input.placeholder = '🎤 Listening...';
    setNLUBox('stt-status',     'RECORDING', 'var(--red)');
    setNLUBox('stt-transcript', 'Listening...', null);
    addLog('stt', 'STT START', 'Microphone active — en-IN');
  };

  recognition.onresult = (event) => {
    const result     = event.results[0];
    const transcript = result[0].transcript;
    const conf       = result[0].confidence;
    const input      = document.getElementById('chat-input');
    if (input) input.value = transcript;
    setNLUBox('stt-status',     result.isFinal ? 'FINAL' : 'INTERIM', null);
    setNLUBox('stt-transcript', `"${transcript.slice(0, 50)}"`, null);
    if (result.isFinal) {
      addLog('stt', 'STT RESULT', `"${transcript.slice(0, 60)}" (conf: ${(conf * 100).toFixed(0)}%)`);
    }
  };

  recognition.onend = () => {
    isRecording = false;
    const btn = document.getElementById('btn-mic');
    if (btn) { btn.classList.remove('recording'); btn.title = 'Click to speak'; }
    const input = document.getElementById('chat-input');
    if (input) input.placeholder = 'Type your query...';
    setNLUBox('stt-status', 'PROCESSED', 'var(--green)');
    const val = input ? input.value.trim() : '';
    if (val) sendMessage('speech');
  };

  recognition.onerror = (e) => {
    isRecording = false;
    const btn = document.getElementById('btn-mic');
    if (btn) btn.classList.remove('recording');
    setNLUBox('stt-status', 'ERROR', 'var(--red)');
    addLog('err', 'STT ERROR', e.error);
  };

  recognition.start();
}

// ============================================================
// ACTIVITY LOG
// ============================================================
function addLog(type, label, msg) {
  logCount++;
  const now = new Date().toLocaleTimeString('en-IN',
    { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const el  = document.createElement('div');
  el.className = `log-item li-${type}`;
  el.innerHTML =
    `<div class="li-time">${now}</div>` +
    `<div class="li-label">${label}</div>` +
    `<div class="li-msg">${escHtml(msg)}</div>`;
  const list = document.getElementById('log-list');
  if (list) list.insertBefore(el, list.firstChild);
  const cnt = document.getElementById('log-cnt');
  if (cnt) cnt.textContent = `${logCount} event${logCount !== 1 ? 's' : ''}`;
}

function clearLog() {
  const list = document.getElementById('log-list');
  if (list) list.innerHTML = '';
  logCount = 0;
  const cnt = document.getElementById('log-cnt');
  if (cnt) cnt.textContent = '0 events';
}

// ============================================================
// CHAT UI HELPERS
// ============================================================
function appendUserMsg(text) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML =
    `<div class="msg-avatar">👤</div>` +
    `<div><div class="msg-bubble">${escHtml(text)}</div>` +
    `<div class="msg-meta">${timeStr()}</div></div>`;
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendBotMsg(text, intentData = null, entities = null) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const el = document.createElement('div');
  el.className = 'msg bot';

  let extra = '';

  if (intentData) {
    const pct   = Math.round((intentData.confidence || 0) * 100);
    const color = pct >= 70 ? 'var(--teal)' : pct >= 40 ? 'var(--amber)' : 'var(--red)';
    extra +=
      `<div class="intent-tag">🎯 ${intentData.intent} <span style="color:${color}">${pct}%</span></div>` +
      `<div style="height:2px;border-radius:1px;background:${color};width:${pct}%;margin-top:3px;"></div>`;
  }

  if (entities && Object.keys(entities).length > 0) {
    const typeMap = {
      PNR_NUMBER: 'ec-pnr', TRAIN_NUMBER: 'ec-train', DATE: 'ec-date',
      FROM_STATION: 'ec-stn', TO_STATION: 'ec-stn',
      TRAVEL_CLASS: 'ec-class', PASSENGER_COUNT: 'ec-pax', COMPLAINT_TYPE: 'ec-other',
    };
    const labels = {
      PNR_NUMBER: '🎫 PNR', TRAIN_NUMBER: '🚂 TRAIN', DATE: '📅 DATE',
      FROM_STATION: '📍 FROM', TO_STATION: '🏁 TO',
      TRAVEL_CLASS: '💺 CLASS', PASSENGER_COUNT: '👥 PAX', COMPLAINT_TYPE: '📋 TYPE',
    };
    extra += '<div class="entity-chips">';
    for (const [k, v] of Object.entries(entities)) {
      extra += `<span class="entity-chip ${typeMap[k] || 'ec-other'}">${labels[k] || k}: ${v}</span>`;
    }
    extra += '</div>';
  }

  el.innerHTML =
    `<div class="msg-avatar">🚆</div>` +
    `<div><div class="msg-bubble">${escHtml(text)}${extra}</div>` +
    `<div class="msg-meta">IRCTC IVR · ${timeStr()}</div></div>`;
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
}

function updateNLUPanel(nlu, entities) {
  if (!nlu) return;
  const pct = Math.round((nlu.confidence || 0) * 100);
  const intentEl = document.getElementById('nlu-intent');
  if (intentEl) intentEl.textContent = nlu.intent || '—';
  const methodEl = document.getElementById('nlu-method');
  if (methodEl) methodEl.textContent =
    `Method: ${nlu.method || '—'} · Matched: ${(nlu.matched_on || []).join(', ') || '—'}`;
  const confEl = document.getElementById('nlu-conf');
  if (confEl) confEl.textContent = `Confidence: ${pct}%`;
  const fillEl = document.getElementById('conf-fill');
  if (fillEl) {
    fillEl.style.width = `${pct}%`;
    fillEl.style.background =
      pct >= 70 ? 'linear-gradient(90deg,var(--teal-dark),var(--teal))' :
      pct >= 40 ? 'linear-gradient(90deg,#d97706,var(--amber))' :
                  'linear-gradient(90deg,#b91c1c,var(--red))';
  }
  const entityEl = document.getElementById('entity-display');
  if (!entityEl) return;
  if (!entities || Object.keys(entities).length === 0) {
    entityEl.textContent = 'No entities found.';
    return;
  }
  const typeMap = {
    PNR_NUMBER: 'ec-pnr', TRAIN_NUMBER: 'ec-train', DATE: 'ec-date',
    FROM_STATION: 'ec-stn', TO_STATION: 'ec-stn',
    TRAVEL_CLASS: 'ec-class', PASSENGER_COUNT: 'ec-pax', COMPLAINT_TYPE: 'ec-other',
  };
  entityEl.innerHTML = Object.entries(entities)
    .map(([k, v]) =>
      `<span class="entity-chip ${typeMap[k] || 'ec-other'}" style="display:inline-block;margin:2px">${k}: ${v}</span>`
    ).join('');
}

// ── Utilities ─────────────────────────────────────────────────
function setNLUBox(id, val, color) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = val;
  if (color) el.style.color = color;
}

function setScreen(text) {
  const el = document.getElementById('screen-text');
  if (!el) return;
  el.classList.remove('idle', 'typing');
  el.textContent = text;
}

function setFlow(f) {
  currentFlow = f;
  const el = document.getElementById('flow-val');
  if (el) el.textContent = f.replace('ivr_', '').toUpperCase();
}

function enableUI(on) {
  document.querySelectorAll('.dk').forEach(k => k.disabled = !on);
  const start = document.getElementById('btn-start');
  if (start) start.disabled = on;
  const end = document.getElementById('btn-end');
  if (end) end.classList.toggle('show', on);
  ['chat-input', 'btn-send', 'btn-mic', 'btn-last-tts'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !on;
  });
  const dot = document.getElementById('caller-dot');
  if (dot) dot.classList.toggle('live', on);
}

// ── Mode Toggle ───────────────────────────────────────────────
function setMode(m) {
  ['dtmf', 'voice', 'menu'].forEach(mode => {
    const btn = document.getElementById(`mode-${mode}`);
    if (btn) btn.classList.toggle('active', mode === m);
    const sec = document.getElementById(`section-${mode}`);
    if (sec) sec.classList.toggle('active', mode === m);
  });
}

// ── Suggestion chips (chat panel) ────────────────────────────
function sendSuggestion(el) {
  if (!sessionId) { alert('Please START CALL first.'); return; }
  const input = document.getElementById('chat-input');
  if (input) input.value = el.textContent.trim();
  sendMessage();
}

// ── Voice command cards (left panel VOICE section) ────────────
function triggerVoiceCmd(el) {
  if (!sessionId) { alert('Please START CALL first.'); return; }
  const cmdEl = el.querySelector('.vc-cmd');
  if (!cmdEl) return;
  const raw   = cmdEl.textContent.replace(/^"|"$/g, '').trim();
  const input = document.getElementById('chat-input');
  if (input) input.value = raw;
  sendMessage('text');
}

// ── Menu list click (left panel MENU section) ─────────────────
function menuClick(key) {
  pressKey(key);
}

function escHtml(t) {
  return String(t)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

function timeStr() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// ============================================================
// START CALL
// ============================================================
async function startCall() {
  addLog('call', 'CALL START', 'POST /call/start');
  try {
    const r1 = await fetch('/call/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caller_id: '+919876543210', language: 'EN' }),
    });
    const d1 = await r1.json();
    sessionId = d1.data.session_id;
    const sidEl = document.getElementById('sid-val');
    if (sidEl) sidEl.textContent = sessionId.slice(0, 8) + '…';
    addLog('call', 'SESSION', `ID: ${sessionId.slice(0, 8)}…`);

    await new Promise(r => setTimeout(r, 400));

    const r2 = await fetch('/call/menu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const d2 = await r2.json();

    // ── Always keep flow as main_menu until a sub-service is selected ──
    setFlow('main_menu');

    // Screen shows compact menu
    setScreen('1:PNR  2:Booking  3:Search  4:Cancel  5:Complaint  6:Agent');

    // Combined TTS
    const combined = d1.prompt + ' ' + d2.prompt;
    speak(combined);
    lastPrompt = combined;

    // Chat shows formatted welcome + menu
    appendBotMsg(
      '🙏 Welcome to IRCTC Smart IVR.\n\n' +
      'Press a key or type your request:\n\n' +
      '▶  1 — PNR Status\n' +
      '▶  2 — Ticket Booking\n' +
      '▶  3 — Train Search\n' +
      '▶  4 — Cancellation & Refund\n' +
      '▶  5 — Register Complaint\n' +
      '▶  6 — Talk to Agent\n' +
      '▶  0 — Repeat Menu'
    );

    enableUI(true);
    addLog('call', 'READY', 'DTMF + Chat + Voice all active.');
  } catch (e) {
    addLog('err', 'ERROR', 'Cannot connect. Is python main.py running?');
  }
}

// ============================================================
// DTMF KEY PRESS
// The key fix: always send "main_menu" as flow for keys 1-6,0
// and only switch flow AFTER a service confirms a sub-step.
// ============================================================
async function pressKey(key) {
  if (!sessionId) { alert('Please START CALL first.'); return; }

  // For keys 1-6 and 0 pressed from any top-level state,
  // always treat as main_menu so backend routes correctly.
  const topLevelKeys = ['0','1','2','3','4','5','6','*','#'];
  const flowToSend   = topLevelKeys.includes(key) ? 'main_menu' : currentFlow;

  addLog('call', `KEY [${key}]`, `Sending flow: ${flowToSend}`);

  try {
    const res  = await fetch('/call/key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id  : sessionId,
        key_pressed : key,
        current_flow: flowToSend,
      }),
    });
    const data = await res.json();

    speak(data.prompt);
    appendBotMsg(data.prompt);
    setScreen(data.prompt.slice(0, 60) + (data.prompt.length > 60 ? '…' : ''));
    lastPrompt = data.prompt;
    addLog('api', 'DTMF RESPONSE', data.prompt.slice(0, 65));

    // Map acs_event → internal flow name
    const flowMap = {
      ivr_pnr_flow      : 'pnr_flow',
      ivr_booking_flow  : 'booking_flow',
      ivr_search_flow   : 'search_flow',
      ivr_cancel_flow   : 'cancel_flow',
      ivr_complaint_flow: 'complaint_type',
      menu_repeated     : 'main_menu',
      ivr_agent_transfer: 'agent',
      agent_transfer    : 'agent',
      // After sub-flow selections, stay responsive
      class_selected          : 'booking_flow',
      complaint_type_selected : 'complaint_detail',
    };
    // Only update flow for sub-menu states; keep main_menu for top-level
    if (data.acs_event && data.acs_event !== 'invalid_key') {
      const mappedFlow = flowMap[data.acs_event];
      if (mappedFlow) setFlow(mappedFlow);
    }

  } catch (e) {
    addLog('err', 'DTMF ERROR', e.message);
  }
}

// ============================================================
// NLU CHAT MESSAGE
// ============================================================
async function sendMessage(mode = 'text') {
  if (!sessionId) { alert('Please START CALL first.'); return; }
  const input = document.getElementById('chat-input');
  const text  = input ? input.value.trim() : '';
  if (!text) return;
  if (input) input.value = '';

  appendUserMsg(text);
  addLog('nlu', 'USER INPUT', `"${text.slice(0, 55)}" [${mode}]`);

  try {
    const res  = await fetch('/nlu/understand', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, user_text: text, input_mode: mode }),
    });
    const data = await res.json();
    const nlu  = data.data?.nlu;
    const ents = data.data?.entities || {};
    const dial = data.data?.dialogue || {};

    updateNLUPanel(nlu, ents);
    appendBotMsg(data.prompt, nlu, ents);
    speak(data.prompt);
    setScreen(data.prompt.slice(0, 60) + (data.prompt.length > 60 ? '…' : ''));
    lastPrompt = data.prompt;

    addLog('nlu',
      `INTENT: ${(nlu?.intent || '?').toUpperCase()}`,
      `Conf: ${Math.round((nlu?.confidence || 0) * 100)}% · Entities: ${Object.keys(ents).join(', ') || 'none'}`
    );

    // Auto-call M2 endpoint when dialogue has all entities ready
    if (dial.action === 'call_endpoint' && dial.endpoint && (dial.missing || []).length === 0) {
      await autoCallEndpoint(dial.endpoint, dial.payload);
    } else if (dial.action === 'end_call') {
      await endCall();
    } else if (dial.follow_up) {
      addLog('nlu', 'FOLLOW-UP', dial.follow_up);
    }

  } catch (e) {
    addLog('err', 'NLU ERROR', e.message);
    appendBotMsg('Sorry, something went wrong. Please try again.');
  }
}

// ============================================================
// AUTO-CALL M2 ENDPOINT (after NLU fills all entities)
// ============================================================
async function autoCallEndpoint(endpoint, payload) {
  addLog('api', 'AUTO CALL', endpoint);
  try {
    const res  = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    appendBotMsg(data.prompt);
    speak(data.prompt);
    setScreen(data.prompt.slice(0, 60) + (data.prompt.length > 60 ? '…' : ''));
    lastPrompt = data.prompt;
    addLog('api', 'RESULT', data.prompt.slice(0, 65));
  } catch (e) {
    addLog('err', 'AUTO CALL ERR', e.message);
  }
}

// ============================================================
// END CALL
// ============================================================
async function endCall() {
  if (!sessionId) return;
  speechSynth.cancel();
  try {
    const res  = await fetch('/call/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const data = await res.json();
    setScreen('Call ended. Thank you!');
    speak(data.prompt);
    appendBotMsg(data.prompt);
    lastPrompt = data.prompt;
    addLog('end', 'CALL ENDED', `Session closed · ${data.data.total_events || 0} events`);
  } catch (e) {
    addLog('err', 'END ERR', e.message);
  }
  enableUI(false);
  sessionId   = null;
  currentFlow = 'idle';
  setFlow('IDLE');
  const sidEl    = document.getElementById('sid-val');
  if (sidEl) sidEl.textContent = '—';
  const intentEl = document.getElementById('nlu-intent');
  if (intentEl) intentEl.textContent = '—';
  const fillEl   = document.getElementById('conf-fill');
  if (fillEl) fillEl.style.width = '0%';
}