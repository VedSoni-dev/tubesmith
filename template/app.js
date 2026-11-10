/* tubesmith site: static, no build step, no tracking. Everything personal lives in localStorage. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem("tube:" + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("tube:" + k, JSON.stringify(v)); } catch { /* private mode */ } },
  };

  let DATA = { meta: {}, videos: [] };
  let BY = new Map();
  const S = { // view state (filters)
    topic: null, type: "", len: "", sort: "best", evergreen: false,
  };
  const prefs = () => Object.assign({ thumbnails: "mid", titles: "original", counts: true, theme: "" },
    { thumbnails: D().thumbnails || "mid", titles: D().titles || "original", counts: !D().hide_counts },
    store.get("prefs", {}));
  const D = () => DATA.meta.display || {};
  const liked = () => store.get("liked", []);
  const later = () => store.get("later", []);
  const history = () => store.get("history", []);
  const toggle = (k, id) => { const a = store.get(k, []); const i = a.indexOf(id); i < 0 ? a.unshift(id) : a.splice(i, 1); store.set(k, a.slice(0, 2000)); };

  /* ---------- formatting ---------- */
  const fmtDur = (s) => { if (!s) return ""; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0"); };
  const fmtN = (n) => n == null ? "" : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "K" : String(n);
  const yr = (d) => d ? d.slice(0, 4) : "";
  const shownTitle = (v) => { const m = prefs().titles; return (m !== "original" && v.pt) ? v.pt : v.t; };

  function thumbHTML(v, tip = "") {
    const mode = prefs().thumbnails;
    const badge = v.dur ? `<span class="badge">${fmtDur(v.dur)}</span>` : "";
    const gem = v.gem ? `<span class="gem">hidden gem</span>` : "";
    if (mode === "none") return `<div class="thumb none"><span>${esc(v.sum || [v.type, (v.top || [])[0]].filter(Boolean).join(" · ") || v.ch)}</span>${badge}${gem}${tip}</div>`;
    const file = { mid: "hq2", frames: "hq1", original: "mqdefault", blur: "mqdefault" }[mode] || "hq2";
    return `<div class="thumb ${mode === "blur" ? "blur" : ""}" ${mode === "frames" ? 'data-frames="1"' : ""}>
      <img loading="lazy" decoding="async" alt="" src="https://i.ytimg.com/vi/${esc(v.id)}/${file}.jpg">${badge}${gem}${tip}</div>`;
  }

  function cardHTML(v) {
    const p = prefs();
    const title = shownTitle(v);
    const showOrig = (p.titles === "both" && v.pt && v.pt !== v.t);
    const bits = [esc(v.ch)];
    if (p.counts && v.views) bits.push(fmtN(v.views) + " views");
    if (v.pub) bits.push(yr(v.pub));
    const saved = later().includes(v.id) ? ` · <span class="saved">saved</span>` : liked().includes(v.id) ? ` · <span class="saved">♥</span>` : "";
    const q = (v.q || [])[0];
    const tip = D().why_tooltip !== false && (v.why || q) ? `<div class="tip">
        ${v.why ? `<b>Why it's here:</b> ${esc(v.why)}` : ""}
        ${v.ppl ? `<div>${v.ppl} people recommended it across ${v.mo} month${v.mo === 1 ? "" : "s"}.</div>` : ""}
        ${q ? `<q>${esc(q.q)}</q> <span>— ${esc(q.by)}</span>` : ""}</div>` : "";
    return `<article class="card" data-id="${esc(v.id)}" tabindex="0" title="${p.titles === "plain" && v.pt && v.pt !== v.t ? "Original: " + esc(v.t) : ""}">
      ${thumbHTML(v, tip)}
      <div class="meta"><div>
        <div class="title">${esc(title)}</div>
        ${showOrig ? `<div class="orig">${esc(v.t)}</div>` : ""}
        <div class="by">${bits.join(" · ")}${saved}</div>
      </div></div></article>`;
  }

  /* ---------- filtering + search ---------- */
  function applyFilters(list) {
    return list.filter((v) => {
      if (S.topic && !(v.top || []).includes(S.topic)) return false;
      if (S.type && v.type !== S.type) return false;
      if (S.evergreen && v.life !== "evergreen") return false;
      if (S.len && v.dur) {
        const m = v.dur / 60;
        if (S.len === "short" && m >= 20) return false;
        if (S.len === "mid" && (m < 20 || m > 60)) return false;
        if (S.len === "long" && m <= 60) return false;
      }
      return true;
    });
  }
  function sortList(list) {
    const a = list.slice();
    if (S.sort === "recent") a.sort((x, y) => (y.last || "").localeCompare(x.last || "") || y.sc - x.sc);
    else if (S.sort === "new") a.sort((x, y) => (y.pub || "").localeCompare(x.pub || ""));
    else if (S.sort === "loved") { // like/view ratio, smoothed so tiny videos can't win on 3 likes
      const r = (v) => v.views ? ((v.likes || 0) + 20) / (v.views + 2000) : 0;
      a.sort((x, y) => r(y) - r(x));
    } else a.sort((x, y) => y.sc - x.sc);
    return a;
  }
  function search(q) {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    const scored = [];
    for (const v of DATA.videos) {
      const fields = [[v.t, 3], [v.pt, 3], [(v.top || []).join(" "), 4], [v.ch, 2], [v.sum, 1.5], [v.why, 1], [v.type, 1]];
      let s = 0, all = true;
      for (const t of terms) {
        let hit = 0;
        for (const [f, w] of fields) if (f && f.toLowerCase().includes(t)) hit += w;
        if (!hit) { all = false; break; }
        s += hit;
      }
      if (all) scored.push([s + v.sc * 0.15, v]);
    }
    return scored.sort((a, b) => b[0] - a[0]).map((x) => x[1]);
  }

  /* ---------- views ---------- */
  const main = $("#main");
  const grid = (list) => list.length ? `<div class="grid">${list.map(cardHTML).join("")}</div>` : `<p class="empty">Nothing here yet. Try loosening a filter.</p>`;
  const playAll = (list) => list.length > 1 ? `<a class="more" target="_blank" rel="noopener" href="https://www.youtube.com/watch_videos?video_ids=${list.slice(0, 50).map((v) => v.id).join(",")}">Play all on YouTube ↗</a>` : "";
  function shelf(title, sub, list, key) {
    if (!list.length) return "";
    return `<section class="shelf"><div class="shelf-h"><h2>${esc(title)}</h2>${sub ? `<span class="sub">${esc(sub)}</span>` : ""}
      ${key ? `<a class="more" href="#/shelf/${key}">See all</a>` : ""}</div>
      <div class="row">${list.slice(0, 12).map(cardHTML).join("")}</div></section>`;
  }

  function shelves() {
    const vids = applyFilters(DATA.videos);
    const seen = new Set(history());
    const fresh = vids.filter((v) => !seen.has(v.id));
    const out = {};
    out.classics = sortList(fresh);
    out.recent = fresh.filter((v) => v.last).sort((a, b) => (b.last || "").localeCompare(a.last || "") || b.sc - a.sc);
    out.gems = fresh.filter((v) => v.gem);
    out.longs = fresh.filter((v) => v.dur && v.dur > 3600).sort((a, b) => b.sc - a.sc);
    out.channels = fresh.filter((v) => v.src === "channel").sort((a, b) => (b.pub || "").localeCompare(a.pub || ""));
    // for you: topics + recommenders of what you liked
    const L = liked().map((id) => BY.get(id)).filter(Boolean);
    if (L.length) {
      const tw = {}, by = new Set();
      L.forEach((v) => { (v.top || []).forEach((t) => tw[t] = (tw[t] || 0) + 1); (v.q || []).forEach((q) => by.add(q.by)); });
      const likedSet = new Set(liked());
      out.foryou = fresh.filter((v) => !likedSet.has(v.id)).map((v) => [
        (v.top || []).reduce((s, t) => s + (tw[t] || 0), 0) * 2 + (v.q || []).filter((q) => by.has(q.by)).length * 1.5 + v.sc * 0.1, v])
        .filter((x) => x[0] > 0.5).sort((a, b) => b[0] - a[0]).map((x) => x[1]);
    } else out.foryou = [];
    // unexplored: topics you haven't touched, best video of each
    const touched = new Set(); [...seen].forEach((id) => (BY.get(id)?.top || []).forEach((t) => touched.add(t)));
    const best = {};
    for (const v of out.classics) for (const t of v.top || []) if (!touched.has(t) && !best[t]) best[t] = v;
    const pickedIds = new Set();
    out.unexplored = Object.values(best).filter((v) => !pickedIds.has(v.id) && pickedIds.add(v.id)).sort(() => Math.random() - 0.5);
    return out;
  }
  const SHELF_NAMES = {
    foryou: ["For you", "from what you liked"], classics: ["Classics", "recommended again and again, for years"],
    recent: ["Recently recommended", ""], gems: ["Hidden gems", "loved by people you trust, barely seen on YouTube"],
    longs: ["Longs", "over an hour. Settle in."], channels: ["From your channels", ""], unexplored: ["Unexplored", "topics you haven't touched yet"],
  };

  function renderHome() {
    const sh = shelves();
    const n = +D().finite_feed || 0;
    if (n > 0) { // finite feed: a fixed daily set, then stop
      const day = new Date().toISOString().slice(0, 10);
      let pick = store.get("daily", {});
      if (pick.day !== day) {
        const pool = [...sh.foryou.slice(0, n), ...sh.unexplored.slice(0, 3), ...sh.classics];
        const ids = [...new Set(pool.map((v) => v.id))].slice(0, n);
        pick = { day, ids }; store.set("daily", pick);
      }
      const list = pick.ids.map((id) => BY.get(id)).filter(Boolean);
      main.innerHTML = `<section class="shelf"><div class="shelf-h"><h2>Today</h2><span class="sub">${list.length} videos, picked once a day</span>${playAll(list)}</div>${grid(list)}</section>
        <div class="end"><b>That's the feed.</b>Come back tomorrow. Or <a href="#/shelf/classics"><u>browse everything</u></a>.</div>`;
      return;
    }
    const order = ["foryou", "classics", D().gems_shelf !== false && "gems", "recent", D().longs_shelf !== false && "longs", "channels", "unexplored"].filter(Boolean);
    const html = order.map((k) => shelf(SHELF_NAMES[k][0], SHELF_NAMES[k][1], sh[k], k)).join("");
    main.innerHTML = html || `<p class="empty">No videos match. Clear a filter above.</p>`;
  }
  function renderShelf(key) {
    const list = shelves()[key] || [];
    const [t, sub] = SHELF_NAMES[key] || [key, ""];
    main.innerHTML = `<section class="shelf"><div class="shelf-h"><h2>${esc(t)}</h2><span class="sub">${esc(sub)} · ${list.length}</span>${playAll(list)}</div>${grid(list.slice(0, 300))}</section>`;
  }
  function renderSearch(q) {
    const list = applyFilters(search(q));
    main.innerHTML = `<section class="shelf"><div class="shelf-h"><h2>“${esc(q)}”</h2><span class="sub">${list.length} result${list.length === 1 ? "" : "s"}</span>${playAll(list)}</div>${grid(list.slice(0, 200))}</section>`;
  }
  function renderTopic(t) {
    S.topic = t; renderFilters();
    const list = sortList(applyFilters(DATA.videos));
    main.innerHTML = `<section class="shelf"><div class="shelf-h"><h2>${esc(t)}</h2><span class="sub">${list.length} videos</span>${playAll(list)}</div>${grid(list)}</section>`;
  }
  function renderLibrary(tab = "liked") {
    const lists = { liked: liked(), later: later(), history: history() };
    const list = (lists[tab] || []).map((id) => BY.get(id)).filter(Boolean);
    main.innerHTML = `<div class="tabs">${[["liked", "Liked"], ["later", "Watch later"], ["history", "History"]].map(([k, n]) =>
      `<a class="chip ${k === tab ? "on" : ""}" href="#/library/${k}">${n} (${lists[k].length})</a>`).join("")}${playAll(list)}</div>${grid(list)}`;
  }

  /* ---------- filters bar ---------- */
  function renderFilters() {
    const counts = {};
    DATA.videos.forEach((v) => (v.top || []).forEach((t) => counts[t] = (counts[t] || 0) + 1));
    const topics = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 18).map((x) => x[0]);
    if (S.topic && !topics.includes(S.topic)) topics.unshift(S.topic);
    const types = [...new Set(DATA.videos.map((v) => v.type).filter(Boolean))].sort();
    const hasDur = DATA.videos.some((v) => v.dur);
    $("#filters").innerHTML =
      `<button class="chip ${!S.topic ? "on" : ""}" data-topic="">All</button>` +
      topics.map((t) => `<button class="chip ${S.topic === t ? "on" : ""}" data-topic="${esc(t)}">${esc(t)}</button>`).join("") +
      `<span class="sep"></span>` +
      (types.length ? `<select id="f-type" aria-label="Type"><option value="">Any type</option>${types.map((t) => `<option ${S.type === t ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>` : "") +
      (hasDur ? `<select id="f-len" aria-label="Length"><option value="">Any length</option><option value="short" ${S.len === "short" ? "selected" : ""}>Under 20 min</option><option value="mid" ${S.len === "mid" ? "selected" : ""}>20–60 min</option><option value="long" ${S.len === "long" ? "selected" : ""}>Over an hour</option></select>` : "") +
      `<select id="f-sort" aria-label="Sort"><option value="best">Most recommended</option><option value="recent" ${S.sort === "recent" ? "selected" : ""}>Recently recommended</option><option value="new" ${S.sort === "new" ? "selected" : ""}>Newest uploads</option>${DATA.videos.some((v) => v.likes) ? `<option value="loved" ${S.sort === "loved" ? "selected" : ""}>Most loved (likes/views)</option>` : ""}</select>` +
      (DATA.videos.some((v) => v.life) ? `<button class="chip ${S.evergreen ? "on" : ""}" id="f-ever">Evergreen only</button>` : "");
  }
  $("#filters").addEventListener("click", (e) => {
    const b = e.target.closest("[data-topic]");
    if (b) { const t = b.dataset.topic; location.hash = t ? "#/t/" + encodeURIComponent(t) : "#/"; if (!t) { S.topic = null; route(); } return; }
    if (e.target.id === "f-ever") { S.evergreen = !S.evergreen; renderFilters(); route(); }
  });
  $("#filters").addEventListener("change", (e) => {
    if (e.target.id === "f-type") S.type = e.target.value;
    if (e.target.id === "f-len") S.len = e.target.value;
    if (e.target.id === "f-sort") S.sort = e.target.value;
    route();
  });

  /* ---------- player ---------- */
  function openPlayer(id) {
    const v = BY.get(id);
    if (!v) return;
    const h = history().filter((x) => x !== id); h.unshift(id); store.set("history", h.slice(0, 2000));
    $("#frame").src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0&modestbranding=1&playsinline=1`;
    const p = prefs();
    const title = shownTitle(v);
    const bits = [esc(v.ch), v.dur && fmtDur(v.dur), p.counts && v.views && fmtN(v.views) + " views", v.pub && yr(v.pub), v.type, v.lvl].filter(Boolean);
    $("#player-body").innerHTML = `
      <h1>${esc(title)}</h1>
      ${title !== v.t ? `<div class="orig">Original title: ${esc(v.t)}</div>` : ""}
      <div class="by">${bits.join(" · ")}</div>
      <div class="actions">
        <button class="btn ${liked().includes(id) ? "on" : ""}" data-act="liked">♥ Like <small>(L)</small></button>
        <button class="btn ${later().includes(id) ? "on" : ""}" data-act="later">＋ Watch later <small>(W)</small></button>
        <a class="btn" target="_blank" rel="noopener" href="https://www.youtube.com/watch?v=${esc(id)}">Open on YouTube ↗</a>
      </div>
      ${v.sum ? `<p class="summary">${esc(v.sum)}</p>` : ""}
      ${v.why ? `<p class="why"><b>Why it's here:</b> ${esc(v.why)}${v.ppl ? ` · ${v.ppl} people, ${v.mo} months` : ""}</p>` : ""}
      ${(v.q || []).length ? `<ul class="quotes">${v.q.map((q) => `<li><q>${esc(q.q)}</q><br><a href="${esc(q.url || "#")}" target="_blank" rel="noopener">— ${esc(q.by)}${q.d ? ", " + esc(q.d) : ""} ↗</a></li>`).join("")}</ul>` : ""}
      ${(v.top || []).length ? `<div class="tags">${v.top.map((t) => `<a class="chip" href="#/t/${encodeURIComponent(t)}">${esc(t)}</a>`).join("")}</div>` : ""}`;
    $("#player").hidden = false;
    $("#player").dataset.id = id;
    $(".player-card").scrollTop = 0;
  }
  function closePlayer() {
    if ($("#player").hidden) return;
    $("#player").hidden = true; $("#frame").src = "about:blank";
    if (location.hash.startsWith("#/v/")) history_back();
  }
  const history_back = () => { if (window.history.length > 1 && sessionStorage.getItem("tube:navved")) window.history.back(); else location.hash = "#/"; };
  $("#player-body").addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    toggle(b.dataset.act, $("#player").dataset.id);
    b.classList.toggle("on");
  });
  $("#close-player").onclick = closePlayer;
  $("#player").addEventListener("click", (e) => { if (e.target.id === "player") closePlayer(); });

  /* ---------- cards: click, keyboard, frame scrubbing ---------- */
  main.addEventListener("click", (e) => { const c = e.target.closest(".card"); if (c) { sessionStorage.setItem("tube:navved", "1"); location.hash = "#/v/" + c.dataset.id; } });
  main.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.classList.contains("card")) e.target.click(); });
  let scrub = null;
  main.addEventListener("mouseover", (e) => {
    const t = e.target.closest('.thumb[data-frames]');
    if (!t || scrub?.el === t) return;
    stopScrub();
    const img = t.querySelector("img"), id = t.closest(".card").dataset.id;
    let i = 1;
    scrub = { el: t, img, id, timer: setInterval(() => { i = i % 3 + 1; img.src = `https://i.ytimg.com/vi/${id}/hq${i}.jpg`; }, 650) };
  });
  main.addEventListener("mouseout", (e) => { if (scrub && !scrub.el.contains(e.relatedTarget)) stopScrub(); });
  function stopScrub() { if (!scrub) return; clearInterval(scrub.timer); scrub.img.src = `https://i.ytimg.com/vi/${scrub.id}/hq1.jpg`; scrub = null; }

  /* ---------- settings ---------- */
  function applyTheme() { const t = prefs().theme; if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
  $("#open-settings").onclick = () => {
    const p = prefs();
    $("#set-thumbs").value = p.thumbnails; $("#set-titles").value = p.titles; $("#set-counts").checked = !!p.counts; $("#set-theme").value = p.theme || "";
    const m = DATA.meta;
    $("#about").innerHTML = `<b>${esc(m.name)}</b>: ${m.counts?.videos ?? 0} videos, rebuilt ${esc(m.generated || "")}.<br>${esc(D().credits || "")}<br>
      Videos play through YouTube's privacy-enhanced player. Likes and history stay in this browser.<br>
      Made with <a href="https://github.com/VedSoni-dev/tubesmith" target="_blank" rel="noopener">tubesmith</a>, after Karpathy's <a href="https://hackertube.org" target="_blank" rel="noopener">HackerTube</a>.`;
    $("#settings").hidden = false;
  };
  const savePrefs = () => { store.set("prefs", { thumbnails: $("#set-thumbs").value, titles: $("#set-titles").value, counts: $("#set-counts").checked, theme: $("#set-theme").value }); applyTheme(); route(); };
  ["#set-thumbs", "#set-titles", "#set-counts", "#set-theme"].forEach((s) => $(s).addEventListener("change", savePrefs));
  document.querySelectorAll("[data-close]").forEach((b) => b.onclick = () => $("#" + b.dataset.close).hidden = true);
  $("#settings").addEventListener("click", (e) => { if (e.target.id === "settings") e.target.hidden = true; });
  $("#reset-local").onclick = () => { if (confirm("Clear likes, watch later and history on this device?")) { ["liked", "later", "history", "daily"].forEach((k) => store.set(k, k === "daily" ? {} : [])); route(); } };

  /* ---------- search + keys ---------- */
  $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); const q = $("#q").value.trim(); location.hash = q ? "#/s/" + encodeURIComponent(q) : "#/"; });
  let deb; $("#q").addEventListener("input", () => { clearTimeout(deb); deb = setTimeout(() => { const q = $("#q").value.trim(); if (q.length > 1) location.replace("#/s/" + encodeURIComponent(q)); else if (!q) location.replace("#/"); }, 220); });
  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName);
    if (e.key === "Escape") { if (!$("#settings").hidden) $("#settings").hidden = true; else closePlayer(); return; }
    if (typing) return;
    if (e.key === "/") { e.preventDefault(); $("#q").focus(); }
    if (!$("#player").hidden && (e.key === "l" || e.key === "w")) $(`[data-act="${e.key === "l" ? "liked" : "later"}"]`)?.click();
  });

  /* ---------- router ---------- */
  function route() {
    const h = decodeURIComponent(location.hash.slice(1) || "/");
    const [, a, b] = h.split("/");
    if (a === "v" && b) { if ($("#player").hidden || $("#player").dataset.id !== b) openPlayer(b); return; }
    if (!$("#player").hidden) { $("#player").hidden = true; $("#frame").src = "about:blank"; }
    if (a !== "t") S.topic = null;
    renderFilters();
    if (a === "s" && b) { $("#q").value = b; renderSearch(b); }
    else if (a === "t" && b) renderTopic(b);
    else if (a === "shelf" && b) renderShelf(b);
    else if (a === "library") renderLibrary(b || "liked");
    else renderHome();
  }
  window.addEventListener("hashchange", route);

  /* ---------- boot ---------- */
  applyTheme();
  fetch("videos.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }).then((d) => {
    DATA = d; BY = new Map(d.videos.map((v) => [v.id, v]));
    document.title = d.meta.name || "My Tube";
    $("#brand-name").textContent = d.meta.name || "My Tube";
    if (D().accent) document.documentElement.style.setProperty("--accent", D().accent);
    if (!d.videos.length) { main.innerHTML = `<p class="empty">No videos yet. Run the pipeline (collect → aggregate → meta → judge → rank).</p>`; return; }
    route();
  }).catch(() => {
    main.innerHTML = `<p class="empty">Couldn't load videos.json. Serve this folder over http (python3 -m http.server -d site), not file://.</p>`;
  });
})();
