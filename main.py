#!/usr/bin/env python3
"""
Phase 4: gesture controller + calibration + One Euro cursor filter.
Control starts OFF; fist held 1 s toggles ON/OFF (once per fist).
When ON:
  - Point (index only): move cursor
  - Pinch thumb + middle fingertip: left click (two quick pinches = double click)
  - Index + middle up (ring, pinky down): move hand up/down to scroll
  - Open palm + fast sideways motion: Left/Right arrow key
  - Open palm held still 1 s: Space (play/pause)
Keys in the preview window: 'q' quit, 'c' start/cancel calibration, 'm' toggle absolute/relative mode, 'p' pause/resume.
"""

import json
import math
import os
import shutil
import time
import cv2
import mediapipe as mp
import pyautogui

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# ------------------------------ CONFIG ------------------------------
FINGER_TIPS = {"Thumb": 4, "Index": 8, "Middle": 12, "Ring": 16, "Pinky": 20}
FINGER_PIPS = {"Thumb": 3, "Index": 6, "Middle": 10, "Ring": 14, "Pinky": 18}

TARGET_FPS = 30

# Active box: used until you calibrate, or if calibration.json is missing/too small
INNER_MARGIN = 0.3
# Store calibration in ~/.config/airpoint/
CALIB_FILE = os.path.join(os.path.expanduser("~"), ".config", "airpoint", "calibration.json")
CALIB_HOLD_TIME = 2.0       # seconds to hold each corner
CALIB_PAUSE = 2.5           # time to move to the next corner
MIN_BOX_W = 0.25            # smallest allowed box (fraction of frame width)
MIN_BOX_H = 0.20            # smallest allowed box (fraction of frame height)

# One Euro filter (cursor smoothing)
FILTER_MIN_CUTOFF = 0.8     # lower = steadier when still, but laggier
FILTER_BETA = 0.03          # higher = more responsive during fast moves
DEAD_ZONE_PX = 2            # ignore cursor moves smaller than this

FIST_HOLD_TIME = 1.0
TOGGLE_COOLDOWN = 0.5

CLICK_ON = 0.25             # pinch distance / hand size below this = pinch
CLICK_OFF = 0.40            # must open past this before the next pinch counts
CLICK_COOLDOWN = 0.10
DOUBLE_CLICK_INTERVAL = 0.4

SCROLL_SPEED = 300
SCROLL_DEADZONE = 0.004

SWIPE_VEL_THRESH = 1.5      # frame-widths per second
SWIPE_COOLDOWN = 0.6

PALM_HOLD_TIME = 1.0

# ---- New additions for this phase ----------------------------------------
EDGE_SNAP = 0.08            # shrink active box inward by this fraction on each side
HAND_LOST_GRACE = 0.5       # seconds hand may be lost before resetting filter/cursor
SHOW_BOX = True             # set False to hide the yellow calibration box
START_RELATIVE = False      # start in absolute mode; toggle with 'm'
MOVE_SENSITIVITY = 2500     # pixels per normalized unit in relative mode
REPOSITION_SAFE_HOLD = 2.5  # seconds fist/open-palm must be held in relative mode to avoid accidental triggers
SWIPE_IN_RELATIVE = False   # disable swipe while in relative mode (prevents accidental swipes)

