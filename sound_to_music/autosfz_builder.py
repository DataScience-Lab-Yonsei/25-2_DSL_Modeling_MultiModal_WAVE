#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autosfz_builder.py — minimal SFZ builder
- melodic: 단일 샘플로 전 음역 커버 (선택: 무음 트림, 루프 크로스페이드)
- drum   : 폴더 내 파일을 연속된 키에 매핑(one-shot)
- drum-one: 단일 WAV를 여러 키에 복제 매핑(GM 또는 범위/리스트)
"""
import os, glob, csv, math, argparse
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

# 로컬 shim(또는 공식 librosa가 있으면 그걸 사용할 수도 있음 — 현재 파일명이 librosa.py이면 이 모듈이 import됨)
import librosa

def ensure_dir(p): os.makedirs(p, exist_ok=True)

def auto_trim(y, sr, trim_db=-40.0, min_sil_ms=30.0,
              frame_length=2048, hop_length=256):
    """RMS 기반 무음 트림.
    - hop_length는 '샘플 수' 그대로 사용 (SR로 환산하지 않음)
    - 결과가 너무 짧거나 비면 원본을 그대로 반환(안전 가드)
    """
    if y.size == 0:
        return y

    rms = librosa.feature.rms(y, frame_length=frame_length,
                              hop_length=hop_length, center=True)
    if rms.size == 0:
        return y

    thr = (10.0 ** (trim_db / 20.0)) * np.max(rms)
    mask = (rms > thr)
    if not mask.any():
        return y  # 전부 무음으로 판단되면 트림하지 않음

    idx = np.where(mask)[0]
    pad = int(sr * (min_sil_ms / 1000.0))
    s = max(0, idx[0] * hop_length - pad)
    e = min(len(y), (idx[-1] * hop_length) + pad)

    if e <= s:
        return y  # 안전 가드: 잘못 계산되면 원본 유지

    y_trim = y[s:e].astype(np.float32)
    if len(y_trim) < 1024:
        return y  # 너무 짧으면 트림하지 않음

    return y_trim


def find_loop_points(y, sr, search_ms=250):
    L = len(y)
    win = int(sr * search_ms / 1000.0)
    if L < 3 * win: return None
    head = y[win:2*win]; tail = y[-2*win:-win]
    c = np.correlate(head, tail, mode='valid')
    k = np.argmax(c)
    start = win; end = L - win + k
    if end - start < 2048: return None
    return (start, end)

def apply_xfade_loop(y, loop, xfade_ms=30.0, sr=48000):
    if loop is None: return y
    s, e = loop
    xf = int(sr * xfade_ms / 1000.0)
    if s < xf or e+xf > len(y) or e - s <= xf: return y
    head = y.copy()
    # 루프 크로스페이드로 이음매 줄이기
    a = np.linspace(1.0, 0.0, xf); b = 1.0 - a
    head[e:e+xf] = head[e:e+xf]*a + head[s:s+xf]*b
    return head[:e+xf].astype(np.float32)

def write_sfz(folder, sample_rel, keycenter=60, loop=None, drum=False):
    ensure_dir(folder)
    sfz = os.path.join(folder, "Instrument.sfz")
    lines = ["<group>"]
    if drum:
        lines.append("pitch_keytrack=0")
        lines.append("<region> sample={}".format(sample_rel))
    else:
        lines.append("<region> sample={} pitch_keycenter={} lokey=0 hikey=127".format(sample_rel, keycenter))
    if loop:
        lines.append("loop_start={}".format(loop[0]))
        lines.append("loop_end={}".format(loop[1]))
    with open(sfz, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def estimate_keycenter(y, sr, fixed_root=60, snap=False):
    if not snap: return fixed_root
    try:
        f0 = librosa.yin(y, fmin=55, fmax=1760, sr=sr)
        if f0.size == 0 or np.all(~np.isfinite(f0)): return fixed_root
        med = np.nanmedian(f0)
        if not np.isfinite(med) or med <= 0: return fixed_root
        midi = int(round(69 + 12 * math.log2(med / 440.0)))
        return int(np.clip(midi, 24, 100))
    except Exception:
        return fixed_root

def pitch_shift_to_key(y, sr, src_key, tgt_key):
    steps = tgt_key - src_key
    if steps == 0: return y
    return librosa.effects.pitch_shift(y, sr, steps)

def save_wav(path, y, sr): sf.write(path, y.astype(np.float32), sr, subtype="PCM_16")

# ------------------------------- MODES --------------------------------------
def do_melodic(root_in, root_out, sr, snap_to_nearest, fixed_root, do_loop, trim_db, min_sil_ms):
    wavs = sorted(glob.glob(os.path.join(root_in, "**/*.wav"), recursive=True))
    rows = []
    for w in wavs:
        name = os.path.splitext(os.path.basename(w))[0]
        folder = os.path.join(root_out, f"{name}_sf")
        y, s = sf.read(w, always_2d=False)
        if y.ndim > 1: y = y.mean(axis=1)
        y = y.astype(np.float32)
        if s != sr: y = librosa.resample(y, s, sr)
        y = auto_trim(y, sr, trim_db, min_sil_ms)
        key_src = estimate_keycenter(y, sr, fixed_root, snap_to_nearest)
        y = pitch_shift_to_key(y, sr, key_src, fixed_root)  # 최종 키센터는 fixed_root로 맞춤
        loop = find_loop_points(y, sr) if do_loop else None
        if do_loop: y = apply_xfade_loop(y, loop, 30.0, sr)
        ensure_dir(folder)
        out_wav = os.path.join(folder, f"{name}.wav")
        save_wav(out_wav, y, sr)
        rel = os.path.basename(out_wav)
        write_sfz(folder, rel, keycenter=fixed_root, loop=loop, drum=False)
        rows.append([w, out_wav, fixed_root, loop[0] if loop else "", loop[1] if loop else ""])
    # manifest
    if rows:
        with open(os.path.join(root_out, "manifest_melodic.csv"), "w", newline="", encoding="utf-8") as f:
            cw = csv.writer(f); cw.writerow(["src","dst","keycenter","loop_start","loop_end"]); cw.writerows(rows)

def parse_key_spec(spec):
    spec = spec.strip().lower()
    if spec == "gm":
        return list(range(35, 82))  # 35..81
    out = []
    for tok in spec.split(","):
        tok = tok.strip()
        if "-" in tok:
            a, b = tok.split("-"); out.extend(list(range(int(a), int(b)+1)))
        else:
            out.append(int(tok))
    return out

def do_drum(root_in, root_out, kit_name, start_key, normalize, one_shot):
    wavs = sorted(glob.glob(os.path.join(root_in, "*.wav")))
    folder = os.path.join(root_out, f"{kit_name}_sf"); ensure_dir(folder)
    lines = ["<group>", "pitch_keytrack=0"]
    key = int(start_key)
    for w in wavs:
        nm = os.path.basename(w)
        if normalize:
            y, s = sf.read(w, always_2d=False)
            if y.ndim > 1: y = y.mean(axis=1)
            y = librosa.util.normalize(y)
            sf.write(os.path.join(folder, nm), y.astype(np.float32), s)
            sample_rel = nm
        else:
            # 원본 복사 없이 상대경로 지정 (동 폴더에 파일이 있어야 함)
            import shutil
            shutil.copy2(w, os.path.join(folder, nm))
            sample_rel = nm
        lines.append(f"<region> sample={sample_rel} key={key} {'loop_mode=one_shot' if one_shot else ''}".strip())
        key += 1
    with open(os.path.join(folder, "Instrument.sfz"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def do_drum_one(in_wav, root_out, keys_spec, one_shot):
    keys = parse_key_spec(keys_spec)
    name = os.path.splitext(os.path.basename(in_wav))[0]
    folder = os.path.join(root_out, f"{name}_sf"); ensure_dir(folder)
    import shutil
    tgt = os.path.join(folder, os.path.basename(in_wav))
    shutil.copy2(in_wav, tgt)
    lines = ["<group>", "pitch_keytrack=0"]
    for k in keys:
        lines.append(f"<region> sample={os.path.basename(in_wav)} key={k} {'loop_mode=one_shot' if one_shot else ''}".strip())
    with open(os.path.join(folder, "Instrument.sfz"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# --------------------------------- CLI --------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["melodic","drum","drum-one"], default="melodic")
    ap.add_argument("--root-in", help="input folder (melodic/drum)")
    ap.add_argument("--root-out", required=True, help="output root folder")
    ap.add_argument("--sr", type=int, default=48000)

    # melodic
    ap.add_argument("--fixed-root", type=int, default=60)
    ap.add_argument("--snap-to-nearest", action="store_true")
    ap.add_argument("--do-loop", action="store_true")
    ap.add_argument("--trim-db", type=float, default=-40.0)
    ap.add_argument("--min-sil-ms", type=float, default=30.0)

    # drum
    ap.add_argument("--kit-name", default="Drum")
    ap.add_argument("--start-key", type=int, default=36)
    ap.add_argument("--normalize", action="store_true")
    ap.add_argument("--one-shot", action="store_true")

    # drum-one
    ap.add_argument("--in-wav")
    ap.add_argument("--keys", default="gm")

    args = ap.parse_args()
    os.makedirs(args.root_out, exist_ok=True)

    if args.mode == "melodic":
        if not args.root_in: raise SystemExit("--root-in is required for melodic")
        do_melodic(args.root_in, args.root_out, args.sr, args.snap_to_nearest, args.fixed_root, args.do_loop, args.trim_db, args.min_sil_ms)
    elif args.mode == "drum":
        if not args.root_in: raise SystemExit("--root-in is required for drum")
        do_drum(args.root_in, args.root_out, args.kit_name, args.start_key, args.normalize, args.one_shot)
    else:
        if not args.in_wav: raise SystemExit("--in-wav is required for drum-one")
        do_drum_one(args.in_wav, args.root_out, args.keys, args.one_shot)

if __name__ == "__main__":
    main()