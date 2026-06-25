const $ = (id) => document.getElementById(id);
const esc = (v = "") => String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const titleOf = (m) => m?.attributes?.title?.["pt-br"] || m?.attributes?.title?.pt || m?.attributes?.title?.en || Object.values(m?.attributes?.title || {})[0] || "Sem titulo";
const descOf = (m) => m?.attributes?.description?.["pt-br"] || m?.attributes?.description?.pt || m?.attributes?.description?.en || "";
const coverOf = (m) => {
  const cover = m?.relationships?.find((r) => r.type === "cover_art");
  return cover?.attributes?.fileName ? `/api/cover/${m.id}/${cover.attributes.fileName}` : "";
};
const statusPt = { ongoing: "Em andamento", completed: "Completo", hiatus: "Hiato", cancelled: "Cancelado" };
const PAGE_SIZE = 40;
const tagPt = {
  Romance: "Romance", Drama: "Drama", Comedy: "Comedia", Fantasy: "Fantasia", "Slice of Life": "Cotidiano",
  "Full Color": "Colorido", Webtoon: "Webtoon", Action: "Acao", Adventure: "Aventura", Mystery: "Misterio",
  Thriller: "Suspense", "Office Workers": "Escritorio", "Long Strip": "Long strip", "User Created": "Usuario"
};

async function getJson(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok || data.error) throw new Error(data.error || "Falha ao carregar");
  return data;
}

function placeholder(title) {
  return `<div class="cover-fallback">${esc(title).slice(0, 2).toUpperCase()}</div>`;
}

function renderCards(items) {
  const grid = $("mangaGrid");
  if (!items.length) {
    grid.innerHTML = `<p class="empty">Nada encontrado em PT-BR.</p>`;
    return;
  }
  grid.innerHTML = items.map((m) => {
    const title = titleOf(m);
    const cover = coverOf(m);
    const tags = (m.attributes.tags || []).slice(0, 3).map((t) => `<span>${esc(tagPt[t.attributes.name.en] || t.attributes.name.en || "")}</span>`).join("");
    return `<a class="card" href="/manga/${m.id}">
      <div class="cover">${cover ? `<img src="${cover}" alt="${esc(title)}" loading="lazy">` : placeholder(title)}</div>
      <div class="card-body">
        <strong>${esc(title)}</strong>
        <small>${esc(statusPt[m.attributes.status] || m.attributes.status || "")}</small>
        <div class="chips">${tags}</div>
      </div>
    </a>`;
  }).join("");
}

function renderPager(total, page, load) {
  const pages = Math.ceil(Math.min(total, 10000) / PAGE_SIZE);
  $("pager").innerHTML = pages > 1 ? `
    <button ${page < 1 ? "disabled" : ""} data-page="${page - 1}">Anterior</button>
    <span>Pagina ${page + 1} de ${pages}</span>
    <button ${page >= pages - 1 ? "disabled" : ""} data-page="${page + 1}">Proxima</button>` : "";
  $("pager").onclick = (e) => e.target.dataset.page && load(Number(e.target.dataset.page));
}

function initHome() {
  let mode = "popular", query = "", tag = "", letter = "", page = 0;
  const letters = ["ALL", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"];
  $("letters").innerHTML = letters.map((l) => `<button data-letter="${l}">${l === "ALL" ? "Todos" : l}</button>`).join("");

  const load = async (nextPage = 0) => {
    page = nextPage;
    $("mangaGrid").innerHTML = `<div class="loading"></div>`;
    $("clearBtn").hidden = mode === "popular" && !tag && !letter;
    const qs = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(page * PAGE_SIZE) });
    let url = "/api/browse?" + qs;
    if (mode === "search") { qs.set("q", query); url = "/api/search?" + qs; }
    if (mode === "browse") {
      if (tag) qs.set("tag", tag);
      if (letter) qs.set("letter", letter);
      url = "/api/browse?" + qs;
    }
    const data = await getJson(url);
    renderCards(data.data || []);
    renderPager(data.total || 0, page, load);
  };

  $("searchForm").onsubmit = (e) => {
    e.preventDefault();
    query = $("searchInput").value.trim();
    if (!query) return;
    mode = "search";
    $("sectionTitle").textContent = `Busca: ${query}`;
    load();
  };
  $("tagSelect").onchange = (e) => {
    tag = e.target.value;
    mode = "browse";
    $("sectionTitle").textContent = tag ? `Categoria: ${e.target.selectedOptions[0].textContent}` : "Categorias";
    load();
  };
  $("letters").onclick = (e) => {
    if (!e.target.dataset.letter) return;
    letter = e.target.dataset.letter === "ALL" ? "" : e.target.dataset.letter;
    mode = "browse";
    document.querySelectorAll(".letters button").forEach((b) => b.classList.toggle("active", b === e.target));
    $("sectionTitle").textContent = letter ? `Letra ${letter}` : "Popular agora";
    load();
  };
  $("clearBtn").onclick = () => {
    mode = "popular"; query = tag = letter = ""; $("searchInput").value = ""; $("tagSelect").value = "";
    $("sectionTitle").textContent = "Popular agora"; document.querySelectorAll(".letters button").forEach((b) => b.classList.remove("active")); load();
  };

  getJson("/api/tags").then((data) => {
    $("tagSelect").innerHTML += (data.data || []).map((t) => `<option value="${t.id}">${esc(tagPt[t.attributes.name.en] || t.attributes.name.en)}</option>`).join("");
  }).catch(() => {});
  load();
}

