/* 语料浏览 — 检索、筛选、分页 */
(function() {

const PAGE_SIZE = 50;
let allPoems = [];
let filteredPoems = [];
let currentPage = 1;

function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function loadCorpus() {
    fetch('/api/corpus/stats').then(r => r.json()).then(d => {
        if (d.ok && d.stats) {
            const s = d.stats;
            document.getElementById('corpus-stats').innerHTML =
                '<span><strong>总诗歌数：</strong>' + s.total + '</span> &nbsp; ' +
                '<span><strong>作者数：</strong>' + s.authors + '</span> &nbsp; ' +
                '<span><strong>朝代数：</strong>' + s.dynasties + '</span> &nbsp; ' +
                '<span><strong>诗体数：</strong>' + s.forms + '</span>';

            // Fill dynasty filter
            if (s.dynasty_list) {
                const sel = document.getElementById('filter-dynasty');
                s.dynasty_list.forEach(d => {
                    const o = document.createElement('option');
                    o.value = d; o.textContent = d + ' (' + (s.dynasty_counts[d] || 0) + '首)';
                    sel.appendChild(o);
                });
            }
        }
    });

    // Try to load poems from current session
    fetch('/api/corpus/poems').then(r => r.json()).then(d => {
        if (d.ok && d.poems) {
            allPoems = d.poems;
            filteredPoems = [...allPoems];
            renderPage(1);
        }
    });
}

function doSearch() {
    const keyword = document.getElementById('search-input').value.trim();
    const dynasty = document.getElementById('filter-dynasty').value;

    filteredPoems = allPoems.filter(p => {
        if (dynasty && p.朝代 !== dynasty) return false;
        if (keyword) {
            const text = (p.标题 + p.作者 + p.原文).toLowerCase();
            if (!text.includes(keyword.toLowerCase())) return false;
        }
        return true;
    });
    renderPage(1);
}

function renderPage(page) {
    currentPage = page;
    const start = (page - 1) * PAGE_SIZE;
    const pagePoems = filteredPoems.slice(start, start + PAGE_SIZE);
    const tbody = document.getElementById('corpus-body');

    if (pagePoems.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">无匹配结果</td></tr>';
    } else {
        tbody.innerHTML = pagePoems.map(p =>
            '<tr><td>' + (p.编号 || '') + '</td>' +
            '<td>' + escHtml(p.标题 || '') + '</td>' +
            '<td>' + escHtml(p.作者 || '') + '</td>' +
            '<td>' + (p.朝代 || '') + '</td>' +
            '<td>' + (p._detected_form || '') + '</td>' +
            '<td style="max-width:300px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">' + escHtml((p.原文 || '').substring(0, 60)) + '</td></tr>'
        ).join('');
    }

    // Pagination
    const totalPages = Math.ceil(filteredPoems.length / PAGE_SIZE);
    const pagDiv = document.getElementById('corpus-pagination');
    if (totalPages <= 1) {
        pagDiv.innerHTML = '';
    } else {
        let html = '<span style="font-size:13px;color:#888">第 ' + page + ' 页 / 共 ' + totalPages + ' 页 &nbsp;</span>';
        if (page > 1) html += '<button class="btn btn-sm" onclick="renderPage(' + (page-1) + ')">上一页</button> ';
        if (page < totalPages) html += '<button class="btn btn-sm" onclick="renderPage(' + (page+1) + ')">下一页</button>';
        pagDiv.innerHTML = html;
    }
    window.renderPage = renderPage;
}

document.addEventListener('DOMContentLoaded', loadCorpus);

})();
