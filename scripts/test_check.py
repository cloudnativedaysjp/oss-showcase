#!/usr/bin/env python3
import tempfile
from pathlib import Path

from check import check

BAD = {
    "apps/foo/app.yaml": """
kind: HTTPRoute
metadata: {name: foo}
spec: {hostnames: [bar.showcase.cloudnativedays.jp]}
---
kind: Namespace
metadata: {name: kube-system}
""",
    "cluster-apps/foo/crb.yaml": """
kind: ClusterRoleBinding
metadata: {name: foo}
roleRef: {name: cluster-admin}
---
kind: ValidatingWebhookConfiguration
metadata: {name: foo}
webhooks: [{name: a}]
---
kind: CustomResourceDefinition
metadata: {name: widgets.example.com}
""",
    "cluster-apps/baz/crd.yaml": """
kind: CustomResourceDefinition
metadata: {name: widgets.example.com}
""",
    "apps/qux/app.yaml": """
kind: Secret
metadata: {name: x, namespace: app-foo}
---
kind: List
metadata: {name: x}
items: []
""",
    "cluster-apps/gw/crd.yaml": """
kind: CustomResourceDefinition
metadata: {name: httproutes.gateway.networking.k8s.io}
spec: {group: gateway.networking.k8s.io}
""",
    "apps/rbac/app.yaml": """
kind: RoleBinding
metadata: {name: x}
roleRef: {name: admin}
---
kind: Role
metadata: {name: x}
rules: [{apiGroups: [cilium.io], resources: ["*"], verbs: ["*"]}]
---
kind: Role
metadata: {name: y}
rules: [{apiGroups: [rbac.authorization.k8s.io], resources: [clusterrolebindings], verbs: [create]}]
---
kind: Service
metadata: {name: x}
spec: {externalIPs: [1.2.3.4]}
---
kind: Service
metadata: {name: y}
spec: {type: ExternalName, externalName: metadata.google.internal}
""",
    "cluster-apps/sys/role.yaml": """
kind: ClusterRole
metadata: {name: "system:basic-user"}
rules: []
""",
    "apps/hook/app.yaml": """
kind: Pod
metadata: {name: test-connection}
---
kind: NetworkPolicy
metadata: {name: allow-all}
""",
    "apps/Bad_Name/app.yaml": "kind: ConfigMap\nmetadata: {name: x}\n",
}

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    for path, body in BAD.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(body)
    errors = "\n".join(check(root))
    for want in ["hostnames", "Namespace", "名前が重なっている", "cluster-admin", "failurePolicy", "CRD が重なっている", "ディレクトリ名", "namespace は", "List は使えない", "API group", "admin には bind", "cilium.io", "externalIPs", "ExternalName は", "同じ名前", "roles と rolebindings だけ", "Pod は apps/", "NetworkPolicy は apps/"]:
        assert want in errors, f"{want} が検出されない:\n{errors}"

assert check(Path(__file__).parent.parent) == [], check(Path(__file__).parent.parent)
print("ok")
