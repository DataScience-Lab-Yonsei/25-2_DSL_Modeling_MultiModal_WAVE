#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
midi_render.py  —  v2-soft one-shot renderer
- 단일 샘플(SFZ) 기반의 간단 샘플러로 MIDI를 렌더하고,
  HPF → 노이즈게이트 → 소량 리버브 → 리미터의 "soft master" 체인을 거쳐
  /root/wave/result/{song}_result.wav 로 저장합니다.
- 경로 하드코딩 없음. --out 미지정 시에만 위 기본 경로를 사용합니다.
"""
import os, re, glob, argparse, math
import numpy as np
import soundfile as sf
from scipy.signal import butter, filtfilt, resample_poly
import pretty_midi as pm

# ---- 내부 유틸 -------------------------------------------------------------
def db_to_lin(db): return 10.0 ** (db / 20.0)

def ensure_dir(p):
    d = os.path.dirname(p)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def resample_to_sr(y, orig_sr, target_sr):
    if orig_sr == target_sr: return y
    g = math.gcd(orig_sr, target_sr)
    up, down = target_sr // g, orig_sr // g
    y = resample_poly(y, up, down).astype(np.float32)
    return y

def normalize_peak(y, peak=0.999):
    m = np.max(np.abs(y)) if y.size else 0.0
    if m > 0: y = (y / m) * float(peak)
    return y.astype(np.float32)

# ---- 간단한 피치시프트(타임보존): rubberband 있으면 사용, 없으면 2-단계 resample 근사 ----
def pitch_shift(y, sr, n_steps):
    try:
        import pyrubberband as rb
        return rb.pitch_shift(y, sr, n_steps).astype(np.float32)
    except Exception:
        # 폴백: librosa의 타임-보존 피치시프트 사용
        try:
            import librosa
            return librosa.effects.pitch_shift(y.astype(np.float32), sr, n_steps).astype(np.float32)
        except Exception:
            # 최후의 안전장치: 너무 짧으면 그대로 반환
            if y is None or len(y) < 64:
                return np.array(y, dtype=np.float32) if y is not None else np.zeros(1, dtype=np.float32)
            # (가능하면 rubberband-cli 설치 권장: apt-get install -y rubberband-cli)
            return y.astype(np.float32)

# ---- 간단한 ADSR, 루프 타일링 ---------------------------------------------
def make_adsr(total_samples, sr, a_ms=5.0, r_ms=40.0):
    s = int(max(1, total_samples))
    a = int(max(0, round(sr * a_ms / 1000.0)))
    r = int(max(0, round(sr * r_ms / 1000.0)))

    # 노트 길이보다 attack/release가 길지 않도록 보정
    if a > s:
        a = s
    if r > s - a:
        r = max(0, s - a)

    env = np.ones(s, dtype=np.float32)
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a, endpoint=False, dtype=np.float32)
    if r > 0:
        env[-r:] = np.linspace(1.0, 0.0, r, endpoint=True, dtype=np.float32)
    return env

def tile_to_length(wav, target_len, loop=None):
    """loop=(start,end) 샘플 인덱스. 없으면 제로패딩."""
    if len(wav) >= target_len:
        return wav[:target_len].astype(np.float32)
    if loop and loop[1] - loop[0] > 1024:
        head = wav[:loop[0]]
        body = wav[loop[0]:loop[1]]
        remain = target_len - len(head)
        tiles = []
        while sum(len(t) for t in tiles) < remain:
            tiles.append(body)
        mid = np.concatenate(tiles, axis=0)[:remain]
        out = np.concatenate([head, mid], axis=0)
        return out.astype(np.float32)
    # no loop → pad
    out = np.zeros(target_len, dtype=np.float32)
    out[:len(wav)] = wav
    return out

# ---- SFZ region 1개만 파싱 -------------------------------------------------
_sfz_re = re.compile(r"(sample|pitch_keycenter|loop_start|loop_end|pitch_keytrack)\s*=\s*([^\s]+)")
def read_sfz_single_region(sfz_dir):
    sfz_path = os.path.join(sfz_dir, "Instrument.sfz")
    if not os.path.exists(sfz_path):
        raise FileNotFoundError(f"SFZ not found: {sfz_path}")
    sample = None; keycenter = 60; loop = None; keytrack = 1
    with open(sfz_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    # 첫 region 블럭만 대강 파싱
    for k, v in _sfz_re.findall(text):
        k = k.strip(); v = v.strip()
        if k == "sample":
            sample = os.path.join(sfz_dir, v) if not os.path.isabs(v) else v
        elif k == "pitch_keycenter":
            try: keycenter = int(v)
            except: pass
        elif k == "loop_start":
            loop = [int(v), None] if loop is None else [int(v), loop[1]]
        elif k == "loop_end":
            loop = [None, int(v)] if loop is None else [loop[0], int(v)]
        elif k == "pitch_keytrack":
            try: keytrack = int(v)
            except: pass
    if loop is not None and (loop[0] is None or loop[1] is None):
        loop = None
    if sample is None:
        # 폴더 내 가장 큰 오디오 파일
        cands = sorted(glob.glob(os.path.join(sfz_dir, "*.*")), key=os.path.getsize, reverse=True)
        for p in cands:
            if os.path.splitext(p)[1].lower() in (".wav", ".flac", ".aiff", ".aif"):
                sample = p; break
    if sample is None:
        raise RuntimeError(f"No sample in {sfz_dir}")
    return sample, keycenter, loop, keytrack

class Sampler:
    def __init__(self, sfz_dir, target_sr=48000):
        self.sample_path, self.keycenter, self.loop, self.keytrack = read_sfz_single_region(sfz_dir)
        y, sr = sf.read(self.sample_path, always_2d=False)
        if y.ndim > 1: y = y.mean(axis=1)
        y = y.astype(np.float32)
        self.orig_sr = sr
        self.sample = resample_to_sr(y, sr, target_sr)
        self.sr = target_sr
        self.cache = {}  # midi -> wav

    def note(self, midi, dur_s, velocity=100):
        if dur_s <= 0: return np.zeros(1, dtype=np.float32)
        n_steps = (midi - self.keycenter) if self.keytrack != 0 else 0
        key = (int(round(n_steps)), int(round(dur_s * self.sr)), int(velocity))
        if key in self.cache: return self.cache[key]
        # 피치
        if n_steps != 0:
            src = pitch_shift(self.sample, self.sr, n_steps)
        else:
            src = self.sample
        # 길이
        target_len = int(round(dur_s * self.sr))
        wav = tile_to_length(src, target_len, loop=self.loop)
        # 벨로시티
        gain = (velocity / 127.0) ** 1.3
        env  = make_adsr(len(wav), self.sr)
        out  = (wav * env * gain).astype(np.float32)
        self.cache[key] = out
        return out

# ---- Soft Master 체인 ------------------------------------------------------
def hpf(y, sr, hz=30.0, order=2):
    b, a = butter(order, hz / (sr * 0.5), btype='highpass')
    return filtfilt(b, a, y).astype(np.float32)

def noise_gate(y, sr, thresh_db=-45.0, win_ms=20.0):
    win = max(1, int(sr * win_ms / 1000.0))
    # 거친 RMS
    pad = np.pad(y, (win//2, win - win//2), mode='reflect')
    cumsum = np.cumsum(pad.astype(np.float64)**2)
    rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    rms = np.concatenate([rms[:len(y)], np.full(max(0, len(y)-len(rms)), rms[-1] if len(rms)>0 else 0)])
    thr = db_to_lin(thresh_db)
    mask = (rms >= thr).astype(np.float32)
    # 부드러운 마스크(이동 평균)
    k = max(1, win//2)
    ker = np.ones(k, dtype=np.float32) / k
    m2 = np.convolve(mask, ker, mode='same')
    return (y * m2).astype(np.float32)

def tiny_reverb(y, sr, t60=0.35, wet=0.08):
    # 지수감쇠 IR
    ir_len = int(sr * t60)
    if ir_len < 1: return y
    t = np.arange(ir_len, dtype=np.float32) / sr
    ir = np.exp(-6.91 * t / t60).astype(np.float32)  # -60dB at t60
    wet_sig = np.convolve(y, ir, mode='full')[:len(y)]
    out = ((1.0 - wet) * y + wet * wet_sig).astype(np.float32)
    return out

def limiter(y, ceiling_db=-1.0):
    ceiling = db_to_lin(ceiling_db)
    peak = np.max(np.abs(y)) if y.size else 0.0
    if peak > 1e-9 and peak > ceiling:
        y = y * (ceiling / peak)
    return y.astype(np.float32)

def apply_soft_master(y, sr):
    y = hpf(y, sr, 30.0)
    y = noise_gate(y, sr, -45.0, 20.0)
    y = tiny_reverb(y, sr, t60=0.35, wet=0.08)
    y = limiter(y, -1.0)
    return y

# ---- GM 기반 역할 자동 분류 ------------------------------------------------
def gm_role(program, is_drum):
    if is_drum: return "drum"
    if 32 <= program <= 39: return "bass"
    if 24 <= program <= 31: return "guitar"
    return "keys"

# ---- 메인 -------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi", required=True, help="input MIDI file")
    ap.add_argument("--guitar-sfz", required=True, help="path to guitar *_sf folder")
    ap.add_argument("--bass-sfz",   required=True, help="path to bass *_sf folder")
    ap.add_argument("--keys-sfz",   required=True, help="path to keys *_sf folder")
    ap.add_argument("--drum-sfz",   required=True, help="path to drum *_sf folder")
    ap.add_argument("--sr", type=int, default=48000)
    ap.add_argument("--gain", type=float, default=0.0, help="pre-master gain dB (optional)")
    ap.add_argument("--out", default=None, help="output wav; default: /root/wave/result/{midi_name}_result.wav")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    # 기본 출력 경로
    if not args.out:
        song = os.path.splitext(os.path.basename(args.midi))[0]
        args.out = f"/root/wave/result/{song}_result.wav"
    ensure_dir(args.out)

    # 샘플러 준비
    samplers = {
        "guitar": Sampler(args.guitar_sfz, args.sr),
        "bass":   Sampler(args.bass_sfz,   args.sr),
        "keys":   Sampler(args.keys_sfz,   args.sr),
        "drum":   Sampler(args.drum_sfz,   args.sr),
    }

    midi = pm.PrettyMIDI(args.midi)
    # 전체 길이 추정
    total_s = midi.get_end_time()
    out = np.zeros(int(math.ceil(total_s * args.sr)) + args.sr, dtype=np.float32)

    for inst in midi.instruments:
        role = gm_role(inst.program, inst.is_drum)
        smp = samplers[role]
        for n in inst.notes:
            start = int(round(n.start * args.sr))
            dur = max(1e-4, n.end - n.start)
            notewav = smp.note(int(round(n.pitch)), dur, n.velocity)
            end = start + len(notewav)
            if end > len(out):
                out = np.pad(out, (0, end - len(out)))
            out[start:end] += notewav

    if args.gain != 0.0:
        out = out * db_to_lin(args.gain)

    # soft master
    out = apply_soft_master(out, args.sr)
    out = normalize_peak(out, peak=0.999)

    sf.write(args.out, out, args.sr, subtype="PCM_16")
    if args.debug:
        print(f"[OK] wrote: {args.out}")

if __name__ == "__main__":
    main()