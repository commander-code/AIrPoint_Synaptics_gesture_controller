# AirPoint  
**Touch‑less hand‑gesture mouse control for Linux (webcam only)**  

**Status:** **Beta**  

![Demo GIF placeholder](./demo.gif)  

---  
## Overview  

AirPoint lets you control the mouse cursor on a Linux desktop using only a standard webcam and hand gestures.  
* No extra hardware is required – just the built‑in or USB webcam you already have.  
* All processing runs locally; video never leaves your machine, preserving privacy.  
* On Linux there are very few open‑source, camera‑based mouse alternatives; AirPoint fills that gap while also serving accessibility and hygiene‑focused use‑cases.  

---  
## Real‑world applications  

| Use case | Why AirPoint helps |
|----------|-------------------|
| **Accessibility** | Users who can still move a hand but find a traditional mouse difficult (e.g., limited fine motor control, tremor) can point, click and scroll with simple gestures. |
| **Hygiene‑sensitive environments** | No need to touch a mouse or touchscreen – ideal for kitchens, labs, medical settings, or shared workstations. |
| **Presentations & media PCs** | Control slides or media playback from a distance without a remote. |
| **Education & research** | Low‑cost platform for experimenting with gesture‑based interaction, prototyping, or teaching computer‑vision concepts. |
| **Everyday desktop use** | A hands‑free alternative when your hands are occupied or you want to reduce repetitive strain. |

**Limitations to keep in mind** – AirPoint works best with good lighting, a relatively static background, and a webcam that can see the whole hand. It is not intended to replace a high‑precision gaming mouse, and it currently runs only on X11 sessions (Wayland shows a notification and exits).

---  
## Features & Gesture table  

| Action | Gesture (as detected by the code) | Notes / Default state |
|--------|-----------------------------------|-----------------------|
| **Move cursor** | Point with the index finger (tip **or** knuckle, selectable via `CURSOR_LANDMARK`) | Works in **absolute** (mapped to a calibrated box) or **relative** (touch‑pad‑style) mode. |
| **Left click** | Thumb tip touches middle‑finger tip (pinch) – requires **≥ 3 consecutive frames** below the click threshold (`CLICK_ON`) and a release above `CLICK_OFF` | Single click per pinch. Two quick pinches (`< DOUBLE_CLICK_INTERVAL`) produce a **double click**. |
| **Double click** | Two thumb‑middle pinches within `DOUBLE_CLICK_INTERVAL` (0.4 s) | Only active when click detection is enabled (always on). |
| **Scroll** | Index + middle fingers up (ring & pinky down) – move hand up/down | Scroll speed proportional to hand movement (`SCROLL_SPEED`). Paused while pinching. |
| **Swipe** (disabled by default) | Open palm (all five fingers up) + fast sideways wrist motion | Generates Left/Right arrow key. Controlled by `ENABLE_SWIPE` and, in relative mode, `SWIPE_IN_RELATIVE`. |
| **Play / Pause** (disabled by default) | Open palm held still for `PALM_HOLD_TIME` (1.0 s) | Sends a Space key. Controlled by `ENABLE_PALM_PLAYPAUSE`. |
| **Control toggle** | Closed fist held for `FIST_HOLD_TIME` (1.0 s) → enables/disables gesture processing | In **absolute** mode only; in relative mode the fist pauses movement instead (see `REPOSITION_SAFE_HOLD`). |
| **Pause / Resume all gestures** | Press **`p`** in the preview window | Shows “PAUSED” in orange; gestures and cursor freeze until resumed. |
| **Calibration** | Press **`c`**, hold index at top‑left for 2 s, then bottom‑right for 2 s | Defines the active box used in absolute mode; saved to `~/.config/airpoint/calibration.json`. |
| **Quit** | Press **`q`** in the preview window | Exits cleanly, releases webcam. |
| **Mode switch** | Press **`m`** in the preview window | Toggles between **absolute** and **relative** mode. |

*Gestures that are **off by default** (set to `False` in the top of `main.py`):*  

- `ENABLE_PALM_PLAYPAUSE` – open‑palm → play/pause  
- `ENABLE_SWIPE` – open‑palm + fast sideways → arrow keys  
- `SWIPE_IN_RELATIVE` – swipe is also disabled while in relative mode (unless you set both to `True`).  

---  
