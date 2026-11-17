"""クラスタの HTTPRoute を読み、動いているアプリの一覧をハニカムで出す

scripts/render_portal.py が、このファイルを configmap.yaml に埋め込む。直したら render_portal.py を実行する。
"""
import base64
import datetime
import hashlib
import html
import json
import ssl
import threading
import time
import urllib.parse
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SA = "/var/run/secrets/kubernetes.io/serviceaccount"
API = "https://kubernetes.default.svc/apis/gateway.networking.k8s.io/v1/httproutes"
# API サーバを叩きすぎないよう、一覧はこの秒数だけ覚えておく
TTL = 10

# CloudNative Days のロゴの 2 色。アプリ名から決め、同じアプリはいつも同じ色にする
TILE_COLORS = ('blue', 'magenta')
# キーノートで使うアプリ。先頭に並べ、アプリ名の代わりに何ができるかを出す。check.py の KEYNOTE と揃える
KEYNOTE = {'sanposhiho': 'スライド<br>資料', 'comments': 'コメント<br>を送る'}
KEYNOTE_SPEAKER = 'sanposhiho'
# 強調するのはキーノートの前後だけ。終わったら、ほかのアプリと同じタイルに戻す
JST = datetime.timezone(datetime.timedelta(hours=9))
KEYNOTE_FROM = datetime.datetime(2026, 11, 18, 11, 0, tzinfo=JST)
KEYNOTE_TO = datetime.datetime(2026, 11, 18, 11, 50, tzinfo=JST)
MASCOTS = 'https://cloudnativedays.jp/images/mascots'
REPO = 'https://github.com/cloudnativedaysjp/oss-showcase'
# github.com/cloudnativedaysjp/oss-showcase を指す QR コード。qrencode -t SVG で作った
QR = '<svg class="qr" viewBox="0 0 35 35" role="img" aria-label="oss-showcase のリポジトリを開く QR コード" xmlns="http://www.w3.org/2000/svg"><g id="QRcode"><rect x="0" y="0" width="35" height="35" fill="#ffffff"/><path style="stroke:#000000" transform="translate(1,1.5)" d="M0,0h1M1,0h1M2,0h1M3,0h1M4,0h1M5,0h1M6,0h1M9,0h1M10,0h1M12,0h1M16,0h1M18,0h1M19,0h1M20,0h1M21,0h1M23,0h1M26,0h1M27,0h1M28,0h1M29,0h1M30,0h1M31,0h1M32,0h1M0,1h1M6,1h1M10,1h1M11,1h1M15,1h1M18,1h1M22,1h1M26,1h1M32,1h1M0,2h1M2,2h1M3,2h1M4,2h1M6,2h1M8,2h1M9,2h1M14,2h1M16,2h1M20,2h1M21,2h1M22,2h1M26,2h1M28,2h1M29,2h1M30,2h1M32,2h1M0,3h1M2,3h1M3,3h1M4,3h1M6,3h1M8,3h1M10,3h1M12,3h1M15,3h1M18,3h1M19,3h1M22,3h1M26,3h1M28,3h1M29,3h1M30,3h1M32,3h1M0,4h1M2,4h1M3,4h1M4,4h1M6,4h1M8,4h1M9,4h1M10,4h1M11,4h1M12,4h1M14,4h1M15,4h1M16,4h1M17,4h1M20,4h1M21,4h1M23,4h1M26,4h1M28,4h1M29,4h1M30,4h1M32,4h1M0,5h1M6,5h1M8,5h1M12,5h1M14,5h1M17,5h1M19,5h1M26,5h1M32,5h1M0,6h1M1,6h1M2,6h1M3,6h1M4,6h1M5,6h1M6,6h1M8,6h1M10,6h1M12,6h1M14,6h1M16,6h1M18,6h1M20,6h1M22,6h1M24,6h1M26,6h1M27,6h1M28,6h1M29,6h1M30,6h1M31,6h1M32,6h1M8,7h1M9,7h1M14,7h1M16,7h1M19,7h1M20,7h1M21,7h1M23,7h1M0,8h1M2,8h1M3,8h1M4,8h1M5,8h1M6,8h1M9,8h1M10,8h1M12,8h1M13,8h1M14,8h1M16,8h1M17,8h1M19,8h1M23,8h1M26,8h1M27,8h1M28,8h1M29,8h1M30,8h1M0,9h1M4,9h1M7,9h1M10,9h1M11,9h1M13,9h1M16,9h1M17,9h1M19,9h1M20,9h1M21,9h1M23,9h1M26,9h1M27,9h1M29,9h1M30,9h1M31,9h1M32,9h1M2,10h1M5,10h1M6,10h1M7,10h1M10,10h1M13,10h1M14,10h1M15,10h1M16,10h1M17,10h1M20,10h1M24,10h1M28,10h1M30,10h1M31,10h1M0,11h1M3,11h1M5,11h1M7,11h1M10,11h1M13,11h1M15,11h1M17,11h1M18,11h1M19,11h1M21,11h1M22,11h1M24,11h1M25,11h1M26,11h1M28,11h1M29,11h1M30,11h1M31,11h1M0,12h1M1,12h1M3,12h1M5,12h1M6,12h1M8,12h1M9,12h1M11,12h1M12,12h1M14,12h1M16,12h1M20,12h1M22,12h1M23,12h1M24,12h1M25,12h1M28,12h1M29,12h1M32,12h1M0,13h1M5,13h1M8,13h1M11,13h1M12,13h1M13,13h1M15,13h1M18,13h1M23,13h1M25,13h1M26,13h1M30,13h1M31,13h1M32,13h1M1,14h1M3,14h1M5,14h1M6,14h1M7,14h1M9,14h1M10,14h1M12,14h1M13,14h1M15,14h1M16,14h1M20,14h1M22,14h1M24,14h1M25,14h1M26,14h1M28,14h1M29,14h1M31,14h1M2,15h1M4,15h1M7,15h1M8,15h1M9,15h1M10,15h1M12,15h1M13,15h1M15,15h1M21,15h1M24,15h1M25,15h1M26,15h1M28,15h1M29,15h1M30,15h1M0,16h1M3,16h1M4,16h1M5,16h1M6,16h1M9,16h1M11,16h1M13,16h1M14,16h1M15,16h1M17,16h1M22,16h1M23,16h1M24,16h1M25,16h1M27,16h1M28,16h1M32,16h1M0,17h1M1,17h1M2,17h1M3,17h1M4,17h1M7,17h1M8,17h1M9,17h1M14,17h1M16,17h1M18,17h1M19,17h1M20,17h1M21,17h1M23,17h1M26,17h1M27,17h1M29,17h1M30,17h1M31,17h1M32,17h1M0,18h1M1,18h1M2,18h1M6,18h1M7,18h1M8,18h1M10,18h1M13,18h1M14,18h1M15,18h1M18,18h1M20,18h1M21,18h1M24,18h1M27,18h1M28,18h1M30,18h1M31,18h1M1,19h1M2,19h1M3,19h1M8,19h1M9,19h1M10,19h1M13,19h1M14,19h1M15,19h1M16,19h1M19,19h1M20,19h1M21,19h1M22,19h1M25,19h1M26,19h1M27,19h1M28,19h1M29,19h1M30,19h1M31,19h1M0,20h1M1,20h1M2,20h1M6,20h1M11,20h1M14,20h1M15,20h1M18,20h1M19,20h1M22,20h1M24,20h1M27,20h1M28,20h1M29,20h1M0,21h1M3,21h1M4,21h1M5,21h1M7,21h1M9,21h1M14,21h1M15,21h1M16,21h1M20,21h1M21,21h1M22,21h1M23,21h1M26,21h1M32,21h1M0,22h1M2,22h1M3,22h1M5,22h1M6,22h1M9,22h1M10,22h1M14,22h1M19,22h1M25,22h1M28,22h1M31,22h1M0,23h1M4,23h1M7,23h1M8,23h1M9,23h1M10,23h1M12,23h1M13,23h1M14,23h1M16,23h1M18,23h1M19,23h1M20,23h1M21,23h1M22,23h1M23,23h1M24,23h1M25,23h1M26,23h1M28,23h1M29,23h1M30,23h1M31,23h1M0,24h1M6,24h1M7,24h1M11,24h1M12,24h1M13,24h1M14,24h1M16,24h1M17,24h1M19,24h1M22,24h1M24,24h1M25,24h1M26,24h1M27,24h1M28,24h1M29,24h1M8,25h1M11,25h1M12,25h1M16,25h1M17,25h1M18,25h1M19,25h1M21,25h1M23,25h1M24,25h1M28,25h1M30,25h1M32,25h1M0,26h1M1,26h1M2,26h1M3,26h1M4,26h1M5,26h1M6,26h1M10,26h1M14,26h1M15,26h1M16,26h1M17,26h1M20,26h1M23,26h1M24,26h1M26,26h1M28,26h1M30,26h1M31,26h1M0,27h1M6,27h1M8,27h1M11,27h1M15,27h1M17,27h1M18,27h1M20,27h1M21,27h1M22,27h1M23,27h1M24,27h1M28,27h1M29,27h1M30,27h1M0,28h1M2,28h1M3,28h1M4,28h1M6,28h1M8,28h1M12,28h1M15,28h1M16,28h1M19,28h1M22,28h1M24,28h1M25,28h1M26,28h1M27,28h1M28,28h1M29,28h1M31,28h1M0,29h1M2,29h1M3,29h1M4,29h1M6,29h1M8,29h1M9,29h1M14,29h1M15,29h1M17,29h1M18,29h1M23,29h1M24,29h1M25,29h1M28,29h1M30,29h1M31,29h1M32,29h1M0,30h1M2,30h1M3,30h1M4,30h1M6,30h1M8,30h1M9,30h1M11,30h1M14,30h1M15,30h1M16,30h1M17,30h1M20,30h1M22,30h1M26,30h1M27,30h1M30,30h1M0,31h1M6,31h1M10,31h1M11,31h1M13,31h1M15,31h1M18,31h1M20,31h1M21,31h1M22,31h1M23,31h1M25,31h1M26,31h1M28,31h1M30,31h1M0,32h1M1,32h1M2,32h1M3,32h1M4,32h1M5,32h1M6,32h1M8,32h1M11,32h1M15,32h1M17,32h1M22,32h1M23,32h1M24,32h1M25,32h1M27,32h1M31,32h1"/></g></svg>'
LOGO = '<svg class="logo" viewBox="0 0 97.46 102.05" aria-hidden="true">\n<g class="m"><polygon points="30.8 17.67 39.43 32.6 58.15 32.6 66.77 17.67"/><polygon points="66.99 84.84 58.2 69.62 39.48 69.62 30.69 84.84"/><polygon points="37.62 68.4 28.26 52.19 10.57 52.19 28.78 83.72"/><polygon points="28.86 18.65 10.74 50.04 28.26 50.04 37.62 33.82"/></g>\n<g class="b"><polygon points="66.77 15.24 57.97 0 39.25 0 30.44 15.24"/><polygon points="97.27 33.65 87.9 17.43 70.59 17.43 88.6 48.64"/><polygon points="59.82 33.65 69.19 49.86 86.71 49.86 68.59 18.47"/><polygon points="68.86 83.71 87.05 52.19 69.38 52.19 60.02 68.4"/><polygon points="88.87 53.53 70.93 84.62 88.1 84.62 97.46 68.4"/><polygon points="30.84 87.09 39.48 102.05 58.2 102.05 66.84 87.09"/><polygon points=".18 68.4 9.54 84.62 26.7 84.62 8.76 53.55"/><polygon points="8.66 48.64 26.68 17.43 9.36 17.43 0 33.65"/></g>\n</svg>'
# タブのアイコン。CND のロゴをそのまま使う
FAVICON = urllib.parse.quote(LOGO.replace('class="logo" ', '').replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ').replace('class="m"', 'fill="#be4493"').replace('class="b"', 'fill="#216a9c"'))


CSS = """
:root {
  --bg: #f3f7fb; --ink: #1e2d3d; --muted: #4c5b6c; --blue: #216a9c; --magenta: #be4493;
  --orange: #ef9214; --orange-line: #c97a0a; --orange-ink: #8f5304;
  /* タイルの大きさ。大きな画面では SCRIPT の fit() が、画面とアプリの数に合わせて決め直す */
  --s: clamp(6.5rem, 5rem + 6vw, 12rem); --m: calc(var(--s) * .025);
  color-scheme: light;
}
body {
  margin: 0; min-block-size: 100dvh; display: grid; grid-template-rows: auto 1fr auto;
  color: var(--ink); overflow-x: clip; line-height: 1.6; font-family: "Zen Kaku Gothic New", sans-serif;
  /* 今の CND のサイトの紙吹雪にならい、ロゴの 3 色の小さな四角を、右上にだけ散らす */
  background: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='900' height='320'><g opacity='.55'><rect x='291' y='48' width='10' height='5' rx='1' fill='%23216a9c' transform='rotate(-60 296 51)'/><rect x='482' y='117' width='10' height='5' rx='1' fill='%23be4493' transform='rotate(57 487 120)'/><rect x='193' y='28' width='16' height='5' rx='1' fill='%23ef9214' transform='rotate(-60 201 30)'/><rect x='82' y='136' width='10' height='5' rx='1' fill='%23216a9c' transform='rotate(63 87 138)'/><rect x='568' y='187' width='10' height='5' rx='1' fill='%23be4493' transform='rotate(11 573 189)'/><rect x='357' y='312' width='10' height='5' rx='1' fill='%23ef9214' transform='rotate(8 362 315)'/><rect x='120' y='134' width='10' height='5' rx='1' fill='%23216a9c' transform='rotate(10 125 137)'/><rect x='504' y='218' width='10' height='5' rx='1' fill='%23be4493' transform='rotate(11 509 221)'/><rect x='575' y='119' width='10' height='5' rx='1' fill='%23ef9214' transform='rotate(9 580 122)'/><rect x='557' y='159' width='16' height='5' rx='1' fill='%23216a9c' transform='rotate(39 565 161)'/><rect x='419' y='296' width='14' height='5' rx='1' fill='%23be4493' transform='rotate(-28 426 298)'/><rect x='715' y='224' width='12' height='5' rx='1' fill='%23ef9214' transform='rotate(-59 721 226)'/><rect x='270' y='158' width='14' height='5' rx='1' fill='%23216a9c' transform='rotate(32 277 161)'/><rect x='259' y='314' width='10' height='5' rx='1' fill='%23be4493' transform='rotate(2 264 316)'/><rect x='148' y='109' width='16' height='5' rx='1' fill='%23ef9214' transform='rotate(-11 156 112)'/><rect x='866' y='25' width='14' height='5' rx='1' fill='%23216a9c' transform='rotate(-22 873 27)'/><rect x='315' y='159' width='16' height='5' rx='1' fill='%23be4493' transform='rotate(-60 323 161)'/><rect x='84' y='86' width='10' height='5' rx='1' fill='%23ef9214' transform='rotate(-62 89 89)'/><rect x='631' y='207' width='16' height='5' rx='1' fill='%23216a9c' transform='rotate(-30 639 210)'/><rect x='347' y='214' width='10' height='5' rx='1' fill='%23be4493' transform='rotate(62 352 216)'/><rect x='320' y='195' width='16' height='5' rx='1' fill='%23ef9214' transform='rotate(-62 328 198)'/><rect x='691' y='41' width='12' height='5' rx='1' fill='%23216a9c' transform='rotate(-14 697 44)'/></g></svg>") right top / min(900px, 60vw) auto no-repeat, var(--bg);
  padding: clamp(1.25rem, .5rem + 3vmin, 4rem); box-sizing: border-box;
}
/* 日本語が単語の途中で折り返さないよう、文節ごとのかたまりの中では折り返さない */
.p { display: inline-block; max-inline-size: 100%; }

/* CND のロゴは、場所の名前の頭に文字と同じ高さで置く */
.logo { inline-size: auto; block-size: 1.15em; vertical-align: -.2em; margin-inline-end: .4em; }
.logo .b { fill: var(--blue); } .logo .m { fill: var(--magenta); }
/* ロゴタイプだけ、今の CND のサイトと同じ Gill Sans にする。ない PC では Zen Kaku Gothic New になる */
h1 { margin: 0; color: var(--blue); font-weight: 700; letter-spacing: .01em; line-height: 1;
  font-family: "Gill Sans Nova", "Gill Sans", "Gill Sans MT", "Zen Kaku Gothic New", sans-serif;
  font-size: clamp(2.2rem, 1rem + 5vmin, 9rem); }
.place { margin: .6rem 0 0; color: var(--muted); font-weight: 500; font-size: clamp(.95rem, .6rem + 1.5vmin, 2.6rem); word-break: auto-phrase; }

/* ハニカム。左に置いた浮動要素の shape-outside で、行ごとに半分ずらす。浮動要素の高さを % で決めるため、親を flex にする */
/* 最後の段が ul の高さに数えられず、1 段分はみ出す（Chrome で測った）。その分を下に足す */
.hive { display: flex; align-self: start; margin-block: clamp(1rem, .5rem + 2.5vmin, 4rem) 0; padding-block-end: var(--s);
  --f: calc(1.732 * var(--s) + 4 * var(--m) - 1px); }
.hive ul { flex: 1; list-style: none; margin: 0; padding: 0; font-size: 0; }
.hive ul::before { content: ""; float: left; inline-size: calc(var(--s) / 2 + var(--m)); block-size: 120%;
  shape-outside: repeating-linear-gradient(#0000 0 calc(var(--f) - 3px), #000 0 var(--f)); }
.hive li { display: inline-block; vertical-align: top; inline-size: var(--s); block-size: calc(var(--s) * 1.1547);
  margin: var(--m); margin-block-end: calc(var(--m) - var(--s) * .2885); font-size: 1rem; }
.hex { position: relative; isolation: isolate; display: grid; place-content: center; text-align: center;
  inline-size: 100%; block-size: 100%; padding: 0 9%; box-sizing: border-box; color: white; text-decoration: none; }
.hex::before, .hex::after { content: ""; position: absolute; inset: 0; z-index: -1;
  clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%); }
.hex::before { background: var(--tile); transition: background-color .2s; }
.blue { --tile: var(--blue); } .magenta { --tile: var(--magenta); }
a.hex:hover::before { background: color-mix(in oklab, var(--tile), black 14%); }
/* clip-path は自分のフォーカスの枠も切るので、ひと回り大きい六角形を後ろに描く */
a.hex:focus-visible { outline: none; }
a.hex:focus-visible::after { inset: calc(var(--s) * -.04); z-index: -2; background: var(--ink); }
/* 文字の大きさはタイルに合わせる。長い名前は小さくして 3 行までにする */
.name { min-inline-size: 0; font-weight: 700; line-height: 1.15; font-size: calc(var(--s) * .125); overflow-wrap: anywhere;
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; line-clamp: 3; overflow: hidden; }
.name.long { font-size: calc(var(--s) * .085); }
/* キーノートのタイル。ほかのアプリと色を変え、小さな見出しを付ける */
.keynote { --tile: var(--ink); }
.keynote small { display: block; color: var(--orange); font-weight: 700; letter-spacing: .08em; font-size: calc(var(--s) * .075); }
.keynote .name { display: block; }
.keynote small.who { color: inherit; opacity: .8; letter-spacing: 0; margin-top: .3em; }

/* 動いているアプリの数。蜂の巣の最初の 1 枚にする */
.count { --tile: var(--orange); color: var(--ink); }
.count b { display: block; font-weight: 700; line-height: 1; font-size: calc(var(--s) * .4); }
.count span { font-weight: 700; font-size: calc(var(--s) * .105); line-height: 1.35; }
/* 蜂の巣の空いているマス。押すとリポジトリが開く */
.invite { --tile: var(--orange-line); color: var(--orange-ink); }
.invite::after { inset: calc(var(--s) * .035); background: var(--bg); }
a.invite:hover::after { background: color-mix(in oklab, var(--bg), var(--orange) 15%); }
.invite .name { font-size: calc(var(--s) * .105); }
.invite .plus { display: block; font-weight: 700; line-height: 1; font-size: calc(var(--s) * .28); }

footer { display: flex; flex-wrap: wrap; align-items: end; gap: clamp(1rem, .5rem + 2vmin, 3rem);
  font-size: clamp(1rem, .6rem + 1.6vmin, 2.8rem); }
footer p { margin: 0; word-break: auto-phrase; }
footer a { color: var(--blue); font-weight: 700; overflow-wrap: anywhere; }
footer a:has(.qr) { flex: none; display: block; border-radius: .5rem; }
footer a:focus-visible { outline: 3px solid var(--blue); outline-offset: 3px; }
.qr { display: block; inline-size: clamp(6rem, 18vmin, 24rem); block-size: auto; border-radius: .5rem;
  box-shadow: 0 0 0 1px rgb(30 45 61 / .12); }
/* スマートフォンで見ている人には QR コードは要らない */
@media (width < 44rem) { footer a:has(.qr) { display: none; } }
.mascots { margin-inline-start: auto; display: flex; align-items: end; gap: clamp(.25rem, 1vw, 1.5rem); }
.mascots img { block-size: clamp(5rem, 15vmin, 20rem); inline-size: auto; }

@media (prefers-reduced-motion: no-preference) {
  /* ページを開いたときに 1 回だけ、タイルが順に現れる */
  .hive li { animation: rise .6s cubic-bezier(.2, .8, .2, 1) both; animation-delay: calc(var(--i) * 60ms); }
  /* 更新で新しく並んだアプリだけ、少し跳ねて知らせる */
  .hive li.new { animation: pop 1.2s cubic-bezier(.2, .8, .2, 1) both; }
}
@keyframes rise { from { opacity: 0; scale: .6; } }
@keyframes pop { 0% { scale: .4; opacity: 0; } 60% { scale: 1.12; opacity: 1; } 100% { scale: 1; } }
"""

SCRIPT = """
const big = () => innerWidth >= 700 && innerHeight >= 500;
// 大きな画面では、タイルを画面いっぱいまで大きくし、アプリが増えたら QR コードまで 1 画面に収まるよう小さくする
function fit() {
  const root = document.documentElement;
  root.style.removeProperty("--s");
  if (!big()) return;
  let s = Math.min(innerWidth * 0.17, innerHeight * 0.34);
  root.style.setProperty("--s", s + "px");
  while (s > 64 && root.scrollHeight > innerHeight) {
    s *= 0.95;
    root.style.setProperty("--s", s + "px");
  }
}
addEventListener("resize", fit);
fit();

// 一覧だけを差し替える。ページごと読み直すと、毎回アニメーションが流れるため
let busy = false;
setInterval(async () => {
  if (busy) return;
  busy = true;
  try {
    const res = await fetch(location.pathname, { cache: "no-store", signal: AbortSignal.timeout(10000) });
    if (!res.ok) return;
    const fresh = new DOMParser().parseFromString(await res.text(), "text/html").getElementById("hive");
    const cur = document.getElementById("hive");
    if (!cur || !fresh || cur.innerHTML === fresh.innerHTML) return;
    const seen = new Set([...cur.querySelectorAll("a")].map((a) => a.href));
    fresh.querySelectorAll("li").forEach((li) => {
      const a = li.querySelector("a.blue, a.magenta");
      if (a && !seen.has(a.href)) li.classList.add("new");
      else li.style.animation = "none";
    });
    cur.replaceWith(fresh);
    fit();
  } catch {
  } finally {
    busy = false;
  }
}, 60000);
"""

# インラインの SCRIPT だけを実行させる。外から読むのはフォントとマスコットの画像だけ
CSP = "; ".join([
    "default-src 'none'",
    "script-src 'sha256-" + base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode() + "'",
    "style-src 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src https://cloudnativedays.jp data:",
    "connect-src 'self'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
])

_lock = threading.Lock()
_cache = {"at": float("-inf"), "hosts": None}
_ctx = None


def fetch_hosts() -> list[str]:
    global _ctx
    if _ctx is None:
        _ctx = ssl.create_default_context(cafile=f"{SA}/ca.crt")
    # トークンは定期的に差し替わるので、毎回読む
    with open(f"{SA}/token") as f:
        token = f.read()
    req = urllib.request.Request(API, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, context=_ctx, timeout=5) as res:
        routes = json.load(res)["items"]
    # 1 つの HTTPRoute を 1 枚のタイルにする
    hosts = set()
    for r in routes:
        names = r["spec"].get("hostnames") or []
        if r["metadata"]["namespace"].startswith("app-") and names and not names[0].startswith("portal."):
            hosts.add(names[0])
    return sorted(hosts)


def hosts() -> list[str]:
    """API が失敗したら、前に読めた一覧を返す。一度も読めていなければ例外にする"""
    with _lock:
        if time.monotonic() - _cache["at"] > TTL:
            # 失敗しても TTL の間は API を叩き直さない
            _cache["at"] = time.monotonic()
            try:
                _cache["hosts"] = fetch_hosts()
            except Exception:
                if _cache["hosts"] is None:
                    raise
        if _cache["hosts"] is None:
            raise RuntimeError("一覧をまだ読めていない")
        return _cache["hosts"]


def page(names: list[str], now: datetime.datetime | None = None) -> str:
    now = now or datetime.datetime.now(JST)
    keynote = KEYNOTE if KEYNOTE_FROM <= now < KEYNOTE_TO else {}
    tiles = [f'<li style="--i:0"><div class="hex count"><b>{len(names)}</b><span>動いている<br>アプリ</span></div></li>']
    # キーノートのアプリを KEYNOTE の順で先頭に寄せる。sorted は安定なので、ほかの並びは変わらない
    order = list(keynote)
    ordered = sorted(names, key=lambda h: order.index(n) if (n := h.split(".")[0]) in keynote else len(order))
    for i, h in enumerate(ordered, start=1):
        name = h.split(".")[0]
        if name in keynote:
            cls = "keynote"
            label = f'<span class="name"><small>KEYNOTE</small>{keynote[name]}<small class="who">{KEYNOTE_SPEAKER}</small></span>'
        else:
            cls = TILE_COLORS[zlib.crc32(h.encode()) % 2]
            label = f'<span class="name{" long" if len(name) > 13 else ""}">{html.escape(name)}</span>'
        tiles.append(f'<li style="--i:{i}"><a class="hex {cls}" href="https://{html.escape(h)}/">{label}</a></li>')
    label = "最初の<br>1 枚に" if not names else "あなたの<br>アプリ"
    tiles.append(f'<li style="--i:{len(names) + 1}"><a class="hex invite" href="{REPO}">'
                 f'<span class="name"><span class="plus">＋</span>{label}</span></a></li>')
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>OSS Showcase | CloudNative Days</title>
<link rel="icon" href="data:image/svg+xml,{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700&display=swap">
<style>{CSS}</style>
</head>
<body>
<header>
<h1>OSS Showcase</h1>
<p class="place"><span class="p">{LOGO}CloudNative Days</span> <span class="p">WAIWAI広場の Kubernetes</span></p>
</header>
<main><section class="hive" id="hive" aria-label="動いているアプリ"><ul>{"".join(tiles)}</ul></section></main>
<footer><a href="{REPO}">{QR}</a><p><span class="p">スマートフォンで読み取ると、</span><span class="p">リポジトリが開きます。</span><br>
<span class="p">PR ひとつで、</span><span class="p">ここにタイルが 1 枚増えます。</span><br>
<a href="{REPO}">github.com/<wbr>cloudnativedaysjp/<wbr>oss-showcase</a></p><div class="mascots"><img src="{MASCOTS}/suu-2.png" alt="" width="2586" height="1716"><img src="{MASCOTS}/toge-2.png" alt="" width="2587" height="1716"></div></footer>
<script>{SCRIPT}</script>
</body>
</html>"""


# API が読めないときも、10 秒ごとに読み直して、直ったら一覧に戻る
ERROR = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta http-equiv="refresh" content="10">
<title>OSS Showcase</title></head><body><p>アプリの一覧を読めませんでした。10 秒後に読み直します。</p></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/healthz":
            # readiness probe 用。API は叩かない
            self.reply(200, b"ok", "text/plain")
            return
        if path != "/":
            self.reply(404, "見つかりません".encode(), "text/plain; charset=utf-8")
            return
        try:
            body, code = page(hosts()).encode(), 200
        except Exception:
            body, code = ERROR.encode(), 503
        self.reply(code, body, "text/html; charset=utf-8")

    def reply(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_HEAD = do_GET

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("", 8080), Handler).serve_forever()
