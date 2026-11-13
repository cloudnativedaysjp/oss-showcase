# AGENTS.md

CloudNative Days のブースで、来場者が推しの OSS を Kubernetes にデプロイする展示のリポジトリ。
main にマージされた YAML を Argo CD が同期する。

## 来場者の OSS を足すとき

README.md の「やってみる」の手順に従う。
docs/rules.md に書かれたことは、すべて守る。
OSS を選ぶときも、docs/rules.md の制限で動くかを確かめる。例えば、外への通信は DNS、80 番、443 番だけ。

- fork したリポジトリで作業し、元のリポジトリに PR を出す
- PR が変えるのは、`apps/<名前>/` か `cluster-apps/<名前>/` のどちらか一方の中だけにする
- YAML はそのディレクトリの直下に置く。Argo CD はサブディレクトリを読まない
- Helm チャートや Kustomize は Argo CD に描画させない。docs/rules.md の「Helm チャートしかないとき」に従い、展開した YAML をコミットする
- Helm で展開したときも、HTTPRoute は `apps/example/` からコピーして書く。`backendRefs` はチャートが作った Service を指す
- Secret は使ってよいが、リポジトリごと公開されて誰でも読める。テスト用の値など、見られても困らない値だけを書く
- 管理者のパスワードも読めるので、そのままでは誰でもログインできる。ログインを止めるか、閲覧だけにする

## 確かめる

```bash
python3 -m pip install pyyaml   # 入っていなければ
python3 scripts/check.py        # 展示のルール。CI と同じ。通ると ok と出る
```

CI では kubeconform も走る。手元にあれば `kubeconform -summary -ignore-missing-schemas apps cluster-apps` で同じものを確かめられる。
