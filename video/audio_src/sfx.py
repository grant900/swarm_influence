import numpy as np
from dsp import *

rng = np.random.default_rng(5)
PK = -6.0


def stereo_from(mono, width=0.0, delay_ms=0.0):
    if delay_ms:
        d = int(delay_ms * SR / 1000)
        r = np.concatenate([np.zeros(d), mono[:-d]])
    else:
        r = mono
    return np.stack([mono, r])


def tail_reverb(x, rt, wet, damp=5000, seed=1):
    pad = np.zeros((2, x.shape[1] + int(rt * SR * 0.5)))
    pad[:, :x.shape[1]] = x
    w = reverb(pad, rt, damp, seed)
    return pad + wet * w


def fit(x, dur, fout_ms=15, fin_ms=0.5):
    n = int(dur * SR)
    x = x[:, :n] if x.shape[1] >= n else np.pad(x, ((0, 0), (0, n - x.shape[1])))
    return edge_fade(x, fin_ms, fout_ms)


# ---- whoosh 0.8 s
def whoosh():
    n = int(0.8 * SR); t = np.arange(n) / SR; u = t / 0.8
    fc = 250 * (5000 / 250) ** np.sin(np.pi * np.clip(u * 1.1, 0, 1) ** 0.8 * 0.5 * 2 / 2 * 1.0) if False else 300 * (4500 / 300) ** (np.sin(np.pi * u) ** 0.9)
    env = np.sin(np.pi * np.clip(u ** 0.7, 0, 1)) ** 1.6
    env = 0.06 + 0.94 * env  # audible at t=0 but soft
    chans = []
    for c in range(2):
        nz = rng.standard_normal(n)
        chans.append(tv_biquad(nz, fc, 1.1, "bp") * env)
    x = np.stack(chans)
    p = (np.sin(np.pi * u / 2) ** 2)  # pan L->R
    x[0] *= np.cos(p * np.pi / 2 * 0.5 + 0.1); x[1] *= np.sin(p * np.pi / 2 * 0.5 + 0.55)
    x = x + 0.0
    return fit(x, 0.8, 80, 0.8)


# ---- impact 2.5 s
def impact():
    b = boom(2.5, 0.75, 70, 26, seed=9)
    clack = tick_burst(2500, 0.03, 0.01, seed=4) * 0.7
    x = b.copy(); x[:len(clack)] += clack
    x = stereo_from(x, 0, 0.7)
    x = tail_reverb(x, 1.8, 0.45, 4500, 70)
    return fit(x, 2.5, 400, 0.5)


# ---- single key click 0.06 s
def click(f=2400, bright=1.0, gain=1.0, seed=0, dur=0.06):
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    nz = r.standard_normal(n)
    nzf = signal.sosfilt(signal.butter(2, [f * 0.6, min(f * 1.8, 12000)], "bandpass", fs=SR, output="sos"), nz)
    s = nzf * np.exp(-t / 0.0025) * bright
    s += 0.9 * np.sin(TWO_PI * (f * 0.09) * t) * np.exp(-t / 0.009)    # body thock
    s += 0.35 * np.sin(TWO_PI * f * 0.45 * t) * np.exp(-t / 0.005)
    return edge_fade(s * gain, 0.2, 12)


def sfx_type():
    x = click(2600, 1.0, 1.0, 1)
    return fit(stereo_from(x, 0, 0.0), 0.06, 12, 0.2)  # review fix


def typing_burst():
    n = int(1.5 * SR); x = np.zeros((2, n))
    t = 0.0
    while t < 1.3:
        f = rng.uniform(1900, 3200); g = rng.uniform(0.5, 1.0)
        place(x, click(f, rng.uniform(0.8, 1.2), 1.0, int(rng.integers(1, 10_000))), t, rng.uniform(-0.3, 0.3), g)
        t += rng.choice([0.045, 0.07, 0.09, 0.13, 0.2, 0.06]) * rng.uniform(0.8, 1.25)
    x = tail_reverb(x, 0.35, 0.18, 6000, 80)
    return fit(x, 1.5, 100, 0.2)


