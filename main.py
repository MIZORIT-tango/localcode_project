# PyQt6 MVP UI with structured layout and placeholders
# Layers kept: model / pid / controller / view

import sys
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame
)
from PyQt6.QtCore import Qt, QTimer


# ================= MODEL =================
class TankModel:
    def __init__(self):
        self.level = 50.0
        self.inflow = 0.0
        self.outflow = 0.0
        self.setpoint = 50.0

    def update(self, dt):
        self.level += (self.inflow - self.outflow) * dt * 3.0
        self.level = max(0.0, min(100.0, self.level))


# ================= PID =================
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


# ================= CONTROLLER =================
class SimulationController:
    def __init__(self):
        self.model = TankModel()
        self.pid = PIDController()
        self.pid_enabled = False
        self.last_time = time.time()

    def step(self):
        now = time.time()
        dt = min(now - self.last_time, 0.05)

        error = self.model.setpoint - self.model.level

        if self.pid_enabled:
            control = self.pid.compute(error, dt)
            self.model.outflow = max(0.0, min(10.0, self.model.inflow + control))
        else:
            self.model.outflow = self.model.inflow * 0.5

        self.model.update(dt)
        self.last_time = now


# ================= VIEW =================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("АСУ: Симулятор уровня жидкости")
        self.setGeometry(100, 100, 1000, 700)

        self.controller = SimulationController()

        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #16213e;
                color: #ffffff;
                border: 1px solid #0f3460;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0f3460;
            }
            QSlider::groove:horizontal {
                border: 1px solid #0f3460;
                height: 8px;
                background: #16213e;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                border: 1px solid #e94560;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(30)

    # -------- UI LAYOUT --------
    def init_ui(self):
        main_layout = QVBoxLayout()

        # ===== HEADER =====
        header = QLabel("Система управления уровнем жидкости")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #e0e0e0; padding: 10px;")
        main_layout.addWidget(header)

        # ===== MAIN AREA =====
        main_area = QHBoxLayout()

        # ---- LEFT: TANK ----
        self.tank_frame = QFrame()
        self.tank_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e; 
                border: 2px solid #0f3460; 
                border-radius: 8px;
            }
        """)
        self.tank_frame.setMinimumSize(300, 400)

        tank_layout = QVBoxLayout()
        self.level_label = QLabel("Уровень: 50.0%")
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.level_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ff88; padding: 20px;")
        tank_layout.addWidget(self.level_label)

        tank_description = QLabel("Индикатор уровня жидкости")
        tank_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tank_description.setStyleSheet("font-size: 14px; color: #a0a0b0; padding: 5px;")
        tank_layout.addWidget(tank_description)

        tank_layout.addStretch()
        self.tank_frame.setLayout(tank_layout)

        # ---- RIGHT: GRAPH ----
        self.graph_frame = QFrame()
        self.graph_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e; 
                border: 2px solid #0f3460; 
                border-radius: 8px;
            }
        """)
        self.graph_frame.setMinimumSize(500, 400)

        graph_layout = QVBoxLayout()
        graph_label = QLabel("График уровня жидкости")
        graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        graph_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #4ecdc4; padding: 15px;")
        graph_layout.addWidget(graph_label)

        graph_placeholder = QLabel("Здесь будет отображаться график\nизменения уровня во времени")
        graph_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        graph_placeholder.setStyleSheet("font-size: 16px; color: #a0a0b0; padding: 10px;")
        graph_layout.addWidget(graph_placeholder)

        graph_layout.addStretch()
        self.graph_frame.setLayout(graph_layout)

        main_area.addWidget(self.tank_frame)
        main_area.addWidget(self.graph_frame)

        main_layout.addLayout(main_area)

        # ===== BOTTOM AREA =====
        bottom = QHBoxLayout()

        # ---- CONTROLS ----
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e; 
                border: 2px solid #0f3460; 
                border-radius: 8px;
                padding: 15px;
            }
        """)
        controls_layout = QVBoxLayout()

        # inflow label (dynamic)
        self.inflow_label = QLabel("Подача: 0%")
        self.inflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff6b6b; padding: 5px;")
        controls_layout.addWidget(self.inflow_label)

        slider_label = QLabel("Регулятор подачи:")
        slider_label.setStyleSheet("font-size: 14px; color: #a0a0b0;")
        controls_layout.addWidget(slider_label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.valueChanged.connect(self.on_slider_change)
        controls_layout.addWidget(self.slider)

        self.pid_button = QPushButton("PID OFF")
        self.pid_button.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                padding: 10px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
        """)
        self.pid_button.clicked.connect(self.toggle_pid)
        controls_layout.addWidget(self.pid_button)

        controls_frame.setLayout(controls_layout)

        # ---- METRICS ----
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e; 
                border: 2px solid #0f3460; 
                border-radius: 8px;
                padding: 15px;
            }
        """)
        metrics_layout = QVBoxLayout()

        metrics_title = QLabel("Метрики системы:")
        metrics_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4ecdc4;")
        metrics_layout.addWidget(metrics_title)

        metrics_layout.addWidget(self.create_metric_label("Время стабилизации:", "-"))
        metrics_layout.addWidget(self.create_metric_label("Перерегулирование:", "-"))
        metrics_layout.addWidget(self.create_metric_label("Оценка:", "-"))

        metrics_frame.setLayout(metrics_layout)

        bottom.addWidget(controls_frame, 2)  # controls занимает 2/3
        bottom.addWidget(metrics_frame, 1)  # metrics занимает 1/3

        main_layout.addLayout(bottom)

        self.setLayout(main_layout)

    @staticmethod
    def create_metric_label(title, value):
        """Создаёт стилизованную метку для метрик"""
        label = QLabel(f"{title} {value}")
        label.setStyleSheet("font-size: 14px; color: #e0e0e0; padding: 5px;")
        return label

    # -------- INTERACTION --------
    def on_slider_change(self, value):
        self.controller.model.inflow = value / 10.0
        self.inflow_label.setText(f"Подача: {value}%")
        if value > 70:
            self.inflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4444; padding: 5px;")
        elif value > 30:
            self.inflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffaa00; padding: 5px;")
        else:
            self.inflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #00cc66; padding: 5px;")

    def toggle_pid(self):
        self.controller.pid_enabled = not self.controller.pid_enabled
        if self.controller.pid_enabled:
            self.pid_button.setText("PID ON")
            self.pid_button.setStyleSheet("""
                QPushButton {
                    background-color: #00cc66;
                    color: #ffffff;
                    border: 1px solid #00cc66;
                    padding: 10px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #00ff88;
                }
            """)
        else:
            self.pid_button.setText("PID OFF")
            self.pid_button.setStyleSheet("""
                QPushButton {
                    background-color: #0f3460;
                    color: #ffffff;
                    border: 1px solid #e94560;
                    padding: 10px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #e94560;
                }
            """)

    # -------- UPDATE LOOP --------
    def update_simulation(self):
        self.controller.step()
        level = self.controller.model.level
        self.level_label.setText(f"Уровень: {level:.1f}%")

        if level > 90 or level < 10:
            self.level_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ff4444; padding: 20px;")
        elif level > 70 or level < 30:
            self.level_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffaa00; padding: 20px;")
        else:
            self.level_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ff88; padding: 20px;")


# ================= MAIN =================
def main():
    app = QApplication(sys.argv)

    app.setStyle('Fusion')
    app.setStyleSheet("""
        QToolTip {
            background-color: #16213e;
            color: #ffffff;
            border: 1px solid #0f3460;
            padding: 5px;
            font-size: 12px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()