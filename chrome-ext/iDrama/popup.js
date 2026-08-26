// popup.js - chỉ là UI, có thể đóng/mở lại thoải mái
// State được lưu trong background service worker

let dramaInfo = null;
let localResults = [];

const notDramaEl = document.getElementById('not-drama');
const dramaInfoEl = document.getElementById('drama-info');
const controlsEl = document.getElementById('controls-area');
const progressEl = document.getElementById('progress-area');
const resultsEl = document.getElementById('results-area');
const debugEl = document.getElementById('debug-area');
const dramaCoverEl = document.getElementById('drama-cover');
const dramaTitleEl = document.getElementById('drama-title');
const tagEpsEl = document.getElementById('tag-eps');
const tagLangEl = document.getElementById('tag-lang');
const tagIdEl = document.getElementById('tag-id');
const epFromEl = document.getElementById('ep-from');
const epToEl = document.getElementById('ep-to');
const selServerEl = document.getElementById('sel-server');
const selDelayEl = document.getElementById('sel-delay');
const btnScrape = document.getElementById('btn-scrape');
const btnStop = document.getElementById('btn-stop');
const btnAllEps = document.getElementById('btn-all-eps');
const btnCopyAll = document.getElementById('btn-copy-all');
const btnExportM3u = document.getElementById('btn-export-m3u');
const btnExportTxt = document.getElementById('btn-export-txt');
const btnDebug = document.getElementById('btn-debug');
const progressText = document.getElementById('progress-text');
const progressCount = document.getElementById('progress-count');
const progressBar = document.getElementById('progress-bar');
const progressStatus = document.getElementById('progress-status');
const resultsCount = document.getElementById('results-count');
const resultsList = document.getElementById('results-list');
const debugLog = document.getElementById('debug-log');

// =====================
// INIT - đọc state từ background
// =====================
async function init() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.includes('idrama.dramafren.org')) {
      showNotDrama(); return;
    }
    const url = new URL(tab.url);
    const page = url.searchParams.get('page');
    if (page !== 'detail' && page !== 'watch') {
      showNotDrama('Vào <strong style="color:#3b82f6">trang chi tiết phim</strong> trước (click vào 1 bộ phim)');
      return;
    }

    const bgState = await bgSend('getState');

    try {
      dramaInfo = await chrome.tabs.sendMessage(tab.id, { action: 'getDramaInfo' });
    } catch (e) {
      dramaInfo = {
        id: url.searchParams.get('id'),
        lang: url.searchParams.get('lang') || 'en',
        server: parseInt(url.searchParams.get('server')) || 1,
        totalEps: 0, title: tab.title || 'Unknown', cover: '', page
      };
    }

    if (!dramaInfo || !dramaInfo.id) {
      showNotDrama('Không tìm được ID phim. Vào trang detail của phim.'); return;
    }

    showDramaInfo();

    if (bgState && bgState.tabId === tab.id) {
      restoreState(bgState);
    }

    chrome.runtime.onMessage.addListener(onBackgroundMessage);
  } catch (err) {
    showNotDrama('Lỗi: ' + err.message);
  }
}

function restoreState(state) {
  localResults = state.results || [];
  resultsList.innerHTML = '';
  localResults.forEach(r => renderResultItem(r.ep, r.url, r.subs, r.ok, r.error));
  if (localResults.length > 0) {
    resultsCount.textContent = localResults.filter(r => r.ok).length;
    resultsEl.classList.add('visible');
  }
  if (state.status === 'running') {
    progressEl.classList.add('visible');
    setRunningUI(true);
    updateProgress(state.progress.done, state.progress.total, 'Đang scrape... (popup mở lại)');
  } else if (state.status === 'done' || state.status === 'stopped') {
    progressEl.classList.add('visible');
    setRunningUI(false);
    const s = localResults.filter(r => r.ok).length;
    progressText.textContent = state.status === 'done'
      ? `Hoan tat! ${s}/${state.progress.total} URL thanh cong.`
      : `Da dung. Thu duoc ${s}/${state.progress.done} URL.`;
    progressBar.style.width = '100%';
    progressCount.textContent = `${state.progress.done}/${state.progress.total}`;
  }
}

