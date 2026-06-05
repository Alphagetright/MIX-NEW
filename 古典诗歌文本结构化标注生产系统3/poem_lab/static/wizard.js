/* 古典诗歌文本结构化标注生产系统 — 五步流水线 */

let headers = [];
let schemaData = null;
let poemCount = 0;

// ─── Utils ───────────────────────────────────────────────────────────

function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function showStep(id) {
    const el = document.getElementById(id);
    el.style.display = '';
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─── Step 1: Upload ──────────────────────────────────────────────────

function switchUploadTab(name) {
    document.querySelectorAll('#step-upload .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#step-upload .tab-content').forEach(c => c.style.display = 'none');
    event.target.classList.add('active');
    document.getElementById('tab-' + name).style.display = 'block';
}

const dz = document.getElementById('drop-zone');
const fi = document.getElementById('file-input');
if (dz) {
    dz.onclick = () => fi.click();
    fi.onchange = () => { if (fi.files[0]) uploadFile(fi.files[0]); };
    dz.ondragover = e => { e.preventDefault(); dz.classList.add('drag-over'); };
    dz.ondragleave = () => dz.classList.remove('drag-over');
    dz.ondrop = e => { e.preventDefault(); dz.classList.remove('drag-over'); if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]); };
}

function uploadFile(file) {
    const fd = new FormData();
    fd.append('file', file);
    fetch('/api/poems/upload', { method: 'POST', body: fd })
        .then(r => r.json()).then(d => { if (d.ok) onPoemsUploaded(d); else toast(d.error, false); });
}

function uploadPoems() {
    const text = document.getElementById('paste-area').value.trim();
    if (!text && fi.files[0]) { uploadFile(fi.files[0]); return; }
    if (!text) { toast('请选择文件或粘贴文本', false); return; }
    const fd = new FormData();
    fd.append('text', text);
    fetch('/api/poems/upload', { method: 'POST', body: fd })
        .then(r => r.json()).then(d => { if (d.ok) onPoemsUploaded(d); else toast(d.error, false); });
}

function onPoemsUploaded(d) {
    poemCount = d.count;
    document.getElementById('status-upload').textContent = '✅ ' + d.count + ' 首';
    document.getElementById('upload-result').innerHTML =
        '<p style="color:green">已解析 <strong>' + d.count + '</strong> 首诗</p>' +
        '<div class="table-wrap"><table class="data-table"><thead><tr><th>编号</th><th>标题</th><th>作者</th><th>原文（前50字）</th></tr></thead><tbody>' +
        d.preview.map(p => '<tr><td>' + p['编号'] + '</td><td>' + escHtml(p['标题']) + '</td><td>' + escHtml(p['作者']) + '</td><td>' + escHtml((p['原文']||'').substring(0,50)) + '</td></tr>').join('') +
        '</tbody></table></div>';
    toast('解析成功：' + d.count + ' 首');
    // 自动展开步骤2
    showStep('step-headers');
}

// ─── Step 2: Headers ─────────────────────────────────────────────────

function addHeader(name, desc) {
    name = (name || document.getElementById('new-header-name').value).trim();
    desc = (desc || document.getElementById('new-header-desc').value).trim();
    if (!name) { toast('请输入列名', false); return; }
    headers.push({ name, desc });
    document.getElementById('new-header-name').value = '';
    document.getElementById('new-header-desc').value = '';
    renderHeaders();
    updateDesignBtn();
}

function removeHeader(i) { headers.splice(i, 1); renderHeaders(); updateDesignBtn(); }

function moveHeader(i, dir) {
    const j = i + dir;
    if (j < 0 || j >= headers.length) return;
    [headers[i], headers[j]] = [headers[j], headers[i]];
    renderHeaders();
}

