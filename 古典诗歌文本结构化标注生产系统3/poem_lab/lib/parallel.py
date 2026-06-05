# -*- coding: utf-8 -*-
"""Parallel batch runner — ThreadPoolExecutor + checkpoint + SSE feed."""
import json, queue, threading, time, uuid

from .llm_client import call_llm
from . import persistence, config_loader


def run_batch_parallel(rid: str, poems: list, generated_prompt: str, column_mapping: list):
    """Run batch processing with parallel workers. Yields SSE event strings."""
    MAX_WORKERS = int(config_loader.get("BATCH_WORKERS", 5))
    CHECKPOINT_EVERY = int(config_loader.get("CHECKPOINT_EVERY", 5))

    total = len(poems)
    done_nos = persistence.get_completed_nos(rid)

    # Filter out already-completed poems (resume)
    pending = [p for p in poems if p.get("编号", "") not in done_nos]
    already_done = total - len(pending)

    if already_done > 0:
        # Re-emit progress for already done
        completed, failed = persistence.update_batch_progress(rid)
        yield f"data: {json.dumps({'resumed': True, 'already_done': already_done, 'current': completed + failed, 'total': total, 'success_count': completed, 'fail_count': failed}, ensure_ascii=False)}\n\n"
        if completed + failed >= total:
            yield f"data: {json.dumps({'done': True, 'total': total, 'success_count': completed}, ensure_ascii=False)}\n\n"
            return

    result_queue = queue.Queue()
    start_time = time.time()
    lock = threading.Lock()
    stats = {"completed": already_done, "failed": 0, "next_checkpoint": already_done + CHECKPOINT_EVERY}

    run_info = persistence.get_batch_run(rid)
    worker_sid = run_info.get("session_id", "") if run_info else ""
    model_name = config_loader.get("MODEL_NAME") or "unknown"

    def worker(poem):
        user_prompt = f"诗歌编号：{poem['编号']}\n标题：《{poem['标题']}》\n作者：{poem['作者']}\n原文：{poem['原文']}"
        parsed, raw_text = call_llm(generated_prompt, user_prompt, return_raw=True)
        if worker_sid:
            persistence.save_conversation(
                worker_sid, poem, generated_prompt, user_prompt, raw_text, parsed, model_name,
                len(raw_text) if raw_text else 0
            )
        with lock:
            if parsed:
                stats["completed"] += 1
            else:
                stats["failed"] += 1
            persistence.save_batch_result(rid, poem, parsed)
            current_total = stats["completed"] + stats["failed"]

            # Checkpoint every N poems
            if current_total >= stats["next_checkpoint"]:
                persistence.update_batch_progress(rid)
                stats["next_checkpoint"] = current_total + CHECKPOINT_EVERY

            elapsed = time.time() - start_time
            rate = current_total / elapsed if elapsed > 0 else 0
            eta = int((total - current_total) / rate) if rate > 0 else 0

        result_queue.put({
            "current": current_total, "total": total,
            "no": poem.get("编号", ""), "title": poem.get("标题", ""),
            "success": parsed is not None,
            "rate": round(rate, 1), "eta": eta,
            "thread": threading.current_thread().name
        })

    # Submit all pending poems
    with threading.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(worker, p) for p in pending]

        # Stream results as they complete
        done_count = 0
        while done_count < len(pending):
            try:
                evt = result_queue.get(timeout=30)
                done_count += 1
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            except queue.Empty:
                # Heartbeat — check if threads are still alive
                pass

        # Final progress update
        completed, failed = persistence.update_batch_progress(rid)
        yield f"data: {json.dumps({'done': True, 'total': total, 'success_count': completed, 'fail_count': failed}, ensure_ascii=False)}\n\n"
