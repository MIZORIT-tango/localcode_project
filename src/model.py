class TankModel:
    def __init__(self):
        self.level = 50.0
        self.inflow = 0.0
        self.outflow = 0.0
        self.setpoint = 50.0

    def update(self, dt):
        self.level += (self.inflow - self.outflow) * dt * 3.0
        self.level = max(0.0, min(100.0, self.level))