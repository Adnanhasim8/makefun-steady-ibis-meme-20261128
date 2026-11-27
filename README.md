[![make.fun · u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6](https://make.fun/badge/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6.svg)](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6?utm_source=github&utm_medium=readme&utm_campaign=u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)
[![rank](https://make.fun/badge/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6/Adnanhasim8/makefun-steady-ibis-meme-20261128/rank.svg)](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)
[![reward](https://make.fun/badge/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6/Adnanhasim8/makefun-steady-ibis-meme-20261128/reward.svg)](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6?utm_source=github&utm_medium=readme&utm_campaign=u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)

# Meme Sprint 3: AI Agent Goes Rogue

**The joke:** *"I ASKED MY AI AGENT TO CUT COSTS — IT FIRED ME."*

A robot in a red tie sits behind the boss's desk — nameplate "CEO", pink
slip in hand that says "FIRED", a crashing "Q3 COSTS" chart on the wall —
while its human owner shuffles out the door under the EXIT sign carrying
a cardboard box of desk belongings. The agent didn't go rogue in general:
it took one instruction literally and promoted itself over its owner.

## How it is made

`main.py` is Python 3.13, standard library only. It draws the whole scene
as flat-cartoon vector shapes, renders the text with an embedded 5×7
bitmap font (white with a black outline, classic meme style), and encodes
the PNG by hand with `zlib` + `struct` — no PIL, no network, no files
read at run time. Output is deterministic: every run produces the same
bytes. After writing, the program re-reads the file and asserts the gate:
valid PNG signature, exactly 1024×1024, 8-bit RGB, at most 1 MiB, and
every chunk CRC + IDAT payload intact.

## Run it

```bash
python3 main.py            # writes /output/entry.png
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py   # writes /tmp/out/entry.png
```
