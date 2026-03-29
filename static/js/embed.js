/**
 * Conquistador Embeddable Chatbot Widget
 *
 * Drop this single <script> tag into any page (Manus, WordPress, etc.):
 *
 *   <script src="https://YOUR-API-HOST/static/js/embed.js"
 *           data-api="https://YOUR-API-HOST"
 *           data-color="#B8860B"
 *           data-position="right">
 *   </script>
 *
 * The widget injects its own HTML/CSS, connects to the Conquistador API via
 * WebSocket (AI mode) with guided-flow fallback, and submits leads via REST.
 */
(function () {
  'use strict';

  // ── Configuration ────────────────────────────────────────────────────
  var script = document.currentScript;
  var API_BASE = (script && script.getAttribute('data-api')) || '';
  var ACCENT = (script && script.getAttribute('data-color')) || '#B8860B';
  var POSITION = (script && script.getAttribute('data-position')) || 'right';

  // Service area zip codes
  var VALID_ZIPS = [
    '17601','17602','17603','17604','17605','17606',
    '17543','17545','17554','17557','17560','17572','17576','17584',
    '17401','17402','17403','17404','17405','17406','17407',
    '17101','17102','17103','17104','17105','17106','17107',
    '17108','17109','17110','17111','17112',
    '17042','17046',
    '19601','19602','19603','19604','19605','19606',
    '19607','19608','19609','19610','19611'
  ];

  // ── Inject CSS ───────────────────────────────────────────────────────
  var css = [
    '#cq-widget-container *{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:0}',
    '#cq-widget-btn{position:fixed;bottom:20px;' + POSITION + ':20px;width:60px;height:60px;border-radius:50%;background:' + ACCENT + ';color:#fff;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.25);z-index:99998;display:flex;align-items:center;justify-content:center;transition:transform .2s}',
    '#cq-widget-btn:hover{transform:scale(1.1)}',
    '#cq-widget-btn svg{width:28px;height:28px}',
    '#cq-widget-box{position:fixed;bottom:90px;' + POSITION + ':20px;width:380px;max-width:calc(100vw - 40px);height:520px;max-height:calc(100vh - 110px);background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.18);z-index:99999;display:none;flex-direction:column;overflow:hidden}',
    '#cq-widget-box.open{display:flex}',
    '#cq-header{background:' + ACCENT + ';color:#fff;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;font-weight:600;font-size:15px}',
    '#cq-header button{background:none;border:none;color:#fff;font-size:20px;cursor:pointer}',
    '#cq-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}',
    '.cq-msg{padding:10px 14px;border-radius:12px;max-width:85%;font-size:14px;line-height:1.5;word-wrap:break-word;white-space:pre-wrap}',
    '.cq-msg.bot{background:#f0f0f0;color:#333;align-self:flex-start;border-bottom-left-radius:4px}',
    '.cq-msg.user{background:' + ACCENT + ';color:#fff;align-self:flex-end;border-bottom-right-radius:4px}',
    '.cq-typing{align-self:flex-start;padding:10px 14px;background:#f0f0f0;border-radius:12px;font-size:14px;color:#888}',
    '#cq-replies{padding:8px 14px;display:flex;flex-wrap:wrap;gap:6px}',
    '#cq-replies button{padding:6px 14px;border-radius:20px;border:1.5px solid ' + ACCENT + ';background:#fff;color:' + ACCENT + ';font-size:13px;cursor:pointer;transition:all .15s}',
    '#cq-replies button:hover{background:' + ACCENT + ';color:#fff}',
    '#cq-input-bar{display:flex;border-top:1px solid #e5e5e5;padding:10px}',
    '#cq-input{flex:1;border:1px solid #ddd;border-radius:20px;padding:8px 14px;font-size:14px;outline:none}',
    '#cq-input:focus{border-color:' + ACCENT + '}',
    '#cq-send{background:' + ACCENT + ';color:#fff;border:none;border-radius:50%;width:36px;height:36px;margin-left:8px;cursor:pointer;display:flex;align-items:center;justify-content:center}',
  ].join('\n');

  var styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── Inject HTML ──────────────────────────────────────────────────────
  var container = document.createElement('div');
  container.id = 'cq-widget-container';
  container.innerHTML = [
    '<button id="cq-widget-btn" aria-label="Open chat">',
    '  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
    '</button>',
    '<div id="cq-widget-box">',
    '  <div id="cq-header"><span>Conquistador Oil</span><button id="cq-close">&times;</button></div>',
    '  <div id="cq-messages"></div>',
    '  <div id="cq-replies"></div>',
    '  <div id="cq-input-bar">',
    '    <input id="cq-input" type="text" placeholder="Type a message..." autocomplete="off">',
    '    <button id="cq-send"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>',
    '  </div>',
    '</div>',
  ].join('');
  document.body.appendChild(container);

  // ── State ────────────────────────────────────────────────────────────
  var messagesEl = document.getElementById('cq-messages');
  var repliesEl = document.getElementById('cq-replies');
  var inputEl = document.getElementById('cq-input');
  var boxEl = document.getElementById('cq-widget-box');
  var ws = null;
  var mode = 'ai';
  var step = 0;
  var leadData = {
    service_type: '', symptoms: '', zip_code: '', name: '',
    phone: '', carrier: '', preferred_time: '', urgency: 'routine'
  };

  // ── Helpers ──────────────────────────────────────────────────────────
  function addMsg(role, text) {
    var div = document.createElement('div');
    div.className = 'cq-msg ' + (role === 'user' ? 'user' : 'bot');
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping() {
    var el = document.createElement('div');
    el.className = 'cq-typing';
    el.id = 'cq-typing';
    el.textContent = 'Typing...';
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTyping() {
    var el = document.getElementById('cq-typing');
    if (el) el.remove();
  }

  function setReplies(replies) {
    repliesEl.innerHTML = '';
    (replies || []).forEach(function (r) {
      var btn = document.createElement('button');
      btn.textContent = r.label;
      btn.onclick = function () {
        addMsg('user', r.label);
        processGuided(r.value || r.label);
      };
      repliesEl.appendChild(btn);
    });
  }

  // ── WebSocket (AI mode) ──────────────────────────────────────────────
  function connectWS() {
    if (!API_BASE) { startGuided(); return; }
    var wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws/chat';
    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = function () {
        mode = 'ai';
        ws.send('hi');
        showTyping();
      };
      ws.onmessage = function (e) {
        hideTyping();
        addMsg('bot', e.data);
      };
      ws.onerror = function () { ws = null; startGuided(); };
      ws.onclose = function () { ws = null; };
    } catch (e) { startGuided(); }
  }

  // ── Guided Flow ──────────────────────────────────────────────────────
  function startGuided() {
    mode = 'guided';
    step = 0;
    showStep();
  }

  function showStep() {
    if (step === 0) {
      addMsg('bot', "Hi! I'm the Conquistador assistant. What do you need help with today?");
      setReplies([
        { label: 'Heating Oil Delivery', value: 'heating_oil' },
        { label: 'HVAC / Furnace Repair', value: 'hvac_repair' },
        { label: 'AC Repair', value: 'ac_service' },
        { label: 'New System Installation', value: 'hvac_install' },
        { label: 'Maintenance / Tune-Up', value: 'furnace_maintenance' },
        { label: 'Emergency — No Heat!', value: 'emergency' }
      ]);
    } else if (step === 1) {
      showDiagnosis();
    } else if (step === 2) {
      addMsg('bot', "Thanks for those details. What is your zip code so we can find a contractor near you?");
      setReplies([]);
    } else if (step === 3) {
      addMsg('bot', "Great, we serve your area! Can I get your name and phone number? (e.g., John Smith, 717-555-1234)");
      setReplies([]);
    } else if (step === 4) {
      addMsg('bot', "Which phone carrier do you use? This helps us send you text updates.");
      setReplies([
        { label: 'Verizon', value: 'verizon' },
        { label: 'AT&T', value: 'att' },
        { label: 'T-Mobile', value: 'tmobile' },
        { label: 'Other / Not Sure', value: 'other' }
      ]);
    } else if (step === 5) {
      addMsg('bot', "When would you like the contractor to come out?");
      setReplies([
        { label: 'As soon as possible', value: 'asap' },
        { label: 'Tomorrow', value: 'tomorrow' },
        { label: 'Within a few days', value: 'few_days' },
        { label: "I'm flexible", value: 'flexible' }
      ]);
    } else if (step === 6) {
      showConfirmation();
    }
  }

  var diagnosisQuestions = {
    heating_oil: {
      msg: "How would you describe your situation?",
      replies: [
        { label: 'Tank is low / almost empty', value: 'Tank is running low or almost empty' },
        { label: 'Scheduled fill-up', value: 'Routine scheduled fill-up needed' },
        { label: 'Tank is empty — no heat!', value: 'Tank is empty, no heat' }
      ]
    },
    hvac_repair: {
      msg: "What's happening with your system?",
      replies: [
        { label: 'Not turning on at all', value: 'System is not turning on' },
        { label: 'Running but not heating', value: 'System runs but does not heat' },
        { label: 'Making strange noises', value: 'System is making unusual noises' },
        { label: 'Short cycling', value: 'System is short cycling' }
      ]
    },
    ac_service: {
      msg: "Tell me what's going on with your AC.",
      replies: [
        { label: 'Not cooling', value: 'AC running but not cooling' },
        { label: 'Blowing warm air', value: 'AC blowing warm air' },
        { label: 'Not turning on', value: 'AC not turning on at all' },
        { label: 'Leaking water', value: 'AC unit leaking water' }
      ]
    },
    hvac_install: {
      msg: "What kind of installation are you looking for?",
      replies: [
        { label: 'New furnace', value: 'Need new furnace installation' },
        { label: 'New AC system', value: 'Need new AC installation' },
        { label: 'Heat pump', value: 'Interested in heat pump' },
        { label: 'Full HVAC system', value: 'Need complete HVAC system' }
      ]
    },
    furnace_maintenance: {
      msg: "Smart choice! What do you need?",
      replies: [
        { label: 'Annual tune-up', value: 'Annual furnace tune-up needed' },
        { label: 'Filter replacement', value: 'Need filter replacement' },
        { label: 'Safety inspection', value: 'Want safety inspection' }
      ]
    },
    emergency: {
      msg: "I understand this is urgent. Can you describe what's happening?",
      replies: [
        { label: 'No heat at all', value: 'Complete loss of heat — emergency' },
        { label: "Furnace won't start", value: 'Furnace will not start — emergency' },
        { label: 'Strange smell', value: 'Strange smell from heating system' },
        { label: 'Water/oil leak', value: 'Active water or oil leak' }
      ]
    }
  };

  function showDiagnosis() {
    var q = diagnosisQuestions[leadData.service_type] || diagnosisQuestions.hvac_repair;
    addMsg('bot', q.msg);
    setReplies(q.replies);
    if (leadData.service_type === 'emergency') leadData.urgency = 'emergency';
  }

  function showConfirmation() {
    var svcLabels = {
      heating_oil: 'Heating Oil Delivery', hvac_repair: 'HVAC / Furnace Repair',
      ac_service: 'AC Repair', hvac_install: 'HVAC Installation',
      furnace_maintenance: 'Maintenance', emergency: 'Emergency Service'
    };
    var timeLabels = {
      asap: 'As soon as possible', tomorrow: 'Tomorrow',
      few_days: 'Within a few days', flexible: 'Flexible'
    };
    var summary =
      "Here's what I have:\n\n" +
      "Name: " + leadData.name + "\n" +
      "Phone: " + leadData.phone + "\n" +
      "Location: " + leadData.zip_code + "\n" +
      "Service: " + (svcLabels[leadData.service_type] || leadData.service_type) +
      (leadData.symptoms ? "\nIssue: " + leadData.symptoms : '') + "\n" +
      "Timing: " + (timeLabels[leadData.preferred_time] || leadData.preferred_time) + "\n\n" +
      "A qualified contractor will reach out to you shortly!";
    addMsg('bot', summary);
    setReplies([]);
    submitLead();
  }

  function submitLead() {
    var url = (API_BASE || '') + '/api/leads/';
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: leadData.name, phone: leadData.phone, carrier: leadData.carrier,
        zip_code: leadData.zip_code, service_type: leadData.service_type,
        urgency: leadData.urgency,
        description: leadData.symptoms + (leadData.preferred_time ? ' | Preferred time: ' + leadData.preferred_time : '')
      })
    }).catch(function (e) { console.error('Lead submit failed:', e); });
  }

  function processGuided(value) {
    setReplies([]);
    switch (step) {
      case 0:
        leadData.service_type = value;
        if (value === 'emergency') leadData.urgency = 'emergency';
        step = 1; showStep(); break;
      case 1:
        leadData.symptoms = value;
        step = 2; setTimeout(showStep, 800); break;
      case 2:
        leadData.zip_code = value.trim();
        if (VALID_ZIPS.indexOf(leadData.zip_code) === -1) {
          addMsg('bot', "That's a bit outside our primary area, but we may still be able to help! Let me get your info.");
        }
        step = 3; showStep(); break;
      case 3:
        var parts = value.split(',').map(function (s) { return s.trim(); });
        if (parts.length >= 2) {
          leadData.name = parts[0]; leadData.phone = parts[1];
        } else {
          leadData.name = value;
          addMsg('bot', "And what's the best phone number to reach you?");
          step = 3.5; return;
        }
        step = 4; showStep(); break;
      case 3.5:
        leadData.phone = value; step = 4; showStep(); break;
      case 4:
        leadData.carrier = value;
        if (leadData.urgency === 'emergency') {
          leadData.preferred_time = 'asap';
          addMsg('bot', "Since this is urgent, we'll get someone out ASAP.");
          step = 6; setTimeout(showStep, 1200);
        } else { step = 5; showStep(); }
        break;
      case 5:
        leadData.preferred_time = value; step = 6; showStep(); break;
    }
  }

  // ── Send ─────────────────────────────────────────────────────────────
  function send() {
    var msg = inputEl.value.trim();
    if (!msg) return;
    addMsg('user', msg);
    inputEl.value = '';

    if (mode === 'ai' && ws && ws.readyState === 1) {
      ws.send(msg);
      showTyping();
    } else {
      processGuided(msg);
    }
  }

  // ── Event Listeners ──────────────────────────────────────────────────
  document.getElementById('cq-widget-btn').onclick = function () {
    var isOpen = boxEl.classList.toggle('open');
    if (isOpen && messagesEl.children.length === 0) connectWS();
  };
  document.getElementById('cq-close').onclick = function () {
    boxEl.classList.remove('open');
  };
  document.getElementById('cq-send').onclick = send;
  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') send();
  });
})();
