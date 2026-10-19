# TI SN76489

Texas InstrumentsのSN76489AN、SN76494NサウンドジェネレータをPythonで実装したものです。入力クロックを1つずつ進め、TIのデータシートに準拠させています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-sn76489-python)](https://github.com/gufranco/ti-sn76489-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

異なるSG-1000イメージ**348**本をそれぞれ**600**フレーム起動、性質の不合格**0**件、データシート内で所在を確認した引用**17**件、**2**品種、テスト**647**件、ステートメントとブランチのカバレッジ**100%**、依存関係なし

```python
import sn76489

part = sn76489.Chip("sn76489an")


def write(value):
    part.write(value)
    while not part.ready:
        part.tick()


for value in (0x85, 0x00, 0x90, 0xBF, 0xDF, 0xFF):
    write(value)

for _ in range(1024):
    part.clock()

sampled = []
for _ in range(12):
    part.clock()
    sampled.append(part.bits[0])
print(sampled)
print(part.periods[0], part.steps, round(part.level, 3))
```

```
[0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
5 [0, 15, 15, 15] 0.0
```

チップは、単体の実チップと同じく、電源投入時にすべてのレジスタが不定の値になっています。2バイトでトーン1の周期を5にし、3バイト目でその減衰を0にし、さらに3バイトでほかのチャンネルをオフにします。書き込みが設定するのは周期であってカウンタではないため、最初の反転は最大1,024周期先になることがあります。それ以降、フリップフロップは5周期ごとに反転します。これがデータシートの`f = N/32n`です。

## インストール

| 要件   | バージョン                           |
| :----- | :----------------------------------- |
| Python | 3.12以降                             |
| git    | 任意。サブモジュールの取得に使います |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-sn76489-python.git
cd ti-sn76489-python
python3 sn76489/doctor.py
```

パッケージは標準ライブラリ以外を何もインポートしません。サブモジュールは`ti-tms9918-python`で、その中に`zilog-z80-python`があり、これらを使うのは全数調査だけです。ZIPダウンロードのリンクから得たソースアーカイブにはサブモジュールが含まれません。その場合、全数調査とそのテストは実行できない理由を報告し、それ以外はすべて動作します。

ドクターはマシンとチェックアウトを検査し、最後に1行を出力します。バグ報告には、その出力全体を貼り付けてください。

```
  10 checks, nothing to report
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付けられ、[リリースページ](https://github.com/gufranco/ti-sn76489-python/releases)に掲載されます。

## インターフェース

`sn76489.Chip(model, seed=UNSET_SEED)`はチップを1つ構築します。`model`は必須です。`seed`は、すべてのレジスタ、カウンタ、フリップフロップ、およびシフトレジスタの電源投入時の不定値を決めます。

| モデル      | 別名                            | 入力クロックの分周比 | 1バイトのロードに要する入力クロック数 |
| :---------- | :------------------------------ | :------------------- | :------------------------------------ |
| `sn76489an` | `sn76489a`, `76489an`, `76489a` | 16                   | 32                                    |
| `sn76494n`  | `sn76494`, `76494n`, `76494`    | 2                    | 4                                     |

### 呼び出し

| 呼び出し       | 効果                                                                                                                                                                                                                                                 |
| :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `write(value)` | CEとWEをストローブしたデータバス上の1バイトです。ビット7が立ったバイトはレジスタを指定し、その下位4ビットを設定します。立っていないバイトは、最後に指定したトーン周期の上位6ビット、またはそれ以外のレジスタの4ビットを設定します。READYが下がります |
| `tick()`       | 入力クロック1つです                                                                                                                                                                                                                                  |
| `clock()`      | プリスケール後の1周期です。SN76489ANでは入力クロック16個、SN76494Nでは2個です                                                                                                                                                                        |
| `reset()`      | このチップにはリセットピンがないため、何も変わりません。チップを返します。ソフトウェアが8つのレジスタ、つまり周期3つ、減衰4つ、ノイズ制御をすべて書き込んで初めて、チップの状態が定まります                                                          |

### 状態

| 属性      | 意味                                                                                           |
| :-------- | :--------------------------------------------------------------------------------------------- |
| `ready`   | READYピンです。書き込みからバイトのロードが終わるまでfalseです                                 |
| `loading` | READYが上がるまでに残っている入力クロック数です                                                |
| `periods` | 3つのトーン周期です。それぞれ10ビットです                                                      |
| `steps`   | 4つの減衰ステップです。0が最大音量、15がオフです                                               |
| `control` | ノイズ制御です。ビット2がホワイトノイズを選択し、ビット0と1がレートを決めます                  |
| `shift`   | 15ビットのノイズ用シフトレジスタです                                                           |
| `latched` | 直前の1バイト目が指定したレジスタです                                                          |
| `bits`    | 各チャンネルの出力ビットです。3つのフリップフロップのあとに、シフトレジスタのビット0が続きます |
| `gains`   | Table 1の重みから求めた各チャンネルのゲインです。ステップ0で1.0、オフで0.0です                 |
| `level`   | ビットがハイのチャンネルのゲインの合計です                                                     |
| `ticks`   | チップの構築以降の入力クロック数です                                                           |
| `model`   | 正規のモデル名です                                                                             |
| `part`    | `Model`レコードです。`prescale`、`load_clocks`、`aliases`、`summary`を持ちます                 |

### モジュールの内容

| 名前                        | 内容                                                                                     |
| :-------------------------- | :--------------------------------------------------------------------------------------- |
| `sn76489.MODELS`            | 2つの`Model`レコードです。正規名をキーとします                                           |
| `sn76489.UnknownModelError` | モデル名がない場合や未知の場合に送出されます。メッセージには受け付ける名前が列挙されます |
| `sn76489.UNSET_SEED`        | シードを指定しなかったときに、チップの不定値の元になるシードです                         |
| `sn76489.__version__`       | インストールされているバージョンです                                                     |

```python
import sn76489

for name, model in sn76489.MODELS.items():
    print(name, model.aliases, model.prescale, model.load_clocks)

try:
    sn76489.Chip("sn76496")
except sn76489.UnknownModelError as error:
    print(error)
```

```
sn76489an ('sn76489a', '76489an', '76489a') 16 32
sn76494n ('sn76494', '76494n', '76494') 2 4
sn76496 is not a model this package covers; it has sn76489an, sn76494n
```

2つの品種の違いは、プリスケーラと、1バイトの読み込みにかかるクロック数です。後者はSN76489ANで32、SN76494Nで4です。同じ周期3で、トーン1のフリップフロップはSN76489ANでは入力クロック48個、SN76494Nでは6個のあいだ保持されます。

```python
import sn76489

for part in (sn76489.Chip("sn76489an"), sn76489.Chip("sn76494n")):
    for value in (0x83, 0x00):
        part.write(value)
        while not part.ready:
            part.tick()
    edges = []
    while len(edges) < 3:
        before = part.bits[0]
        part.tick()
        if part.bits[0] != before:
            edges.append(part.ticks)
    print(part.model, edges[2] - edges[1], edges[1] - edges[0])
```

```
sn76489an 48 48
sn76494n 6 6
```

## READYとノイズジェネレータ

```python
import sn76489

part = sn76489.Chip("sn76489an")
part.write(0xE4)
held = 0
while not part.ready:
    part.tick()
    held += 1
print(held, hex(part.shift))

shifts = 0
for _ in range(32 * 4):
    before = part.shift
    part.clock()
    shifts += part.shift != before
print(shifts, hex(part.shift))
```

```
32 0x4000
4 0x400
```

1バイトでN/512のホワイトノイズを選択します。READYは、データシートがロードに要するとしている32入力クロックのあいだローのままです。また、データシートの要求どおり、書き込みはシフトレジスタをクリアして最上位ビットだけを立てます。その後、レジスタは32周期ごと、つまり入力クロック512個ごとに1回シフトします。ビット0と1がどちらもクリアなので、最初の4回のシフトではそれぞれ0がフィードバックされます。

データシートはシフトレジスタについて何も述べていません。その幅、タップ、出力を取り出す位置は、SMS Powerのノートから取っています。このノートは、単体のSN76489ANを搭載したSC-3000Hで取得したデータを引用しています。MAMEは同じ系列を生成しますが、出力は2シフト後になります。どちらも[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)に記録しています。

## 全数調査

```bash
python3 -m conformance.census /path/to/sg1000/library --frames 600 --jobs 10
```

SG-1000のソフトウェアは、プロセッサとビデオチップが動き出してからでないとサウンドポートに書き込みません。そのため全数調査は、すべてのイメージを[`ti-tms9918-python`](https://github.com/gufranco/ti-tms9918-python)のSG-1000ボード上で起動します。プロセッサは`zilog-z80-python`で、このチップをポート`0x40`から`0x7F`に置き、プロセッサのクロックごとに1回ティックします。ディレクトリ、ZIPアーカイブ、単体のイメージを受け付け、異なるイメージをダイジェストで1回ずつ数えます。概要を出力し、[`conformance/corpus.json`](conformance/corpus.json)を書き出し、性質が破れた場合は終了コード1で終了します。

実行のゲートになる性質は2つです。どのイメージでもモデルが例外を送出しないこと、そしてシフトレジスタが決して0にならないことです。前のバイトのロードが終わる前に行われた書き込みは、イメージごとに数えて名前を挙げますが、ゲートにはしません。データシートが、その場合にチップがどう動作するかを述べていないからです。

| 観測内容                                                      | イメージ数、348本中 |
| :------------------------------------------------------------ | :------------------ |
| サウンドポートに一度も書き込まなかったもの                    | 35                  |
| トーン周期をラッチしたもの、トーン1、2、3                     | 174, 140, 140       |
| 減衰をラッチしたもの、トーン1、2、3とノイズ                   | 312, 312, 311, 312  |
| ノイズ制御をラッチしたもの                                    | 49                  |
| 周期のラッチのあとに2バイト目を送ったもの、トーン1、2、3      | 174, 140, 140       |
| 減衰のラッチのあとに2バイト目を送ったもの、トーン1、2とノイズ | 4, 4, 2             |
| ノイズ制御のラッチのあとに2バイト目を送ったもの               | 4                   |
| ノイズ制御0、3、4、5、6、7を書き込んだもの                    | 22, 8, 4, 3, 3, 13  |
| ノイズ制御1または2を書き込んだもの                            | 0                   |
| 減衰15でチャンネルをオフにしたもの                            | 313                 |
| 周期0を書き込んだもの                                         | 38                  |

全イメージを通じて、チップは1,629,574回の書き込みを受けました。そのうち市販イメージでの117,926回と、それ以外での873,222回は、前のバイトのロードが終わる前に届きました。

[`conformance/corpus.json`](conformance/corpus.json)はそれらの件数だけを保持し、カートリッジ由来のデータは何も含みません。そのため、ライブラリのないマシンでもテストスイートで件数を検証できます。

## 正しいかどうか

TIが記載した事実のうち、テストで到達できるものはすべてコードと照合しています。[`conformance/hardware.json`](conformance/hardware.json)は各事実をその文とページとともに保持し、[`conformance/hardware.test.py`](conformance/hardware.test.py)がそれらをパッケージ内の定数と比較します。`python3 -m conformance.quotes`は、引用した文のすべてをデータシート内で見つけます。

データシートに記載のない値はすべて、同じファイルの`notStated`の下に未検証として置かれ、その出典と、決着をつけるための測定が添えられています。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)にその一覧があります。データシートが自己矛盾している箇所は[`conformance/divergences.json`](conformance/divergences.json)にあります。

## 開発に参加する

| 必要なもの                                                 | 場所                                                                  |
| :--------------------------------------------------------- | :-------------------------------------------------------------------- |
| すべてのゲートと実行順序                                   | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| コーディングエージェント向けの同じ内容                     | [AGENTS.md](AGENTS.md)                                                |
| このリポジトリがファミリーのほかのリポジトリと共有する標準 | [FAMILY.md](FAMILY.md)                                                |
| バグ報告                                                   | [GitHub Issues](https://github.com/gufranco/ti-sn76489-python/issues) |
| セキュリティ報告                                           | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
python3 sn76489/core.test.py
```

各モジュールの隣には、そのモジュール名にちなんだテストファイルがあり、上のようにそれぞれ単独で実行できます。カバレッジはステートメントとブランチの100%を必須とするゲートです。

## 参考文献

- *SN76489AN Digital Complex Sound Generator*データシート、Texas Instruments、日付なし。9ページ、342,317バイト、SHA-256 `ad2b99beee0f4f7979828c4f3d9f2bf013deac39fa6263309875232e78a99f91`。再配布はできず、このリポジトリには含まれていません。知られている唯一のコピーはhttps://wiki.console5.com/tw/images/b/b0/SN76489.pdf にありますが、スクリプトでは通過できないチャレンジページの奥にあります。そのため、お手元のコピーを`docs/manufacturer/`に置いてください。`python3 -m conformance.documents --check`はそれ以外のファイルを拒否します。
- *SN76489AN Digital Complex Sound Generator*データシートの、後から手が加えられていない同じ版の2つ目のスキャン、Texas Instruments、日付なし。9ページ、1,711,168バイト、SHA-256 `af0a54394d3a92a50cbf25a13b384e8d44687cd2c58314d39cb15d58f6eba2d0`、https://github.com/MajicDesigns/MD_SN76489/raw/30b974c97d99aface74a780dec1046b308f48317/media/doc/SN76489AN%20DataSheet.pdf 。テキストレイヤーがないため、ページ画像として読んでいます。3ページと4ページにTIが実際に印刷した内容を確定します。`python3 -m conformance.documents`がこれを`docs/manufacturer/`に取得します。
- SMS Power、_SN76489_、https://www.smspower.org/Development/SN76489 。ノイズ用シフトレジスタと、単体チップの電源投入時の状態に使用しています。事実のみを利用し、コードは一切取り込んでいません。
- MAME、コミット`92f8878050f78c55c6961b688d4960b078150c6a`時点の`src/devices/sound/sn76496.cpp`、https://github.com/mamedev/mame 。データシートに記載のない動作に使用しています。事実のみを利用し、コードは一切取り込んでいません。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻印するスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
