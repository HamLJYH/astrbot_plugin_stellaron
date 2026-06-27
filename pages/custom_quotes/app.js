const bridge = window.AstrBotPluginPage;

let currentPage = 1;
let perPage = 10;
let allQuotes = [];
let searchKeyword = '';

const els = {
    content: document.getElementById('content'),
    character: document.getElementById('character'),
    source: document.getElementById('source'),
    btnAdd: document.getElementById('btn-add'),
    addMsg: document.getElementById('add-msg'),
    quotesList: document.getElementById('quotes-list'),
    pagination: document.getElementById('pagination'),
    search: document.getElementById('search'),
    statTotal: document.getElementById('stat-total'),
    statDefault: document.getElementById('stat-default'),
};

async function init() {
    await bridge.ready();
    loadQuotes();
    els.btnAdd.addEventListener('click', handleAdd);
    els.search.addEventListener('input', debounce(handleSearch, 300));
    els.quotesList.addEventListener('click', handleListClick);
    els.content.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') handleAdd();
    });
}

function handleListClick(e) {
    const btn = e.target.closest('.btn-delete');
    if (!btn) return;
    const index = parseInt(btn.dataset.index);
    const content = btn.dataset.content;
    handleDelete(index, content);
}

async function loadQuotes() {
    try {
        els.quotesList.innerHTML = '<div class="loading">加载中...</div>';
        const result = await bridge.apiGet('custom-quotes/list', {
            page: currentPage, per_page: perPage, keyword: searchKeyword,
        });
        allQuotes = result.quotes || [];
        renderQuotes(allQuotes);
        renderPagination(result.total, result.page, result.per_page, result.total_pages);
        els.statTotal.textContent = result.total_custom || 0;
        els.statDefault.textContent = result.total_default || 0;
    } catch (err) {
        els.quotesList.innerHTML = `<div class="empty">❌ 加载失败: ${err.message}</div>`;
    }
}

function renderQuotes(quotes) {
    if (!quotes || quotes.length === 0) {
        els.quotesList.innerHTML = '<div class="empty">暂无自定义金句，快去添加一条吧！</div>';
        return;
    }
    els.quotesList.innerHTML = quotes.map((q, idx) => {
        const safeContent = (q.content || '').replace(/"/g, '&quot;').replace(/'/g, "&#39;");
        return `
        <div class="quote-item">
            <div class="quote-content">${escapeHtml(q.content)}</div>
            <div class="quote-meta">
                <div class="quote-tags">
                    <span class="tag">${escapeHtml(q.character || '未知角色')}</span>
                    ${q.source ? `<span class="tag source">${escapeHtml(q.source)}</span>` : ''}
                </div>
                <button class="btn-danger btn-delete" data-index="${idx}" data-content="${safeContent}">🗑️ 删除</button>
            </div>
        </div>`;
    }).join('');
}

function renderPagination(total, page, perPage, totalPages) {
    if (totalPages <= 1) { els.pagination.innerHTML = ''; return; }
    let html = '';
    html += `<button class="page-btn" ${page <= 1 ? 'disabled' : ''} onclick="goPage(${page - 1})">上一页</button>`;
    const maxButtons = 5;
    let startPage = Math.max(1, page - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    if (endPage - startPage < maxButtons - 1) startPage = Math.max(1, endPage - maxButtons + 1);
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
    }
    html += `<button class="page-btn" ${page >= totalPages ? 'disabled' : ''} onclick="goPage(${page + 1})">下一页</button>`;
    html += `<span class="page-info">${page}/${totalPages} 页 (共${total}条)</span>`;
    els.pagination.innerHTML = html;
}

async function handleAdd() {
    const content = els.content.value.trim();
    const character = els.character.value.trim() || '未知角色';
    const source = els.source.value.trim();
    if (!content) { showMsg('add-msg', '金句内容不能为空', 'error'); return; }
    if (content.length > 500) { showMsg('add-msg', '金句内容过长（最多500字符）', 'error'); return; }
    els.btnAdd.disabled = true; els.btnAdd.textContent = '添加中...';
    try {
        await bridge.apiPost('custom-quotes/add', { content, character, source });
        showMsg('add-msg', '✅ 金句添加成功！', 'success');
        els.content.value = ''; els.character.value = ''; els.source.value = '';
        currentPage = 1; loadQuotes();
    } catch (err) {
        showMsg('add-msg', `❌ 添加失败: ${err.message}`, 'error');
    } finally {
        els.btnAdd.disabled = false; els.btnAdd.textContent = '➕ 添加金句';
    }
}

async function handleDelete(index, content) {
    const displayContent = content.length > 50 ? content.substring(0, 50) + '...' : content;
    if (!confirm(`确定要删除这条金句吗？\n\n"${displayContent}"`)) return;
    try {
        await bridge.apiPost('custom-quotes/delete', { keyword: content });
        loadQuotes();
    } catch (err) { alert(`删除失败: ${err.message}`); }
}

function handleSearch(e) { searchKeyword = e.target.value.trim(); currentPage = 1; loadQuotes(); }
function goPage(page) { currentPage = page; loadQuotes(); }

function showMsg(id, text, type) {
    const el = document.getElementById(id);
    el.textContent = text; el.className = `msg show ${type}`;
    setTimeout(() => { el.className = 'msg'; }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(fn, delay) {
    let timer;
    return function(...args) { clearTimeout(timer); timer = setTimeout(() => fn.apply(this, args), delay); };
}

init();