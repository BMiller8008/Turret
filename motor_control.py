import gpiod
import time
import threading
import sys
import termios
import tty

class MotorController:
    def __init__(self, chip: gpiod.Chip, step_gpio, dir_gpio, en_gpio, name="Motor"):
        self.name = name
        self.chip = chip
        self.step_line = chip.get_line(step_gpio)
        self.dir_line = chip.get_line(dir_gpio)
        self.en_line = chip.get_line(en_gpio)

        self.step_line.request(consumer=name, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
        self.dir_line.request(consumer=name, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        self.en_line.request(consumer=name, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])  # enabled

        self.enabled = True
        self.direction = 1

        self._step_thread = threading.Thread(target=self._step_loop, daemon=True)
        self._step_thread.start()

    def _step_loop(self):
        while True:
            if self.enabled:
                self.step_line.set_value(1)
                time.sleep(0.001)
                self.step_line.set_value(0)
                time.sleep(0.001)
            else:
                time.sleep(0.01)

    def toggle_direction(self):
        self.direction ^= 1
        self.dir_line.set_value(self.direction)
        print(f"{self.name} direction: {'CW' if self.direction else 'CCW'}")

    def set_direction(self, direction: int):
        self.direction = direction
        self.dir_line.set_value(direction)

    def toggle_enable(self):
        self.enabled = not self.enabled
        self.en_line.set_value(not self.enabled)
        print(f"{self.name} {'enabled' if self.enabled else 'disabled'}")

    def set_enable(self, enable: bool):
        self.enabled = enable
        self.en_line.set_value(not enable)

    def is_enabled(self):
        return self.enabled

    def get_direction(self):
        return self.direction

class MotorManager:
    def __init__(self, motors):
        self.motors = motors
        self.input_thread = threading.Thread(target=self._listen_for_input, daemon=True)
        self.input_thread.start()

    def _listen_for_input(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        print("Controls:")
        print("  q = Toggle Motor 1 direction")
        print("  w = Toggle Motor 2 direction")
        print("  a = Toggle Motor 1 on/off")
        print("  s = Toggle Motor 2 on/off")
        print("  Ctrl+C to exit")

        try:
            tty.setcbreak(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == 'q':
                    self.motors[0].toggle_direction()
                elif ch == 'w':
                    self.motors[1].toggle_direction()
                elif ch == 'a':
                    self.motors[0].toggle_enable()
                elif ch == 's':
                    self.motors[1].toggle_enable()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Optional usage example:
if __name__ == "__main__":
    chip = gpiod.Chip("gpiochip0")

    motor1 = MotorController(chip, step_gpio=5, dir_gpio=23, en_gpio=18, name="Motor1")
    motor2 = MotorController(chip, step_gpio=19, dir_gpio=25, en_gpio=21, name="Motor2")

    manager = MotorManager([motor1, motor2])

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDisabling motors...")
        motor1.set_enable(False)
        motor2.set_enable(False)
