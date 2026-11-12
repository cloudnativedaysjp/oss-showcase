# AGENTS.md

CloudNative Days のブースで、来場者が推しの OSS を Kubernetes にデプロイする展示のリポジトリ。
main にマージされた YAML を Argo CD が同期する。

## 来場者の OSS を足すとき

README.md の「デプロイのしかた」の手順に従う。
「使えるリソース」「制限」「リソースの上限」に書かれたことは、すべて守る。
OSS を選ぶときも、この 3 つの節で動くかを確かめる。例えば、外への通信は DNS、80 番、443 番だけ。

- fork したリポジトリで作業し、元のリポジトリに PR を出す
- PR が変えるのは、`apps/<名前>/` か `cluster-apps/<名前>/` のどちらか一方の中だけにする
- YAML はそのディレクトリの直下に置く。Argo CD はサブディレクトリを読まない
- Helm チャートや Kustomize は Argo CD に描画させない。README の「Helm チャートしかないとき」に従い、展開した YAML をコミットする
- Helm で展開したときも、HTTPRoute は `apps/example/` からコピーして書く。`backendRefs` はチャートが作った Service を指す
- Secret は公開される。本物の認証情報やトークンは書かず、ダミーの値にする。管理者のパスワードを Secret に置く OSS は、ログインを止める

## 確かめる

```bash
python3 -m pip install pyyaml   # 入っていなければ
python3 scripts/check.py        # 展示のルール。CI と同じ。通ると ok と出る
```

CI では kubeconform も走る。手元にあれば `kubeconform -summary -ignore-missing-schemas apps cluster-apps` で同じものを確かめられる。
