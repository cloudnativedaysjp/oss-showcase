# 展示のルール

OSS を置くときに守るルールと、クラスタの上限です。`scripts/check.py` と CI が、ここに書いたルールを確かめます。

## 使えるリソース

- Deployment、StatefulSet、Job、CronJob
- HorizontalPodAutoscaler、PodDisruptionBudget
- Service、HTTPRoute
- ConfigMap、Secret、PersistentVolumeClaim
- ServiceAccount、Role、RoleBinding
- CloudNativePG の Cluster（`postgresql.cnpg.io`）

YAML は `apps/<OSS の名前>/` の直下に置いてください。サブディレクトリは読みません。
ファイルは何個に分けても構いません。

## 制限

### 公開と通信

- 外から届くのは、HTTPRoute で公開した HTTP だけです。Ingress、LoadBalancer、NodePort は使えません
- HTTP 以外のポートの Service も作れますが、届くのは同じ namespace の中だけです
- 別のアプリの namespace からの通信は届きません
- 外への通信は、DNS、80 番、443 番と、Kubernetes の API サーバだけが通ります
- Service の `externalIPs` と `type: ExternalName`、手で書いた Endpoints と EndpointSlice は使えません

### Pod

- Pod Security の baseline に従います。特権コンテナ、hostPath、hostNetwork、hostPort、`NET_ADMIN` などの capabilities の追加は使えません
- コンテナは root で動かして構いません
- 書かれていなければ、`seccompProfile: RuntimeDefault` と `allowPrivilegeEscalation: false` が付きます。sudo のように実行中に権限を上げる処理は動きません
- user namespace を作ろうとしたプロセスは止められます。Chromium のサンドボックスのように user namespace を使う OSS は動きません
- `priorityClassName` は書けません

### 権限

- Role の `apiGroups` に `*` と `cilium.io` は書けません
- `rbac.authorization.k8s.io` で使えるのは `roles` と `rolebindings` だけです
- verbs の `escalate`、`bind`、`impersonate` は使えません
- RoleBinding で `cluster-admin`、`admin`、`edit` と `system:` で始まる ClusterRole は参照できません

### 運営が入れるもの

Namespace、ResourceQuota、LimitRange、NetworkPolicy、CiliumNetworkPolicy は書かないでください。

## リソースの上限

`resources` を書かなかったコンテナには、次の既定値が付きます。

| | requests | limits |
|---|---|---|
| CPU | 50m | 500m |
| メモリ | 64Mi | 256Mi |
| emptyDir とログ | 64Mi | 200Mi |

足りなければ `resources` を書いてください。1 コンテナの limits は、CPU 4 コア、メモリ 4Gi、emptyDir とログ 2Gi までです。
limits を超えてメモリを使うとコンテナが止まり、emptyDir とログが超えると Pod が退避させられます。

1 アプリの合計の上限は次のとおりです。

| | 上限 |
|---|---|
| CPU の requests / limits | 2 コア / 4 コア |
| メモリの requests / limits | 2Gi / 4Gi |
| emptyDir とログの limits | 5Gi |
| Pod | 10 個 |
| PersistentVolumeClaim | 2 個、合計 2Gi |

## Helm チャートしかないとき

Helm チャートや Kustomize はそのままでは使えません。`.yaml` と `.yml` だけを読みます。
手元で YAML に展開して、その結果をコミットしてください。

```sh
helm template <OSS の名前> <チャート> --namespace app-<OSS の名前> --skip-tests > apps/<OSS の名前>/app.yaml
```

- 展開に使ったコマンドと values は、`app.yaml` の先頭にコメントで残してください。バージョンを上げるときに使います
- 出力に `namespace: app-<OSS の名前>` が入っていても構いません
- HTTPRoute はチャートに入っていないので、`apps/example/` から別のファイルにコピーしてください。`backendRefs` には、チャートが作った Service の名前とポートを書きます
- 「使えるリソース」にない種類が出てきたら、チャートの values で止めてください
  - Ingress は使えません。代わりに HTTPRoute を書いてください
  - NetworkPolicy と ServiceMonitor は使えません
  - ClusterRole が出てきたら、namespace に閉じた Role にする values を探してください。Grafana なら `rbac.namespaced=true` です
- チャートの `resources` が、上の上限に収まっているかを確かめてください

## PostgreSQL が要るとき

[CloudNativePG](https://cloudnative-pg.io/) の `Cluster` を書くと、自分の namespace に PostgreSQL ができます。
`<Cluster の名前>-app` という Secret に、接続先とパスワードが入ります。
PostgreSQL の Pod と PVC も、上のリソースの上限に数えます。

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: db
spec:
  instances: 1
  storage:
    size: 1Gi
```

## CRD やクラスタの権限が要るとき

Operator のように、CRD や ClusterRole が要る OSS は `cluster-apps/<名前>/` に置いてください。
`apps/` の代わりに置くもので、両方には置けません。
実行委員が中身を確認してからマージします。
上の制限は `cluster-apps/` にもかかります。特権が必要なときは実行委員に相談してください。