function renderManga(m, chapters) {
  const title = titleOf(m), cover = coverOf(m), desc = descOf(m);
  document.title = `${title} | Hana Reader`;
  $("mangaPanel").innerHTML = `
    <div class="detail-cover">${cover ? `<img src="${cover}" alt="${esc(title)}">` : placeholder(title)}</div>
    <div>
      <p class="eyebrow">${esc(statusPt[m.attributes.status] || m.attributes.status || "")}</p>
      <h1>${esc(title)}</h1>
      <p>${esc(desc).slice(0, 700)}</p>
    </div>`;
  $("chapterCount").textContent = `${chapters.length} encontrados`;
  $("chaptersList").innerHTML = chapters.length ? chapters.map((c) => {
    const a = c.attributes;
    return `<a class="chapter" href="/read/${m.id}/${c.id}">
      <strong>Cap. ${esc(a.chapter || "?")}</strong>
      <span>${esc(a.title || "")}</span>
      <small>${a.pages || 0} pags</small>
    </a>`;
  }).join("") : `<p class="empty">Nenhum capitulo em PT-BR encontrado.</p>`;
}

async function initManga() {
  const id = document.body.dataset.mangaId;
  $("mangaPanel").innerHTML = `<div class="loading"></div>`;
  const [manga, chapters] = await Promise.all([getJson(`/api/manga/${id}`), getJson(`/api/manga/${id}/chapters?all=1`)]);
  renderManga(manga.data, chapters.data || []);
}

function initReader() {
  const mangaId = document.body.dataset.mangaId, chapterId = document.body.dataset.chapterId;
  let pages = [], index = 0, strip = true;
  $("backManga").href = `/manga/${mangaId}`;
  const update = () => {
    $("progress").textContent = strip ? `${pages.length} paginas` : `${index + 1} / ${pages.length}`;
    $("readerStage").className = strip ? "reader-stage strip" : "reader-stage paged";
    $("readerStage").innerHTML = strip
      ? pages.map((p, i) => `<img src="${p}" alt="Pagina ${i + 1}" loading="lazy">`).join("")
      : `<img src="${pages[index]}" alt="Pagina ${index + 1}">`;
  };
  const move = (step) => { if (!strip) { index = Math.max(0, Math.min(pages.length - 1, index + step)); update(); } };
  $("prevBtn").onclick = () => move(-1);
  $("nextBtn").onclick = () => move(1);
  $("modeBtn").onclick = () => { strip = !strip; $("modeBtn").textContent = strip ? "Pagina" : "Scroll"; update(); };
  document.onkeydown = (e) => { if (e.key === "ArrowLeft") move(-1); if (e.key === "ArrowRight") move(1); };
  $("readerStage").innerHTML = `<div class="loading"></div>`;
  getJson(`/api/chapter/${chapterId}/pages`).then((data) => {
    pages = data.pages || [];
    pages.length ? update() : $("readerStage").innerHTML = `<p class="empty">Capitulo sem paginas.</p>`;
  }).catch(() => $("readerStage").innerHTML = `<p class="empty">Erro ao abrir capitulo.</p>`);
}

const page = document.body.dataset.page;
if (page === "home") initHome();
if (page === "manga") initManga();
if (page === "reader") initReader();
