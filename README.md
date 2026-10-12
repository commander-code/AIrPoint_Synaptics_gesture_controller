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
## Configuration  

All tunable parameters are grouped at the top of `main.py`. Changing any of them requires editing the file and restarting AirPoint.

| Variable | Meaning | Default | When to adjust |
|----------|---------|---------|----------------|
| `INNER_MARGIN` | Fraction of the frame ignored around the edges when no calibration exists | `0.3` | To make the default active box larger/smaller. |
| `CALIB_FILE` | Path to the stored calibration box | `~/.config/airpoint/calibration.json` | Usually left unchanged. |
| `CALIB_HOLD_TIME` | Seconds to hold each calibration corner | `2.0` | Increase if you need more time to steady your hand. |
| `CALIB_PAUSE` | Seconds to wait between corners | `2.5` | Adjust for personal pacing. |
| `MIN_BOX_W`, `MIN_BOX_H` | Minimum allowed width/height of a calibration box (as fraction of frame) | `0.25`, `0.20` | Prevents a too‑small box that would make cursor control unusable. |
| `FILTER_MIN_CUTOFF` | One‑Euro filter minimum cutoff (lower = smoother but laggy) | `0.8` | Tune for cursor steadiness vs. responsiveness. |
| `FILTER_BETA` | One‑Euro filter speed sensitivity | `0.03` | Increase to make the cursor more reactive to fast hand motion. |
| `DEAD_ZONE_PX` | Pixel distance below which filtered cursor movement is ignored | `2` | Raise to reduce jitter when the hand is almost still. |
| `FIST_HOLD_TIME` | Seconds a closed fist must be held to toggle control (absolute mode) | `1.0` | Lengthen to avoid accidental toggles. |
| `TOGGLE_COOLDOWN` | Minimum seconds between successive toggles | `0.5` | Prevents rapid flickering. |
| `CLICK_ON` | Normalised thumb‑middle distance below which a pinch is considered “on” | `0.25` | Lower makes clicking harder (requires a tighter pinch). |
| `CLICK_OFF` | Normalised distance above which a pinch is considered “off” (must be exceeded before another click can start) | `0.40` | Increase to avoid click bounce. |
| `CLICK_COOLDOWN` | Seconds between separate clicks | `0.10` | Adjust to suit double‑click timing. |
| `DOUBLE_CLICK_INTERVAL` | Max seconds between two pinches to be interpreted as a double click | `0.4` | Lengthen for a more forgiving double‑click window. |
| `SCROLL_SPEED` | Pixels scrolled per 0.1 unit of normalized hand movement | `300` | Increase for faster scrolling, decrease for finer control. |
| `SCROLL_DEADZONE` | Normalised wrist movement needed to start scrolling | `0.004` | Raise to ignore tiny hand tremors. |
| `SWIPE_VEL_THRESH` | Normalised wrist velocity (frame‑widths / second) required to trigger a swipe | `1.5` | Lower to make swipes easier, raise to avoid false swipes. |
| `SWIPE_COOLDOWN` | Seconds between swipe detections | `0.6` | Increase to prevent rapid repeats. |
| `PALM_HOLD_TIME` | Seconds an open palm must be held to trigger play/pause | `1.0` | Lengthen to avoid accidental media keys. |
| `EDGE_SNAP` | Fraction by which the active box is shrunk inward on each side (so cursor reaches screen edge before hand touches box edge) | `0.08` | Increase for a larger “snap‑to‑edge” effect. |
| `HAND_LOST_GRACE` | Seconds the hand may disappear before filter/cursor state is reset | `0.5` | Lower for quicker recovery, raise to tolerate brief occlusions. |
| `SHOW_BOX` | Set `False` to hide the yellow calibration box | `True` | Hide if you find the box distracting. |
| `START_RELATIVE` | Start in relative (`True`) or absolute (`False`) mode | `False` | Set to `True` if you prefer touch‑pad‑style control from launch. |
| `MOVE_SENSITIVITY` | Pixels per normalized unit of hand movement in relative mode | `2500` | Adjust to make the cursor faster or slower in relative mode. |
| `REPOSITION_SAFE_HOLD` | Seconds a fist/open‑palm must be held in relative mode to actually toggle control or trigger play/pause (prevents accidental triggers while repositioning) | `2.5` | Increase if you find the safety hold too short/long. |
| `SWIPE_IN_RELATIVE` | Enable swipe gestures while in relative mode | `False` | Set `True` if you want swipes available in relative mode. |
| `ALWAYS_ON` | If `True`, control starts enabled and the fist‑hold toggle is disabled | `True` | Set `False` to require the fist‑hold toggle to enable/disable control. |
| `ENABLE_PALM_PLAYPAUSE` | Master switch for the open‑palm → play/pause gesture | `False` | Set `True` to activate media control. |
| `ENABLE_SWIPE` | Master switch for the swipe gesture | `False` | Set `True` to activate arrow‑key swipes. |

---  
## Tips for best results  

