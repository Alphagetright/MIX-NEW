/* 古典诗歌文本结构化标注生产系统 — 批量运行 SSE 进度 */

// 此文件为备用，主要逻辑内嵌在 run.html 中
// 如需更复杂的进度可视化，可在此扩展

class BatchRunner {
    constructor() {
        this.eventSource = null;
        this.onProgress = null;
        this.onDone = null;
        this.onError = null;
    }

    start() {
        this.eventSource = new EventSource('/api/batch-run');

        this.eventSource.onmessage = (e) => {
            const d = JSON.parse(e.data);
            if (d.error) {
                if (this.onError) this.onError(d.error);
                this.stop();
                return;
            }
            if (d.done) {
                if (this.onDone) this.onDone(d);
                this.stop();
                return;
            }
            if (this.onProgress) this.onProgress(d);
        };

        this.eventSource.onerror = () => {
            this.stop();
            if (this.onError) this.onError('连接中断');
        };
    }

    stop() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// 暴露到全局
window.BatchRunner = BatchRunner;
