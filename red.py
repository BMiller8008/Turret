import cv2
import numpy as np
import subprocess
import gpiod
from motor_control import MotorController

# Camera resolution
WIDTH, HEIGHT = 640, 360

# Launch libcamera-vid and ffmpeg for MJPEG capture
libcamera_cmd = [
    "libcamera-vid",
    "--codec", "mjpeg",
    "--width", str(WIDTH),
    "--height", str(HEIGHT),
    "--inline",
    "--framerate", "30",
    "--timeout", "0",
    "--nopreview",
    "--output", "-"
]

ffmpeg_cmd = [
    "ffmpeg",
    "-loglevel", "quiet",
    "-f", "mjpeg",
    "-i", "pipe:0",
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "pipe:1"
]

frame_size = WIDTH * HEIGHT * 3

# Initialize motors
chip = gpiod.Chip("gpiochip0")
x_motor = MotorController(chip, 5, 23, 18, name="XMotor")
y_motor = MotorController(chip, 19, 25, 21, name="YMotor")

x_motor.set_enable(False)
y_motor.set_enable(False)

# Start video stream
libcamera = subprocess.Popen(libcamera_cmd, stdout=subprocess.PIPE)
ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=libcamera.stdout, stdout=subprocess.PIPE)

print("🔴 Centering on red floppy disk. Ctrl+C to exit.")

dead_zone = 50
min_area = 1200

try:
    while True:
        raw = ffmpeg.stdout.read(frame_size)
        if len(raw) != frame_size:
            print("Frame read error")
            continue

        frame = np.frombuffer(raw, np.uint8).reshape((HEIGHT, WIDTH, 3))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 80, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 80, 50])
        upper_red2 = np.array([180, 255, 255])

        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        M = cv2.moments(mask)
        if M["m00"] > min_area:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            offset_x = cx - WIDTH // 2
            offset_y = cy - HEIGHT // 2

            print(f"Center: ({cx}, {cy}) | Offset: X={offset_x}, Y={offset_y}")

            # Adjust step_delay dynamically based on proximity to center
            def compute_delay(offset):
                abs_offset = abs(offset)
                return 0.001 - (0.00195 * (abs_offset / WIDTH))

            # X axis control
            if abs(offset_x) > dead_zone:
                x_motor.set_enable(True)
                x_motor.set_direction(1 if offset_x > 0 else 0)
                x_motor.step_delay = compute_delay(offset_x)
                x_motor.step(1)
            else:
                x_motor.set_enable(False)

            # Y axis control
            if abs(offset_y) > dead_zone:
                y_motor.set_enable(True)
                y_motor.set_direction(1 if offset_y > 0 else 0)
                y_motor.step_delay = compute_delay(offset_y)
                y_motor.step(1)
            else:
                y_motor.set_enable(False)
        else:
            x_motor.set_enable(False)
            y_motor.set_enable(False)
            print("Red target not found")

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    x_motor.set_enable(False)
    y_motor.set_enable(False)
    libcamera.terminate()
    ffmpeg.terminate()
