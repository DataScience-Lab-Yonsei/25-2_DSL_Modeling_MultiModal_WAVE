# Phase 1: Image-to-Sound Pipeline

This phase converts a single image into **realistic sound effects** that could plausibly occur in the scene.
The output of this phase serves as the input to Phase 2 (Sound-to-Music).

Phase 1 focuses on **semantic alignment** between visual content and generated audio by carefully designing the textual intermediate representation.

---

## 1. Pipeline Overview
Image  
↓  
Vision-Language Model (Qwen2.5-VL)  
↓  
Structured sound source description (text)  
↓  
prompt engineering   
↓  
AudioLDM2  
↓  
Sound effects (wav)  

---

## 2. Environment Setup

### Requirements
- Python 3.8+
- CUDA-enabled GPU (recommended)
- Hugging Face access token (for model download)

Install dependencies:
```
bash
pip install -r requirements.txt
```

Set Hugging Face token: 
```
export HUGGING_FACE_TOKEN=your_token_here
```

---

## 3.Directory Structure
image_to_sound/
├─ main.py                # Entry point for full pipeline  
├─ image_to_text.py       # VLM inference  
├─ vlm_qwen.py            # Qwen2.5-VL wrapper  
├─ audio_prompt.py        # Audio-oriented prompt construction  
├─ audioldm2.py           # Audio generation  
├─ data/                  # Input images  
├─ sound_sources/         # Extracted sound source descriptions (JSON)  
├─ result/                # Generated sound effects (wav)  
└─ vlm_prompt/            # Prompt templates  

---

## 4. Running the Pipeline
### 4.1 Run Full Pipeline (Image → Sound)
Processes all images in data/:
```
python main.py
```
Outputs:
* structured sound descriptions → sound_sources/
* generated audio files → result/

### 4.2 Process a Single Image
```
python main.py --single data/example.jpg
```

### 4.3 Run Only Image-to-Text (VLM)
Useful for inspecting or debugging sound source extraction:
```
python main.py --skip_audio
```
Result:
```
only JSON sound descriptions are generated
```
### 4.4 Run Only Audio Generation
If sound source descriptions already exist:
```
python main.py --skip_vlm
```

---

## 5. Output Format
Sound Source (JSON)
Each image is converted into a structured representation including:
* scene description
* mood description
* sound-producing objects
* material, action, and timbre attributes

Audio Output
* Non-musical, realistic sound effects
* Designed to be reused as musical material in Phase 2
