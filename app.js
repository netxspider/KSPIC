const API = '/api';
const state = { results: [], selected: null, map: null, markers: null, analytics: null };
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[c]));
const formatDate = (value) => value ? new Date(value).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }) : '—';

async function api(path, options) {
  const response = await fetch(API + path, options);
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || body.error || `Request failed (${response.status})`); }
  return response.json();
}
function toast(message) { const node = $('#toast'); node.textContent = message; node.classList.add('show'); setTimeout(() => node.classList.remove('show'), 2600); }
function showView(name) {
  document.querySelectorAll('.view').forEach(view => view.classList.toggle('active', view.id === name));
  document.querySelectorAll('.nav-item').forEach(button => button.classList.toggle('active', button.dataset.view === name));
  $('#page-label').textContent = name === 'overview' ? 'COMMAND CENTRE' : name.toUpperCase();
  if (name === 'graph') renderGraph();
  if (name === 'map') setTimeout(loadMap, 30);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function renderCases(rows, selected) {
  state.results = rows || state.results; state.selected = selected || state.selected || state.results[0];
  const list = $('#case-list'); const detail = $('#case-detail');
  if (!state.results.length) { list.innerHTML = '<p class="empty-state">No records matched the safe SQL filters.</p>'; detail.innerHTML = '<p class="empty-state">Run an investigation query to inspect a sourced case.</p>'; return; }
  list.innerHTML = state.results.slice(0,25).map(c => `<button class="case-row ${c.CrimeNo === state.selected.CrimeNo ? 'selected' : ''}" data-crime="${escapeHtml(c.CrimeNo)}"><div class="case-doc">▤</div><div><b>${escapeHtml(c.CrimeNo)}</b><strong>${escapeHtml(c.CrimeType)} · ${escapeHtml(c.DistrictName)}</strong><span>${escapeHtml(c.StationName)} · ${formatDate(c.CrimeRegisteredDate)}</span></div><div class="case-score"><b>${escapeHtml(c.CaseStatusName)}</b><span>case status</span></div></button>`).join('');
  list.querySelectorAll('.case-row').forEach(button => button.addEventListener('click', () => { state.selected = state.results.find(c => c.CrimeNo === button.dataset.crime); renderCases(state.results, state.selected); renderCaseDetail(state.selected.CrimeNo); }));
  renderCaseDetail(state.selected.CrimeNo);
}
async function renderCaseDetail(crimeNo) {
  const pane = $('#case-detail'); pane.innerHTML = '<p class="empty-state">Retrieving cited case record…</p>';
  try {
    const c = await api(`/cases/${encodeURIComponent(crimeNo)}`); state.selected = c;
    const evidence = c.evidence.map(e => `<div class="match"><i>✓</i><b>${escapeHtml(e.EvidenceType)} · ${escapeHtml(e.EvidenceLabel)}</b><em>${Math.round(e.Confidence * 100)}% provenance</em></div>`).join('');
    const vehicle = c.vehicles[0];
    pane.innerHTML = `<div class="detail-top"><span class="status open">${escapeHtml(c.CaseStatusName)}</span><button class="icon-button plain">•••</button></div><span class="detail-label">CASEMASTER · ${escapeHtml(c.DistrictName)}</span><h2>${escapeHtml(c.CrimeNo)}</h2><h3>${escapeHtml(c.CrimeType)} · ${escapeHtml(c.StationName)}</h3><p>${escapeHtml(c.BriefFacts)}</p><div class="detail-block"><span>CITED EVIDENCE</span>${evidence}</div><div class="detail-block"><span>PRIMARY ENTITY</span><div class="entity-inline"><i>▱</i><div><b>${escapeHtml(vehicle?.RegistrationNo || 'No linked vehicle')}</b><small>${escapeHtml(vehicle ? `${vehicle.VehicleColor} ${vehicle.VehicleMake} · ${vehicle.RelationshipType}` : 'No vehicle record')}</small></div></div></div><button class="primary-button" data-view="graph">Open relationship graph →</button>`;
    pane.querySelector('[data-view]').addEventListener('click', () => showView('graph'));
  } catch (error) { pane.innerHTML = `<p class="empty-state">Could not load cited case: ${escapeHtml(error.message)}</p>`; }
}
function addUser(query) { $('#conversation').insertAdjacentHTML('beforeend', `<div class="message user-message"><div class="message-content"><p>${escapeHtml(query)}</p></div></div>`); }
function answerMarkup(answer) {
  const reasons = answer.reasoning.map(r => `<div class="reason"><i>✓</i><span>${escapeHtml(r.label || r)}</span><em>${escapeHtml(r.status || 'grounded')}</em></div>`).join('');
  const cites = answer.citations.map(c => `<button class="citation" data-crime="${escapeHtml(c.crime_no)}">${escapeHtml(c.crime_no)} ↗</button>`).join('');
  return `<div class="message assistant-message answer"><div class="ai-avatar">K</div><div class="message-content"><div class="answer-heading"><span class="answer-label">${escapeHtml(answer.provider).toUpperCase()}</span><span class="answer-time">cited response</span></div><p class="answer-title">${escapeHtml(answer.answer)}</p><div class="reasoning"><div class="reasoning-head"><b>Why these records are included</b><span>Traceable rationale</span></div>${reasons}</div><div class="answer-bottom"><div class="confidence"><span>Evidence confidence</span><b>${answer.confidence}%</b><div><i style="width:${answer.confidence}%"></i></div></div><div class="citations"><span>Source citations</span><div>${cites}</div></div></div><div class="answer-actions"><button data-view="graph">◎ Explore entity graph</button><button data-view="cases">▤ Review case records</button><button class="copy-answer">↗ Briefing note</button></div></div></div>`;
}
async function executeQuery(query) {
  if (!query.trim()) return; addUser(query); $('#query').value = '';
  const conversation = $('#conversation'); const loading = document.createElement('div'); loading.className = 'message assistant-message typing'; loading.innerHTML = '<div class="ai-avatar">K</div><div class="message-content"><span></span><span></span><span></span> Running safe SQL filters and evidence retrieval…</div>'; conversation.appendChild(loading);
  try {
    const answer = await api('/assistant', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query}) }); loading.remove(); conversation.insertAdjacentHTML('beforeend', answerMarkup(answer));
    if (answer.results.length) renderCases(answer.results, answer.results[0]);
    conversation.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
    conversation.querySelectorAll('.citation').forEach(button => button.addEventListener('click', () => { const found = state.results.find(c => c.CrimeNo === button.dataset.crime); if (found) { renderCases(state.results, found); showView('cases'); } }));
    conversation.querySelector('.copy-answer:last-child')?.addEventListener('click', () => { navigator.clipboard?.writeText(answer.answer); toast('Evidence-grounded briefing copied'); });
  } catch (error) { loading.innerHTML = `<div class="ai-avatar">!</div><div class="message-content">Backend unavailable: ${escapeHtml(error.message)}. Run <code>npm run dev</code>.</div>`; }
  conversation.scrollTop = conversation.scrollHeight;
}
async function renderGraph() {
  const canvas = $('.graph-canvas');
  if (!state.selected?.CrimeNo) { canvas.innerHTML = '<div class="graph-empty">Run a case query first to build an evidence graph.</div>'; return; }
  canvas.innerHTML = '<div class="graph-empty">Building relationship graph from linked records…</div>';
  try {
    const data = await api(`/graph/${encodeURIComponent(state.selected.CrimeNo)}`); const nodes = data.nodes.slice(0,16), cx = 490, cy = 235, pos = {};
    nodes.forEach((node,index) => { const angle=Math.PI * 2 * index / nodes.length - Math.PI/2, radius=index ? 155+(index%3)*35 : 0; pos[node.id]={x:cx+Math.cos(angle)*radius,y:cy+Math.sin(angle)*radius}; });
    const links = data.edges.filter(e => pos[e.source] && pos[e.target]).map(e => `<line x1="${pos[e.source].x}" y1="${pos[e.source].y}" x2="${pos[e.target].x}" y2="${pos[e.target].y}"/><text x="${(pos[e.source].x+pos[e.target].x)/2}" y="${(pos[e.source].y+pos[e.target].y)/2}">${escapeHtml(e.label)}</text>`).join('');
    const fills={case:'#6f95ff',vehicle:'#a49aff',person:'#63d5bd',evidence:'#ffb36d'};
    const circles=nodes.map(node=>{ const p=pos[node.id]; return `<g><circle cx="${p.x}" cy="${p.y}" r="${node.id===state.selected.CrimeNo?39:28}" fill="#15263e" stroke="${fills[node.type] || '#9dabc0'}" stroke-width="${Math.max(1.5,node.confidence*3)}"/><text x="${p.x}" y="${p.y-2}">${escapeHtml(node.label).slice(0,16)}</text><text class="node-type" x="${p.x}" y="${p.y+12}">${escapeHtml(node.type)}</text></g>`; }).join('');
    canvas.innerHTML = `<svg viewBox="0 0 980 470" aria-label="Live entity graph"><g class="graph-live-links">${links}</g><g class="graph-live-nodes">${circles}</g></svg><div class="graph-tooltip"><b>${escapeHtml(state.selected.CrimeNo)}</b><span>Live graph from relational database</span></div>`;
  } catch (error) { canvas.innerHTML = `<div class="graph-empty">Could not build graph: ${escapeHtml(error.message)}</div>`; }
}
async function loadMap() {
  const mapElement = $('#crime-map'); if (!window.L) { mapElement.innerHTML='<div class="map-loading">Leaflet could not load. Check your network and reload.</div>'; return; }
  if (!state.map) { state.map=L.map('crime-map').setView([15.2,75.9],7); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors'}).addTo(state.map); state.markers=L.layerGroup().addTo(state.map); }
  const params = new URLSearchParams(); ['crime-type','district','status'].forEach(key => { const value=$(`#map-${key}`).value; if (value) params.set(key.replace('-','_'),value); });
  try { const data=await api(`/map?${params}`); state.markers.clearLayers(); const points=[]; data.results.forEach(c => { state.markers.addLayer(L.circleMarker([c.latitude,c.longitude],{radius:4,color:'#8c82ff',fillColor:'#a79fff',fillOpacity:.6,weight:1}).bindPopup(`<b>${escapeHtml(c.CrimeNo)}</b><br>${escapeHtml(c.CrimeType)} · ${escapeHtml(c.DistrictName)}`));points.push([c.latitude,c.longitude]); }); $('#map-title').textContent=$('#map-district').value || 'Karnataka'; $('#map-summary').textContent=`${data.results.length.toLocaleString()} geocoded FIR records returned by active filters.`; if (points.length) state.map.fitBounds(points,{padding:[24,24],maxZoom:11}); }
  catch(error) { $('#map-summary').textContent=`Map query failed: ${error.message}`; }
}
async function loadAnalytics() {
  const analytics=await api('/analytics'); state.analytics=analytics; const metrics=document.querySelectorAll('.metric-card strong'); metrics[0].textContent=analytics.total_cases.toLocaleString(); metrics[1].textContent=analytics.by_type[0]?.value || '—'; metrics[2].textContent=`${Math.round((analytics.by_type[0]?.value || 0)/analytics.total_cases*100)}%`;
  document.querySelector('.metric-card:nth-child(1) div:nth-child(2)>span').textContent='Generated FIR records'; document.querySelector('.metric-card:nth-child(2) div:nth-child(2)>span').textContent=`Largest type · ${analytics.by_type[0]?.label || '—'}`;
  $('#map-crime-type').innerHTML='<option value="">All crime types</option>'+analytics.by_type.map(x=>`<option>${escapeHtml(x.label)}</option>`).join(''); $('#map-district').innerHTML='<option value="">All districts</option>'+analytics.by_district.map(x=>`<option>${escapeHtml(x.label)}</option>`).join('');
  const top=analytics.by_type.slice(0,4); $('.breakdown').innerHTML=`<div class="panel-head"><div><span>CASE MIX · LIVE DATABASE</span><h2>By reported category</h2></div><span class="count">${analytics.total_cases.toLocaleString()} FIRs</span></div>${top.map(x=>`<div class="bar-row"><b>${escapeHtml(x.label)}</b><div><i style="width:${Math.round(x.value/top[0].value*100)}%"></i></div><span>${x.value}</span></div>`).join('')}`;
}
$('#query-form').addEventListener('submit', event => { event.preventDefault(); executeQuery($('#query').value); });
document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => executeQuery(button.dataset.query)));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
$('#clear-chat').addEventListener('click', () => { $('#conversation').innerHTML='<div class="message assistant-message"><div class="ai-avatar">K</div><div class="message-content"><p>Session cleared. Ask across the live generated FIR database.</p></div></div>'; });
$('#mic').addEventListener('click', () => { const Recognition=window.SpeechRecognition || window.webkitSpeechRecognition; if (!Recognition) { toast('Native speech recognition is unavailable in this browser.'); return; } const recognition=new Recognition(); recognition.lang='en-IN'; recognition.interimResults=false; toast('Listening…'); recognition.start(); recognition.onresult=e=>{ $('#query').value=e.results[0][0].transcript; toast('Voice query transcribed - review then send'); }; recognition.onerror=()=>toast('Voice transcription unavailable. Please type the query.'); });
['map-crime-type','map-district','map-status'].forEach(id=>$('#'+id).addEventListener('change',loadMap));
(async()=>{ try { await loadAnalytics(); const initial=await api('/search?q=burglary'); renderCases(initial.results,initial.results[0]); } catch(error) { toast('Backend unavailable. Run npm run dev to use live data.'); } })();
