#!/usr/bin/env python3
"""来場者の YAML が、AppProject では防げない展示のルールを守っているか確かめる"""
import re
import sys
from pathlib import Path

import yaml

DOMAIN = "showcase.cloudnativedays.jp"
TIERS = ("apps", "cluster-apps")
# namespace は app-<名前> になるので、DNS ラベルの 63 文字から prefix 分を引く
NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]{0,57}[a-z0-9])?$")
# 運営が入れるもの。来場者が書くと乗っ取りや同期エラーになる
FORBIDDEN_KINDS = {"Namespace", "ResourceQuota", "LimitRange", "CiliumNetworkPolicy", "TracingPolicyNamespaced"}
# 手で書くと、Gateway の Envoy をノードや内部ネットワークへの踏み台にできる
ENDPOINT_KINDS = {"Endpoints", "EndpointSlice"}
WEBHOOK_KINDS = {"ValidatingWebhookConfiguration", "MutatingWebhookConfiguration"}
# クラスタと運営が使う API group。同じ名前の CRD で上書きされると、消したときに全員のリソースが消える
BUILTIN_ROLES = {"cluster-admin", "admin", "edit", "view"}
SYSTEM_GROUPS = ("k8s.io", "argoproj.io", "cilium.io", "cattle.io")
# AppProject で拒否されると、マージした後の同期で初めて分かる。PR の時点で知らせる
# oss-showcase-platform の argocd/project.yaml の showcase と揃える
APP_KINDS = {
    ("", "Service"), ("", "ConfigMap"), ("", "Secret"), ("", "ServiceAccount"), ("", "PersistentVolumeClaim"),
    ("apps", "Deployment"), ("apps", "StatefulSet"), ("batch", "Job"), ("batch", "CronJob"),
    ("autoscaling", "HorizontalPodAutoscaler"), ("policy", "PodDisruptionBudget"),
    ("rbac.authorization.k8s.io", "Role"), ("rbac.authorization.k8s.io", "RoleBinding"),
    ("gateway.networking.k8s.io", "HTTPRoute"), ("postgresql.cnpg.io", "Cluster"),
}


