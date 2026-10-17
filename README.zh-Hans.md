# TI SN76489

用 Python 实现的 Texas Instruments SN76489AN 和 SN76494N 声音发生器，每次推进一个输入时钟，并以 TI 的数据手册为准。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-sn76489-python)](https://github.com/gufranco/ti-sn76489-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**348** 个不同的 SG-1000 镜像各启动 **600** 帧，**0** 个属性失败，在数据手册中定位到 **16** 处引文，**2** 款芯片，**592** 个测试，**100%** 语句和分支覆盖率，无依赖

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

芯片上电时每个寄存器的内容都是乱的，与分立芯片一样。两个字节将音调 1 的周期设为 5，第三个字节将其衰减设为 0，再用三个字节关闭其他通道。写入设置的是周期而不是计数器，所以第一次翻转最多可能在 1,024 个周期之后；此后触发器每 5 个周期翻转一次，即数据手册中的 `f = N/32n`。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更高 |
| git | 任意版本，用于获取子模块 |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-sn76489-python.git
cd ti-sn76489-python
python3 sn76489/doctor.py
```

该包不导入标准库以外的任何内容。子模块是 `ti-tms9918-python`，其中又包含 `zilog-z80-python`，只有普查会用到它们。通过下载 zip 链接获得的源码归档不含子模块：在那里普查及其测试会报告无法运行的原因，其余一切正常工作。

诊断脚本检查本机和检出的代码，最后输出一行。提交缺陷报告时请粘贴它的完整输出。

```
  10 checks, nothing to report
```

版本发布遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/ti-sn76489-python/releases)上。

## 接口

`sn76489.Chip(model, seed=UNSET_SEED)` 构建一颗芯片。`model` 为必填项。`seed` 设置每个寄存器、计数器、触发器以及移位寄存器的上电乱值。

| 型号 | 别名 | 输入时钟分频 | 载入一个字节所需的输入时钟数 |
|:--|:--|:--|:--|
| `sn76489an` | `sn76489a`、`76489an`、`76489a` | 16 | 32 |
| `sn76494n` | `sn76494`、`76494n`、`76494` | 2 | 4 |

### 调用

| 调用 | 作用 |
|:--|:--|
| `write(value)` | 在数据总线上放一个字节，同时选通 CE 和 WE。第 7 位置位的字节寻址一个寄存器并设置其低四位；第 7 位未置位的字节设置最后寻址的音调周期的高六位，或其他寄存器的四位。READY 变低 |
| `tick()` | 一个输入时钟 |
| `clock()` | 一个预分频周期：在 SN76489AN 上为 16 个输入时钟，在 SN76494N 上为 2 个 |
| `reset()` | 该芯片没有复位引脚，因此什么也不改变。返回该芯片。只有在软件写入全部 8 个寄存器，即 3 个周期、4 个衰减和噪声控制之后，芯片状态才确定 |

### 状态

| 属性 | 含义 |
|:--|:--|
| `ready` | READY 引脚：从一次写入起直到该字节载入完成为 false |
| `loading` | READY 变高之前剩余的输入时钟数 |
| `periods` | 三个音调周期，每个 10 位 |
| `steps` | 四个衰减级，0 为最大音量，15 为关闭 |
| `control` | 噪声控制：第 2 位选择白噪声，第 0 和第 1 位选择速率 |
| `shift` | 15 位噪声移位寄存器 |
| `latched` | 最后一个首字节所寻址的寄存器 |
| `bits` | 每个通道的输出位：三个触发器，然后是移位寄存器的第 0 位 |
| `gains` | 每个通道按 Table 1 的权重得出的增益，衰减级 0 时为 1.0，关闭时为 0.0 |
| `level` | 输出位为高的各通道增益之和 |
| `ticks` | 自芯片构建以来的输入时钟数 |
| `model` | 规范型号名 |
| `part` | `Model` 记录：`prescale`、`load_clocks`、`aliases`、`summary` |

### 模块内容

| 名称 | 内容 |
|:--|:--|
| `sn76489.MODELS` | 两条 `Model` 记录，以规范名称为键 |
| `sn76489.UnknownModelError` | 型号名缺失或未知时抛出。消息中列出可接受的名称 |
| `sn76489.UNSET_SEED` | 未提供种子时芯片用来生成乱值的种子 |
| `sn76489.__version__` | 已安装的版本 |

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

两款芯片的区别在于预分频器，以及载入一个字节所需的时钟数：32 对 4。同样是周期 3，音调 1 的触发器在 SN76489AN 上保持 48 个输入时钟，在 SN76494N 上保持 6 个。

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

## READY 与噪声发生器

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

一个字节选择 N/512 的白噪声。READY 在数据手册给出的载入所需的 32 个输入时钟内保持低电平，并且写入按数据手册的要求将移位寄存器清零，只保留最高位。此后寄存器每 32 个周期移位一次，即 512 个输入时钟。由于第 0 位和第 1 位都为 0，前四次移位每次都反馈一个零。

数据手册从未描述移位寄存器。它的宽度、抽头以及输出的取出位置来自 SMS Power 的笔记，这些笔记引用了在一台装有分立 SN76489AN 的 SC-3000H 上采集的数据。MAME 生成相同的序列，但输出晚两次移位。两者都记录在 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 中。

## 普查

```bash
python3 -m conformance.census /path/to/sg1000/library --frames 600 --jobs 10
```

SG-1000 软件只有在其处理器和视频芯片运行之后才会写入声音端口，因此普查在 [`ti-tms9918-python`](https://github.com/gufranco/ti-tms9918-python) 的 SG-1000 主板上启动每个镜像，使用 `zilog-z80-python` 处理器，并将本芯片置于端口 `0x40` 到 `0x7F`，每个处理器时钟推进一次。它接受目录、zip 归档和单个镜像，并按摘要对每个不同的镜像只计数一次。它打印一份摘要，写入 [`conformance/corpus.json`](conformance/corpus.json)，并在某个属性被破坏时以 1 退出。

两个属性作为本次运行的门禁检查：模型在任何镜像上都不抛出异常，并且移位寄存器从不变为零。在上一个字节载入完成之前进行的写入会按镜像计数并列出，但不作为门禁检查，因为数据手册没有说明芯片如何处理这些写入。

| 观察项 | 镜像数，共 348 个 |
|:--|:--|
| 从未写入声音端口 | 35 |
| 锁存了音调周期，音调 1、2 和 3 | 174, 140, 140 |
| 锁存了衰减，音调 1、2、3 和噪声 | 312, 312, 311, 312 |
| 锁存了噪声控制 | 49 |
| 在周期锁存之后发送了第二个字节，音调 1、2 和 3 | 174, 140, 140 |
| 在衰减锁存之后发送了第二个字节，音调 1、2 和噪声 | 4, 4, 2 |
| 在噪声控制锁存之后发送了第二个字节 | 4 |
| 写入了噪声控制 0、3、4、5、6 和 7 | 22, 8, 4, 3, 3, 13 |
| 写入了噪声控制 1 或 2 | 0 |
| 用衰减 15 关闭了某个通道 | 313 |
| 写入了为零的周期 | 38 |

在所有镜像上，芯片共接收了 1,629,574 次写入。其中零售版镜像上的 117,926 次和其余镜像上的 873,222 次是在上一个字节载入完成之前到达的。

[`conformance/corpus.json`](conformance/corpus.json) 保存了这些计数，不含任何卡带的内容，因此测试套件可以在没有库的机器上检查它们。

## 是否正确

TI 列出的、测试能够触及的每一项事实都与代码对照。[`conformance/hardware.json`](conformance/hardware.json) 记录每项事实及其原句和页码，[`conformance/hardware.test.py`](conformance/hardware.test.py) 将它们与包中的常量进行比较。`python3 -m conformance.quotes` 在数据手册中找出每一句引文。

数据手册未列出的每个值都放在同一文件的 `notStated` 下，标记为未验证，并附有其来源以及能够确定它的测量。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了这些值。数据手册自相矛盾之处记录在 [`conformance/divergences.json`](conformance/divergences.json) 中。

## 参与开发

| 需求 | 位置 |
|:--|:--|
| 所有门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编码代理的同一份内容 | [AGENTS.md](AGENTS.md) |
| 本仓库与该系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| 缺陷报告 | [GitHub Issues](https://github.com/gufranco/ti-sn76489-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 sn76489/core.test.py
```

每个模块旁边都有一个以其命名的测试文件，每个测试文件都可以像上面那样单独运行。覆盖率是硬性门禁检查，要求语句和分支均达到 100%。

## 参考资料

- *SN76489AN Digital Complex Sound Generator* 数据手册，Texas Instruments，未注明日期。9 页，342,317 字节，SHA-256 `ad2b99beee0f4f7979828c4f3d9f2bf013deac39fa6263309875232e78a99f91`。该手册不可再分发，也不在本仓库中。已知唯一的副本位于 https://wiki.console5.com/tw/images/b/b0/SN76489.pdf ，其前面有一个脚本无法通过的验证页面，因此请将你的副本放入 `docs/manufacturer/`，`python3 -m conformance.documents --check` 会拒绝任何其他文件。
- SMS Power，*SN76489*，https://www.smspower.org/Development/SN76489 ，用于噪声移位寄存器和分立芯片的上电状态。只取事实，不取任何代码。
- MAME，提交 `92f8878050f78c55c6961b688d4960b078150c6a` 中的 `src/devices/sound/sn76496.cpp`，https://github.com/mamedev/mame ，用于数据手册未说明的行为。只取事实，不取任何代码。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本号的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
