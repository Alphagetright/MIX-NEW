# -*- coding: utf-8 -*-
"""Tests for persistence layer — CRUD, concurrent writes, checkpoint/resume."""
import sys, os, threading, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

import persistence


def setup():
    """Ensure clean state before each test."""
    pass


def teardown():
    """Clean DB after all tests."""
    try:
        persistence._conn().close()
    except Exception:
        pass
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state.db")
    if os.path.exists(db_path):
        os.remove(db_path)


def test_create_session():
    sid = persistence.create_session("test")
    assert len(sid) == 12
    s = persistence.get_session(sid)
    assert s is not None
    assert s["name"] == "test"


def test_list_sessions():
    sid1 = persistence.create_session("test1")
    sid2 = persistence.create_session("test2")
    sessions = persistence.list_sessions()
    assert len(sessions) >= 2


def test_save_and_get_poems():
    sid = persistence.create_session("poem-test")
    poems = [
        {"编号": "P001", "标题": "静夜思", "作者": "李白", "朝代": "唐", "原文": "床前明月光"},
        {"编号": "P002", "标题": "春望", "作者": "杜甫", "朝代": "唐", "原文": "国破山河在"}
    ]
    persistence.save_poems(sid, poems)
    assert persistence.get_poem_count(sid) == 2
    result = persistence.get_poems(sid)
    assert result[0]["标题"] == "静夜思"


def test_overwrite_poems():
    sid = persistence.create_session("overwrite-test")
    persistence.save_poems(sid, [{"编号": "P001", "标题": "A", "作者": "", "朝代": "", "原文": "text"}])
    persistence.save_poems(sid, [{"编号": "P002", "标题": "B", "作者": "", "朝代": "", "原文": "text"}])
    assert persistence.get_poem_count(sid) == 1


def test_schema_snapshots():
    sid = persistence.create_session("schema-test")
    persistence.save_schema(sid, "parsed_headers", {"headers": [{"name": "test"}]})
    s = persistence.get_schema(sid, "parsed_headers")
    assert s == {"headers": [{"name": "test"}]}


def test_schema_overwrite():
    sid = persistence.create_session("schema-overwrite")
    persistence.save_schema(sid, "stage1", {"v": 1})
    persistence.save_schema(sid, "stage1", {"v": 2})
    s = persistence.get_schema(sid, "stage1")
    assert s == {"v": 2}


def test_batch_run_flow():
    sid = persistence.create_session("batch-test")
    persistence.save_poems(sid, [
        {"编号": "P001", "标题": "A", "作者": "X", "朝代": "唐", "原文": "content1"},
        {"编号": "P002", "标题": "B", "作者": "Y", "朝代": "宋", "原文": "content2"},
    ])
    cm = [{"header": "result", "field": "output"}]
    rid = persistence.create_batch_run(sid, "test-prompt", cm, 2)

    persistence.save_batch_result(rid, {"编号": "P001", "标题": "A"}, {"output": "ok1"})
    persistence.save_batch_result(rid, {"编号": "P002", "标题": "B"}, None)

    completed, failed = persistence.update_batch_progress(rid)
    assert completed == 1
    assert failed == 1

    run = persistence.get_batch_run(rid)
    assert run is not None
    assert run["total"] == 2
    assert run["completed"] == 1

    results = persistence.get_batch_results(rid)
    assert len(results) == 2


def test_get_completed_nos():
    sid = persistence.create_session("checkpoint-test")
    persistence.save_poems(sid, [
        {"编号": "P001", "标题": "A", "原文": "content"},
        {"编号": "P002", "标题": "B", "原文": "content"},
    ])
    rid = persistence.create_batch_run(sid, "prompt", [], 2)
    persistence.save_batch_result(rid, {"编号": "P001"}, {"r": 1})
    done = persistence.get_completed_nos(rid)
    assert done == {"P001"}


def test_concurrent_writes():
    sid = persistence.create_session("concurrent-test")
    errors = []

    def write_poem(i):
        try:
            persistence.save_poems(sid, [{"编号": f"P{i:03d}", "标题": f"Poem_{i}", "作者": "", "朝代": "", "原文": f"content_{i}"}])
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=write_poem, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_export_paths():
    sid = persistence.create_session("export-test")
    rid = persistence.create_batch_run(sid, "prompt", [], 1)
    persistence.set_run_export_paths(rid, "test.csv", "test.json")
    run = persistence.get_batch_run(rid)
    assert run["csv_path"] == "test.csv"
    assert run["json_path"] == "test.json"


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
