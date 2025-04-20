import cv2
import numpy as np
import subprocess
import gpiod
from motor_control import MotorController

# ────────── Camera resolution ──────────
WIDTH, HEIGHT = 640, 360
frame_size    = WIDTH * HEIGHT * 3

# ────────── libcamera + ffmpeg pipeline ──────────
libcamera_cmd = [
    "libcamera-vid", "--codec", "mjpeg",
    "--width", str(WIDTH), "--height", str(HEIGHT),
    "--inline", "--framerate", "30",
    "--timeout", "0", "--nopreview", "--output", "-"
]

ffmpeg_cmd = [
    "ffmpeg", "-loglevel", "quiet",
    "-f", "mjpeg", "-i", "pipe:0",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"
]

# ────────── Motor setup ──────────
chip   = gpiod.Chip("gpiochip0")
x_motor = MotorController(chip, 5, 23, 18, name="XMotor")
y_motor = MotorController(chip, 19, 25, 21, name="YMotor")
x_motor.set_enable(False)
y_motor.set_enable(False)

# ────────── Start video stream ──────────
libcamera = subprocess.Popen(libcamera_cmd, stdout=subprocess.PIPE)
ffmpeg    = subprocess.Popen(ffmpeg_cmd, stdin=libcamera.stdout,
                             stdout=subprocess.PIPE)

print("🔵 Centering on blue object. Ctrl+C to exit.")

# ────────── Thresholds & helpers ──────────
dead_zone = 50
min_area  = 1200

def compute_delay_x(offset):
    return 0.001 - (0.001975 * (abs(offset) / WIDTH))

def compute_delay_y(offset):
    return 0.001 - (0.001975 * (abs(offset) / HEIGHT))

# ────────── Lost‑target memory for both axes ──────────
last_dir_x, last_dir_y         = None, None     # 1=positive/right/down, 0=negative/left/up
last_delay_x, last_delay_y     = 0.002, 0.002   # default step‑delays
lost_frames_x = lost_frames_y  = 0
MAX_LOST_FRAMES = 10

try:
    while True:
        raw = ffmpeg.stdout.read(frame_size)
        if len(raw) != frame_size:
            print("Frame read error"); continue

        frame = np.frombuffer(raw, np.uint8).reshape((HEIGHT, WIDTH, 3))
        hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_blue = np.array([100, 150, 50])
        upper_blue = np.array([140, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        M = cv2.moments(mask)
        if M["m00"] > min_area:                             # ── Blob FOUND
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            off_x = cx - WIDTH  // 2
            off_y = cy - HEIGHT // 2
            print(f"Center: ({cx},{cy}) | Offset: X={off_x} Y={off_y}")

            # ----- X axis control -----
            if abs(off_x) > dead_zone:
                dir_x  = 1 if off_x > 0 else 0
                delayx = compute_delay_x(off_x)
                x_motor.set_enable(True)
                x_motor.set_direction(dir_x)
                x_motor.step_delay = delayx
                x_motor.step(1)
                last_dir_x, last_delay_x = dir_x, delayx
                lost_frames_x = 0
            else:
                x_motor.set_enable(False)
                last_dir_x = None
                lost_frames_x = 0

            # ----- Y axis control -----
            if abs(off_y) > dead_zone:
                dir_y  = 1 if off_y > 0 else 0  # down = positive
                delayy = compute_delay_y(off_y)
                y_motor.set_enable(True)
                y_motor.set_direction(dir_y)
                y_motor.step_delay = delayy
                y_motor.step(1)
                last_dir_y, last_delay_y = dir_y, delayy
                lost_frames_y = 0
            else:
                y_motor.set_enable(False)
                last_dir_y = None
                lost_frames_y = 0

        else:                                               # ── Blob LOST
            print("Blue object not found")

            # ----- Continue X for up to 20 frames -----
            if last_dir_x is not None and lost_frames_x < MAX_LOST_FRAMES:
                x_motor.set_enable(True)
                x_motor.set_direction(last_dir_x)
                x_motor.step_delay = last_delay_x
                x_motor.step(1)
                lost_frames_x += 1
                print(f"X continuing ({lost_frames_x}/{MAX_LOST_FRAMES})")
            else:
                x_motor.set_enable(False)

            # ----- Continue Y for up to 20 frames -----
            if last_dir_y is not None and lost_frames_y < MAX_LOST_FRAMES:
                y_motor.set_enable(True)
                y_motor.set_direction(last_dir_y)
                y_motor.step_delay = last_delay_y
                y_motor.step(1)
                lost_frames_y += 1
                print(f"Y continuing ({lost_frames_y}/{MAX_LOST_FRAMES})")
            else:
                y_motor.set_enable(False)

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    x_motor.set_enable(False)
    y_motor.set_enable(False)
    libcamera.terminate()
    ffmpeg.terminate()
