import cv2
import numpy as np
import subprocess
import time

def capture_frame():
    """Capture a single JPEG frame using libcamera-still."""
    result = subprocess.run(
        ["libcamera-still", "-n", "--immediate", "--width", "640", "--height", "360",
         "--quality", "85", "--timeout", "1", "-o", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    return np.frombuffer(result.stdout, dtype=np.uint8)

def detect_red_from_buffer(jpeg_bytes):
    """Detect red areas in the JPEG byte array."""
    img_array = np.asarray(jpeg_bytes, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        print("❌ Failed to decode frame")
        return False

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 | mask2

    red_pixels = cv2.countNonZero(red_mask)

    return red_pixels > 500

# ========== MAIN LOOP ==========

print("Starting red detection at 10 Hz... (Press Ctrl+C to stop)")
try:
    while True:
        start = time.time()

        jpeg_bytes = capture_frame()
        if detect_red_from_buffer(jpeg_bytes):
            print("🔴 Red detected!")

        # Delay to maintain ~10 Hz (100ms/frame)
        elapsed = time.time() - start
        sleep_time = max(0, 0.1 - elapsed)
        time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\nStopped.")