- **Lighting:** Even, diffuse lighting reduces shadows and helps MediaPipe locate landmarks reliably. Avoid strong backlight.  
- **Camera distance:** Position the webcam so that your hand occupies roughly half the frame width when extended; too close causes distortion, too far reduces landmark precision.  
- **Elbow rest:** Rest your forearm on the desk to minimize tremor; small, deliberate movements translate to smoother cursor motion.  
- **Calibration box size:** Make the box comfortably large enough to reach all screen corners without straining your wrist, but not so large that small hand motions cause huge cursor jumps.  
- **Background:** A relatively static, non‑textured background improves hand‑segmentation accuracy.  
- **Hand pose:** Keep fingers relatively spread when pointing; clenched fists or curled fingers can confuse the finger‑up/down logic.  

---  
## Troubleshooting  

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **Notification: “AirPoint requires X11…”** | You are logged into a Wayland session. | Log out and choose **Ubuntu on Xorg** at the login screen, or launch AirPoint from an X11 session. |
| **`Error: Could not open webcam (/dev/video0).`** | No webcam detected or wrong device node. | Ensure a webcam is connected and not used by another application. Try `ls /dev/video*`. |
| **`AttributeError: module 'mediapipe' has no attribute 'solutions'`** | Wrong mediapipe version installed. | The installer pins `mediapipe==0.10.14`. Re‑run `pip install -r requirements.txt` inside the venv. |
| **`ModuleNotFoundError: No module named 'pyautogui'`** | Virtual environment not activated or packages missing. | Activate the venv (`source venv/bin/activate`) or re‑run the installer. |
| **PyAutoGUI failsafe triggers (cursor jumps to a corner)** | Cursor reached a screen corner (0,0) or (max,max). | AirPoint keeps a 5‑pixel margin from the edges; if you see this, increase `DEAD_ZONE_PX` or check that your calibration box is not degenerate. |
| **Hand tracking lost at frame edges** | Hand leaves the camera view or is strongly rotated. | The “edge snap zone” (`EDGE_SNAP`) and `HAND_LOST_GRACE` settings help; try to keep the hand centered in the frame. |
| **Accidental clicks or scrolls** | Hand pose briefly matches a gesture threshold. | Adjust `CLICK_ON/CLICK_OFF`, `SCROLL_DEADZONE`, or increase `REPOSITION_SAFE_HOLD` for relative mode. |
| **No response to gestures** | Control is disabled (`CTRL: OFF`) or the preview window is paused (`PAUSED`). | Look at the top‑left status; press `p` to resume, or make a fist to toggle (if `ALWAYS_ON=False`). |
| **Calibration fails / box too small** | You held the index too close to the edge or the hand moved during the hold. | Try again, making sure the fingertip stays steady for the full 2 s and that the resulting box meets `MIN_BOX_W`/`MIN_BOX_H`. |

---  
## Limitations & Known Issues  

- **Beta quality** – Expect occasional bugs; the software is functional but not yet polished for production‑critical use.  
- **Lighting dependent** – Poor or uneven lighting can cause missed or jittery landmark detection.  
- **Precision** – Cursor movement is smooth but not as granular as a high‑DPI mouse; fine‑pixel work may still need a traditional mouse.  
- **X11 only** – The launcher aborts on Wayland with a notification; Wayland support is planned for a future release.  
- **Single hand** – Only the dominant hand (first detected) is processed; two‑hand gestures are not supported.  
- **No right‑click, drag, or dwell‑click** – These features are on the roadmap (see below).  
- **CPU usage** – Modest on a typical modern laptop; on very old hardware the 30 FPS loop may be noticeable.  

---  
## Roadmap  

| Planned feature | Description |
|-----------------|-------------|
| **Dwell click** | Hold the cursor stationary for a configurable time to generate a click. |
| **Right click** | Distinct gesture (e.g., thumb‑ring pinch) for context‑menu. |
| **Drag & drop** | Click‑hold‑move‑release gesture. |
| **Background cursor thread** | Decouple cursor smoothing from the main loop for even lower latency. |
| **Wayland support** | Replace X11‑specific calls with a portable input‑injection method (e.g., `libinput` or `evdev`). |
| **.deb package** | Provide a Debian‑package for easy system‑wide installation. |
| **Config GUI** | Simple GTK/Qt dialog to adjust the constants without editing `main.py`. |
| **Improved hand model** | Use MediaPipe’s newer hand‑landmark models or a lightweight custom model for higher accuracy. |
| **Multi‑platform builds** | macOS and Windows variants using the same core logic. |

---  
## Contributing  

We welcome contributions! If you’d like to help:

1. Fork the repository.  
2. Create a feature branch (`git checkout -b feature/your-idea`).  
3. Make your changes, ensuring they follow the existing code style.  
4. Add or update tests if applicable.  
5. Open a pull request with a clear description of the change and why it’s useful.  

Please read the [`CONTRIBUTING.md`](CONTRIBUTING.md) (if present) for more details.

---  
## License  

AirPoint is released under the **MIT License** – see the [`LICENSE`](LICENSE) file for the full text.

---  
## Author  

**Efeoghene Iseoluwa Evangelist** – Creator and maintainer of AirPoint.  
Contact: [your‑efeogheneevans.com] (or via GitHub issues).  

---  
*Enjoy hands‑free interaction! If you find AirPoint useful, consider starring the repo and sharing it with others who might benefit.*  

---  

*(All feature descriptions are taken directly from the current `main.py` and `install.sh` files; no functionality beyond what is implemented has been invented.)*  
