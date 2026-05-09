import random
import time
from collections import deque

from src.model import TankModel
from src.pid import PIDController

# ================= CONTROLLER =================
class SimulationController:
    def __init__(self):
        self.model = TankModel()
        self.pid = PIDController()
        self.pid_enabled = False
        self.last_time = time.time()
        self.mode = "zero" # manual / auto / tuning / zero - исключительно начальный режим (выкл)

        self.time_data = deque(maxlen=1000)
        self.level_data = deque(maxlen=1000)
        self.start_time = time.time()

    def step(self):
        now = time.time()
        dt = min(now - self.last_time, 0.05)

        error = self.model.level - self.model.setpoint

        if self.mode == "manual":
            self.model.outflow = random.uniform(2,4)
        else:
            control = self.pid.compute(error, dt)
            self.model.outflow += control * dt
            self.model.outflow = max(0.0, min(10.0, self.model.outflow))

        self.model.update(dt)
        self.last_time = now