ALWAYS_ON = True            # when True, control starts ON and fist-hold toggle is disabled
ENABLE_PALM_PLAYPAUSE = False   # enable/disable open-palm -> play/pause gesture
ENABLE_SWIPE = False        # enable/disable swipe gesture
# --------------------------------------------------------------------------

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class OneEuro:
    """One Euro filter: steady when still, responsive when moving fast."""

    def __init__(self, min_cutoff, beta, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self.x = None
        self.dx = 0.0
        self.t = None

    @staticmethod
    def _alpha(dt, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self.t is None:
            self.x, self.dx, self.t = x, 0.0, t
            return x
        dt = max(t - self.t, 1e-3)
        raw_dx = (x - self.x) / dt
        a_d = self._alpha(dt, self.d_cutoff)
        self.dx = a_d * raw_dx + (1.0 - a_d) * self.dx
        cutoff = self.min_cutoff + self.beta * abs(self.dx)
        a = self._alpha(dt, cutoff)
        self.x = a * x + (1.0 - a) * self.x
        self.t = t
        return self.x


def fingers_up(hand_landmarks, handedness_label):
    up = {}
    lm = hand_landmarks.landmark
    for name, tip_idx in FINGER_TIPS.items():
        if name == "Thumb":
            continue
        up[name] = lm[tip_idx].y < lm[FINGER_PIPS[name]].y
    tip_x = lm[FINGER_TIPS["Thumb"]].x
    ip_x = lm[FINGER_PIPS["Thumb"]].x
    up["Thumb"] = tip_x < ip_x if handedness_label == "Right" else tip_x > ip_x
    return up


def dist2d(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def default_box():
    m = INNER_MARGIN
    return (m, m, 1.0 - m, 1.0 - m)


def load_box():
    try:
        with open(CALIB_FILE) as f:
            d = json.load(f)
        x1, y1 = d["top_left"]
        x2, y2 = d["bottom_right"]
        # an old, too-small calibration is ignored automatically
        if x2 - x1 >= MIN_BOX_W and y2 - y1 >= MIN_BOX_H:
            return (x1, y1, x2, y2)
    except Exception:
        pass
    return None


def save_box(box):
    with open(CALIB_FILE, "w") as f:
        json.dump({"top_left": [box[0], box[1]], "bottom_right": [box[2], box[3]]}, f, indent=2)


def clamp01(v):
    return max(0.0, min(1.0, v))


def main():
    # Ensure config directory exists and migrate old calibration if present
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "airpoint")
    os.makedirs(config_dir, exist_ok=True)
    old_calib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")
    if os.path.isfile(old_calib) and not os.path.isfile(CALIB_FILE):
        try:
            shutil.copy(old_calib, CALIB_FILE)
        except Exception:
            pass  # if copy fails, we'll just use the default box

    # Log file path
    log_dir = os.path.join(os.path.expanduser("~"), ".local", "state", "airpoint")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "airpoint.log")

    def log_and_print(message, end='\n'):
        """Print to terminal and append to log file (if message ends with newline)."""
        print(message, end=end)
        if end == '\n':  # only log complete lines (avoid logging the per-frame finger text)
            try:
                with open(log_file_path, 'a') as f:
                    f.write(message + '\n')
            except Exception:
                pass  # fail silently on logging issues

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        log_and_print("Error: Could not open webcam (/dev/video0).")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    screen_w, screen_h = pyautogui.size()

    box = load_box() or default_box()

    # ---- Control state -------------------------------------------------
    if ALWAYS_ON:
        control_enabled = True
        toggle_disabled = True   # fist-hold toggle ignored
    else:
        control_enabled = False
        toggle_disabled = False

    fist_start = None
    last_toggle = 0.0
    fist_fired = False

    fx = OneEuro(FILTER_MIN_CUTOFF, FILTER_BETA)
    fy = OneEuro(FILTER_MIN_CUTOFF, FILTER_BETA)
    last_mx = last_my = None
    pinch_active = False
    last_click = 0.0
    last_swipe = 0.0
    palm_start = None
    palm_fired = False
    prev_wx = prev_wy = prev_t = None
    scroll_prev_y = None
    g = {"text": "None", "until": 0.0}

    # calibration state
    calibrating = False
    cal_stage = 0
    cal_start = None
    cal_sum_x = cal_sum_y = 0.0
    cal_n = 0
    cal_p1 = None
    cal_wait_until = 0.0

    # ---- New state for hand-lost grace and relative mode ----
    hand_lost_start = None          # timestamp when hand last disappeared
    relative_mode = START_RELATIVE  # start in absolute/relative mode per config
    cursor_x, cursor_y = screen_w // 2, screen_h // 2  # fallback start position
    prev_rel_x, prev_rel_y = None, None  # previous fingertip pos for relative mode

    # Initialise fingertip coords for edge-warning (prevents undefined variable)
    ix, iy = 0.5, 0.5

    paused = False          # global pause flag (gestures + cursor)

    def flash(text):
        g["text"] = text
        g["until"] = time.time() + 0.8

    def reset_motion():
        nonlocal last_mx, last_my, pinch_active, palm_start, palm_fired
        nonlocal prev_wx, prev_wy, prev_t, scroll_prev_y
        fx.reset()
        fy.reset()
        last_mx = last_my = None
        pinch_active = False
        palm_start = None
        palm_fired = False
        prev_wx = prev_wy = prev_t = None
        scroll_prev_y = None

    log_and_print("Show your hand to the camera. 'q' = quit, 'c' = calibrate, 'm' = toggle absolute/relative mode, 'p' = pause/resume.")
    try:
        with mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as hands:
            while True:
                loop_start = time.time()
                ret, frame = cap.read()
                if not ret:
                    log_and_print("Warning: Empty frame received.")
                    break

                frame = cv2.flip(frame, 1)
                results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                now = time.time()
                finger_text = "No hand"
                cal_text = ""
                target = "TOP-LEFT" if cal_stage == 0 else "BOTTOM-RIGHT"
                if calibrating:
                    cal_text = f"CALIBRATE: point index finger at {target}"

                hand_seen = bool(results.multi_hand_landmarks)

                if results.multi_hand_landmarks and results.multi_handedness:
                    # hand is present - reset lost-timer
                    hand_lost_start = None

                    hl = results.multi_hand_landmarks[0]
                    handed = results.multi_handedness[0].classification[0].label
                    lm = hl.landmark

                    mp_drawing.draw_landmarks(
                        frame, hl, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2),
                    )

                    up = fingers_up(hl, handed)
                    finger_text = ", ".join(
                        f"{n}:{'UP' if v else 'DOWN'}" for n, v in up.items()
                    )
                    print(f"\r{finger_text}".ljust(70), end="", flush=True)

                    index_up, middle_up = up["Index"], up["Middle"]
                    ring_up, pinky_up = up["Ring"], up["Pinky"]
                    ix, iy = lm[FINGER_TIPS["Index"]].x, lm[FINGER_TIPS["Index"]].y  # update for edge warning

                    # ---- Fist toggle: once per fist (thumb ignored) ----
                    if not toggle_disabled:
                        hold_needed = REPOSITION_SAFE_HOLD if relative_mode else FIST_HOLD_TIME
                        if not (index_up or middle_up or ring_up or pinky_up):
                            if fist_start is None:
                                fist_start = now
                            elif (not fist_fired
                                  and now - fist_start >= hold_needed
                                  and now - last_toggle >= TOGGLE_COOLDOWN):
                                control_enabled = not control_enabled
                                last_toggle = now
                                fist_fired = True
                                reset_motion()
                                log_and_print(f"\nControl {'ON' if control_enabled else 'OFF'}")
                        else:
                            fist_start = None
                            fist_fired = False

                    if calibrating:
                        # ---- Calibration: hold index at each corner ----
                        if now < cal_wait_until:
                            cal_start = None
                            cal_text = f"Captured. Move to {target}..."
                        elif index_up:
                            if cal_start is None:
                                cal_start = now
                                cal_sum_x = cal_sum_y = 0.0
                                cal_n = 0
                            cal_sum_x += ix
                            cal_sum_y += iy
                            cal_n += 1
                            held = now - cal_start
                            cal_text = (f"CALIBRATE {target}: hold "
                                        f"{max(0.0, CALIB_HOLD_TIME - held):.1f}s")
                            if held >= CALIB_HOLD_TIME and cal_n > 0:
                                avg = (cal_sum_x / cal_n, cal_sum_y / cal_n)
                                if cal_stage == 0:
                                    cal_p1 = avg
                                    cal_stage = 1
                                    cal_wait_until = now + CALIB_PAUSE
                                    log_and_print("\nTop-left captured.")
                                else:
                                    x1, x2 = sorted((cal_p1[0], avg[0]))
                                    y1, y2 = sorted((cal_p1[1], avg[1]))
                                    if x2 - x1 < MIN_BOX_W or y2 - y1 < MIN_BOX_H:
                                        log_and_print("\nBox too small, try again "
                                              "(use a bigger area).")
                                        cal_stage = 0
                                        cal_wait_until = now + CALIB_PAUSE
                                    else:
                                        box = (x1, y1, x2, y2)
                                        save_box(box)
                                        calibrating = False
                                        log_and_print(f"\nCalibration saved to {CALIB_FILE}")
                                cal_start = None
                        else:
                            cal_start = None

                    elif control_enabled and not paused:
                        wrist = lm[0]
                        hand_size = max(dist2d(wrist, lm[9]), 1e-6)
                        pinch_norm = dist2d(lm[FINGER_TIPS["Thumb"]],
                                            lm[FINGER_TIPS["Middle"]]) / hand_size

                        four_up = index_up and middle_up and ring_up and pinky_up
                        scroll_pose = index_up and middle_up and not ring_up and not pinky_up
                        point_pose = index_up and not middle_up and not ring_up and not pinky_up

                        # ---- Click: one click per pinch ----
                        if not pinch_active and pinch_norm < CLICK_ON:
                            pinch_active = True
                            if now - last_click > CLICK_COOLDOWN:
                                pyautogui.click()
                                if now - last_click < DOUBLE_CLICK_INTERVAL:
                                    flash("DOUBLE CLICK")
                                else:
                                    flash("LEFT CLICK")
                                last_click = now
                        elif pinch_active and pinch_norm > CLICK_OFF:
                            pinch_active = False

                        # ---- Scroll ----
                        if scroll_pose and not pinch_active:
                            if scroll_prev_y is not None:
                                dy = wrist.y - scroll_prev_y
                                if abs(dy) > SCROLL_DEADZONE:
                                    amount = int(-dy * SCROLL_SPEED)
                                    if amount != 0:
                                        pyautogui.scroll(amount)
                                        flash(f"SCROLL {amount}")
                            scroll_prev_y = wrist.y
                        else:
                            scroll_prev_y = None

                        # ---- Swipe (open palm, fast sideways) ----
                        # Swipe is disabled globally by ENABLE_SWIPE, and also in relative mode when SWIPE_IN_RELATIVE is False
                        if ENABLE_SWIPE and not (relative_mode and not SWIPE_IN_RELATIVE):
                            if four_up and prev_t is not None:
                                dt = now - prev_t
                                if dt > 0:
                                    vx = (wrist.x - prev_wx) / dt
                                    vy = (wrist.y - prev_wy) / dt
                                    if (abs(vx) > SWIPE_VEL_THRESH
                                            and abs(vx) > 2 * abs(vy)
                                            and now - last_swipe > SWIPE_COOLDOWN):
                                        pyautogui.press("right" if vx > 0 else "left")
                                        flash("SWIPE RIGHT" if vx > 0 else "SWIPE LEFT")
                                        last_swipe = now
                                        palm_start = None
                                        palm_fired = True
                        prev_wx, prev_wy, prev_t = wrist.x, wrist.y, now

                        # ---- Open palm held: play/pause (once per hold) ----
                        if ENABLE_PALM_PLAYPAUSE:
                            palm_hold_needed = REPOSITION_SAFE_HOLD if relative_mode else PALM_HOLD_TIME
                            if four_up:
                                if palm_start is None:
                                    palm_start = now
                                elif not palm_fired and now - palm_start >= palm_hold_needed:
                                    pyautogui.press("space")
                                    flash("PLAY/PAUSE")
                                    palm_fired = True
                            else:
                                palm_start = None
                                palm_fired = False

                        # ---- Cursor movement ----
                        if point_pose and not pinch_active:
                            # ----- Determine mode -----
                            if not relative_mode:
                                # -------- Absolute mode (original behaviour) --------
                                bx1, by1, bx2, by2 = box
                                # shrink box by EDGE_SNAP on each side
                                box_w = bx2 - bx1
                                box_h = by2 - by1
                                shrink_x = EDGE_SNAP * box_w
                                shrink_y = EDGE_SNAP * box_h
                                ibx1 = bx1 + shrink_x
                                iby1 = by1 + shrink_y
                                ibx2 = bx2 - shrink_x
                                iby2 = by2 - shrink_y
                                # guard against degenerate box
                                if ibx2 - ibx1 <= 0 or iby2 - iby1 <= 0:
                                    ibx1, iby1, ibx2, iby2 = bx1, by1, bx2, by2
                                nx = clamp01((ix - ibx1) / (ibx2 - ibx1))
                                ny = clamp01((iy - iby1) / (iby2 - iby1))
                                # stay 5 px from corners so the failsafe isn't triggered
                                tx = 5 + nx * (screen_w - 10)
                                ty = 5 + ny * (screen_h - 10)
                                mx = fx(tx, now)
                                my = fy(ty, now)
                                if (last_mx is None
                                        or math.hypot(mx - last_mx, my - last_my) >= DEAD_ZONE_PX):
                                    pyautogui.moveTo(mx, my, duration=0)
                                    last_mx, last_my = mx, my
                            else:
                                # -------- Relative mode --------
                                if prev_rel_x is None:
                                    # first frame in pointing pose – initialise from real cursor
                                    cursor_x, cursor_y = pyautogui.position()
                                    prev_rel_x, prev_rel_y = ix, iy
                                    target_x, target_y = cursor_x, cursor_y
                                else:
                                    dx = ix - prev_rel_x
                                    dy = iy - prev_rel_y
                                    move_x = dx * MOVE_SENSITIVITY
                                    move_y = dy * MOVE_SENSITIVITY
                                    cursor_x += move_x
                                    cursor_y += move_y
                                    # clamp to screen with 5 px margin (failsafe safety)
                                    cursor_x = max(5, min(screen_w - 6, cursor_x))
                                    cursor_y = max(5, min(screen_h - 6, cursor_y))
                                    prev_rel_x, prev_rel_y = ix, iy
                                    target_x, target_y = cursor_x, cursor_y
                                # apply One-Euro filter and dead-zone
                                mx = fx(target_x, now)
                                my = fy(target_y, now)
                                if (last_mx is None
                                        or math.hypot(mx - last_mx, my - last_my) >= DEAD_ZONE_PX):
                                    pyautogui.moveTo(mx, my, duration=0)
                                    last_mx, last_my = mx, my
                        else:
                            # not pointing or pinching - reset relative-mode state
                            prev_rel_x, prev_rel_y = None, None
                            fx.reset()
                            fy.reset()
                            last_mx = last_my = None
                    else:
                        # control disabled or paused - reset gesture state but keep filter/cursor
                        reset_motion()
                else:
                    # ----- No hand detected -----
                    if hand_lost_start is None:
                        hand_lost_start = now
                    # immediate reset of gesture-specific state (keep filter/cursor)
                    scroll_prev_y = None
                    pinch_active = False
                    palm_start = None
                    palm_fired = False
                    fist_start = None
                    fist_fired = False
                    prev_wx = prev_wy = prev_t = None
                    prev_rel_x = prev_rel_y = None
                    # if grace period exceeded, reset filter/cursor as well
                    if now - hand_lost_start >= HAND_LOST_GRACE:
                        reset_motion()
                        hand_lost_start = None
                    # else: within grace period - keep filter/cursor unchanged
                    cal_start = None

                # ----- Overlays -----
                if paused:
                    status, color = "PAUSED", (0, 165, 255)   # orange
                elif control_enabled:
                    status, color = "CTRL: ON", (0, 255, 0)
                else:
                    status, color = "CTRL: OFF", (0, 0, 255)
                gesture = g["text"] if now < g["until"] else "None"

                h, w = frame.shape[:2]
                bx1, by1, bx2, by2 = box

                # Edge-warning: dark gray border when fingertip not near edge,
                # red when fingertip within 5% of any frame edge.
                border_color = (50, 50, 50)  # dark gray
                if hand_seen:
                    if ix < 0.05 or ix > 0.95 or iy < 0.05 or iy > 0.95:
                        border_color = (0, 0, 255)  # red
                # draw full-frame border
                cv2.rectangle(frame, (0, 0), (w - 1, h - 1), border_color, 2)

                if SHOW_BOX:
                    cv2.rectangle(frame, (int(bx1 * w), int(by1 * h)),
                                  (int(bx2 * w), int(by2 * h)), (0, 255, 255), 1)

                cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.9, color, 2, cv2.LINE_AA)
                cv2.putText(frame, f"Fingers: {finger_text}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(frame, f"Gesture: {gesture}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1, cv2.LINE_AA)
                # mode indicator
                mode_text = f"Mode: {'RELATIVE' if relative_mode else 'ABSOLUTE'}"
                cv2.putText(frame, mode_text, (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1, cv2.LINE_AA)

                # ---- Active gesture set (small text) ----
                gesture_set = ["click", "scroll"]
                if ENABLE_PALM_PLAYPAUSE:
                    gesture_set.append("palm play/pause")
                if ENABLE_SWIPE:
                    gesture_set.append("swipe")
                gesture_set_text = "Gestures: " + ", ".join(gesture_set)
                cv2.putText(frame, gesture_set_text, (10, 180),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

                if calibrating:
                    cv2.putText(frame, cal_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (0, 165, 255), 2, cv2.LINE_AA)

                cv2.imshow("Gesture Controller - Phase 4", frame)

                # ----- Single key read (works with or without a hand in view) -----
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("c"):
                    if calibrating:
                        calibrating = False
                        log_and_print("\nCalibration cancelled.")
                    else:
                        calibrating = True
                        cal_stage = 0
                        cal_start = None
                        cal_n = 0
                        cal_wait_until = 0.0
                        reset_motion()
                        log_and_print("\nCalibration started.")
                if key == ord("m"):
                    relative_mode = not relative_mode
                    # reset relative-mode state to avoid jump when switching
                    prev_rel_x, prev_rel_y = None, None
                    log_and_print(f"\nSwitched to {'RELATIVE' if relative_mode else 'ABSOLUTE'} mode")
                if key == ord("p"):
                    paused = not paused
                    log_and_print(f"\n{'Paused' if paused else 'Resumed'}")

                elapsed = time.time() - loop_start
                time.sleep(max(0.0, (1.0 / TARGET_FPS) - elapsed))
    finally:
        cap.release()
        cv2.destroyAllWindows()
        log_and_print("\nWebcam released. Goodbye!")


if __name__ == "__main__":
    main()
