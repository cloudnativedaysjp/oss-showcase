#!/usr/bin/env python3
"""CloudNativePG のリリースのマニフェストを、展示のルールに合わせて cluster-apps/cnpg/ に書き出す

使い方: python scripts/render_cnpg.py <ダウンロードした cnpg-<版>.yaml>
"""
import sys
from pathlib import Path

import yaml

NS = "app-cnpg"


def render(text: str) -> list[dict]:
    docs = []
    for doc in yaml.safe_load_all(text.replace("cnpg-system", NS)):
        if not doc or doc["kind"] == "Namespace":
            continue
        for hook in doc.get("webhooks") or []:
            hook["failurePolicy"] = "Ignore"
        # Application を消しても CRD は残す。消すと来場者の PostgreSQL も一緒に消える
        if doc["kind"] == "CustomResourceDefinition":
            doc["metadata"].setdefault("annotations", {})["argocd.argoproj.io/sync-options"] = "Delete=false"
        docs.append(doc)
    return docs


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "cluster-apps/cnpg/cnpg.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# scripts/render_cnpg.py で生成する。手で書き換えない\n" + yaml.safe_dump_all(render(Path(sys.argv[1]).read_text()), sort_keys=False, width=1000))