function onBackgroundMessage(msg) {
  if (msg.type === 'progressUpdate') {
    const { ep, url, subs, ok, error, done, total } = msg.payload;
    localResults.push({ ep, url, subs, ok, error });
    renderResultItem(ep, url, subs, ok, error);
    updateProgress(done, total, `Tap ${ep}: ${ok ? 'OK' : 'LOI - ' + (error || '')}`);
    resultsCount.textContent = localResults.filter(r => r.ok).length;
    resultsEl.classList.add('visible');
  }
  if (msg.type === 'scrapeFinished') {
    setRunningUI(false);
    const s = localResults.filter(r => r.ok).length;
    progressText.textContent = msg.payload.stopped
      ? `Da dung. Thu duoc ${s} URL.`
      : `Hoan tat! ${s}/${localResults.length} URL thanh cong.`;
    progressStatus.textContent = '';
  }
  if (msg.type === 'error') {
    log('ERR: ' + msg.payload.message);
    setRunningUI(false);
  }
}

// =====================
// UI
// =====================
function showNotDrama(msg) {
  document.querySelector('#not-drama p').innerHTML = msg || 'Mo trang idrama.dramafren.org va vao trang detail phim.';
  notDramaEl.classList.add('visible');
}

function showDramaInfo() {
  notDramaEl.classList.remove('visible');
  dramaInfoEl.classList.add('visible');
  controlsEl.classList.add('visible');
  dramaTitleEl.textContent = dramaInfo.title || 'Unknown Drama';
  if (dramaInfo.cover) dramaCoverEl.src = dramaInfo.cover;
  tagEpsEl.textContent = (dramaInfo.totalEps || '?') + ' tap';
  tagLangEl.textContent = (dramaInfo.lang || 'EN').toUpperCase();
  tagIdEl.textContent = 'ID: ' + dramaInfo.id;
  selServerEl.value = String(dramaInfo.server || 1);
  epFromEl.value = 1;
  epToEl.value = dramaInfo.totalEps || 1;
  epFromEl.max = dramaInfo.totalEps || 999;
  epToEl.max = dramaInfo.totalEps || 999;
}

function setRunningUI(running) {
  btnScrape.disabled = running;
  btnScrape.style.display = running ? 'none' : '';
  btnStop.style.display = running ? '' : 'none';
}

function updateProgress(done, total, statusMsg) {
  progressEl.classList.add('visible');
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  progressBar.style.width = pct + '%';
  progressCount.textContent = done + '/' + total;
  progressText.textContent = 'Dang scrape... (' + pct + '%)';
  if (statusMsg) progressStatus.textContent = statusMsg;
}

function renderResultItem(ep, url, subs, ok, error) {
  const item = document.createElement('div');
  item.className = 'ep-item';

  const numEl = document.createElement('div');
  numEl.className = 'ep-num';
  numEl.textContent = 'Ep ' + ep;

  const urlEl = document.createElement('div');
  urlEl.className = 'ep-url ' + (ok ? 'ok' : 'error');
  urlEl.textContent = ok ? url : 'LOI: ' + (error || 'That bai');
  urlEl.title = ok ? url : (error || 'That bai');

  const actionsEl = document.createElement('div');
  actionsEl.className = 'ep-actions';

  if (ok && url) {
    const copyBtn = document.createElement('button');
    copyBtn.className = 'ep-btn';
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = async () => {
      await copyText(url);
      copyBtn.textContent = 'OK';
      copyBtn.classList.add('copy-ok');
      setTimeout(() => { copyBtn.textContent = 'Copy'; copyBtn.classList.remove('copy-ok'); }, 1500);
    };

    const ytBtn = document.createElement('button');
    ytBtn.className = 'ep-btn';
    ytBtn.textContent = 'yt-dlp';
    ytBtn.onclick = async () => {
      const cmd = 'yt-dlp "' + url + '" -o "Ep' + String(ep).padStart(3, '0') + '.%(ext)s" --add-header "Referer:https://idrama.dramafren.org/"';
      await copyText(cmd);
      ytBtn.textContent = 'OK';
      setTimeout(() => { ytBtn.textContent = 'yt-dlp'; }, 1500);
    };

    actionsEl.appendChild(copyBtn);
    actionsEl.appendChild(ytBtn);
  }

  item.appendChild(numEl);
  item.appendChild(urlEl);
  item.appendChild(actionsEl);
  resultsList.appendChild(item);
  resultsList.scrollTop = resultsList.scrollHeight;
}

