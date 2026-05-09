from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont
import pyqtgraph as pg
import time

from src.controller import SimulationController


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("АСУ: Симулятор уровня жидкости")
        self.setGeometry(100, 100, 1200, 750)

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

        # ===== HEADER=====
        header_layout = QHBoxLayout()

        self.help_button = QPushButton("ℹ  О программе")
        self.help_button.setFixedWidth(150)
        self.help_button.clicked.connect(self.show_help)

        header = QLabel("Система управления уровнем жидкости")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold;")

        header_layout.addWidget(self.help_button)

        header_layout.addStretch()

        header_layout.addWidget(header)

        header_layout.addStretch()

        spacer = QLabel()
        spacer.setFixedWidth(40)
        header_layout.addWidget(spacer)

        main_layout.addLayout(header_layout)

        # ===== MAIN AREA =====
        main_area = QHBoxLayout()

        # ---- LEFT: TANK ----
        self.tank_widget = TankWidget(self.controller)
        main_area.addWidget(self.tank_widget)

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
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#121826')
        self.plot_widget.getPlotItem().layout.setContentsMargins(10, 10, 20, 30)

        self.plot_widget.setTitle("Уровень жидкости")
        self.plot_widget.setLabel('left', 'Уровень (%)')
        self.plot_widget.setLabel('bottom', 'Время (с)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setYRange(0, 100)
        self.plot_widget.setXRange(0, 30)

        self.plot_widget.disableAutoRange()

        self.level_curve = self.plot_widget.plot(
            pen=pg.mkPen('#4ecdc4', width=3)
        )

        self.setpoint_line = pg.InfiniteLine(
            pos=50,
            angle=0,
            pen=pg.mkPen('#00ff88', width=2, style=Qt.PenStyle.DashLine)
        )

        self.plot_widget.addItem(self.setpoint_line)

        graph_layout.addWidget(self.plot_widget)
        self.graph_frame.setLayout(graph_layout)

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

        mode_buttons = QHBoxLayout()

        mode_label = QLabel("Режим работы:")
        self.manual_btn = QPushButton("Ручной")
        self.auto_btn = QPushButton("Авто")
        self.tuning_btn = QPushButton("PID")

        self.manual_btn.clicked.connect(lambda: self.set_mode("manual"))
        self.auto_btn.clicked.connect(lambda: self.set_mode("auto"))
        self.tuning_btn.clicked.connect(lambda: self.set_mode("tuning"))

        mode_buttons.addWidget(mode_label)
        mode_buttons.addWidget(self.manual_btn)
        mode_buttons.addWidget(self.auto_btn)
        mode_buttons.addWidget(self.tuning_btn)

        controls_layout.addLayout(mode_buttons)

        in_out_labels = QHBoxLayout()

        self.inflow_label = QLabel("Подача: 0%")
        self.inflow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff6b6b; padding: 5px;")

        self.outflow_label = QLabel("Отдача: 0%")
        self.outflow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.outflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff6b6b; padding: 5px;")

        in_out_labels.addWidget(self.inflow_label)
        in_out_labels.addWidget(self.outflow_label)
        controls_layout.addLayout(in_out_labels)

        slider_label = QLabel("Регулятор подачи:")
        slider_label.setStyleSheet("font-size: 14px; color: #a0a0b0;")
        controls_layout.addWidget(slider_label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.valueChanged.connect(self.on_slider_change)
        controls_layout.addWidget(self.slider)

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

    def set_mode(self, mode):
        self.controller.mode = mode

        if mode == "manual":
            self.controller.pid_enabled = False
        else:
            self.controller.pid_enabled = True

        self.manual_btn.setStyleSheet("")
        self.auto_btn.setStyleSheet("")
        self.tuning_btn.setStyleSheet("")

        if mode == "manual":
            self.manual_btn.setStyleSheet("background-color: #00cc66;")
        elif mode == "auto":
            self.auto_btn.setStyleSheet("background-color: #00cc66;")
        else:
            self.tuning_btn.setStyleSheet("background-color: #00cc66;")

    def show_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("О программе")

        from PyQt6.QtGui import QIcon
        msg.setWindowIcon(QIcon.fromTheme("dialog-information"))

        msg.setStyleSheet("""
                QMessageBox {
                    background-color: #1a1a2e;
                    color: #ffffff;
                    font-size: 16px;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                    font-size: 14px;
                }
                QMessageBox QPushButton {
                    background-color: #16213e;
                    color: #ffffff;
                    border: 1px solid #0f3460;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 14px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #0f3460;
                }
            """)
        msg.setText(
            "Этот симулятор демонстрирует, как работают системы автоматического управления.\n\n"
            "Вы управляете уровнем жидкости в резервуаре:\n"
            "- В ручном режиме вы сами регулируете подачу\n"
            "- В автоматическом режиме система делает это за вас\n"
            "- В режиме настройки вы можете изменить поведение системы\n\n"
            "Такие системы используются в промышленности, робототехнике и даже в автопилотах."
        )

        msg.exec()

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

    # -------- UPDATE LOOP --------
    def update_simulation(self):
        self.controller.step()
        level = self.controller.model.level
        self.tank_widget.update()

        outflow_percent = self.controller.model.outflow * 10
        self.outflow_label.setText(f"Отдача: {outflow_percent:.1f}%")

        current_time = time.time() - self.controller.start_time
        self.controller.time_data.append(current_time)
        self.controller.level_data.append(level)

        window = 30
        if current_time > window:
            self.plot_widget.setXRange(current_time - window, current_time)

        self.level_curve.setData(
            list(self.controller.time_data),
            list(self.controller.level_data)
        )
        if outflow_percent > 75:
            self.outflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4444; padding: 5px;")
        elif outflow_percent > 50:
            self.outflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffaa00; padding: 5px;")
        else:
            self.outflow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #00cc66; padding: 5px;")


class TankWidget(QWidget):
    def __init__(self, controller):
        super().__init__()

        self.controller = controller
        self.setMinimumSize(300, 500)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # размеры бака
        tank_width = 140
        tank_height = 320

        x = (width - tank_width) // 2
        y = 60

        level  = self.controller.model.level
        level_percent = self.controller.model.level / 100.0

        # ВНЕШНИЙ ЦИЛИНДР
        painter.setPen(QPen(QColor(220, 220, 220), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # стенки
        painter.drawRect(x, y, tank_width, tank_height)

        # верхний эллипс
        painter.drawEllipse(x, y - 15, tank_width, 30)

        # нижний эллипс
        painter.drawEllipse(x, y + tank_height - 15, tank_width, 30)

        # ЖИДКОСТЬ
        fluid_height = int(tank_height * level_percent)
        fluid_y = y + tank_height - fluid_height
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 140, 255, 180)))

        # жидкость внутри
        painter.drawRect(
            x + 2,
            fluid_y,
            tank_width - 4,
            fluid_height
        )

        # верх жидкости
        painter.drawEllipse(
            x + 2,
            fluid_y - 12,
            tank_width - 4,
            24
        )

        # низ жидкости
        painter.drawEllipse(x, y + tank_height - 15, tank_width, 30)

        # ТЕКСТ
        if level < 20 or level > 80:
            text_color = QColor(255, 80, 80)
        elif level < 35 or level > 65:
            text_color = QColor(255, 220, 120)
        else:
            text_color = QColor(100, 255, 180)

        font = QFont()
        font.setPointSize(16)
        font.setBold(True)

        painter.setFont(font)

        painter.setPen(text_color)
        painter.drawText(
            x - 10,
            y + tank_height + 50,
            tank_width + 20,
            40,
            Qt.AlignmentFlag.AlignCenter,
            f"Уровень: {level:.1f}%"
        )