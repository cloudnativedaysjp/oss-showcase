#!/usr/bin/env python3
"""cluster-apps/portal/server.py の、一覧の覚え方と HTML のエスケープを確かめる"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("portal", Path(__file__).parent.parent / "cluster-apps/portal/server.py")
portal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portal)

calls = []


def fake(result):
    def fetch():
        calls.append(1)
        if isinstance(result, Exception):
            raise result
        return result
    portal.fetch_hosts = fetch


# 一度も読めていないときは例外にする
fake(OSError("api down"))
try:
    portal.hosts()
    raise AssertionError("一度も読めていないのに例外にならない")
except OSError:
    pass

# 読めたら、その一覧を返す
portal._cache["at"] = float("-inf")
fake(["a.showcase.cloudnativedays.jp"])
assert portal.hosts() == ["a.showcase.cloudnativedays.jp"]

# API が落ちても、前の一覧を返す。TTL の間は API を叩き直さない
portal._cache["at"] = float("-inf")
fake(OSError("api down"))
calls.clear()
assert portal.hosts() == ["a.showcase.cloudnativedays.jp"]
assert portal.hosts() == ["a.showcase.cloudnativedays.jp"]
assert len(calls) == 1, calls

# 名前は HTML としてエスケープする
out = portal.page(['"><script>x</script>.showcase.cloudnativedays.jp'])
assert "<script>x" not in out and "&lt;script&gt;" in out

# キーノートの時間だけ、キーノートのアプリを先頭に、キーノートの見た目で並べる
apps = ["a.showcase.cloudnativedays.jp", "sanposhiho.showcase.cloudnativedays.jp"]
out = portal.page(apps, now=portal.KEYNOTE_FROM)
assert out.index("sanposhiho.") < out.index("a.showcase") and 'class="hex keynote"' in out and portal.KEYNOTE_SPEAKER in out
for t in (portal.KEYNOTE_FROM - portal.datetime.timedelta(minutes=1), portal.KEYNOTE_TO):
    out = portal.page(apps, now=t)
    assert out.index("a.showcase") < out.index("sanposhiho.") and 'class="hex keynote"' not in out, t
# 一覧の読み直しでも、?at=keynote を付けたまま取りにいく
assert "location.pathname + location.search" in portal.page([])
print("ok")
