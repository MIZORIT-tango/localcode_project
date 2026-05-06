class PIDController:
    def __init__(self, kp=1.6, ki=0.5, kd=0.3):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        self.integral += error * dt
        self.integral = max(-100.0, min(100.0, self.integral))

        derivative = (error - self.prev_error) / dt if dt > 1e-6 else 0.0
        self.prev_error = error

        return (
                self.kp * error +
                self.ki * self.integral +
                self.kd * derivative
        )