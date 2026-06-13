// World Cup 2026 — Betting Intelligence Frontend v3.0

const CONF_LABELS   = { HIGH: 'ביטחון גבוה', MEDIUM: 'ביטחון בינוני', LOW: 'ביטחון נמוך' };
const RESULT_LABELS = { home_win: 'ניצחון ביתי', draw: 'תיקו', away_win: 'ניצחון אורח' };
const AGENT_KEYS    = ['news','form','h2h','value','orchestrator'];
const AGENT_ICONS   = { news:'📰', form:'💪', h2h:'🔁', value:'💰', orchestrator:'🎯' };
const KEY_HINTS     = {
  anthropic:  'קבל מפתח: console.anthropic.com',
  openai:     'קבל מפתח: platform.openai.com/api-keys',
  google:     'קבל מפתח: aistudio.google.com/app/apikey',
  openrouter: 'קבל מפתח: openrouter.ai/keys',
};
const LM_LABELS = {
  CONFIRMS_MODEL:    { text: '📈 תנועת קו מאשרת את המודל', cls: 'lm-confirm' },
  CONTRADICTS_MODEL: { text: '⚠️ תנועת קו סותרת את המודל', cls: 'lm-warn' },
  NEUTRAL:           { text: '➡️ שוק יציב', cls: 'lm-neutral' },
  UNKNOWN:           { text: '—', cls: 'lm-neutral' },
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let providers     = {};
let defaultAgents = {};
let tokenHistory  = [];

// ---------------------------------------------------------------------------
// Modal helpers
// ---------------------------------------------------------------------------
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function overlayClose(e, id) { if (e.target === document.getElementById(id)) closeModal(id); }

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([loadProviders(), loadAgentDefaults()]);
  loadPretournament();
  if (!getSetting('api_key')) {
    setTimeout(() => {
      openModal('settingsOverlay');
      showStatus('settingsStatus', 'הכנס מפתח API כדי להתחיל', 'error');
    }, 600);
  }
});

// ---------------------------------------------------------------------------
// Settings modal
// ---------------------------------------------------------------------------
async function loadProviders() {
  try {
    const res = await fetch('/api/providers');
    providers = await res.json();
    buildProviderSelect();
  } catch(e) { console.error('loadProviders', e); }
}

function buildProviderSelect() {
  const sel = document.getElementById('providerSelect');
  sel.innerHTML = '';
  for (const [key, info] of Object.entries(providers)) {
    const opt = document.createElement('option');
    opt.value = key; opt.textContent = info.label;
    sel.appendChild(opt);
  }
  sel.value = getSetting('provider') || 'anthropic';
  onProviderChange(false);
}

function onProviderChange(resetModel = true) {
  const provider = document.getElementById('providerSelect').value;
  const info = providers[provider];
  if (!info) return;
  const dl = document.getElementById('modelSuggestions');
  dl.innerHTML = '';
  for (const m of info.models) {
    const opt = document.createElement('option'); opt.value = m; dl.appendChild(opt);
  }
  const inp = document.getElementById('modelInput');
  inp.value = resetModel ? (info.models[0] || '') : (getSetting('model') || info.models[0] || '');
  document.getElementById('apiKeyHint').textContent = KEY_HINTS[provider] || '';
}

function openSettings() {
  document.getElementById('apiKeyInput').value    = getSetting('api_key')          || '';
  document.getElementById('oddsApiKeyInput').value = getSetting('odds_api_key')    || '';
  document.getElementById('apifKeyInput').value    = getSetting('api_football_key')|| '';
  document.getElementById('newsApiKeyInput').value = getSetting('newsapi_key')     || '';
  document.getElementById('providerSelect').value  = getSetting('provider')        || 'anthropic';
  onProviderChange(false);
  showStatus('settingsStatus', '', '');
  openModal('settingsOverlay');
}

function saveSettings() {
  const provider = document.getElementById('providerSelect').value;
  const model    = document.getElementById('modelInput').value.trim();
  const apiKey   = document.getElementById('apiKeyInput').value.trim();
  if (!apiKey) { showStatus('settingsStatus', 'נדרש מפתח API', 'error'); return; }
  if (!model)  { showStatus('settingsStatus', 'נדרש שם מודל', 'error'); return; }
  setSetting('provider',         provider);
  setSetting('model',            model);
  setSetting('api_key',          apiKey);
  setSetting('odds_api_key',     document.getElementById('oddsApiKeyInput').value.trim());
  setSetting('api_football_key', document.getElementById('apifKeyInput').value.trim());
  setSetting('newsapi_key',      document.getElementById('newsApiKeyInput').value.trim());
  showStatus('settingsStatus', '✓ הגדרות נשמרו', 'success');
  setTimeout(() => { closeModal('settingsOverlay'); loadPretournament(); }, 900);
}

