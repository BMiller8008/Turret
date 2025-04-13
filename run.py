from motor_control import MotorController, MotorManager
import gpiod
import time

def run_keyboard_control():
    chip = gpiod.Chip("gpiochip0")

    # Motor 1: GPIO 5 (step), 23 (dir), 18 (enable)
    motor1 = MotorController(chip, step_gpio=5, dir_gpio=23, en_gpio=18, name="Motor1")

    # Motor 2: GPIO 19 (step), 25 (dir), 21 (enable)
    motor2 = MotorController(chip, step_gpio=19, dir_gpio=25, en_gpio=21, name="Motor2")

    # MotorManager will listen for keyboard input to control both motors
    MotorManager([motor1, motor2])

    print("Motor control started. Use keyboard:")
    print("  q = Toggle Motor 1 direction")
    print("  w = Toggle Motor 2 direction")
    print("  a = Toggle Motor 1 on/off")
    print("  s = Toggle Motor 2 on/off")
    print("  Ctrl+C = Exit")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDisabling motors and exiting...")
        motor1.set_enable(False)
        motor2.set_enable(False)

if __name__ == "__main__":
    run_keyboard_control()
