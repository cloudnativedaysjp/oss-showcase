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
    "apps/more/app.yaml": """
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: {name: nohost}
spec: {}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: prio}
spec: {template: {spec: {priorityClassName: system-node-critical, containers: []}}}
---
apiVersion: cluster.x-k8s.io/v1beta2
kind: Cluster
metadata: {name: capi}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: esc}
rules: [{apiGroups: [""], resources: [pods], verbs: [escalate]}]
""",
    "apps/more/sub/x.yaml": "kind: ConfigMap\nmetadata: {name: x}\n",
    "cluster-apps/eps/app.yaml": """
kind: EndpointSlice
metadata: {name: x}
---
kind: ClusterRole
metadata: {name: agg, labels: {rbac.authorization.k8s.io/aggregate-to-view: "true"}}
rules: [{apiGroups: [""], resources: [secrets], verbs: [get]}]
""",
    "apps/Bad_Name/app.yaml": "kind: ConfigMap\nmetadata: {name: x}\n",
}

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    for path, body in BAD.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(body)
    errors = "\n".join(check(root))
    for want in ["hostnames", "Namespace", "名前が重なっている", "cluster-admin", "failurePolicy", "CRD が重なっている", "ディレクトリ名", "namespace は", "List は使えない", "API group", "admin には bind", "cilium.io", "externalIPs", "ExternalName は", "同じ名前", "roles と rolebindings だけ", "hostnames に", "priorityClassName は", "Cluster は apps/", "escalate、bind", "サブディレクトリ", "EndpointSlice は", "aggregate できない", "Pod は apps/", "NetworkPolicy は使えない"]:
        assert want in errors, f"{want} が検出されない:\n{errors}"

assert check(Path(__file__).parent.parent) == [], check(Path(__file__).parent.parent)
print("ok")
