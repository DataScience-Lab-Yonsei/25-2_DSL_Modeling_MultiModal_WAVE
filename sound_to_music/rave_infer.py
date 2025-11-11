# /root/multimodal/rave_infer.py  (교체본)
import argparse, os, glob
import numpy as np
import soundfile as sf
import librosa
import torch
from tqdm import tqdm

def load_audio_mono(path, target_sr):
    y, sr = librosa.load(path, sr=None, mono=False)
    if y.ndim > 1:  # stereo -> mono
        y = np.mean(y, axis=0)
    if sr != target_sr:
        res_type = "soxr_vhq" if "soxr" in librosa.resample.__code__.co_names else "kaiser_best"
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr, res_type=res_type)
    y = np.clip(y, -1.0, 1.0).astype(np.float32)
    return y, target_sr

def save_wav(path, y, sr):
    y = np.asarray(y, dtype=np.float32)
    sf.write(path, np.clip(y, -1.0, 1.0), sr)

def _guess_total_stride(model):
    """
    TorchScript 모델 속성에서 인코더 stride 추정.
    없으면 보수적으로 256 사용.
    """
    cand_names = ["encoder_ratios", "ratios", "downsampling_ratio", "ratios_enc"]
    for n in cand_names:
        try:
            v = getattr(model, n)
            if isinstance(v, (list, tuple)):
                s = 1
                for x in v: s *= int(x)
                if s > 1: return s
            elif isinstance(v, int) and v > 1:
                return int(v)
        except Exception:
            pass
    return 256  # 안전 기본값

def run_rave(ts_path, in_dir, out_dir, target_sr=48000, device=None, suffix="_rave"):
    os.makedirs(out_dir, exist_ok=True)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.jit.load(ts_path, map_location=device).eval()
    total_stride = _guess_total_stride(model)

    wavs = sorted(glob.glob(os.path.join(in_dir, "*.wav")))
    if not wavs:
        print(f"[warn] no wav files in {in_dir}")
        return

    for w in tqdm(wavs, desc=f"RAVE infer: {os.path.basename(in_dir)}"):
        y, _ = load_audio_mono(w, target_sr)
        orig_len = len(y)
        # 입력 길이를 인코더 총 stride의 배수로 패딩
        pad_len = (-orig_len) % total_stride
        if pad_len:
            y = np.pad(y, (0, pad_len), mode="constant")

        # (B, 1, T)로 투입
        x = torch.from_numpy(y).to(device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0)

        with torch.no_grad():
            out = model(x)
            if isinstance(out, (list, tuple)):
                out = out[0]
            # 출력도 (B, 1, T) 혹은 (B, T)일 수 있으니 안전하게 squeeze
            y_hat = out.squeeze().detach().to("cpu").numpy()

        # 패딩을 넣었으면 원래 길이로 크롭
        if y_hat.ndim > 1:
            # 혹시 (C, T) 형태면 마지막 축 기준
            y_hat = y_hat[..., :orig_len]
        else:
            y_hat = y_hat[:orig_len]

        stem = os.path.splitext(os.path.basename(w))[0]
        out_path = os.path.join(out_dir, f"{stem}{suffix}.wav")
        save_wav(out_path, y_hat, target_sr)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ts", required=True, help="TorchScript .ts model path")
    p.add_argument("--in_dir", required=True, help="input wav dir")
    p.add_argument("--out_dir", required=True, help="output dir")
    p.add_argument("--sr", type=int, default=48000)
    p.add_argument("--suffix", default="_rave")
    p.add_argument("--device", default=None)
    args = p.parse_args()

    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb=128")
    run_rave(args.ts, args.in_dir, args.out_dir, target_sr=args.sr, device=args.device, suffix=args.suffix)