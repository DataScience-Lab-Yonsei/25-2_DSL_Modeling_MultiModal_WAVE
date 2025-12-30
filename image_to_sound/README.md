# Phase 1: Image-to-Sound Pipeline

Phase 1 converts a single image into **realistic, non-musical sound effects** that could plausibly occur in the scene.
The generated sound effects are designed to be reused as musical material in Phase 2.

This phase focuses on **how to run the pipeline end-to-end**, from image input to sound effect output.

---

## 0. Installation

From the project root or `image_to_sound/`:

```bash
pip install -r requirements.txt

Model Access:
Some models require a Hugging Face access token.
```bash
export HUGGING_FACE_TOKEN=your_token_here
```

---

## 1. Directory Structure
image_to_sound/
├─ data/                  # Input images
├─ sound_sources/          # Extracted sound source descriptions (JSON)
├─ result/                # Generated sound effects (wav)
├─ vlm_prompt/             # Prompt templates and examples
├─ main.py                 # Full pipeline entry point
├─ image_to_text.py        # VLM inference (image → text)
├─ vlm_qwen.py             # Qwen2.5-VL model wrapper
├─ audio_prompt.py         # Audio-oriented prompt construction
├─ audioldm2.py            # AudioLDM2 sound generation
└─ requirements.txt

Create output directories if missing:
```bash
mkdir -p image_to_sound/{data,sound_sources,result}
```

---

## 2. Pipeline Overview
Image
 ↓
Image-to-Text (Qwen2.5-VL)
 ↓
Structured sound source description (JSON)
 ↓
Prompt construction
 ↓
Text-to-Audio (AudioLDM2)
 ↓
Sound effects (wav)

---

## 3. Execution Order
### (1) Run Full Pipeline (Image → Sound)
Processes all images in data/:
```bash
python main.py
```
Outputs:
* Sound source descriptions → sound_sources/
* Generated sound effects → result/
This is the default and recommended execution mode.
### (2) Process a Single Image
```bash
python main.py --single data/example.jpg
```
Only the specified image is processed.
Outputs are saved in the same directories as the full run.
### (3) Run Only Image-to-Text (VLM Stage)
Useful for inspecting or debugging sound source extraction.
```bash
python main.py --skip_audio
```
Outputs:
* JSON sound source descriptions only
* No audio files are generated
### (4) Run Only Text-to-Audio (AudioLDM2 Stage)
If sound source descriptions already exist:
```bash
python main.py --skip_vlm
```
This reuses existing JSON files in sound_sources/ and generates audio only.

---

## 4. Output Description
### Sound Source Descriptions (sound_sources/)
Each image is converted into a structured JSON file containing:
* scene description
* mood description
* sound-producing objects
* material, action, and timbre attributes
* optional instrument mapping information
These files act as the explicit interface between Phase 1 and Phase 2.
### Generated Audio (result/)
* Output format: WAV
* Content: realistic sound effects or ambience
* Explicitly constrained to be non-musical
* Designed to serve as raw material for musical transformation

---

## 5. Notes & Troubleshooting
* The first run may take time due to model downloads.
* CUDA-enabled GPU is strongly recommended for AudioLDM2.
* If generated audio sounds musical rather than environmental, verify that
* prompt constraints have not been modified.
* Large images or batch runs may require additional GPU memory.

Phase 1 does not generate music.
Its sole responsibility is to design and generate scene-consistent sound effects
that can be meaningfully transformed into music in Phase 2.
