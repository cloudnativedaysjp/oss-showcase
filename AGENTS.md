# AGENTS.md

CloudNative Days のブースで、来場者が推しの OSS を Kubernetes にデプロイする展示のリポジトリ。
main にマージされた YAML を Argo CD が同期する。

## 来場者の OSS を足すとき

1. `apps/example/` をコピーして `apps/<名前>/` を作る。`<名前>` は英小文字、数字、ハイフンにする
2. `image` と `containerPort`、Service の `targetPort` をその OSS に合わせる
3. HTTPRoute の `hostnames` を `<名前>.showcase.cloudnativedays.jp` だけにする
4. 「確かめる」のコマンドがすべて通ったら完了

PR が変えるのは `apps/<名前>/` の中だけにする。
Helm チャートや Kustomize は Argo CD に描画させない。`helm template` や `kustomize build` の結果を YAML でコミットする。
`helm template` には `--namespace app-<名前> --skip-tests` を付ける。使えない種類のリソースは、チャートの values で止める。
CRD や ClusterRole が要る OSS は、`apps/` の代わりに `cluster-apps/<名前>/` に置く。

作れるリソースの種類は README.md の「使えるリソース」にある。
Namespace、ResourceQuota、LimitRange は運営が入れるので、来場者の YAML には書かない。
公開には HTTPRoute を使う。Ingress、LoadBalancer、NodePort は使えない。

### リソースと権限の上限

- 1 アプリの合計で、CPU 4 コア、メモリ 4Gi、Pod 10 個、PVC 2 個、emptyDir とログ 5Gi まで
- コンテナは root で動いてよいが、特権コンテナと hostPath は使わない
- イメージは認証なしで pull できるものにする
- Secret もリポジトリで公開される。本物の認証情報やトークンは書かず、ダミーの値にする

## 確かめる

```bash
pip install pyyaml
python scripts/check.py        # 展示のルール。CI と同じ
```

CI では kubeconform も走る。手元にあれば `kubeconform -summary -ignore-missing-schemas apps cluster-apps` で同じものを確かめられる。
