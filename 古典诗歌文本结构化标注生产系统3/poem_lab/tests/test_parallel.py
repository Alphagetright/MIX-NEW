# -*- coding: utf-8 -*-
"""Tests for parallel batch runner — threading, checkpoint, SSE format."""
import sys, os, json, queue, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

import persistence


def test_checkpoint_resume():
    """Verify that completed poems are skipped on resume."""
    sid = persistence.create_session("resume-test")
    poems = [
        {"编号": "P001", "标题": "A", "作者": "X", "朝代": "", "原文": "content1"},
        {"编号": "P002", "标题": "B", "作者": "Y", "朝代": "", "原文": "content2"},
        {"编号": "P003", "标题": "C", "作者": "Z", "朝代": "", "原文": "content3"},
    ]
    persistence.save_poems(sid, poems)

    cm = [{"header": "结果", "field": "result"}]
    rid = persistence.create_batch_run(sid, "test prompt", cm, 3)

    # Simulate partial completion
    persistence.save_batch_result(rid, poems[0], {"result": "done1"})
    persistence.save_batch_result(rid, poems[2], {"result": "done3"})
    persistence.update_batch_progress(rid)

    # Check completed_nos
    done = persistence.get_completed_nos(rid)
    assert done == {"P001", "P003"}

    # Only P002 should be pending
    pending = [p for p in poems if p["编号"] not in done]
    assert len(pending) == 1
    assert pending[0]["编号"] == "P002"

    print("  [OK] Checkpoint resume: P002 is the only pending poem")


def test_batch_run_completes():
    sid = persistence.create_session("complete-test")
    poems = [{"编号": f"P{i+1:03d}", "标题": f"Poem_{i}", "作者": "X", "朝代": "", "原文": f"text_{i}"} for i in range(3)]
    persistence.save_poems(sid, poems)

    rid = persistence.create_batch_run(sid, "prompt", [], 3)
    for p in poems:
        persistence.save_batch_result(rid, p, {"result": f"ok_{p['编号']}"})
    completed, failed = persistence.update_batch_progress(rid)

    assert completed == 3
    assert failed == 0

    run = persistence.get_batch_run(rid)
    assert run["status"] == "completed"


def test_sse_event_format():
    """Verify SSE event JSON format is parseable."""
    event = {"current": 5, "total": 100, "no": "P005", "title": "静夜思", "success": True, "rate": 3.5, "eta": 27}
    sse_line = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    assert sse_line.startswith("data: ")
    # Parse back
    parsed = json.loads(sse_line[6:].strip())
    assert parsed["current"] == 5
    assert parsed["total"] == 100


def test_sse_progress_stream():
    """Verify SSE stream can be parsed line by line."""
    events = [
        'data: {"current":1,"total":3,"no":"P001","title":"A","success":true,"rate":1.0,"eta":2}\n\n',
        'data: {"current":2,"total":3,"no":"P002","title":"B","success":true,"rate":2.0,"eta":1}\n\n',
        'data: {"done":true,"total":3,"success_count":3,"fail_count":0}\n\n',
    ]
    parsed_events = []
    for line in events:
        if line.startswith("data: "):
            parsed_events.append(json.loads(line[6:].strip()))

    assert parsed_events[0]["current"] == 1
    assert parsed_events[-1]["done"] is True
    assert parsed_events[-1]["success_count"] == 3


def test_batch_run_partial_failure():
    sid = persistence.create_session("partial-test")
    poems = [{"编号": f"P{i+1:03d}", "标题": f"P{i}", "作者": "", "朝代": "", "原文": "t"} for i in range(5)]
    persistence.save_poems(sid, poems)

    rid = persistence.create_batch_run(sid, "prompt", [], 5)
    success_indices = [0, 1, 3]
    for i in range(5):
        if i in success_indices:
            persistence.save_batch_result(rid, poems[i], {"result": f"ok_{i}"})
        else:
            persistence.save_batch_result(rid, poems[i], None)

    completed, failed = persistence.update_batch_progress(rid)
    assert completed == 3
    assert failed == 2

    run = persistence.get_batch_run(rid)
    assert run["status"] == "completed"


def teardown():
    try:
        persistence._conn().close()
    except Exception:
        pass
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state.db")
    if os.path.exists(db_path):
        os.remove(db_path)


def run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {e}")
    print(f"\n  {passed} passed, {failed} failed, {len(tests)} total")
    teardown()
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