function toggleVis(id) {
  const inp = document.getElementById(id);
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

// Map each service to its input element id
const CONN_INPUTS = {
  ai:           'apiKeyInput',
  odds:         'oddsApiKeyInput',
  api_football: 'apifKeyInput',
  newsapi:      'newsApiKeyInput',
};

async function testConn(service, btn) {
  const key = (document.getElementById(CONN_INPUTS[service])?.value || '').trim();
  const statusEl = document.getElementById('connStatus-' + service);
  if (!key) { statusEl.textContent = '⚠️ הכנס מפתח קודם'; statusEl.className = 'conn-status conn-warn'; return; }

  const oldLabel = btn.textContent;
  btn.disabled = true; btn.textContent = '⏳ בודק...';
  statusEl.textContent = ''; statusEl.className = 'conn-status';

  const payload = { service, key };
  if (service === 'ai') {
    payload.provider = document.getElementById('providerSelect').value;
    payload.model    = document.getElementById('modelInput').value.trim();
  }

  try {
    const res = await fetch('/api/test-connection', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.ok) { statusEl.textContent = '✓ ' + data.msg; statusEl.className = 'conn-status conn-ok'; }
    else         { statusEl.textContent = '✕ ' + data.msg; statusEl.className = 'conn-status conn-fail'; }
  } catch (e) {
    statusEl.textContent = '✕ שגיאת רשת: ' + e.message; statusEl.className = 'conn-status conn-fail';
  } finally {
    btn.disabled = false; btn.textContent = oldLabel;
  }
}

// ---------------------------------------------------------------------------
// Token stats modal
// ---------------------------------------------------------------------------
function openStats() { renderStats(); openModal('statsOverlay'); }

function renderStats() {
  const body = document.getElementById('statsBody');
  if (!tokenHistory.length) {
    body.innerHTML = '<div class="empty-state">טרם בוצע חיזוי בסשן זה</div>'; return;
  }
  const totIn  = tokenHistory.reduce((s,r) => s + r.total_input,  0);
  const totOut = tokenHistory.reduce((s,r) => s + r.total_output, 0);
  const totCost= tokenHistory.reduce((s,r) => s + r.total_cost_usd, 0);
  let html = `<div class="stats-summary">
    <div class="stat-pill"><div class="stat-pill-label">חיזויים</div><div class="stat-pill-value">${tokenHistory.length}</div></div>
    <div class="stat-pill"><div class="stat-pill-label">טוקנים נכנסים</div><div class="stat-pill-value token-in">${fmtNum(totIn)}</div></div>
    <div class="stat-pill"><div class="stat-pill-label">טוקנים יוצאים</div><div class="stat-pill-value token-out">${fmtNum(totOut)}</div></div>
    <div class="stat-pill"><div class="stat-pill-label">עלות כוללת</div><div class="stat-pill-value cost-val">$${totCost.toFixed(4)}</div></div>
  </div>`;
  for (const run of [...tokenHistory].reverse()) {
    html += `<div class="stats-run">
      <div class="stats-run-header">
        <span class="stats-run-title">${escHtml(run.home)} vs ${escHtml(run.away)}</span>
        <span class="stats-run-meta">${escHtml(run.provider)} · ${escHtml(run.model)}</span>
      </div>
      <table class="stats-table"><thead><tr><th>סוכן</th><th>נכנסים</th><th>יוצאים</th><th>עלות</th></tr></thead><tbody>`;
    for (const row of run.per_agent) {
      html += `<tr><td>${escHtml(row.agent)}</td><td class="token-in">${fmtNum(row.input_tokens)}</td>
        <td class="token-out">${fmtNum(row.output_tokens)}</td><td class="cost-val">$${row.cost_usd.toFixed(5)}</td></tr>`;
    }
    html += `<tr class="total-row"><td>סה"כ</td><td class="token-in">${fmtNum(run.total_input)}</td>
      <td class="token-out">${fmtNum(run.total_output)}</td><td class="cost-val">$${run.total_cost_usd.toFixed(4)}</td>
      </tr></tbody></table>
      <div style="padding:.4rem 1rem;font-size:.68rem;color:var(--muted)">מחיר למיליון: קלט $${run.price_per_m.in} · פלט $${run.price_per_m.out}</div>
    </div>`;
  }
  body.innerHTML = html;
}

function clearStats() { tokenHistory = []; renderStats(); }

// ---------------------------------------------------------------------------
// Agents config modal
// ---------------------------------------------------------------------------
async function loadAgentDefaults() {
  try { const res = await fetch('/api/agents'); defaultAgents = await res.json(); }
  catch(e) { console.error('loadAgents', e); }
}

function getAgentOverrides() {
  try { return JSON.parse(getSetting('agent_overrides') || 'null'); } catch { return null; }
}

function openAgents() { renderAgents(); openModal('agentsOverlay'); }

function renderAgents() {
  const body = document.getElementById('agentsBody');
  const overrides = getAgentOverrides() || {};
  const merged = mergeAgentConfigs(overrides);
  const totalW = AGENT_KEYS.filter(k => k !== 'value' && k !== 'orchestrator')
    .reduce((s,k) => s + (merged[k]?.weight ?? 0), 0);
  const totalPct = Math.round(totalW * 100);
  const weightOk = Math.abs(totalPct - 100) <= 1;

  let html = `<div class="weight-total-bar">
    <span>סה"כ משקולות (סוכני ניתוח)</span>
    <span class="${weightOk ? 'weight-total-ok' : 'weight-total-warn'}">${totalPct}% ${weightOk ? '✓' : '⚠ צריך להיות 100%'}</span>
  </div>`;

  for (const key of AGENT_KEYS) {
    const cfg = merged[key] || {};
    const isFixed = key === 'value' || key === 'orchestrator';
    const weightPct = isFixed ? null : Math.round((cfg.weight ?? 0) * 100);
    const icon = AGENT_ICONS[key] || '🤖';
    html += `<div class="agent-card" id="agentCard-${key}">
      <div class="agent-card-header" onclick="toggleAgentCard('${key}')">
        <span class="agent-card-icon">${icon}</span>
        <div class="agent-card-title">
          <div class="agent-card-name">${escHtml(cfg.name || key)}</div>
          <div class="agent-card-desc">${escHtml(cfg.description || '')}</div>
        </div>
        ${isFixed ? `<span class="agent-card-weight">${key === 'value' ? '💰' : '🎯'}</span>` : `<span class="agent-card-weight" id="weightLabel-${key}">${weightPct}%</span>`}
        <span class="agent-card-toggle" id="toggle-${key}">▼</span>
      </div>
      <div class="agent-card-body collapsed" id="agentBody-${key}">
        ${cfg.note ? `<div class="agent-note">ℹ️ ${escHtml(cfg.note)}</div>` : ''}
        ${cfg.data_sources ? `<div class="field-group"><label>מקורות מידע</label><div class="data-sources-list">${escHtml(cfg.data_sources)}</div></div>` : ''}
        ${!isFixed ? `<div class="field-group"><label>משקל</label>
          <div class="weight-slider-row">
            <input type="range" min="0" max="60" step="1" value="${weightPct}" id="weightSlider-${key}" oninput="onWeightChange('${key}', this.value)" />
            <span class="weight-slider-val" id="weightSliderVal-${key}">${weightPct}%</span>
          </div></div>` : ''}
        <div class="field-group"><label>System Prompt</label>
          <textarea id="systemPrompt-${key}" rows="5">${escHtml(cfg.system || '')}</textarea>
        </div>
      </div>
    </div>`;
  }
  body.innerHTML = html;
}

function toggleAgentCard(key) {
  const body   = document.getElementById(`agentBody-${key}`);
  const toggle = document.getElementById(`toggle-${key}`);
  body.classList.toggle('collapsed');
  toggle.classList.toggle('open', !body.classList.contains('collapsed'));
}

function onWeightChange(key, val) {
  document.getElementById(`weightSliderVal-${key}`).textContent = val + '%';
  document.getElementById(`weightLabel-${key}`).textContent     = val + '%';
  const total = AGENT_KEYS.filter(k => k !== 'value' && k !== 'orchestrator').reduce((s, k) => {
    const sl = document.getElementById(`weightSlider-${k}`);
    return s + (sl ? Number(sl.value) : 0);
  }, 0);
  const bar = document.querySelector('.weight-total-bar span:last-child');
  if (bar) { const ok = Math.abs(total - 100) <= 1; bar.textContent = `${total}% ${ok ? '✓' : '⚠ צריך להיות 100%'}`; bar.className = ok ? 'weight-total-ok' : 'weight-total-warn'; }
}

function saveAgents() {
  const overrides = {};
  for (const key of AGENT_KEYS) {
    const slider = document.getElementById(`weightSlider-${key}`);
    const prompt = document.getElementById(`systemPrompt-${key}`);
    if (!prompt) continue;
    overrides[key] = {};
    if (slider) overrides[key].weight = Number(slider.value) / 100;
    overrides[key].system = prompt.value;
  }
  setSetting('agent_overrides', JSON.stringify(overrides));
  showStatus('agentsStatus', '✓ נשמר', 'success');
  setTimeout(() => closeModal('agentsOverlay'), 800);
}

function resetAgentDefaults() { localStorage.removeItem('wc2026_agent_overrides'); renderAgents(); }

function mergeAgentConfigs(overrides) {
  const merged = {};
  for (const key of AGENT_KEYS) {
    merged[key] = { ...(defaultAgents[key] || {}), ...(overrides[key] || {}) };
  }
  return merged;
}

// ---------------------------------------------------------------------------
// Pre-tournament predictions
// ---------------------------------------------------------------------------
async function loadPretournament() {
  const oddsApiKey = getSetting('odds_api_key') || '';
  const url = oddsApiKey
    ? `/api/pretournament/live?odds_api_key=${encodeURIComponent(oddsApiKey)}`
    : '/api/pretournament';
  let data, winnerLive = false, scorerLive = false;
  try {
    const res  = await fetch(url);
    const json = await res.json();
    if (json.data) { data = json.data; winnerLive = json.winner_live||false; scorerLive = json.scorer_live||false; }
    else             { data = json; }
  } catch(e) { console.error('loadPretournament', e); return; }
  const badge = document.getElementById('ptSourceBadge');
  if (winnerLive && scorerLive) { badge.textContent = '📡 נתונים חיים'; badge.className = 'live-badge'; }
  else if (winnerLive) { badge.textContent = '📡 מנצח חי · מלך שערים סטטי'; badge.className = 'live-badge'; }
  else { badge.textContent = oddsApiKey ? '⚠️ סטטי' : '🔒 סטטי'; badge.className = 'locked-badge'; }
  renderPtCards('ptWinnerCards', data.winner,      'winner',  winnerLive);
  renderPtCards('ptScorerCards', data.golden_boot, 'scorer',  scorerLive);
}

function renderPtCards(containerId, items, type, isLive) {
  const container = document.getElementById(containerId);
  if (!container || !items?.length) return;
  container.innerHTML = items.map((item, idx) => {
    const medal = ['🥇','🥈','🥉'][idx] || `${idx+1}.`;
    const srcBadge = isLive ? `<span class="pt-source-live">📡 חי</span>` : `<span class="pt-source-sim">🔒 סטטי</span>`;
    if (type === 'winner') {
      return `<div class="pt-card pt-card-ranked"><div class="pt-rank">${medal}</div><div class="pt-flag">${item.flag||'🏳️'}</div>
        <div class="pt-nation">${escHtml(item.nation)}</div><div class="pt-prob">${item.probability}%</div>
        <div class="pt-reason">${escHtml(item.reasoning||'')}</div>${srcBadge}</div>`;
    } else {
      const stat = item.expected_goals != null ? `${item.expected_goals} xG` : (item.probability != null ? `${item.probability}%` : '');
      return `<div class="pt-card pt-card-ranked"><div class="pt-rank">${medal}</div><div class="pt-flag">${item.flag||'⚽'}</div>
        <div class="pt-nation">${escHtml(item.player)}</div><div class="pt-prob">${stat}</div>
        <div class="pt-reason">${escHtml(item.reasoning||item.nation||'')}</div>${srcBadge}</div>`;
    }
  }).join('');
}

// ---------------------------------------------------------------------------
// Prediction
// ---------------------------------------------------------------------------
async function runPrediction(matchId) {
  const apiKey = getSetting('api_key');
  if (!apiKey) { openSettings(); showStatus('settingsStatus', 'הכנס מפתח API', 'error'); return; }

  const provider         = getSetting('provider')          || 'anthropic';
  const model            = getSetting('model')             || '';
  const oddsApiKey       = getSetting('odds_api_key')      || '';
  const apiFootballKey   = getSetting('api_football_key')  || '';
  const newsApiKey       = getSetting('newsapi_key')       || '';
  const agentOverrides   = getAgentOverrides();

  const btn      = document.querySelector(`[data-match-id="${matchId}"]`);
  const resultEl = document.getElementById(`result-${matchId}`);

  btn.disabled = true; btn.classList.add('loading'); btn.textContent = '⏳ מנתח...';
  resultEl.style.display = 'block';
  resultEl.innerHTML = spinnerHTML(provider, model, { oddsApiKey, apiFootballKey, newsApiKey });

  try {
    const res  = await fetch(`/api/predict/${matchId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: apiKey, provider, model,
        odds_api_key: oddsApiKey,
        api_football_key: apiFootballKey,
        newsapi_key: newsApiKey,
        agent_overrides: agentOverrides,
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      resultEl.innerHTML = `<div class="error-msg">❌ ${escHtml(data.error || 'שגיאה בחיזוי')}</div>`;
      resetBtn(btn); return;
    }
    if (data.token_stats) tokenHistory.push({ ...data.token_stats, home: data.home, away: data.away });
    resultEl.innerHTML = buildResultHTML(data);
    animateWeightBars(matchId, data);
  } catch(e) {
    resultEl.innerHTML = `<div class="error-msg">❌ שגיאת רשת — נסה שוב</div>`;
  }
  btn.textContent = '🔄 ניתוח מחדש'; btn.disabled = false; btn.classList.remove('loading');
}

function resetBtn(btn) { btn.textContent = '⚡ ניתוח AI + ערך'; btn.disabled = false; btn.classList.remove('loading'); }

function spinnerHTML(provider, model, keys) {
  const label = providers[provider]?.label || provider;
  const live = [
    keys.oddsApiKey     ? '📡 Odds API' : null,
    keys.apiFootballKey ? '⚽ API-Football' : null,
    keys.newsApiKey     ? '📰 NewsAPI' : null,
  ].filter(Boolean);
  const liveStr = live.length ? ` · נתונים חיים: ${live.join(', ')}` : ' · ללא מפתחות נתונים חיים';
  return `<div class="spinner">
    <div class="spinner-dot"></div><div class="spinner-dot"></div><div class="spinner-dot"></div>
    <span>מריץ מודל Poisson+Elo + סוכני AI (${escHtml(label)} · ${escHtml(model)})${liveStr}...</span>
  </div>`;
}

// ---------------------------------------------------------------------------
// Result rendering
// ---------------------------------------------------------------------------
function buildResultHTML(d) {
  const conf      = d.confidence || 'MEDIUM';
  const predKey   = d.result_prediction || 'draw';

  return `
    ${buildDataSourcesHTML(d)}
    ${buildFinalOutcomeHTML(d, predKey, conf)}
    <div class="probs-row">
      <div class="prob-box${predKey==='home_win'?' prob-box-win':''}"><div class="prob-label">ניצחון ${escHtml(d.home||'ביתי')}</div><div class="prob-value">${pct(d.home_win_prob)}%</div></div>
      <div class="prob-box${predKey==='draw'?' prob-box-win':''}"><div class="prob-label">תיקו</div><div class="prob-value">${pct(d.draw_prob)}%</div></div>
      <div class="prob-box${predKey==='away_win'?' prob-box-win':''}"><div class="prob-label">ניצחון ${escHtml(d.away||'אורח')}</div><div class="prob-value">${pct(d.away_win_prob)}%</div></div>
    </div>
    <div class="score-xg-row">
      <div><div class="score-label">תוצאה צפויה</div><div class="score-value">${escHtml(d.predicted_score||'?-?')}</div></div>
      <div style="text-align:center"><div class="xg-label">xG ${escHtml(d.home||'ביתי')}</div><div class="xg-value">${fmt(d.home_xg)}</div></div>
      <div style="text-align:center"><div class="xg-label">xG ${escHtml(d.away||'אורח')}</div><div class="xg-value">${fmt(d.away_xg)}</div></div>
    </div>
    ${buildModelProbs(d)}
    <div class="section-divider"><span>💰 הזדמנות הימור</span></div>
    ${buildBestBetHTML(d)}
    ${buildEvTableHTML(d)}
    ${buildLineMovementHTML(d)}
    ${buildKeyDriversHTML(d)}
    ${buildTokenTag(d)}`;
}

function buildFinalOutcomeHTML(d, predKey, conf) {
  // Clear verdict: winning team (or tie) + exact score
  const isDraw = predKey === 'draw';
  const winner = predKey === 'home_win' ? (d.home || 'ביתי')
               : predKey === 'away_win' ? (d.away || 'אורח')
               : null;
  const winProb = predKey === 'home_win' ? d.home_win_prob
                : predKey === 'away_win' ? d.away_win_prob
                : d.draw_prob;
  const verdict = isDraw
    ? `🤝 תיקו צפוי`
    : `🏆 ניצחון ל${escHtml(winner)}`;
  const score = escHtml(d.predicted_score || '?-?');
  // Goals-total line — a DIFFERENT question from the exact score: the expected
  // total goals and the model's Over/Under 2.5 lean. Shown explicitly so the
  // two numbers don't read as a contradiction.
  let goals = '';
  const mp = d.model_probs || {};
  const over = mp.over25_prob, under = mp.under25_prob;
  if (over != null && under != null) {
    const isOver = over > under;
    const dir = isOver ? 'מעל 2.5' : 'מתחת ל-2.5';
    const dirProb = Math.round((isOver ? over : under) * 100);
    const total = mp.expected_goals_total != null ? mp.expected_goals_total : '—';
    goals = `<div class="fo-goals-row">
      <span class="fo-goals-label">סך שערים צפוי</span>
      <span class="fo-goals-total">${total}</span>
      <span class="fo-goals-ou">${dir} (${dirProb}%)</span>
    </div>`;
  }
  // Top-3 most likely scorelines, if available
  let alt = '';
  if (Array.isArray(d.top3_scores) && d.top3_scores.length) {
    const chips = d.top3_scores.map(s =>
      `<span class="fo-alt-chip">${escHtml(s.score)} · ${Math.round((s.prob||0)*100)}%</span>`).join('');
    alt = `<div class="fo-alts"><span class="fo-alts-label">תרחישים נוספים:</span>${chips}</div>`;
  }
  return `
    <div class="final-outcome fo-${predKey}">
      <div class="fo-top">
        <div class="fo-verdict">${verdict}</div>
        <div class="confidence-badge confidence-${conf}">${CONF_LABELS[conf] || conf}</div>
      </div>
      <div class="fo-score-row">
        <span class="fo-score-label">תוצאה מדויקת צפויה</span>
        <span class="fo-score-big">${score}</span>
        <span class="fo-winprob">${pct(winProb)}% הסתברות</span>
      </div>
      ${goals}
      ${alt}
    </div>`;
}

function buildDataSourcesHTML(d) {
  const ds = d.data_sources || {};
  const chips = Object.entries(ds).map(([key, val]) => {
    const isLive = val && val.includes('live') || val && val.includes('NewsAPI');
    const icon = { odds:'📡', stats:'⚽', news:'📰' }[key] || '📊';
    const cls  = isLive ? 'ds-chip ds-live' : 'ds-chip ds-fallback';
    return `<span class="${cls}" title="${escHtml(val)}">${icon} ${escHtml(val || 'N/A')}</span>`;
  });
  return chips.length ? `<div class="data-sources-row">${chips.join('')}</div>` : '';
}

function buildBestBetHTML(d) {
  const bb = d.best_bet;
  if (!bb) {
    const reason = d.no_bet_reason || 'אין בט בעל ערך חיובי מעל 5% EV';
    return `<div class="no-bet-panel">
      <div class="no-bet-icon">🚫</div>
      <div class="no-bet-text"><strong>אין בט מומלץ</strong><br><span>${escHtml(reason)}</span></div>
    </div>`;
  }
  const ev   = bb.expected_value_pct != null ? `${Number(bb.expected_value_pct).toFixed(1)}%` : '—';
  const edge = bb.edge_pct != null ? `${Number(bb.edge_pct).toFixed(1)}%` : '—';
  const kelly= bb.recommended_stake_pct != null ? `${Number(bb.recommended_stake_pct).toFixed(1)}%` : '—';
  const conf = bb.confidence || 'MEDIUM';
  const lmSignal = LM_LABELS[d.line_movement_signal] || LM_LABELS.UNKNOWN;
  return `<div class="best-bet-panel">
    <div class="bb-header">
      <div class="bb-title-row">
        <span class="bb-label">💰 בט מומלץ</span>
        <span class="confidence-badge confidence-${conf}">${CONF_LABELS[conf] || conf}</span>
      </div>
      <div class="bb-market">${escHtml(bb.selection || bb.market || '')}</div>
      <div class="bb-subtitle">הימור הערך הטוב ביותר מול השוק — לא בהכרח הזוכה הצפוי</div>
    </div>
    <div class="bb-stats">
      <div class="bb-stat">
        <div class="bb-stat-label">Expected Value</div>
        <div class="bb-stat-value ev-value">${ev}</div>
      </div>
      <div class="bb-stat">
        <div class="bb-stat-label">Edge</div>
        <div class="bb-stat-value">${edge}</div>
      </div>
      <div class="bb-stat">
        <div class="bb-stat-label">סיכוי מודל</div>
        <div class="bb-stat-value">${bb.model_probability_pct != null ? Number(bb.model_probability_pct).toFixed(1)+'%' : '—'}</div>
      </div>
      <div class="bb-stat">
        <div class="bb-stat-label">סיכוי שוק</div>
        <div class="bb-stat-value muted-val">${bb.market_implied_pct != null ? Number(bb.market_implied_pct).toFixed(1)+'%' : '—'}</div>
      </div>
      <div class="bb-stat">
        <div class="bb-stat-label">מקדם</div>
        <div class="bb-stat-value odds-val">${bb.odds ? Number(bb.odds).toFixed(2) : '—'}</div>
      </div>
      <div class="bb-stat">
        <div class="bb-stat-label">Kelly Stake</div>
        <div class="bb-stat-value kelly-val">${kelly} מהבנקרול</div>
      </div>
    </div>
    <div class="bb-book">📖 ${escHtml(bb.bookmaker || 'Best available')}</div>
    <div class="${lmSignal.cls} bb-lm">${lmSignal.text}</div>
    ${bb.reasoning ? `<div class="bb-reasoning">${escHtml(bb.reasoning)}</div>` : ''}
  </div>`;
}

function buildEvTableHTML(d) {
  const ev = d.all_markets_ev;
  if (!ev || !Object.keys(ev).length) return '';
  const rows = Object.entries(ev).map(([key, v]) => {
    const isVal = v.is_value;
    return `<tr class="${isVal ? 'ev-value-row' : ''}">
      <td>${escHtml(v.market || key)}</td>
      <td>${v.best_odds ? Number(v.best_odds).toFixed(2) : '—'}</td>
      <td>${v.model_prob != null ? (v.model_prob*100).toFixed(1)+'%' : '—'}</td>
      <td>${v.market_implied_prob != null ? (v.market_implied_prob*100).toFixed(1)+'%' : '—'}</td>
      <td class="${v.ev > 0.05 ? 'ev-positive' : v.ev < 0 ? 'ev-negative' : ''}">${v.ev != null ? (v.ev*100).toFixed(1)+'%' : '—'}</td>
      <td>${v.kelly != null ? (v.kelly*100).toFixed(1)+'%' : '—'}</td>
      <td class="book-col">${escHtml(v.best_book || '')}</td>
    </tr>`;
  }).join('');
  return `<details class="ev-table-wrap">
    <summary class="ev-table-toggle">📊 טבלת ערך לכל השווקים</summary>
    <table class="ev-table">
      <thead><tr><th>שוק</th><th>מקדם</th><th>מודל</th><th>שוק</th><th>EV%</th><th>Kelly</th><th>בוקמייקר</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </details>`;
}

function buildLineMovementHTML(d) {
  const lm = d.line_movement;
  if (!lm) return '';
  const sig = LM_LABELS[d.line_movement_signal] || LM_LABELS.UNKNOWN;
  return `<div class="line-movement-row">
    <span class="lm-label">תנועת קו:</span>
    <span>${escHtml(String(lm.open||'—'))} → ${escHtml(String(lm.current||'—'))}</span>
    ${lm.steam_detected ? '<span class="steam-badge">🔥 STEAM</span>' : ''}
    <span class="${sig.cls}">${sig.text}</span>
  </div>`;
}

function buildModelProbs(d) {
  const mp = d.model_probs;
  if (!mp) return '';
  return `<div class="model-probs-row">
    <span class="model-label">מודל Poisson+Elo:</span>
    <span>${(mp.home_win*100).toFixed(1)}% / ${(mp.draw*100).toFixed(1)}% / ${(mp.away_win*100).toFixed(1)}%</span>
    <span class="muted-val" style="font-size:.68rem">${escHtml(mp.method||'')}</span>
  </div>`;
}

function buildKeyDriversHTML(d) {
  const drivers = (d.key_drivers || []).map(dr => {
    const text = typeof dr === 'object' ? dr.text : dr;
    return `<div class="driver-item">${escHtml(text)}</div>`;
  }).join('');
  return drivers ? `<div class="drivers-title">גורמי מפתח</div>${drivers}` : '';
}

function buildTokenTag(d) {
  const ts = d.token_stats;
  if (!ts) return '';
  return `<div style="font-size:.65rem;color:var(--muted);margin-top:.5rem;display:flex;justify-content:space-between">
    <span>${escHtml(ts.provider)} · ${escHtml(ts.model)}</span>
    <span>🔢 ${fmtNum(ts.total_input+ts.total_output)} טוקנים · <span style="color:#f59e0b">$${ts.total_cost_usd.toFixed(4)}</span></span>
  </div>`;
}

function animateWeightBars(matchId, d) {
  const card = document.getElementById(`result-${matchId}`);
  if (!card) return;
  card.querySelectorAll('.weight-bar-fill').forEach(bar => {
    requestAnimationFrame(() => { bar.style.width = (bar.dataset.pct||0) + '%'; });
  });
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function pct(val) {
  if (val == null) return '--';
  const n = Number(val);
  return Math.round(n <= 1 ? n*100 : n);
}
function fmt(val)     { return val == null ? '--' : Number(val).toFixed(2); }
function fmtNum(n)    { return Number(n).toLocaleString(); }
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function showStatus(id, msg, type) {
  const el = document.getElementById(id); if (!el) return;
  el.textContent = msg; el.className = `modal-status ${type}`;
}

// ---------------------------------------------------------------------------
// LocalStorage
// ---------------------------------------------------------------------------
const PROVIDER_LABEL_TO_KEY = { "google gemini": "google", openai: "openai", anthropic: "anthropic", openrouter: "openrouter" };

function getSetting(key) {
  const val = localStorage.getItem(`wc2026_${key}`);
  if (key === 'provider' && val) {
    const norm = PROVIDER_LABEL_TO_KEY[val.toLowerCase()] || val;
    if (norm !== val) localStorage.setItem(`wc2026_${key}`, norm);
    return norm;
  }
  return val;
}
function setSetting(key, val) { localStorage.setItem(`wc2026_${key}`, val); }

// ---------------------------------------------------------------------------
// Schedule view toggle — "by stage" (default) vs "by date & time"
// Cards are MOVED between the two containers (never duplicated), so prediction
// results, event handlers, and element ids stay intact.
// ---------------------------------------------------------------------------
let _origPositions = null;   // captured once: original stage-view layout

function _captureOrig() {
  if (_origPositions) return;
  _origPositions = [...document.querySelectorAll('#stageView .match-card')]
    .map(c => ({ card: c, parent: c.parentNode }));
}

function _formatDateHe(iso) {
  const months = ['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר'];
  const days   = ['ראשון','שני','שלישי','רביעי','חמישי','שישי','שבת'];
  const parts = (iso || '').split('-').map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) return iso || '';
  const [y, m, d] = parts;
  const dt = new Date(Date.UTC(y, m - 1, d));
  return `יום ${days[dt.getUTCDay()]} · ${d} ב${months[m - 1]} ${y}`;
}

function buildDateView() {
  const dateView = document.getElementById('dateView');
  dateView.innerHTML = '';
  const cards = _origPositions.map(o => o.card);
  const sorted = [...cards].sort((a, b) => {
    const ka = `${a.dataset.date}T${a.dataset.time}`;
    const kb = `${b.dataset.date}T${b.dataset.time}`;
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
  let curDate = null, grid = null;
  for (const card of sorted) {
    const dkey = card.dataset.date || '';
    if (dkey !== curDate) {
      curDate = dkey;
      const sec = document.createElement('section');
      sec.className = 'stage-section';
      const h = document.createElement('h2');
      h.className = 'stage-title';
      h.textContent = '📅 ' + _formatDateHe(dkey);
      sec.appendChild(h);
      grid = document.createElement('div');
      grid.className = 'matches-grid';
      sec.appendChild(grid);
      dateView.appendChild(sec);
    }
    grid.appendChild(card);   // moves the live node (with its result + handlers)
  }
}

function restoreStageView() {
  if (!_origPositions) return;
  // Append in original document order — grids hold only match cards, so
  // appendChild rebuilds each grid in its original sequence.
  for (const o of _origPositions) o.parent.appendChild(o.card);
}

function setView(mode) {
  _captureOrig();
  const stageView = document.getElementById('stageView');
  const dateView  = document.getElementById('dateView');
  const bStage = document.getElementById('vtStage');
  const bDate  = document.getElementById('vtDate');
  if (mode === 'date') {
    buildDateView();
    stageView.style.display = 'none';
    dateView.style.display  = '';
    bDate.classList.add('active');  bStage.classList.remove('active');
  } else {
    restoreStageView();
    dateView.style.display  = 'none';
    stageView.style.display = '';
    bStage.classList.add('active'); bDate.classList.remove('active');
  }
}