# ---- blip 0.25
def blip():
    n = int(0.25 * SR); t = np.arange(n) / SR
    def note(f, t0, tau):
        s = np.zeros(n)
        m = t >= t0
        tt = np.where(m, t - t0, 0)
        s += (np.sin(TWO_PI * f * tt) + 0.25 * np.sin(TWO_PI * 2 * f * tt) + 0.08 * np.sin(TWO_PI * 3 * f * tt)) * np.exp(-tt / tau) * m * (1 - np.exp(-tt / 0.002))
        return s
    s = note(988, 0.0, 0.06) + 0.85 * note(1319, 0.08, 0.07)
    x = stereo_from(s, 0, 0.0)  # review fix: no L/R delay (mono comb)
    x = tail_reverb(x, 0.4, 0.2, 6000, 90)
    return fit(x, 0.25, 90, 0.5)


# ---- alert 0.8
def alert():
    n = int(0.8 * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for f, t0, tau in ((392.0, 0.0, 0.22), (277.2, 0.34, 0.3)):
        m = t >= t0; tt = np.where(m, t - t0, 0)
        vib = 1 + 0.004 * np.sin(TWO_PI * 5.5 * tt)
        ph = TWO_PI * f * tt * vib
        v = sum(k ** -1.1 * np.sin(k * ph) for k in range(1, 9))
        v = np.tanh(2.2 * v / 2.0)
        v = filt(v, "low", 2600, 2)
        s += v * np.exp(-tt / tau) * m * (1 - np.exp(-tt / 0.006)) * 0.9
        s += 0.4 * np.sin(TWO_PI * f / 2 * tt) * np.exp(-tt / tau) * m * (1 - np.exp(-tt / 0.01))  # sub octave
    x = stereo_from(s, 0, 0.6)
    x = tail_reverb(x, 0.8, 0.22, 4500, 95)
    return fit(x, 0.8, 120, 0.5)


# ---- stamp 0.6
def stamp():
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = 52 + 90 * np.exp(-t / 0.03)
    body = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    res = 0.35 * np.sin(TWO_PI * 185 * t) * np.exp(-t / 0.06)
    paper = filt(rng.standard_normal(n), "band" if False else "high", 1800) * np.exp(-t / 0.012)
    paper = filt(paper, "low", 7000)
    thump = filt(rng.standard_normal(n), "low", 400, 2) * np.exp(-t / 0.03)
    s = 1.1 * body + res + 0.35 * paper + 0.8 * thump
    s = np.tanh(1.5 * s)
    x = stereo_from(s, 0, 0.4)
    x = tail_reverb(x, 0.5, 0.15, 3500, 110)
    return fit(x, 0.6, 120, 0.4)


# ---- riser 3.0 s ending abruptly
def riser():
    T = 3.0; n = int(T * SR); t = np.arange(n) / SR; u = t / T
    chans = []
    for c in range(2):
        nz = rng.standard_normal(n)
        fc = 200 * (9000 / 200) ** u
        chans.append(tv_biquad(nz, fc, 1.3, "bp"))
    noise = np.stack(chans)
    f = 90 * 10 ** u
    ph = TWO_PI * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.5 * np.sin(2.005 * ph) + 0.25 * np.sin(3.01 * ph)
    trem = 1 - 0.3 * (0.5 + 0.5 * np.sin(TWO_PI * np.cumsum(2 + 12 * u ** 2) / SR))
    sub = np.sin(TWO_PI * np.cumsum(35 + 30 * u) / SR) * u ** 2
    x = (noise * 3.0 * u ** 2.2 + tone * 0.5 * u ** 2.5 + 0.5 * sub) * trem
    x = edge_fade(x, 30, 25)  # review fix: softer end
    return x


# ---- data 1.2 s
def data():
    n = int(1.2 * SR); x = np.zeros((2, n))
    t = 0.0
    freqs = np.array([880, 1175, 1568, 1760, 2349, 3136, 3520, 4699])
    while t < 1.1:
        dur = rng.choice([0.018, 0.025, 0.035, 0.05])
        m = int(dur * SR); tt = np.arange(m) / SR
        f0 = rng.choice(freqs); f1 = f0 * rng.choice([1.0, 1.0, 1.5, 0.75, 2.0])
        f = f0 + (f1 - f0) * tt / dur
        s = np.sin(TWO_PI * np.cumsum(f) / SR)
        if rng.random() < 0.35:  # bit-crushed grit
            s = np.round(s * 5) / 5
        s *= np.sin(np.pi * tt / dur) ** 2
        u = t / 1.1
        env = (0.5 + 0.5 * np.sin(np.pi * np.clip(u * 1.2, 0, 1) * 0.5 + 0.0)) * (1 - 0.6 * u ** 2)
        pan = -0.7 + 1.4 * u   # drifts left -> right
        place(x, s, t, pan, 0.45 * env * rng.uniform(0.6, 1.0))
        t += dur * rng.uniform(0.6, 1.4) + rng.choice([0, 0, 0.01, 0.03])
    x = edge_fade(x, 0.5, 100)
    x = tail_reverb(x, 0.4, 0.12, 6000, 120)
    # slight echo
    d = int(0.09 * SR); y = x.copy(); y[:, d:] += 0.3 * x[:, :-d][:, ::1] * 1.0
    return fit(y, 1.2, 200, 0.3)


# ---- tick 0.05
def tick():
    n = int(0.05 * SR); t = np.arange(n) / SR
    s = np.sin(TWO_PI * 1900 * t) * np.exp(-t / 0.006) + 0.35 * np.sin(TWO_PI * 3800 * t) * np.exp(-t / 0.003)
    s += 0.12 * filt(np.random.default_rng(2).standard_normal(n), "high", 4000) * np.exp(-t / 0.002)
    return fit(stereo_from(s, 0, 0.0), 0.05, 12, 0.3)  # review fix


# ---- glitch 0.5
def glitch():
    r = np.random.default_rng(8)
    n = int(0.5 * SR); x = np.zeros((2, n))
    # source fragment: noisy chirp
    m = int(0.045 * SR); tt = np.arange(m) / SR
    src = np.sin(TWO_PI * np.cumsum(600 + 3500 * tt / 0.045) / SR) + 0.4 * filt(r.standard_normal(m), "band" if False else "high", 2500)
    src = src * np.sin(np.pi * np.arange(m) / m) ** 0.5
    t = 0.0; gap = 0.07; i = 0
    while t < 0.42:
        seg = src.copy()
        if i % 2: seg = seg[::-1]
        q = r.choice([4, 6, 10, 24]); seg = np.round(seg * q) / q
        ln = int(m * r.choice([1.0, 0.7, 0.45, 0.3]))
        seg = edge_fade(seg[:ln], 1, 2)
        place(x, seg, t, r.uniform(-0.8, 0.8), 0.7 * (1 - t / 0.55))
        t += max(gap, 0.014); gap *= 0.82; i += 1
    # fading tail buzz
    bz = np.sin(TWO_PI * 140 * np.arange(n) / SR) * np.exp(-np.arange(n) / SR / 0.1) * 0.2
    x += bz
    x = filt(x, "low", 9000)
    return fit(x, 0.5, 60, 0.3)


for name, fn in [("sfx_whoosh", whoosh), ("sfx_impact", impact), ("sfx_type", sfx_type), ("sfx_typing_burst", typing_burst),
                 ("sfx_blip", blip), ("sfx_alert", alert), ("sfx_stamp", stamp), ("sfx_riser", riser),
                 ("sfx_data", data), ("sfx_tick", tick), ("sfx_glitch", glitch)]:
    x = fn()
    x = edge_fade(signal.sosfilt(sos("high", 25, 2), x, axis=-1), 0.4, 0)
    write_wav(name + ".wav", x, peak_db=PK)
