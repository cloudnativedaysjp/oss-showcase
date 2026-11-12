#!/usr/bin/env python3
"""Cluster API と cert-manager のリリースのマニフェストを、展示のルールに合わせて cluster-apps/ に書き出す

使い方: python scripts/render_cluster_api.py <ダウンロードしたディレクトリ>
"""
import re
import sys
from pathlib import Path

import yaml

CAPI_NS = "app-cluster-api"
CM_NS = "app-cert-manager"
CAPI_OLD_NS = ["capi-kubeadm-control-plane-system", "capi-kubeadm-bootstrap-system", "capi-system", "capd-system"]
# ClusterClass は topology の機能を使う。下の 5 つはデモの Cluster の値
VARS = {
    "CLUSTER_TOPOLOGY": "true",
    "NAMESPACE": CAPI_NS,
    "CLUSTER_NAME": "demo",
    "KUBERNETES_VERSION": "v1.34.1",
    "CONTROL_PLANE_MACHINE_COUNT": "1",
    "WORKER_MACHINE_COUNT": "2",
}
WEBHOOKS = {"MutatingWebhookConfiguration", "ValidatingWebhookConfiguration"}
CLUSTER_SCOPED = WEBHOOKS | {"CustomResourceDefinition", "ClusterRole", "ClusterRoleBinding"}
# 別のアプリの cert-manager の CRD を使うので、CRD がまだなくても同期を止めない
SKIP_DRY_RUN = {"Certificate", "Issuer"}


def substitute(text: str) -> str:
    return re.sub(r"\$\{([A-Z_]+)(?::=([^}]*))?\}", lambda m: VARS.get(m.group(1)) or m.group(2).strip('"'), text)


def common(doc: dict) -> dict:
    if doc["kind"] in WEBHOOKS:
        for hook in doc.get("webhooks") or []:
            hook["failurePolicy"] = "Ignore"
    if doc["kind"] == "Deployment":
        for c in doc["spec"]["template"]["spec"]["containers"]:
            c.setdefault("resources", {}).setdefault("limits", {"memory": "512Mi"})
    return doc


def capi(text: str) -> list[dict]:
    for ns in CAPI_OLD_NS:
        text = text.replace(ns, CAPI_NS)
    docs = []
    for doc in yaml.safe_load_all(substitute(text)):
        if not doc or doc["kind"] == "Namespace":
            continue
        if doc["kind"] not in CLUSTER_SCOPED:
            doc["metadata"]["namespace"] = CAPI_NS
        if doc["kind"] in SKIP_DRY_RUN:
            doc["metadata"].setdefault("annotations", {})["argocd.argoproj.io/sync-options"] = "SkipDryRunOnMissingResource=true"
        if doc["kind"] == "Deployment" and doc["metadata"]["name"] == "capd-controller-manager":
            # in-memory の backend だけを使うので、Docker のソケットと特権は外す
            spec = doc["spec"]["template"]["spec"]
            spec["volumes"] = [v for v in spec.get("volumes", []) if "hostPath" not in v]
            names = {v["name"] for v in spec["volumes"]}
            for c in spec["containers"]:
                c["volumeMounts"] = [m for m in c.get("volumeMounts", []) if m["name"] in names]
                c.get("securityContext", {}).pop("privileged", None)
        docs.append(common(doc))
    return docs


def cert_manager(text: str) -> list[dict]:
    docs = []
    for doc in yaml.safe_load_all(text):
        if not doc or doc["kind"] == "Namespace":
            continue
        meta = doc["metadata"]
        if meta.get("namespace") in ("cert-manager", "kube-system"):
            meta["namespace"] = CM_NS
        for s in doc.get("subjects") or []:
            if s.get("namespace") == "cert-manager":
                s["namespace"] = CM_NS
        ann = meta.get("annotations") or {}
        for k, v in ann.items():
            if k.startswith("cert-manager.io/inject-ca-from"):
                ann[k] = v.replace("cert-manager/", f"{CM_NS}/", 1)
        for hook in doc.get("webhooks") or []:
            svc = hook.get("clientConfig", {}).get("service")
            if svc:
                svc["namespace"] = CM_NS
        if doc["kind"] == "Deployment" and meta["name"] in ("cert-manager", "cert-manager-cainjector"):
            for c in doc["spec"]["template"]["spec"]["containers"]:
                c["args"] = [a for a in c["args"] if not a.startswith("--leader-election-namespace")]
                c["args"].append("--leader-election-namespace=$(POD_NAMESPACE)")
        docs.append(common(doc))
    return docs


def write(path: Path, docs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "# scripts/render_cluster_api.py で生成する。手で書き換えない\n"
    path.write_text(header + yaml.safe_dump_all(docs, sort_keys=False, width=1000))


if __name__ == "__main__":
    src = Path(sys.argv[1])
    root = Path(__file__).resolve().parent.parent
    write(root / "cluster-apps/cert-manager/cert-manager.yaml", cert_manager((src / "cert-manager.yaml").read_text()))
    write(root / "cluster-apps/cluster-api/core.yaml", capi((src / "cluster-api-components.yaml").read_text()))
    write(root / "cluster-apps/cluster-api/capd.yaml", capi((src / "infrastructure-components-development.yaml").read_text()))
    demo = (src / "clusterclass-in-memory.yaml").read_text() + "\n---\n" + (src / "cluster-template-in-memory.yaml").read_text()
    write(root / "cluster-apps/cluster-api/demo.yaml", capi(demo))
