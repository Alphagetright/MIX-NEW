/* 古典诗歌文本结构化标注生产系统 — 表头设计器 */

let headers = [];

// ─── Header CRUD ─────────────────────────────────────────────────────

function addHeader(name, desc) {
    name = (name || document.getElementById('new-header-name').value).trim();
    desc = (desc || document.getElementById('new-header-desc').value).trim();
    if (!name) { toast('请输入列名', false); return; }

    headers.push({ name, desc });
    document.getElementById('new-header-name').value = '';
    document.getElementById('new-header-desc').value = '';
    renderHeaders();
    updateDesignButton();
}

function removeHeader(index) {
    headers.splice(index, 1);
    renderHeaders();
    updateDesignButton();
}

function moveHeader(index, dir) {
    const newIdx = index + dir;
    if (newIdx < 0 || newIdx >= headers.length) return;
    [headers[index], headers[newIdx]] = [headers[newIdx], headers[index]];
    renderHeaders();
}

function renderHeaders() {
    const tbody = document.getElementById('headers-tbody');
    if (headers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#999">暂无表头，请添加</td></tr>';
        return;
    }
    tbody.innerHTML = headers.map((h, i) => `
        <tr>
            <td>${i + 1}</td>
            <td class="editable-cell"><input value="${escHtml(h.name)}" onchange="headers[${i}].name = this.value.trim()"></td>
            <td class="editable-cell"><input value="${escHtml(h.desc)}" onchange="headers[${i}].desc = this.value.trim()"></td>
            <td>
                <button class="btn btn-sm" onclick="moveHeader(${i},-1)" ${i===0?'disabled':''} title="上移">↑</button>
                <button class="btn btn-sm" onclick="moveHeader(${i},1)" ${i===headers.length-1?'disabled':''} title="下移">↓</button>
                <button class="btn btn-sm btn-danger" onclick="removeHeader(${i})" title="删除">✕</button>
            </td>
        </tr>`).join('');
}

function updateDesignButton() {
    const card = document.getElementById('design-card');
    card.style.display = headers.length > 0 ? '' : 'none';
    document.getElementById('design-status').textContent =
        headers.length > 0 ? `当前 ${headers.length} 列待生成方案` : '';
}

// ─── Entry B: AI 解析需求 ────────────────────────────────────────────

function parseRequirement() {
    const text = document.getElementById('requirement-text').value.trim();
    if (!text) { toast('请输入需求描述', false); return; }

    const btn = document.getElementById('btn-parse');
    btn.disabled = true; btn.textContent = 'AI 分析中...';

    fetch('/api/parse-requirement', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ requirement: text })
    })
    .then(r => r.json())
    .then(d => {
        btn.disabled = false; btn.textContent = 'AI 解析需求';
        if (!d.ok) { toast(d.error, false); return; }

        const data = d.data;
        document.getElementById('parse-result').style.display = '';
        document.getElementById('parse-suggested-name').textContent = data.suggested_name || '';
        document.getElementById('parse-focus').textContent = data.analysis_focus || '';

        const tbody = document.querySelector('#parse-headers-table tbody');
        tbody.innerHTML = (data.headers || []).map(h =>
            `<tr><td>${h.name}</td><td>${h.desc || ''}</td></tr>`).join('');

        document.getElementById('parse-result').scrollIntoView({behavior: 'smooth'});
        toast('AI 建议已生成');
    });
}

function adoptParsedHeaders() {
    const rows = document.querySelectorAll('#parse-headers-table tbody tr');
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        const name = cells[0].textContent.trim();
        const desc = cells[1].textContent.trim();
        if (name && !headers.find(h => h.name === name)) {
            headers.push({ name, desc });
        }
    });
    renderHeaders();
    updateDesignButton();
    toast('已采用 AI 建议的表头');
}

// ─── Trigger Prompt 1 ────────────────────────────────────────────────

function triggerDesign() {
    if (headers.length === 0) { toast('请先定义表头', false); return; }

    const btn = document.getElementById('btn-design');
    btn.disabled = true; btn.textContent = 'AI 生成中（可能需要30秒+）...';
    document.getElementById('design-status').textContent = '正在调用 AI 设计标注方案...';

    fetch('/api/design-schema', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ headers })
    })
    .then(r => r.json())
    .then(d => {
        btn.disabled = false; btn.textContent = '重新生成方案';
        if (!d.ok) {
            document.getElementById('design-status').textContent = '生成失败：' + d.error;
            toast(d.error, false); return;
        }

        document.getElementById('design-status').innerHTML =
            `<p style="color:green">方案已生成！分析维度：${d.data.analysis_notes || '-'} | 预估 ${d.data.estimated_tokens_per_poem || '?'} tokens/首</p>
             <a href="/review" class="btn btn-primary" style="margin-top:8px">前往审核确认</a>`;

        // 缓存到 sessionStorage 供 review 页面使用
        sessionStorage.setItem('schema_result', JSON.stringify(d.data));
        toast('方案生成成功！');
    });
}

// ─── Template Operations ─────────────────────────────────────────────

function saveAsTemplate() {
    const name = document.getElementById('template-name').value.trim();
    if (!name) { toast('请输入模板名称', false); return; }
    if (headers.length === 0) { toast('请先定义表头', false); return; }

    const data = { headers, saved_at: new Date().toISOString() };

    fetch('/api/save-template', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name, data })
    })
    .then(r => r.json())
    .then(d => {
        if (d.ok) {
            toast('模板已保存');
            // 刷新下拉列表
            const sel = document.getElementById('template-select');
            if (![...sel.options].find(o => o.value === name)) {
                const opt = document.createElement('option');
                opt.value = name; opt.textContent = name;
                sel.appendChild(opt);
            }
        } else {
            toast(d.error, false);
        }
    });
}

function loadTemplate(name) {
    if (!name) return;
    fetch('/api/load-template/' + encodeURIComponent(name))
        .then(r => r.json())
        .then(d => {
            if (d.ok && d.data.headers) {
                headers = d.data.headers;
                renderHeaders();
                updateDesignButton();
                toast('模板已加载：' + name);
            }
        });
}

// ─── Helpers ─────────────────────────────────────────────────────────

function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
