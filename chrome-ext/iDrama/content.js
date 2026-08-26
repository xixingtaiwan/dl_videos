// content.js - chạy trong context của trang idrama.dramafren.org
// Fetch từ đây = same-origin = có đầy đủ cookie, bypass Cloudflare

let isScraping = false;
let shouldStop = false;

// ===========================
// LẤY THÔNG TIN DRAMA TỪ TRANG
// ===========================
function getDramaInfo() {
  const url = new URL(window.location.href);
  const params = url.searchParams;
  const page = params.get('page');
  const id = params.get('id');
  const lang = params.get('lang') || 'en';
  const ep = parseInt(params.get('ep')) || 1;
  const server = parseInt(params.get('server')) || 1;

  let totalEps = 0;
  let title = '';
  let cover = '';
  let description = '';

  // Lấy tổng số tập từ badge
  const epsBadge = document.querySelector('.bg-blue-900');
  if (epsBadge) {
    const match = epsBadge.textContent.match(/(\d+)/);
    if (match) totalEps = parseInt(match[1]);
  }

  // Fallback: đếm link tập
  if (!totalEps) {
    const epLinks = document.querySelectorAll('a[href*="page=watch"]');
    // Lấy số tập cao nhất
    epLinks.forEach(a => {
      const m = a.href.match(/ep=(\d+)/);
      if (m) totalEps = Math.max(totalEps, parseInt(m[1]));
    });
  }

  // Fallback từ JS variables trong trang
  if (!totalEps) {
    const scripts = document.querySelectorAll('script');
    for (const s of scripts) {
      const m = s.textContent.match(/totalEpisodes\s*=\s*(\d+)/);
      if (m) { totalEps = parseInt(m[1]); break; }
    }
  }

  // Title
  const h1 = document.querySelector('h1');
  if (h1) title = h1.textContent.trim();
  if (!title) title = document.title.replace(' - Full Episodes', '').trim();

  // Cover
  const coverImg = document.querySelector('img.poster-shadow, .flex-shrink-0 img');
  if (coverImg) cover = coverImg.src;

  // Description - đoạn synopsis trong trang detail
  const descEl = document.querySelector('p.text-slate-300, .flex-1 p');
  if (descEl) description = descEl.textContent.trim();
  // Fallback từ meta description
  if (!description) {
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) description = metaDesc.getAttribute('content') || '';
  }

  return { page, id, lang, ep, server, totalEps, title, cover, description };
}

// ===========================
// FETCH 1 TẬP (SAME-ORIGIN) - 2 bước
// Bước 1: watch_stream → intermediate URL
// Bước 2: fetch intermediate URL → real video_url
// ===========================
async function fetchEpisodeStream(id, ep, server, lang) {
  // --- Bước 1: Lấy intermediate URL từ watch_stream ---
  const apiUrl = `https://idrama.dramafren.org/index.php?action=watch_stream&id=${id}&ep=${ep}&server=${server}&lang=${lang}&_=${Date.now()}`;

  const res1 = await fetch(apiUrl, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json, text/plain, */*',
      'X-Requested-With': 'XMLHttpRequest',
      'Referer': window.location.href
    }
  });

  const text1 = await res1.text();
  if (text1.trim().startsWith('<')) {
    throw new Error('Buoc 1: Server tra HTML (Cloudflare chan)');
  }

  const data1 = JSON.parse(text1);
  if (!data1 || !data1.ok || !data1.video_url) {
    console.warn('[iDrama] Buoc 1 that bai:', JSON.stringify(data1));
    throw new Error('Buoc 1: ' + (data1 && data1.error ? data1.error : 'Khong co video_url'));
  }

  const intermediateUrl = data1.video_url;
  const subs = data1.subs || [];

  // --- Bước 2: Fetch intermediate URL để lấy real video URL ---
  try {
    const res2 = await fetch(intermediateUrl, {
      credentials: 'omit',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://idrama.dramafren.org/'
      }
    });

    const text2 = await res2.text();

    // Nếu trả về JSON → lấy video_url thật
    if (text2.trim().startsWith('{')) {
      const data2 = JSON.parse(text2);
      if (data2 && data2.ok && data2.video_url) {
        return {
          ok: true,
          video_url: data2.video_url,
          subs: data2.subs && data2.subs.length ? data2.subs : subs,
          intermediate_url: intermediateUrl
        };
      }
    }

    // Nếu trả về m3u8 thực hoặc không parse được → dùng luôn intermediate URL
    console.log('[iDrama] Buoc 2 khong tra JSON, dung intermediate URL');
    return { ok: true, video_url: intermediateUrl, subs };

  } catch (err2) {
    // Nếu bước 2 lỗi (CORS, etc.) → vẫn trả intermediate URL từ bước 1
    console.warn('[iDrama] Buoc 2 loi, fallback intermediate URL:', err2.message);
    return { ok: true, video_url: intermediateUrl, subs };
  }
}


// ===========================
// VÒNG LẶP SCRAPE CHÍNH
// ===========================
async function runScrape(config) {
  if (isScraping) return;
  isScraping = true;
  shouldStop = false;

  const { id, lang, server, epFrom, epTo, delay } = config;
  const total = epTo - epFrom + 1;
  let done = 0;

  for (let ep = epFrom; ep <= epTo; ep++) {
    if (shouldStop) break;

    try {
      const data = await fetchEpisodeStream(id, ep, server, lang);
      
      let ok = false;
      let videoUrl = null;
      let subs = [];
      let error = null;

      if (data && data.ok && data.video_url) {
        ok = true;
        videoUrl = data.video_url;
        subs = data.subs || [];
      } else {
        error = (data && data.error) ? data.error : 'video_url trống';
        // Log full response để debug
        console.warn('[iDrama Scraper] Ep', ep, 'response:', JSON.stringify(data));
      }

      done++;
      chrome.runtime.sendMessage({
        action: 'progressUpdate',
        ep, url: videoUrl, subs, ok, error, done, total
      });

    } catch (err) {
      done++;
      console.error('[iDrama Scraper] Ep', ep, 'error:', err);
      chrome.runtime.sendMessage({
        action: 'progressUpdate',
        ep, url: null, subs: [], ok: false, error: err.message, done, total
      });
    }

    if (ep < epTo && !shouldStop) {
      await new Promise(r => setTimeout(r, delay));
    }
  }

  isScraping = false;
  chrome.runtime.sendMessage({
    action: 'scrapeFinished',
    stopped: shouldStop
  });
}

// ===========================
// LẮNG NGHE TỪ BACKGROUND / POPUP
// ===========================
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  
  if (msg.action === 'getDramaInfo') {
    sendResponse(getDramaInfo());
    return true;
  }

  if (msg.action === 'startScrape') {
    runScrape(msg.config);
    sendResponse({ ok: true });
    return true;
  }

  if (msg.action === 'stopScrape') {
    shouldStop = true;
    sendResponse({ ok: true });
    return true;
  }

  // Debug: test 1 tập
  if (msg.action === 'testFetch') {
    const { id, ep, server, lang } = msg;
    fetchEpisodeStream(id, ep, server, lang)
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});