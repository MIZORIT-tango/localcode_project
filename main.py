import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time


class LevelSimulatorPID:
    def __init__(self, root):
        self.root = root
        self.root.title("PID Level Simulator")
        self.root.geometry("1200x700")
        self.root.configure(bg="#0f111a")

        # ================= MODEL =================
        self.level = 50.0
        self.inflow = 0.0
        self.outflow = 0.0
        self.setpoint = 50.0

        # PID
        self.kp = 1.6
        self.ki = 0.5
        self.kd = 0.3

        self.integral = 0.0
        self.prev_error = 0.0

        self.pid_enabled = False
        self.running = True

        # history (строго float)
        self.history = [50.0 for _ in range(100)]
        self.xdata = [i for i in range(100)]

        self.build_ui()

        threading.Thread(target=self.simulation_loop, daemon=True).start()

    # ================= UI =================
    def build_ui(self):
        left = tk.Frame(self.root, bg="#0f111a")
        left.pack(side=tk.LEFT, padx=15, pady=15)

        # ===== LEVEL GAUGE =====
        self.canvas = tk.Canvas(left, width=140, height=320, bg="#1b1f2a", highlightthickness=0)
        self.canvas.pack()

        self.level_bar = self.canvas.create_rectangle(
            40, 300, 100, 300,
            fill="cyan"
        )

        self.level_label = tk.Label(
            left,
            text="50.0%",
            font=("Arial", 16),
            fg="white",
            bg="#0f111a"
        )
        self.level_label.pack(pady=10)

        # ===== SLIDER =====
        self.slider = tk.Scale(
            left,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=380,
            label="Inflow",
            command=self.update_inflow
        )
        self.slider.pack(pady=15)

        # PID toggle
        self.btn = tk.Button(
            left,
            text="PID OFF",
            command=self.toggle_pid,
            width=18,
            height=2
        )
        self.btn.pack(pady=10)

        # ================= GRAPH =================
        right = tk.Frame(self.root, bg="#0f111a")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor("#0f111a")
        self.ax.set_facecolor("#121826")

        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, 100)

        self.ax.grid(True, alpha=0.3)
        self.ax.tick_params(colors="white")

        # LEVEL LINE
        self.level_line, = self.ax.plot(
            self.xdata,
            self.history,
            color="orange",
            linewidth=2
        )

        # SETPOINT LINE
        self.sp_line, = self.ax.plot(
            [0, 100],
            [self.setpoint, self.setpoint],
            "--",
            color="lime",
            linewidth=2
        )

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas_plot.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ================= PID =================
    def pid(self, error, dt):
        self.integral += error * dt
        self.integral = max(-100.0, min(100.0, self.integral))

        derivative = (error - self.prev_error) / dt if dt > 1e-6 else 0.0
        self.prev_error = error

        return (
            self.kp * error +
            self.ki * self.integral +
            self.kd * derivative
        )

    # ================= SIMULATION =================
    def simulation_loop(self):
        last_time = time.time()

        while True:
            if not self.running:
                time.sleep(0.05)
                continue

            now = time.time()
            dt = now - last_time
            dt = float(min(dt, 0.05))

            error = self.setpoint - self.level

            if self.pid_enabled:
                control = self.pid(error, dt)
                self.outflow = max(0.0, min(10.0, self.inflow + control))
            else:
                self.outflow = self.inflow * 0.5

            # system dynamics
            self.level += (self.inflow - self.outflow) * dt * 3.0
            self.level = float(max(0.0, min(100.0, self.level)))

            # history update
            self.history.append(float(self.level))
            if len(self.history) > 100:
                self.history.pop(0)

            self.root.after(0, self.update_ui)

            last_time = now
            time.sleep(0.03)

    # ================= UI UPDATE =================
    def update_ui(self):
        self.level_label.config(text=f"{self.level:.1f}%")

        # gauge
        h = int(300 * (self.level / 100.0))
        self.canvas.coords(self.level_bar, 40, 300 - h, 100, 300)

        color = "red" if self.level > 80 else "cyan"
        self.canvas.itemconfig(self.level_bar, fill=color)

        # ограничение на отрисовку кадров
        now_graph = time.time()
        if not hasattr(self, '_last_graph_draw'):
            self._last_graph_draw = 0
        if now_graph - self._last_graph_draw < 0.1:
            return
        self._last_graph_draw = now_graph

        # ================= GRAPH FIX =================
        x = [int(i) for i in range(len(self.history))]
        y = [float(v) for v in self.history]

        self.level_line.set_xdata(x)
        self.level_line.set_ydata(y)

        sp = float(self.setpoint)
        self.sp_line.set_ydata([sp, sp])
        self.sp_line.set_xdata([0, 100])

        self.canvas_plot.draw_idle()

    # ================= CALLBACKS =================
    def update_inflow(self, value):
        self.inflow = float(value) / 10.0

    def toggle_pid(self):
        self.pid_enabled = not self.pid_enabled
        self.btn.config(text="PID ON" if self.pid_enabled else "PID OFF")


if __name__ == "__main__":
    root = tk.Tk()
    app = LevelSimulatorPID(root)
    root.mainloop()