// =====================
// SCRAPE
// =====================
async function startScrape() {
  if (!dramaInfo) return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const config = {
    id: dramaInfo.id,
    lang: dramaInfo.lang || 'en',
    server: parseInt(selServerEl.value) || 1,
    delay: parseInt(selDelayEl.value) || 500,
    epFrom: parseInt(epFromEl.value) || 1,
    epTo: parseInt(epToEl.value) || 1
  };
  if (config.epFrom > config.epTo) { alert('Tap "tu" phai <= tap "den"!'); return; }

  localResults = [];
  resultsList.innerHTML = '';
  resultsEl.classList.remove('visible');
  setRunningUI(true);
  updateProgress(0, config.epTo - config.epFrom + 1, 'Khoi dong...');
  log('START: id=' + config.id + ', ep' + config.epFrom + '->' + config.epTo + ', server=' + config.server + ', lang=' + config.lang);

  const res = await bgSend('startJob', { tabId: tab.id, config, dramaInfo });
  if (!res || !res.ok) {
    log('ERR: Khong start duoc job - ' + JSON.stringify(res));
    setRunningUI(false);
  }
}

async function debugTestFetch() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  const id = dramaInfo && dramaInfo.id;
  const lang = (dramaInfo && dramaInfo.lang) || 'en';
  const server = parseInt(selServerEl.value) || 1;
  log('TEST: id=' + id + ', ep=1, server=' + server + ', lang=' + lang);
  try {
    const res = await chrome.tabs.sendMessage(tab.id, { action: 'testFetch', id, ep: 1, server, lang });
    log('RESP: ' + JSON.stringify(res && res.data || res));
  } catch (err) {
    log('ERR: ' + err.message);
  }
}

// =====================
// EXPORT
// =====================
function exportM3U() {
  const title = (dramaInfo && dramaInfo.title) || 'iDrama';
  let m3u = '#EXTM3U\n';
  localResults.filter(r => r.ok).forEach(r => {
    m3u += '#EXTINF:-1,' + title + ' - Tap ' + r.ep + '\n' + r.url + '\n';
  });
  downloadBlob(m3u, 'audio/x-mpegurl', 'idrama_' + (dramaInfo && dramaInfo.id || 'drama') + '.m3u');
}

function exportJSON() {
  const id = (dramaInfo && dramaInfo.id) || 'unknown';
  const output = {
    source: 'idrama',
    scraped_at: new Date().toISOString(),
    drama: {
      id: id,
      name: (dramaInfo && dramaInfo.title) || '',
      description: (dramaInfo && dramaInfo.description) || '',
      cover: (dramaInfo && dramaInfo.cover) || '',
      total_episodes: (dramaInfo && dramaInfo.totalEps) || localResults.length,
      lang: (dramaInfo && dramaInfo.lang) || 'en'
    },
    episodes: localResults.map(r => ({
      ep: r.ep,
      url: r.ok ? r.url : null,
      subs: r.ok ? (r.subs || []) : [],
      ok: r.ok,
      error: r.ok ? null : (r.error || 'unknown')
    }))
  };
  const json = JSON.stringify(output, null, 2);
  downloadBlob(json, 'application/json', 'idrama_' + id + '.json');
}

function downloadBlob(content, type, filename) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  chrome.downloads.download({ url, filename, saveAs: true });
}

function bgSend(action, payload) {
  return new Promise(resolve => {
    chrome.runtime.sendMessage(Object.assign({ action }, payload), res => resolve(res));
  });
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

function log(msg) {
  debugEl.classList.add('visible');
  const line = document.createElement('div');
  line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
  debugLog.appendChild(line);
  debugLog.scrollTop = debugLog.scrollHeight;
}

// Events
btnScrape.addEventListener('click', startScrape);
btnStop.addEventListener('click', async () => {
  btnStop.textContent = 'Dang dung...';
  btnStop.disabled = true;
  await bgSend('stopJob');
});
btnAllEps.addEventListener('click', () => {
  epFromEl.value = 1;
  epToEl.value = (dramaInfo && dramaInfo.totalEps) || 1;
});
btnCopyAll.addEventListener('click', async () => {
  const text = localResults.filter(r => r.ok).map(r => 'Ep' + r.ep + ': ' + r.url).join('\n');
  if (!text) { alert('Chua co URL nao!'); return; }
  await copyText(text);
  btnCopyAll.textContent = 'Da copy!';
  setTimeout(() => { btnCopyAll.textContent = 'Copy tat ca'; }, 2000);
});
btnExportM3u.addEventListener('click', () => {
  if (!localResults.some(r => r.ok)) { alert('Chua co URL nao!'); return; }
  exportM3U();
});
btnExportTxt.addEventListener('click', () => {
  if (!localResults.length) { alert('Chua co ket qua!'); return; }
  exportJSON();
});
btnDebug.addEventListener('click', debugTestFetch);

init();