function renderHeaders() {
    const tbody = document.getElementById('headers-tbody');
    if (!headers.length) { tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">暂无表头，请添加或让 AI 推导</td></tr>'; return; }
    tbody.innerHTML = headers.map((h, i) =>
        '<tr><td>' + (i+1) + '</td>' +
        '<td class="editable-cell"><input value="' + escHtml(h.name) + '" onchange="headers['+i+'].name=this.value.trim()"></td>' +
        '<td class="editable-cell"><input value="' + escHtml(h.desc) + '" onchange="headers['+i+'].desc=this.value.trim()"></td>' +
        '<td><button class="btn btn-sm" onclick="moveHeader('+i+',-1)" ' + (i===0?'disabled':'') + '>↑</button> ' +
        '<button class="btn btn-sm" onclick="moveHeader('+i+',1)" ' + (i===headers.length-1?'disabled':'') + '>↓</button> ' +
        '<button class="btn btn-sm btn-danger" onclick="removeHeader('+i+')">✕</button></td></tr>').join('');
}

function updateDesignBtn() {
    document.getElementById('btn-design').disabled = headers.length === 0;
}

// Entry B: AI parse requirement
function parseRequirement() {
    const text = document.getElementById('requirement-text').value.trim();
    if (!text) { toast('请输入需求描述', false); return; }
    const btn = document.getElementById('btn-parse');
    btn.disabled = true; btn.textContent = 'AI 分析中...';

    fetch('/api/parse-requirement', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ requirement: text })
    }).then(r => r.json()).then(d => {
        btn.disabled = false; btn.textContent = 'AI 解析需求';
        if (!d.ok) { toast(d.error, false); return; }
        const data = d.data;
        const el = document.getElementById('parse-result');
        el.style.display = '';
        el.innerHTML = '<h4>' + escHtml(data.suggested_name || '') + '</h4>' +
            '<p class="hint">' + escHtml(data.analysis_focus || '') + '</p>' +
            '<div class="table-wrap"><table class="data-table"><thead><tr><th>列名</th><th>说明</th></tr></thead><tbody>' +
            (data.headers||[]).map(h => '<tr><td>' + escHtml(h.name) + '</td><td>' + escHtml(h.desc||'') + '</td></tr>').join('') +
            '</tbody></table></div>' +
            '<button class="btn" onclick="adoptParsedHeaders()" style="margin-top:6px">采用此方案</button>';
        el.scrollIntoView({ behavior: 'smooth' });
        toast('AI 建议已生成');
    });
}

function adoptParsedHeaders() {
    const rows = document.querySelectorAll('#parse-result tbody tr');
    rows.forEach(row => {
        const name = row.cells[0].textContent.trim();
        const desc = row.cells[1].textContent.trim();
        if (name && !headers.find(h => h.name === name)) headers.push({ name, desc });
    });
    renderHeaders(); updateDesignBtn();
    toast('已采用 AI 建议');
}

// Trigger Prompt 1
function triggerDesign() {
    if (!headers.length) { toast('请先定义表头', false); return; }
    if (!poemCount) { toast('请先上传诗歌数据', false); return; }

    const btn = document.getElementById('btn-design');
    btn.disabled = true; btn.textContent = 'AI 生成中（可能需要30秒+）...';
    document.getElementById('design-status').innerHTML = '<p class="loading">正在调用 AI 设计标注方案...</p>';

    fetch('/api/design-schema', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ headers })
    }).then(r => r.json()).then(d => {
        btn.disabled = false; btn.textContent = '重新生成方案';
        if (!d.ok) { document.getElementById('design-status').innerHTML = '<p class="err">生成失败：' + escHtml(d.error) + '</p>'; toast(d.error, false); return; }

        schemaData = d.data;
        sessionStorage.setItem('schema_result', JSON.stringify(schemaData));
        document.getElementById('design-status').innerHTML = '<p style="color:green">方案已生成！分析维度：' + escHtml(d.data.analysis_notes||'-') + ' | 预估 ' + (d.data.estimated_tokens_per_poem||'?') + ' tokens/首</p>';
        document.getElementById('status-headers').textContent = '✅ 已完成';
        toast('方案生成成功');

        // 填充审核页面
        populateReview(d.data);
        // 自动跳转步骤3
        setTimeout(() => showStep('step-review'), 600);
    });
}

// ─── Step 3: Review ──────────────────────────────────────────────────

