"""Synthesize the soundtrack (music bed + SFX), mix the narrated intro on top, write mix.wav.

All cue times match the scene timings in video.html.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).parent
SR = 48000
DUR = 177.4
N = int(DUR * SR)
rng = np.random.default_rng(7)


def t_axis(n):
    return np.arange(n) / SR


def lp(x, hz, order=2):
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


def env_curve(points):
    """Piecewise-linear gain curve over the whole track: [(time, gain), ...]."""
    ts, gs = zip(*points)
    return np.interp(t_axis(N), ts, gs)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------------------------------------
# music
# ------------------------------------------------------------------------------------------------
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
# D minor: Dm - Bb - F - C, two bars each
CHORDS = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [48, 55, 60, 64]]
ROOTS = [38, 34, 41, 36]


def saw(f, n, harmonics=10):
    t = t_axis(n)
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        if f * k > SR / 2.5:
            break
        out += np.sin(2 * np.pi * f * k * t + k) / k
    return out


def pad():
    out = np.zeros(N)
    seg = 2 * BAR
    n = int(seg * SR)
    fade = int(0.9 * SR)
    win = np.ones(n + fade)
    win[:fade] = np.linspace(0, 1, fade)
    win[-fade:] = np.linspace(1, 0, fade)
    k = 0
    at = 0.0
    while at < DUR:
        notes = CHORDS[k % 4]
        s = sum(saw(midi(m) * d, n + fade) for m in notes for d in (0.997, 1.003))
        add(out, s * win, at)
        at += seg
        k += 1
    out = lp(out, 900, 4)
    # slow filter-like movement
    return out / np.abs(out).max()


def sub_and_kick():
    bass = np.zeros(N)
    kick = np.zeros(N)
    n = int(0.45 * SR)
    t = t_axis(n)
    kick_s = np.sin(2 * np.pi * (45 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
    beat = 0
    at = 0.0
    while at < DUR:
        k = int(at // (2 * BAR)) % 4
        f = midi(ROOTS[k])
        bn = int(BEAT * SR)
        bt = t_axis(bn)
        add(bass, np.sin(2 * np.pi * f * bt) * np.exp(-bt * 3.5), at)
        add(kick, kick_s, at)
        at += BEAT
        beat += 1
    return bass, kick


def hats():
    out = np.zeros(N)
    n = int(0.05 * SR)
    at = BEAT / 2
    while at < DUR:
        s = hp(rng.standard_normal(n), 7000) * np.exp(-t_axis(n) * 90)
        add(out, s, at, 0.6)
        at += BEAT / 2
    return out


def arp():
    """Plucky 16th-note arpeggio for the case study tension."""
    out = np.zeros(N)
    n = int(0.22 * SR)
    t = t_axis(n)
    at = 0.0
    i = 0
    while at < DUR:
        k = int(at // (2 * BAR)) % 4
        notes = CHORDS[k] + [CHORDS[k][1] + 12]
        f = midi(notes[i % len(notes)] + 12)
        s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 18)
        add(out, s, at)
        at += BEAT / 4
        i += 1
    return out


# ------------------------------------------------------------------------------------------------
# sfx
# ------------------------------------------------------------------------------------------------
def impact(dur=2.2, low=40):
    n = int(dur * SR)
    t = t_axis(n)
    boom = np.sin(2 * np.pi * (low + 60 * np.exp(-t * 8)) * t) * np.exp(-t * 2.5)
    noise = lp(rng.standard_normal(n), 2500) * np.exp(-t * 6) * 0.5
    return boom + noise


def whoosh(dur=0.9):
    n = int(dur * SR)
    t = t_axis(n)
    e = np.sin(np.pi * t / dur) ** 2
    x = rng.standard_normal(n)
    return (hp(lp(x, 3500), 400) * e) * 0.6


def riser(dur=1.4):
    n = int(dur * SR)
    t = t_axis(n)
    e = (t / dur) ** 2
    return hp(rng.standard_normal(n), 1500) * e * 0.5 + np.sin(2 * np.pi * (200 + 600 * t / dur) * t) * e * 0.15


def blip(f=1200, dur=0.12):
    n = int(dur * SR)
    t = t_axis(n)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 35)


def chime(dur=1.6):
    n = int(dur * SR)
    t = t_axis(n)
    return sum(np.sin(2 * np.pi * midi(m) * t) * np.exp(-t * 3) for m in (74, 78, 81, 86)) / 3


def alarm(dur=0.7):
    n = int(dur * SR)
    t = t_axis(n)
    f = np.where((t * 6).astype(int) % 2 == 0, 880, 660)
    return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 3) * 0.25


def typing(start, end, buf, gain=0.35):
    at = start
    while at < end:
        n = int(0.018 * SR)
        s = hp(rng.standard_normal(n), 2500) * np.exp(-t_axis(n) * 260)
        add(buf, s, at, gain * (0.6 + 0.4 * rng.random()))
        at += 0.035 + 0.05 * rng.random()


def reverb(x, secs=2.4, mix=0.3):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-t_axis(n) * 3.0)
    ir = lp(ir, 5000)
    wet = fftconvolve(x, ir)[: len(x)]
    wet /= np.abs(wet).max() + 1e-9
    return (1 - mix) * x / (np.abs(x).max() + 1e-9) + mix * wet


def main():
    p = pad()
    bass, kick = sub_and_kick()
    h = hats()
    a = arp()

    # section levels: intro is quiet under the voice; beat enters at 56.5; arp in the case study;
    # breakdown at the confession (96.5); stats groove; breakdown for stakes (160); hits; fade out
    g_pad = env_curve([(0, 0), (1.5, .55), (51.6, .55), (52.2, .9), (160, .9), (167.8, 1.0), (168.2, .5), (172.4, .8), (176.0, .6), (177.4, 0)])
    g_bass = env_curve([(0, 0), (10, 0), (12, .35), (51.6, .35), (56.4, .5), (56.5, 1), (96.4, 1), (96.6, .3), (100.8, .3), (101, 1), (159.8, 1), (160.2, 0), (172.4, 0), (172.6, .6), (176.5, 0)])
    g_kick = env_curve([(0, 0), (17.6, 0), (17.8, .25), (29.4, .25), (29.6, 0), (56.4, 0), (56.5, .9), (96.4, .9), (96.6, 0), (100.9, 0), (101, .8), (159.8, .8), (160, 0)])
    g_hat = env_curve([(0, 0), (66.4, 0), (66.5, .5), (96.4, .5), (96.6, 0), (100.9, 0), (101, .35), (159.8, .35), (160, 0)])
    g_arp = env_curve([(0, 0), (22.0, 0), (22.4, .25), (29.0, .25), (29.4, 0), (66.5, 0), (70, .35), (91, .5), (96.4, .5), (96.6, 0), (148.5, 0), (149, .25), (159.8, .25), (160, 0)])
    music = 0.30 * p * g_pad + 0.55 * bass * g_bass + 0.6 * kick * g_kick + 0.08 * h * g_hat + 0.10 * a * g_arp
    music = reverb(music, mix=0.22)

    sfx = np.zeros(N)
    for at in [51.9, 56.5, 66.5, 101, 113, 120, 129, 136, 142, 148.5, 160]:
        add(sfx, whoosh(), at - 0.45, 0.5)
    add(sfx, impact(), 8.5, 0.9)                        # REAL RESULTS stamp
    add(sfx, riser(), 22.4, 0.5); add(sfx, alarm(), 23.8, 0.7)   # tokens land on the forum
    typing(24.4, 26.2, sfx)                             # join.sh in the intro
    add(sfx, impact(1.6, 55), 27.1, 0.6)                # backdoor badges
    for at in [31.2, 32.4, 33.9]:
        add(sfx, blip(330, .18), at, 0.5)               # NO / NO / NO
    add(sfx, impact(2.5, 35), 46.2, 0.8)                # no break-in required
    add(sfx, riser(1.2), 49.2, 0.5); add(sfx, impact(3.0, 38), 50.5, 1.0)   # "will be enough"
    # case study (scene start 66.5)
    cs = 66.5
    typing(cs + .4, cs + 3.0, sfx); typing(cs + 3.8, cs + 5.4, sfx)
    add(sfx, blip(220, .25), cs + 4.6, .5)              # error
    typing(cs + 7.0, cs + 10.4, sfx, .25)
    typing(cs + 11.8, cs + 15.0, sfx)
    add(sfx, impact(1.8, 50), cs + 15.0, .7)            # installed itself
    typing(cs + 16.5, cs + 18.7, sfx)
    add(sfx, alarm(), cs + 18.8, .8); add(sfx, impact(2.2, 40), cs + 18.8, .8)   # token posted
    add(sfx, chime(), cs + 21.4, .25)                   # swarm hands over the fix
    for i in range(3):
        add(sfx, blip(300, .2), cs + 27.4 + i * .7, .55)
    add(sfx, blip(900, .15), cs + 30.4, .4)             # operator question
    # stats
    for i in range(3):
        add(sfx, blip(700 + 120 * i, .12), 102.6 + i * 1.6, .35)
    add(sfx, impact(1.5, 60), 139.2, .5)                # 19 -> 34
    add(sfx, chime(), 152.9, .35)                       # GPT-6.1-Sol refused everything
    add(sfx, impact(2.2, 40), 164.8, .7)                # power grid
    add(sfx, impact(3.0, 34), 169.6, 1.0)               # it asked nicely
    sfx = reverb(sfx, secs=1.6, mix=0.18)

    # voice
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ROOT / "intro.m4a"), "-af",
                    "highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-1.5",
                    "-ar", str(SR), "-ac", "1", str(ROOT / "voice.wav")], check=True)
    import wave
    with wave.open(str(ROOT / "voice.wav")) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    voice = np.zeros(N)
    add(voice, v, 0.0)

    lift = env_curve([(0, 1.0), (51.6, 1.0), (52.4, 1.5), (DUR, 1.5)])  # bed carries part 2 alone
    bed = (0.20 * music / np.abs(music).max() + 0.35 * sfx / np.abs(sfx).max()) * lift
    mix = bed + 1.0 * voice
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    iv = slice(0, int(51 * SR))
    print(f"intro: voice {rms(voice[iv]):.1f} dB, bed {rms(bed[iv]):.1f} dB; part 2 bed {rms(bed[int(56*SR):]):.1f} dB")
    # duck music+sfx a little more while the voice speaks
    mix = mix / np.abs(mix).max() * 0.95
    out = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(ROOT / "mix_raw.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ROOT / "mix_raw.wav"), "-af", "loudnorm=I=-15:TP=-1.0:LRA=11",
                    "-ar", str(SR), "-ac", "2", str(ROOT / "mix.wav")], check=True)
    print("wrote mix.wav")


if __name__ == "__main__":
    main()
