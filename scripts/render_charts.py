#!/usr/bin/env python3
"""charts/<名前>/helm.yaml を、Argo CD と同じ条件で .rendered/charts/<名前>.yaml に描画する

check.py と kubeconform に、チャートの中身を確かめさせるために使う。helm が要る。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

root = Path(__file__).resolve().parent.parent
out = root / ".rendered/charts"
out.mkdir(parents=True, exist_ok=True)
failed = False
for helm in sorted(root.glob("charts/*/helm.yaml")):
    name = helm.parent.name
    spec = yaml.safe_load(helm.read_text()) or {}
    with tempfile.NamedTemporaryFile("w", suffix=".yaml") as values:
        values.write(spec.get("values") or "")
        values.flush()
        cmd = ["helm", "template", name, spec["chart"], "--repo", spec["repoURL"], "--version", spec["version"],
               "--namespace", f"app-{name}", "--include-crds", "--skip-tests", "-f", values.name]
        result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"::error::charts/{name}: helm template に失敗しました: {result.stderr.strip()}")
        failed = True
        continue
    (out / f"{name}.yaml").write_text(result.stdout)
    print(f"charts/{name}: {spec['chart']} {spec['version']} を描画しました")
sys.exit(1 if failed else 0)
