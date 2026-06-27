const bridge = window.AstrBotPluginPage;

// 状态
let currentPage = 1;
let perPage = 10;
let allQuotes = [];
let searchKeyword = "";

// DOM 元素
const els = {
  content: document.getElementById("content"),
  character: document.getElementById("character"),
  source: document.getElementById("source"),
  btnAdd: document.getElementById("btn-add"),
  addMsg: document.getElementById("add-msg"),
  quotesList: document.getElementById("quotes-list"),
  pagination: document.getElementById("pagination"),
  search: document.getElementById("search"),
  statTotal: document.getElementById("stat-total"),
  statDefault: document.getElementById("stat-default"),
};

// 初始化
async function init() {
  await bridge.ready();
  loadQuotes();

  // 绑定事件
  els.btnAdd.addEventListener("click", handleAdd);
  els.search.addEventListener("input", debounce(handleSearch, 300));

  // 回车添加
  els.content.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key === "Enter") handleAdd();
  });
}

// 加载金句列表
async function loadQuotes() {
  try {
    els.quotesList.innerHTML = '<div class="loading">加载中...</div>';

    const result = await bridge.apiGet("custom-quotes/list", {
      page: currentPage,
      per_page: perPage,
      keyword: searchKeyword,
    });

    allQuotes = result.quotes || [];
    renderQuotes(allQuotes);
    renderPagination(
      result.total,
      result.page,
      result.per_page,
      result.total_pages
    );

    // 更新统计
    els.statTotal.textContent = result.total_custom || 0;
    els.statDefault.textContent = result.total_default || 0;
  } catch (err) {
    els.quotesList.innerHTML = `<div class="empty">❌ 加载失败: ${err.message}</div>`;
  }
}

// 渲染金句列表
function renderQuotes(quotes) {
  if (!quotes || quotes.length === 0) {
    els.quotesList.innerHTML =
      '<div class="empty">暂无自定义金句，快去添加一条吧！</div>';
    return;
  }

  // 计算当前页第一条的真实索引（用于精准删除）
  const startIndex = (currentPage - 1) * perPage;

  els.quotesList.innerHTML = quotes
    .map(
      (q, idx) => {
        const realIndex = startIndex + idx;
        // 安全转义 content 用于 onclick 属性
        const safeContent = escapeHtml(q.content).replace(/\'/g, "\\\'").replace(/"/g, "\&quot;");
        return `
        <div class="quote-item" data-index="${realIndex}">
            <div class="quote-content">${escapeHtml(q.content)}</div>
            <div class="quote-meta">
                <div class="quote-tags">
                    <span class="tag">${escapeHtml(
                      q.character || "未知角色"
                    )}</span>
                    ${
                      q.source
                        ? `<span class="tag source">${escapeHtml(
                            q.source
                          )}</span>`
                        : ""
                    }
                </div>
                <button class="btn-danger" onclick="handleDelete(${realIndex}, '${safeContent}')">🗑️ 删除</button>
            </div>
        </div>
    `;
      }
    )
    .join("");
}

// 渲染分页
function renderPagination(total, page, perPage, totalPages) {
  if (totalPages <= 1) {
    els.pagination.innerHTML = "";
    return;
  }

  let html = "";

  // 上一页
  html += `<button class="page-btn" ${
    page <= 1 ? "disabled" : ""
  } onclick="goPage(${page - 1})">上一页</button>`;

  // 页码
  const maxButtons = 5;
  let startPage = Math.max(1, page - Math.floor(maxButtons / 2));
  let endPage = Math.min(totalPages, startPage + maxButtons - 1);

  if (endPage - startPage < maxButtons - 1) {
    startPage = Math.max(1, endPage - maxButtons + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    html += `<button class="page-btn ${ i === page ? "active" : "" }" onclick="goPage(${i})">${i}</button>`;
  }

  // 下一页
  html += `<button class="page-btn" ${
    page >= totalPages ? "disabled" : ""
  } onclick="goPage(${page + 1})">下一页</button>`;

  // 页码信息
  html += `<span class="page-info">${page}/${totalPages} 页 (共${total}条)</span>`;

  els.pagination.innerHTML = html;
}

// 添加金句
async function handleAdd() {
  const content = els.content.value.trim();
  const character = els.character.value.trim() || "未知角色";
  const source = els.source.value.trim();

  if (!content) {
    showMsg("add-msg", "金句内容不能为空", "error");
    return;
  }

  if (content.length > 500) {
    showMsg("add-msg", "金句内容过长（最多500字符）", "error");
    return;
  }

  els.btnAdd.disabled = true;
  els.btnAdd.textContent = "添加中...";

  try {
    const result = await bridge.apiPost("custom-quotes/add", {
      content,
      character,
      source,
    });

    showMsg("add-msg", "✅ 金句添加成功！", "success");

    // 清空表单
    els.content.value = "";
    els.character.value = "";
    els.source.value = "";

    // 刷新列表（使用后端返回的列表直接 re-render，减少一次请求）
    if (result.quotes) {
      allQuotes = result.quotes.slice(0, perPage);
      renderQuotes(allQuotes);
      // 更新统计
      els.statTotal.textContent = result.total || 0;
    } else {
      currentPage = 1;
      loadQuotes();
    }
  } catch (err) {
    showMsg("add-msg", `❌ 添加失败: ${err.message}`, "error");
  } finally {
    els.btnAdd.disabled = false;
    els.btnAdd.textContent = "➕ 添加金句";
  }
}

// 删除金句 — 改用 index 精准删除（Bug 修复）
async function handleDelete(index, content) {
  if (
    !confirm(
      `确定要删除这条金句吗？\n\n"${content.substring(0, 50)}${ content.length > 50 ? "..." : "" }"`
    )
  ) {
    return;
  }

  try {
    const result = await bridge.apiPost("custom-quotes/delete", {
      index: index,   // ← 传真实索引，不再传 keyword（修复 Bug）
    });

    // 直接使用后端返回的列表 re-render，减少一次请求
    if (result.quotes) {
      allQuotes = result.quotes.slice((currentPage - 1) * perPage, currentPage * perPage);
      renderQuotes(allQuotes);
      // 更新统计
      els.statTotal.textContent = result.total || 0;
      // 如果当前页空了，回到上一页
      if (allQuotes.length === 0 && currentPage > 1) {
        currentPage--;
        loadQuotes();
      }
    } else {
      loadQuotes();
    }
  } catch (err) {
    alert(`删除失败: ${err.message}`);
  }
}

// 搜索
function handleSearch(e) {
  searchKeyword = e.target.value.trim();
  currentPage = 1;
  loadQuotes();
}

// 翻页
function goPage(page) {
  currentPage = page;
  loadQuotes();
}

// 显示消息
function showMsg(id, text, type) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = `msg show ${type}`;
  setTimeout(() => {
    el.className = "msg";
  }, 3000);
}

// HTML 转义
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// 防抖
function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// 启动
init();