function populateReview(data) {
    document.getElementById('generated-prompt').value = data.generated_prompt || '';
    document.querySelector('#mapping-table tbody').innerHTML = (data.column_mapping||[]).map(c =>
        '<tr><td>' + escHtml(c.header||'') + '</td><td><code>' + escHtml(c.field||'') + '</code></td>' +
        '<td>' + escHtml(c.dimension||'') + '</td><td>' + escHtml(c.data_type||'string') + '</td>' +
        '<td>' + escHtml((c.enum_values||[]).join(', ') || '-') + '</td></tr>').join('');
    document.getElementById('sample-row').textContent = JSON.stringify(data.sample_row || {}, null, 2);
    document.getElementById('analysis-notes').textContent = data.analysis_notes || '';
    document.getElementById('est-tokens').textContent = data.estimated_tokens_per_poem || '';

    const sv = data.sample_validation || {};
    document.getElementById('sample-validation').innerHTML = sv.ok
        ? '<p style="color:green">✅ 示例数据校验通过</p>'
        : '<p style="color:#b33a3a">⚠ 校验问题：' + (sv.issues||[]).join('; ') + '</p>';
}

function runQualityCheck() {
    const btn = document.getElementById('btn-quality');
    btn.disabled = true; btn.textContent = '试跑中...';

    if (!schemaData) schemaData = JSON.parse(sessionStorage.getItem('schema_result') || '{}');
    schemaData.generated_prompt = document.getElementById('generated-prompt').value;
    const settings = getSettings();

    fetch('/api/quality-check', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            generated_prompt: schemaData.generated_prompt,
            column_mapping: schemaData.column_mapping || [],
            test_count: settings.test_count || 5
        })
    }).then(r => r.json()).then(d => {
        btn.disabled = false; btn.textContent = '重新试跑';
        const el = document.getElementById('quality-result');
        el.style.display = '';
        if (d.ok && d.data) {
            const q = d.data;
            el.innerHTML = '<div class="quality-card">' +
                '<p><strong>总体评分：</strong><span class="score">' + (q.overall_score||'?') + ' / 100</span> &nbsp; ' +
                '<strong>成功率：</strong>' + (q.success_rate||'?') + ' &nbsp; ' +
                (q.ready_for_batch ? '<span style="color:green">✅ 可批量</span>' : '<span style="color:#b33a3a">❌ 建议调整</span>') + '</p>' +
                '<p><strong>建议：</strong>' + escHtml(q.recommendation||'') + '</p>' +
                (q.top_issues && q.top_issues.length ? '<p><strong>主要问题：</strong></p><ul>' + q.top_issues.map(i => '<li>'+escHtml(i)+'</li>').join('') + '</ul>' : '') +
                (q.column_quality ? '<table class="data-table" style="margin-top:8px"><thead><tr><th>列名</th><th>合规率</th><th>问题</th></tr></thead><tbody>' +
                q.column_quality.map(c => '<tr><td>'+escHtml(c.header)+'</td><td>'+c.compliance+'%</td><td>'+escHtml(c.issues||'-')+'</td></tr>').join('') + '</tbody></table>' : '') +
                '</div>';

            // 显示确认按钮
            const confirmBtn = document.getElementById('btn-confirm');
            if (q.ready_for_batch || q.overall_score >= 60) {
                confirmBtn.style.display = '';
            }
            document.getElementById('status-review').textContent = '评分 ' + (q.overall_score||'?') + '/100';
        } else {
            el.innerHTML = '<p style="color:#b33a3a">质量检查失败：' + escHtml(d.error||'未知错误') + '</p>';
        }
        el.scrollIntoView({ behavior: 'smooth' });
    });
}

function confirmAndGo() {
    if (!schemaData) schemaData = JSON.parse(sessionStorage.getItem('schema_result') || '{}');
    schemaData.generated_prompt = document.getElementById('generated-prompt').value;
    sessionStorage.setItem('schema_result', JSON.stringify(schemaData));

    // Sync edited prompt to server (so batch-run reads the latest)
    fetch('/api/sync-schema', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            generated_prompt: schemaData.generated_prompt,
            column_mapping: schemaData.column_mapping
        })
    }).then(r => r.json()).then(d => {
        if (d.ok) {
            document.getElementById('status-review').textContent = '✅ 已确认';
            showStep('step-run');
        } else {
            toast('同步失败，请重试', false);
        }
    });
}