def keys(obj, key):
    """入れ子のどこかにある key の値を集める。Pod のテンプレートは種類ごとに場所が違う"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from keys(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys(v, key)


def check(root: Path) -> list[str]:
    errors = []
    owner = {}
    crds = {}
    for tier in TIERS:
        if not (root / tier).is_dir():
            continue
        for app in sorted(p for p in (root / tier).iterdir() if p.is_dir()):
            name = app.name
            if not NAME_RE.match(name):
                errors.append(f"{tier}/{name}: ディレクトリ名には、英小文字、数字、ハイフンを 59 文字まで使えます")
            if name in owner:
                errors.append(f"{tier}/{name}: {owner[name]}/{name} と同じ名前です。別の名前にしてください")
            owner.setdefault(name, tier)

            for f in sorted(app.rglob("*.y*ml")):
                path = f.relative_to(root)
                if f.parent != app:
                    errors.append(f"{path}: サブディレクトリの YAML はデプロイされません。{tier}/{name}/ の直下に移してください")
                    continue
                try:
                    docs = [d for d in yaml.safe_load_all(f.read_text()) if d]
                except yaml.YAMLError as e:
                    errors.append(f"{path}: YAML として読めませんでした。インデントや記号を確かめてください: {e}")
                    continue
                for doc in docs:
                    kind = doc.get("kind")
                    where = f"{path}: {kind}/{doc.get('metadata', {}).get('name')}"
                    spec = doc.get("spec") or {}

                    ns = doc.get("metadata", {}).get("namespace")
                    if ns not in (None, f"app-{name}"):
                        errors.append(f"{where}: namespace が {ns} になっています。消すか、app-{name} にしてください")
                    # Argo CD は List の items を展開するので、中身をこのチェックに通せない
                    if str(kind).endswith("List"):
                        errors.append(f"{where}: {kind} はそのままでは読めません。中のリソースを 1 つずつ書いてください")
                    if kind in FORBIDDEN_KINDS:
                        errors.append(f"{where}: {kind} は運営が用意するので、書かなくて大丈夫です。消してください")
                    elif kind == "Ingress":
                        errors.append(f"{where}: Ingress は使えません。外への公開には、apps/example/ と同じ HTTPRoute を使ってください")
                    elif kind == "NetworkPolicy":
                        errors.append(f"{where}: NetworkPolicy は使えません。アプリ同士の通信は運営のポリシーで分けているので、消してください")
                    elif kind in ENDPOINT_KINDS:
                        errors.append(f"{where}: {kind} は Kubernetes が自動で作るので、消してください。Service の selector で Pod を選べば作られます")
                    elif tier == "apps" and (str(doc.get("apiVersion", "")).rpartition("/")[0], kind) not in APP_KINDS:
                        errors.append(f"{where}: {kind} は apps/ では使えません。使える種類は docs/rules.md の「使えるリソース」にあります")
                    if kind == "HTTPRoute":
                        if not spec.get("hostnames"):
                            errors.append(f"{where}: HTTPRoute の hostnames に {name}.{DOMAIN} を書いてください")
                        for host in spec.get("hostnames") or []:
                            if host != f"{name}.{DOMAIN}":
                                errors.append(f"{where}: hostnames が {host} になっています。{name}.{DOMAIN} にしてください")
                    role = doc.get("roleRef", {}).get("name", "")
                    if kind in ("RoleBinding", "ClusterRoleBinding") and (role in ("cluster-admin", "admin", "edit") or role.startswith("system:")):
                        errors.append(f"{where}: {role} は権限が広すぎるので bind できません。必要な権限だけの Role を作ってください")
                    if kind in ("ClusterRole", "ClusterRoleBinding") and (doc["metadata"]["name"] in BUILTIN_ROLES or doc["metadata"]["name"].startswith("system:")):
                        errors.append(f"{where}: 組み込みの ClusterRole と同じ名前です。OSS の名前を付けた別の名前にしてください")
                    if kind in ("Role", "ClusterRole"):
                        for rule in doc.get("rules") or []:
                            groups = set(rule.get("apiGroups") or [])
                            if groups & {"*", "cilium.io"}:
                                errors.append(f"{where}: apiGroups に * と cilium.io は使えません。必要な API group だけを書いてください")
                            if "rbac.authorization.k8s.io" in groups and not set(rule.get("resources") or []) <= {"roles", "rolebindings"}:
                                errors.append(f"{where}: rbac.authorization.k8s.io で使えるのは roles と rolebindings だけです")
                            if set(rule.get("verbs") or []) & {"escalate", "bind", "impersonate"}:
                                errors.append(f"{where}: verbs の escalate、bind、impersonate は使えません")
                        labels = doc.get("metadata", {}).get("labels") or {}
                        core = any(set(r.get("apiGroups") or []) & {"", "rbac.authorization.k8s.io"} for r in doc.get("rules") or [])
                        if core and any(k.startswith("rbac.authorization.k8s.io/aggregate-to-") for k in labels):
                            errors.append(f"{where}: core と RBAC の API group は、組み込みの ClusterRole に aggregate できません")
                        for sel in (doc.get("aggregationRule") or {}).get("clusterRoleSelectors") or []:
                            if any(k.startswith(("rbac.authorization.k8s.io/", "kubernetes.io/")) for k in sel.get("matchLabels") or {}):
                                errors.append(f"{where}: 組み込みの ClusterRole は aggregate できません")
                    if any(isinstance(v, str) and v for v in keys(spec, "priorityClassName")):
                        errors.append(f"{where}: priorityClassName は使えません。消してください")
                    if kind == "Service" and spec.get("externalIPs"):
                        errors.append(f"{where}: externalIPs は使えません。外への公開は HTTPRoute でできます")
                    if kind == "Service" and spec.get("type") == "ExternalName":
                        errors.append(f"{where}: type: ExternalName は使えません")
                    if kind in WEBHOOK_KINDS:
                        for hook in doc.get("webhooks") or []:
                            if hook.get("failurePolicy") != "Ignore":
                                errors.append(f"{where}: failurePolicy を Ignore にしてください。webhook が落ちたときに、ほかの人のデプロイまで止まらないようにするためです")
                    if kind == "CustomResourceDefinition":
                        crd = doc["metadata"]["name"]
                        group = spec.get("group", "")
                        if any(group == g or group.endswith("." + g) for g in SYSTEM_GROUPS):
                            errors.append(f"{where}: {group} はクラスタが使う API group なので、この CRD は作れません")
                        if crd in crds and crds[crd] != name:
                            errors.append(f"{where}: この CRD は {crds[crd]} がすでに入れています。同じ CRD は 1 か所にまとめてください")
                        crds.setdefault(crd, name)
    return errors


if __name__ == "__main__":
    errors = check(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    for e in errors:
        print(f"::error::{e}")
    if errors:
        print(f"\n直してほしいところが {len(errors)} か所あります。ルールは docs/rules.md にまとめています。")
        print("分からないときは、そのまま Pull Request を出して相談してください。スタッフが一緒に見ます。")
    else:
        print("ok: 展示のルールを満たしています。Pull Request を出してください")
    sys.exit(1 if errors else 0)
