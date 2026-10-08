import subprocess, sys
from pathlib import Path
fs = sorted(Path("stills").glob("*.png"))
for s in range(0, len(fs), 4):
    ch = fs[s:s+4]
    args = []
    for f in ch: args += ["-i", str(f)]
    for _ in range(4 - len(ch)): args += ["-f", "lavfi", "-i", "color=black:s=1920x1080", "-frames:v", "1"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex",
                    "[0][1][2][3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0,scale=1920:1080", "-frames:v", "1", f"sheet{s//4}.png"], check=True)
    print(f"sheet{s//4}.png", [f.name for f in ch])