// ─── Step 4: Batch Run ───────────────────────────────────────────────

let evtSource = null;

function startBatch() {
    if (!schemaData) schemaData = JSON.parse(sessionStorage.getItem('schema_result') || '{}');

    const btn = document.getElementById('btn-start');
    btn.disabled = true; btn.textContent = '运行中...';

    evtSource = new EventSource('/api/batch-run');

    evtSource.onmessage = function(e) {
        const d = JSON.parse(e.data);
        if (d.error) { toast(d.error, false); btn.disabled = false; btn.textContent = '重新运行'; evtSource.close(); return; }
        if (d.done) {
            document.getElementById('progress-bar').style.width = '100%';
            document.getElementById('progress-text').textContent = '完成！成功 ' + d.success_count + ' / ' + d.total + ' 首';
            document.getElementById('status-run').textContent = '✅ ' + d.success_count + '/' + d.total;
            document.getElementById('export-links').innerHTML =
                '<a href="/api/export/csv/' + d.csv_file + '" class="btn btn-primary" style="margin-right:8px">📥 下载 CSV</a>' +
                '<a href="/api/export/json/' + d.json_file + '" class="btn">📥 下载 JSON</a>';
            btn.disabled = false; btn.textContent = '重新运行';
            evtSource.close();
            // 自动展开步骤5
            showStep('step-export');
            document.getElementById('final-export-links').innerHTML =
                '<a href="/api/export/csv/' + d.csv_file + '" class="btn btn-primary btn-lg" style="margin-right:8px">📥 下载 CSV</a>' +
                '<a href="/api/export/json/' + d.json_file + '" class="btn btn-lg">📥 下载 JSON</a>';
            return;
        }
        const pct = Math.round(d.current / d.total * 100);
        document.getElementById('progress-bar').style.width = pct + '%';
        document.getElementById('progress-text').textContent = '处理中 ' + d.current + ' / ' + d.total + '（' + pct + '%）';
        document.getElementById('progress-detail').textContent = '速度 ' + d.rate + ' 首/分钟 | 预计剩余 ' + Math.floor(d.eta/60) + '分' + (d.eta%60) + '秒';
        document.getElementById('current-poem').textContent = '当前：' + d.no + ' 《' + d.title + '》 ' + (d.success ? '✅' : '❌');

        const tbody = document.querySelector('#results-table tbody');
        const row = tbody.querySelector('tr[data-no="' + d.no + '"]');
        if (!row) {
            tbody.insertAdjacentHTML('beforeend', '<tr data-no="' + d.no + '"><td>' + d.no + '</td><td>' + escHtml(d.title) + '</td><td></td><td>' + (d.success?'✅':'❌') + '</td></tr>');
        } else {
            row.cells[3].textContent = d.success ? '✅' : '❌';
        }
    };

    evtSource.onerror = function() { evtSource.close(); btn.disabled = false; btn.textContent = '重新运行'; };
}

// ─── Template Operations ─────────────────────────────────────────────

function saveAsTemplate() {
    const name = document.getElementById('template-name').value.trim();
    if (!name) { toast('请输入模板名称', false); return; }
    if (!headers.length) { toast('请先定义表头', false); return; }
    fetch('/api/save-template', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name, data: { headers, saved_at: new Date().toISOString() } })
    }).then(r => r.json()).then(d => {
        if (d.ok) {
            toast('模板已保存');
            const sel = document.getElementById('template-select');
            if (![...sel.options].find(o => o.value === name)) {
                const o = document.createElement('option'); o.value = name; o.textContent = name; sel.appendChild(o);
            }
        } else toast(d.error, false);
    });
}

function loadTemplate(name) {
    if (!name) return;
    fetch('/api/load-template/' + encodeURIComponent(name)).then(r => r.json()).then(d => {
        if (d.ok && d.data.headers) { headers = d.data.headers; renderHeaders(); updateDesignBtn(); toast('模板已加载：' + name); }
    });
}
