# TI SN76489

以 Python 實現的 Texas Instruments SN76489AN 和 SN76494N 聲音產生器，每次推進一個輸入時鐘，並以 TI 的數據表為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/ti-sn76489-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/ti-sn76489-python?style=flat-square&label=release)](https://github.com/gufranco/ti-sn76489-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/ti-sn76489-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/ti-sn76489-python)
[![license](https://img.shields.io/github/license/gufranco/ti-sn76489-python?style=flat-square&label=license)](LICENSE)

**348** 個不同的 SG-1000 映像檔各啟動 **600** 幀，屬性失敗為 **0**，在數據表中找到 **17** 處引文，**2** 款晶片，**701** 個測試，**100%** 語句和分支覆蓋率，沒有依賴套件

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

晶片上電時每個暫存器的內容都是亂的，與分立晶片一樣。兩個位元組將音調 1 的週期設為 5，第三個位元組將其衰減設為 0，另外三個位元組關閉其他聲道。寫入設定的是週期，而不是計數器，所以第一次翻轉最多可能在 1,024 個週期之後；此後正反器每 5 個週期翻轉一次，即數據表中的 `f = N/32n`。

## 安裝

| 要求   | 版本                     |
| :----- | :----------------------- |
| Python | 3.12 或更新              |
| git    | 任何版本，用於取得子模組 |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-sn76489-python.git
cd ti-sn76489-python
python3 sn76489/doctor.py
```

套件只匯入標準程式庫。子模組是 `ti-tms9918-python`，其中又包含 `zilog-z80-python`，只有普查會使用它們。從下載 zip 連結取得的原始碼封存檔沒有子模組：此時普查及其測試會報告無法執行的原因，其他一切正常運作。

診斷腳本檢查機器和簽出的程式碼，最後輸出一行結果。提交錯誤報告時，請貼上它的完整輸出。

```
  10 checks, nothing to report
```

版本發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列在[版本發佈頁面](https://github.com/gufranco/ti-sn76489-python/releases)上。

## 介面

`sn76489.Chip(model, seed=UNSET_SEED)` 建立一款晶片。`model` 為必填。`seed` 設定每個暫存器、計數器、正反器以及移位暫存器的上電亂數。

| 型號        | 別名                            | 輸入時鐘的除數 | 載入一個位元組所需的輸入時鐘數 |
| :---------- | :------------------------------ | :------------- | :----------------------------- |
| `sn76489an` | `sn76489a`、`76489an`、`76489a` | 16             | 32                             |
| `sn76494n`  | `sn76494`、`76494n`、`76494`    | 2              | 4                              |

### 呼叫

| 呼叫           | 作用                                                                                                                                                                                                               |
| :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `write(value)` | 在 CE 和 WE 選通的情況下，向數據匯流排送出一個位元組。第 7 位元為 1 的位元組會定址一個暫存器並設定其低四位元；第 7 位元為 0 的位元組會設定最後定址的音調週期的高六位元，或任何其他暫存器的四個位元。READY 隨即下降 |
| `tick()`       | 一個輸入時鐘                                                                                                                                                                                                       |
| `clock()`      | 一個預分頻週期：SN76489AN 上為 16 個輸入時鐘，SN76494N 上為 2 個                                                                                                                                                   |
| `reset()`      | 晶片沒有重設針腳，所以任何內容都不會改變。返回該晶片。只有在軟件寫入全部 8 個暫存器，即 3 個週期、4 個衰減和噪音控制之後，晶片狀態才確定                                                                           |

### 狀態

| 屬性      | 含義                                                                 |
| :-------- | :------------------------------------------------------------------- |
| `ready`   | READY 針腳：從寫入起直到該位元組載入完成為止都是 false               |
| `loading` | READY 上升前剩餘的輸入時鐘數                                         |
| `periods` | 三個音調週期，各 10 位元                                             |
| `steps`   | 四個衰減級別，0 為最大音量，15 為關閉                                |
| `control` | 噪音控制：第 2 位元選擇白噪音，第 0 和第 1 位元選擇速率              |
| `shift`   | 15 位元的噪音移位暫存器                                              |
| `latched` | 最近一個首位元組所定址的暫存器                                       |
| `bits`    | 每個聲道的輸出位元：先是三個正反器，然後是移位暫存器的第 0 位元      |
| `gains`   | 每個聲道根據 Table 1 的權重得出的增益，級別 0 時為 1.0，關閉時為 0.0 |
| `level`   | 位元為高電平的各聲道增益之和                                         |
| `ticks`   | 自晶片建立以來的輸入時鐘數                                           |
| `model`   | 標準型號名稱                                                         |
| `part`    | `Model` 記錄：`prescale`、`load_clocks`、`aliases`、`summary`        |

### 模組內容

| 名稱                        | 內容                                             |
| :-------------------------- | :----------------------------------------------- |
| `sn76489.MODELS`            | 兩個 `Model` 記錄，以標準名稱為鍵                |
| `sn76489.UnknownModelError` | 型號名稱缺失或未知時拋出。訊息會列出可接受的名稱 |
| `sn76489.UNSET_SEED`        | 未提供種子時，晶片產生亂數所用的種子             |
| `sn76489.__version__`       | 已安裝的版本                                     |

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

兩款晶片的分別在於預分頻器，以及載入一個字節所需的時鐘數：32 對 4。同樣是週期 3，音調 1 的正反器在 SN76489AN 上保持 48 個輸入時鐘，在 SN76494N 上則保持 6 個。

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

## READY 與噪音產生器

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

一個位元組選擇 N/512 的白噪音。READY 在數據表為一次載入列出的 32 個輸入時鐘內保持低電平，而寫入會按數據表的要求，將移位暫存器清除至只剩最高位元。之後暫存器每 32 個週期移位一次，即每 512 個輸入時鐘一次。由於第 0 和第 1 位元都為 0，最初四次移位每次都回饋一個 0。

數據表從未描述移位暫存器。其寬度、抽頭以及輸出的取出位置均來自 SMS Power 的筆記，這些筆記引用了在一部裝有分立 SN76489AN 的 SC-3000H 上取得的數據。MAME 產生相同的序列，但輸出晚兩次移位。兩者都記錄在 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。

## 普查

```bash
python3 -m conformance.census "external/SG-1000" --frames 600 --jobs 10
```

SG-1000 軟件要等其處理器和視像晶片運行後才會寫入聲音埠，所以普查在 [`ti-tms9918-python`](https://github.com/gufranco/ti-tms9918-python) 的 SG-1000 主機板上啟動每個映像檔，配合 `zilog-z80-python` 處理器，並將本晶片置於埠 `0x40` 至 `0x7F`，每個處理器時鐘推進一次。它接受目錄、zip 封存檔和單個映像檔，並按摘要值將每個不同的映像檔只計算一次。它會列印摘要，寫入 [`conformance/corpus.json`](conformance/corpus.json)，並在任何屬性失敗時以 1 退出。

兩項屬性作為本次執行的關卡檢查：模型在任何映像檔上都不拋出例外，以及移位暫存器永遠不會變為零。在上一個位元組載入完成之前進行的寫入會按映像檔計數並列出名稱，但不作關卡檢查，因為數據表沒有說明晶片如何處理這些寫入。

| 觀察結果                                       | 映像檔數，共 348 個 |
| :--------------------------------------------- | :------------------ |
| 從未寫入聲音埠                                 | 35                  |
| 鎖存了音調週期，音調 1、2 和 3                 | 174, 140, 140       |
| 鎖存了衰減，音調 1、2、3 和噪音                | 312, 312, 311, 312  |
| 鎖存了噪音控制                                 | 49                  |
| 在週期鎖存後送出第二個位元組，音調 1、2 和 3   | 174, 140, 140       |
| 在衰減鎖存後送出第二個位元組，音調 1、2 和噪音 | 4, 4, 2             |
| 在噪音控制鎖存後送出第二個位元組               | 4                   |
| 寫入噪音控制 0、3、4、5、6 和 7                | 22, 8, 4, 3, 3, 13  |
| 寫入噪音控制 1 或 2                            | 0                   |
| 以衰減 15 關閉一個聲道                         | 313                 |
| 寫入為零的週期                                 | 38                  |

在所有映像檔上，晶片共接受 1,629,574 次寫入。其中零售版映像檔上的 117,926 次和其餘映像檔上的 873,222 次，都在上一個位元組載入完成之前到達。

[`conformance/corpus.json`](conformance/corpus.json) 只保存這些數字，不包含任何卡帶的內容，所以測試套件在沒有映像檔庫的機器上也能檢查它們。

## 是否正確

TI 列出的每個測試可觸及的事實，都以程式碼加以核對。[`conformance/hardware.json`](conformance/hardware.json) 記載每個事實及其原句和頁碼，[`conformance/hardware.test.py`](conformance/hardware.test.py) 將它們與套件中的常數比較。`python3 -m conformance.quotes` 會在數據表中找出每一句引文。

數據表沒有列出的每個數值都放在同一檔案的 `notStated` 下，標示為未經核實，並附有來源及能確定它的量度方法。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了這些數值。數據表自相矛盾之處記錄在 [`conformance/divergences.json`](conformance/divergences.json)。

## 參與開發

| 需要                                 | 位置                                                                  |
| :----------------------------------- | :-------------------------------------------------------------------- |
| 每項關卡檢查及其執行次序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 供程式編寫代理使用的相同資料         | [AGENTS.md](AGENTS.md)                                                |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md)                                                |
| 錯誤報告                             | [GitHub Issues](https://github.com/gufranco/ti-sn76489-python/issues) |
| 安全報告                             | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
python3 sn76489/core.test.py
```

每個模組旁邊都有一個以其命名的測試檔案，每個都可以如上所示獨立執行。覆蓋率是硬性關卡檢查，要求 100% 語句和分支覆蓋率。

## 參考資料

- _SN76489AN Digital Complex Sound Generator_ 數據表，Texas Instruments，無日期。9 頁，342,317 位元組，SHA-256 `ad2b99beee0f4f7979828c4f3d9f2bf013deac39fa6263309875232e78a99f91`。它不可再分發，也不在本儲存庫中。目前已知的唯一副本位於 https://wiki.console5.com/tw/images/b/b0/SN76489.pdf ，前面有一個腳本無法通過的驗證頁面，所以請將你的副本放在 `docs/manufacturer/`，`python3 -m conformance.documents --check` 會拒絕任何其他檔案。
- _SN76489AN Digital Complex Sound Generator_ 數據表的第二份掃描，屬同一印刷版本，沒有後人改動，Texas Instruments，無日期。9 頁，1,711,168 位元組，SHA-256 `af0a54394d3a92a50cbf25a13b384e8d44687cd2c58314d39cb15d58f6eba2d0`，位於 https://github.com/MajicDesigns/MD_SN76489/raw/30b974c97d99aface74a780dec1046b308f48317/media/doc/SN76489AN%20DataSheet.pdf 。它沒有文字層，所以按頁面圖像閱讀。它確定了 TI 在第 3 頁和第 4 頁實際印刷的內容。`python3 -m conformance.documents` 會把它取到 `docs/manufacturer/`。
- SMS Power，_SN76489_，https://www.smspower.org/Development/SN76489 ，用於噪音移位暫存器和分立晶片的上電狀態。只取事實，沒有採用任何程式碼。
- MAME，`src/devices/sound/sn76496.cpp`，提交 `92f8878050f78c55c6961b688d4960b078150c6a`，https://github.com/mamedev/mame ，用於數據表沒有說明的行為。只取事實，沒有採用任何程式碼。

## 引用本專案

[CITATION.cff](CITATION.cff) 在每次版本發佈時，由標記套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
