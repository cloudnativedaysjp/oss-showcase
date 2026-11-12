# OSS Showcase

あなたが作った OSS や推しの OSS を、ブースの Kubernetes にデプロイしてみませんか。

## デプロイのしかた

1. このリポジトリを fork する
2. `apps/example/` をコピーして `apps/<OSS の名前>/` を作る
3. `image` をその OSS のコンテナイメージに書き換える
4. HTTPRoute の `hostnames` を `<OSS の名前>.showcase.cloudnativedays.jp` にする
5. Pull Request を出す。スタッフがマージすると、1 分ほどでデプロイされる

`http://<OSS の名前>.showcase.cloudnativedays.jp` を開くと表示されます。

Claude Code などのエージェントに任せるときは、`AGENTS.md` を読ませてください。

このリポジトリは公開されています。Secret に本物のパスワードやトークンを書かないでください。

## 使えるリソース

- Deployment、StatefulSet、Job、CronJob
- HorizontalPodAutoscaler、PodDisruptionBudget
- Service、HTTPRoute
- ConfigMap、Secret、PersistentVolumeClaim
- ServiceAccount、Role、RoleBinding
- CloudNativePG の Cluster

外部への公開には HTTPRoute を使ってください。Ingress は使えません。
別のアプリの namespace からの通信は届きません。
外への通信は、DNS と 80 番、443 番だけが通ります。
Pod には、書かれていなければ `seccompProfile: RuntimeDefault` と `allowPrivilegeEscalation: false` が付きます。sudo のように実行中に権限を上げる処理は動きません。
user namespace を作ろうとしたプロセスは止められます。Chromium のサンドボックスのように user namespace を使う OSS は動きません。

### Helm チャートしかないとき

Helm チャートや Kustomize はそのままでは使えません。`.yaml` と `.yml` だけを読みます。
手元で YAML に展開して、その結果をコミットしてください。

```sh
helm template <OSS の名前> <チャート> --namespace app-<OSS の名前> --skip-tests > apps/<OSS の名前>/app.yaml
```

`apps/` で使えるのは、上の「使えるリソース」に並んだ種類だけです。
ほかの種類が出てきたら、チャートの values で止めてください。よく出てくるものは次のとおりです。

- Ingress は使えません。代わりに HTTPRoute を書いてください
- NetworkPolicy と ServiceMonitor は使えません
- ClusterRole が出てきたら、namespace に閉じた Role にする values を探してください。Grafana なら `rbac.namespaced=true` です

### PostgreSQL が要るとき

[CloudNativePG](https://cloudnative-pg.io/) の `Cluster` を書くと、自分の namespace に PostgreSQL ができます。
`<Cluster の名前>-app` という Secret に、接続先とパスワードが入ります。

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

### CRD やクラスタの権限が要るとき

Operator のように、CRD や ClusterRole が要る OSS は `cluster-apps/<名前>/` に置いてください。
`apps/` の代わりに置くもので、両方には置けません。
実行委員が中身を確認してからマージします。

どちらに置いても、特権コンテナは使えません。必要なときは実行委員に相談してください。

`resources` を書かなければ、コンテナごとに CPU 0.5 コアとメモリ 256Mi が上限になります。
足りなければ `resources.limits` を書いてください。1 アプリの合計で、CPU 4 コアとメモリ 4Gi まで使えます。emptyDir とログは合わせて 5Gi までです。

## ライセンス

[Apache License 2.0](LICENSE)
