/* 数据看板 — 统计与历史记录 */
(function() {

function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function loadStats() {
    fetch('/api/sessions').then(r => r.json()).then(d => {
        if (d.ok) {
            document.getElementById('stat-sessions').textContent = d.sessions.length;
        }
    });

    fetch('/api/batch-runs').then(r => r.json()).then(d => {
        if (d.ok && d.runs) {
            const runs = d.runs;
            document.getElementById('stat-batches').textContent = runs.length;

            if (runs.length > 0) {
                const totalRate = runs.reduce((s, r) => s + (r.total > 0 ? r.completed / r.total * 100 : 0), 0);
                const avgRate = Math.round(totalRate / runs.length);
                document.getElementById('stat-completion').textContent = avgRate + '%';
                document.getElementById('stat-success').textContent = avgRate + '%';
                document.getElementById('stat-quality').textContent = avgRate >= 80 ? '良好' : avgRate >= 60 ? '一般' : '待改进';
            }
        }
    });

    fetch('/api/list-exports').then(r => r.json()).then(d => {
        if (d.ok && d.exports) {
            document.getElementById('export-list').innerHTML = d.exports.length === 0
                ? '<p class="empty-cell">暂无导出文件</p>'
                : '<div class="table-wrap"><table class="data-table"><thead><tr><th>文件名</th><th>大小</th><th>修改时间</th><th>下载</th></tr></thead><tbody>' +
                  d.exports.map(f => '<tr><td>' + escHtml(f.name) + '</td><td>' + (f.size / 1024).toFixed(1) + ' KB</td><td>' + f.mtime + '</td><td>' +
                      (f.name.endsWith('.csv')
                          ? '<a href="/api/export/csv/' + f.name + '" class="btn btn-sm">CSV</a>'
                          : '<a href="/api/export/json/' + f.name + '" class="btn btn-sm">JSON</a>')
                      + '</td></tr>').join('') +
                  '</tbody></table></div>';
        }
    });
}

function loadBatchHistory() {
    fetch('/api/batch-runs').then(r => r.json()).then(d => {
        const tbody = document.getElementById('batch-history-body');
        if (!d.ok || !d.runs || d.runs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-cell">暂无批处理记录</td></tr>';
            return;
        }
        tbody.innerHTML = d.runs.map(r => {
            const rate = r.total > 0 ? Math.round(r.completed / r.total * 100) : 0;
            const statusCn = {'running': '运行中', 'completed': '已完成', 'failed': '失败'}[r.status] || r.status;
            const statusColor = r.status === 'completed' ? 'green' : r.status === 'running' ? '#b39c3a' : '#b33a3a';
            return '<tr><td><code>' + r.id + '</code></td>' +
                '<td>' + (r.started_at || '-') + '</td>' +
                '<td>' + r.total + '</td>' +
                '<td>' + r.completed + '</td>' +
                '<td>' + r.failed + '</td>' +
                '<td>' + rate + '%</td>' +
                '<td style="color:' + statusColor + '">' + statusCn + '</td>' +
                '<td>' + (r.csv_path ? '<a href="/api/export/csv/' + r.csv_path + '" class="btn btn-sm">CSV</a>' : '-') + '</td></tr>';
        }).join('');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadBatchHistory();
});

})();
