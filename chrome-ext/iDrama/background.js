// background.js - Service Worker (lưu state, không fetch)
// State tồn tại suốt session dù popup đóng

let jobState = {
  status: 'idle',    // idle | running | paused | done | stopped
  tabId: null,
  config: null,
  results: [],       // [{ep, url, subs, ok, error}]
  progress: { done: 0, total: 0, current: 0 },
  dramaInfo: null
};

// Lưu state vào storage để popup có thể đọc khi mở lại
async function saveState() {
  await chrome.storage.session.set({ jobState });
}

// Gửi progress update cho popup nếu đang mở
function broadcastUpdate(type, payload) {
  chrome.runtime.sendMessage({ type, payload }).catch(() => {});
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  
  // === POPUP: Lấy state hiện tại khi popup mở ===
  if (msg.action === 'getState') {
    sendResponse(jobState);
    return true;
  }

  // === POPUP: Bắt đầu scrape ===
  if (msg.action === 'startJob') {
    const { tabId, config, dramaInfo } = msg;

    jobState = {
      status: 'running',
      tabId,
      config,
      dramaInfo,
      results: [],
      progress: { done: 0, total: config.epTo - config.epFrom + 1, current: config.epFrom }
    };

    saveState();

    // Gửi lệnh scrape cho content script trong tab đó
    chrome.tabs.sendMessage(tabId, {
      action: 'startScrape',
      config
    }).catch(err => {
      jobState.status = 'error';
      broadcastUpdate('error', { message: 'Không kết nối được content script: ' + err.message });
      saveState();
    });

    sendResponse({ ok: true });
    return true;
  }

  // === POPUP: Dừng scrape ===
  if (msg.action === 'stopJob') {
    if (jobState.tabId) {
      chrome.tabs.sendMessage(jobState.tabId, { action: 'stopScrape' }).catch(() => {});
    }
    jobState.status = 'stopped';
    saveState();
    sendResponse({ ok: true });
    return true;
  }

  // === CONTENT SCRIPT: Báo cáo progress ===
  if (msg.action === 'progressUpdate') {
    const { ep, url, subs, ok, error, done, total } = msg;

    jobState.results.push({ ep, url, subs, ok, error });
    jobState.progress = { done, total, current: ep };

    if (done >= total) {
      jobState.status = 'done';
    }

    saveState();
    // Relay sang popup
    broadcastUpdate('progressUpdate', { ep, url, subs, ok, error, done, total });
    return true;
  }

  // === CONTENT SCRIPT: Scrape xong ===
  if (msg.action === 'scrapeFinished') {
    jobState.status = msg.stopped ? 'stopped' : 'done';
    saveState();
    broadcastUpdate('scrapeFinished', { stopped: msg.stopped });
    return true;
  }

});