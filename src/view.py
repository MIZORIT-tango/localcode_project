import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame, QMessageBox, QSizePolicy
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

        # Сохраняем начальные значения PID по умолчанию
        self.default_pid = {
            'kp': 1.6,
            'ki': 0.5,
            'kd': 0.3
        }

        self.failure_active = False
        self.failure_start_time = None
        self.failure_duration = 30

        self.best_error = 999999
        self.best_overshoot = 999999
        self.best_settling = 999999
        self.best_score = 0

        self.max_level = self.controller.model.level

        self.settled = False
        self.settling_time = None
        self.final_settling_time = None
        self.unstable_since = 0

        self.previous_error = None
        self.has_crossed_target = False
        self.max_overshoot = 0

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

        # Устанавливаем начальные значения PID после создания UI
        self.set_pid_values(self.default_pid['kp'], self.default_pid['ki'], self.default_pid['kd'])

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(30)

        self.failure_start_sim_time = None

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

        self.failure_button = QPushButton("Старт аварии")
        self.failure_button.setFixedWidth(170)
        self.failure_button.clicked.connect(self.trigger_failure)

        header_layout.addStretch()

        header_layout.addWidget(self.failure_button)

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
        self.controls_frame = QFrame()
        self.controls_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e; 
                border: 2px solid #0f3460; 
                border-radius: 8px;
                padding: 15px;
            }
        """)
        self.controls_frame.setMaximumHeight(500)
        controls_layout = QVBoxLayout()

        self.pid_frame = QFrame()
        self.pid_frame.setMaximumHeight(120)
        self.pid_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        pid_layout = QVBoxLayout()
        pid_layout.setContentsMargins(8, 0, 8, 0)  # Уменьшаем отступы
        pid_layout.setSpacing(2)

        pid_controls = QHBoxLayout()

        kp_block = QVBoxLayout()
        self.kp_label = QLabel(f"Kp: {self.controller.pid.kp:.2f}")
        self.kp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kp_slider = QSlider(Qt.Orientation.Horizontal)
        self.kp_slider.setMinimum(0)
        self.kp_slider.setMaximum(1000)
        self.kp_slider.setValue(0)
        self.kp_slider.valueChanged.connect(self.update_kp)
        kp_block.addWidget(self.kp_label)
        kp_block.addWidget(self.kp_slider)
        self.kp_label.setStyleSheet("color: #ff6b6b;")
        pid_controls.addLayout(kp_block)

        ki_block = QVBoxLayout()
        self.ki_label = QLabel(f"Ki: {self.controller.pid.ki:.2f}")
        self.ki_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ki_slider = QSlider(Qt.Orientation.Horizontal)
        self.ki_slider.setMinimum(0)
        self.ki_slider.setMaximum(500)
        self.ki_slider.setValue(0)
        self.ki_slider.valueChanged.connect(self.update_ki)
        ki_block.addWidget(self.ki_label)
        ki_block.addWidget(self.ki_slider)
        self.ki_label.setStyleSheet("color: #6bff6b;")
        pid_controls.addLayout(ki_block)

        kd_block = QVBoxLayout()
        self.kd_label = QLabel(f"Kd: {self.controller.pid.kd:.2f}")
        self.kd_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kd_slider = QSlider(Qt.Orientation.Horizontal)
        self.kd_slider.setMinimum(0)
        self.kd_slider.setMaximum(500)
        self.kd_slider.setValue(0)
        self.kd_slider.valueChanged.connect(self.update_kd)
        kd_block.addWidget(self.kd_label)
        kd_block.addWidget(self.kd_slider)
        self.kd_label.setStyleSheet("color: #6b9fff;")
        pid_controls.addLayout(kd_block)

        pid_layout.addLayout(pid_controls)

        self.pid_frame.setLayout(pid_layout)
        self.pid_frame.hide()
        self.pid_frame.setStyleSheet("""
            background-color: #161a24;
            border-radius: 6px;
        """)
        controls_layout.addWidget(self.pid_frame)

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

        controls_layout.addStretch()
        self.controls_frame.setLayout(controls_layout)

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

        self.settling_label = self.create_metric_label(
            "Время стабилизации:", "-"
        )
        self.overshoot_label = self.create_metric_label(
            "Перерегулирование:", "-"
        )
        self.error_label = self.create_metric_label(
            "Ошибка:", "-"
        )
        self.quality_label = self.create_metric_label(
            "Оценка:", "-"
        )

        metrics_layout.addWidget(self.settling_label)
        metrics_layout.addWidget(self.overshoot_label)
        metrics_layout.addWidget(self.error_label)
        metrics_layout.addWidget(self.quality_label)

        metrics_frame.setLayout(metrics_layout)

        bottom.addWidget(self.controls_frame, 2)  # controls занимает 2/3
        bottom.addWidget(metrics_frame, 1)  # metrics занимает 1/3

        main_layout.addLayout(bottom)

        self.setLayout(main_layout)

    def calculate_score(self, overshoot, settling_time):
        """
        Рассчитывает балльную оценку системы.
        Максимальный балл: 10000

        Критерии:
        - Если система не стабилизировалась или перерегулирование >= 50%: 0 баллов
        - Баллы складываются из двух компонентов:
          1. Оценка перерегулирования (макс. 5000 баллов)
          2. Оценка времени стабилизации (макс. 5000 баллов)
        """
        # Проверка на критические условия
        if settling_time is None or overshoot >= 50:
            return 0

        # ===== 1. ОЦЕНКА ПЕРЕРЕГУЛИРОВАНИЯ (0-5000 баллов) =====
        # Используем экспоненциальную функцию для плавного снижения баллов
        # При 0% перерегулирования -> 5000 баллов
        # При 50% перерегулирования -> 0 баллов
        if overshoot <= 0:
            overshoot_score = 5000
        else:
            # Экспоненциальное затухание: чем меньше перерегулирование, тем выше балл
            # Коэффициент затухания подобран так, чтобы при 50% было близко к 0
            decay_rate = 0.1
            overshoot_score = 5000 * (2.71828 ** (-decay_rate * overshoot))
            overshoot_score = max(0, min(5000, overshoot_score))

        # ===== 2. ОЦЕНКА ВРЕМЕНИ СТАБИЛИЗАЦИИ (0-5000 баллов) =====
        # При времени стабилизации 0 -> 5000 баллов
        # При времени стабилизации 30с и более -> 0 баллов
        if settling_time <= 0:
            time_score = 5000
        elif settling_time >= 30:
            time_score = 0
        else:
            # Линейная интерполяция с усилением для быстрых результатов
            # Используем квадратичную функцию для поощрения быстрой стабилизации
            normalized_time = settling_time / 30.0  # 0 до 1
            time_score = 5000 * (1 - normalized_time) ** 2
            time_score = max(0, min(5000, time_score))

        # ===== 3. ИТОГОВЫЙ СЧЕТ =====
        total_score = overshoot_score + time_score

        # Округляем до целого
        return round(total_score)

    def set_pid_values(self, kp, ki, kd):
        """Устанавливает значения PID и обновляет слайдеры и метки"""
        self.controller.pid.kp = kp
        self.controller.pid.ki = ki
        self.controller.pid.kd = kd

        # Обновляем слайдеры (блокируем сигналы, чтобы избежать рекурсии)
        self.kp_slider.blockSignals(True)
        self.ki_slider.blockSignals(True)
        self.kd_slider.blockSignals(True)

        self.kp_slider.setValue(int(kp * 100))
        self.ki_slider.setValue(int(ki * 100))
        self.kd_slider.setValue(int(kd * 100))

        self.kp_slider.blockSignals(False)
        self.ki_slider.blockSignals(False)
        self.kd_slider.blockSignals(False)

        # Обновляем метки
        self.kp_label.setText(f"Kp: {kp:.2f}")
        self.ki_label.setText(f"Ki: {ki:.2f}")
        self.kd_label.setText(f"Kd: {kd:.2f}")

    def set_mode(self, mode):
        self.controller.mode = mode

        if mode == "manual":
            self.controller.pid_enabled = False
            # Устанавливаем PID коэффициенты в 0
            self.set_pid_values(0, 0, 0)
        elif mode == "auto":
            self.controller.pid_enabled = True
            # Возвращаем стандартные значения PID
            self.set_pid_values(
                self.default_pid['kp'],
                self.default_pid['ki'],
                self.default_pid['kd']
            )
        elif mode == "tuning":
            self.controller.pid_enabled = True
            # Всегда сбрасываем коэффициенты в 0 при входе в режим настройки
            self.set_pid_values(0, 0, 0)

        # Обновляем стили кнопок
        self.manual_btn.setStyleSheet("")
        self.auto_btn.setStyleSheet("")
        self.tuning_btn.setStyleSheet("")

        self.controls_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e; 
                border: 2px solid #0f3460; 
                border-radius: 8px;
                padding: 15px;
            }
        """)

        if mode == "manual":
            self.manual_btn.setStyleSheet("background-color: #00cc66;")
            self.pid_frame.hide()
        elif mode == "auto":
            self.auto_btn.setStyleSheet("background-color: #00cc66;")
            self.pid_frame.hide()
        elif mode == "tuning":
            self.tuning_btn.setStyleSheet("background-color: #00cc66;")
            self.controls_frame.setStyleSheet("""
                QFrame {
                    background-color: #16213e; 
                    border: 2px solid #0f3460; 
                    border-radius: 8px;
                    padding: 5px;
                    padding-left: 6px;
                    padding-right: 6px;
                }
            """)
            self.pid_frame.show()


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

        target = self.controller.model.setpoint
        signed_error = target - level
        error = abs(signed_error)
        self.error_label.setText(f"Ошибка: {error:.1f}%")

        current_time = time.time() - self.controller.start_time

        if self.previous_error is not None:
            error_derivative = signed_error - self.previous_error

            if hasattr(self, 'prev_derivative') and self.prev_derivative is not None:
                if (self.prev_derivative > 0 and error_derivative <= 0) or \
                        (self.prev_derivative < 0 and error_derivative >= 0):

                    if not self.has_crossed_target:
                        self.has_crossed_target = True
                        self.max_overshoot = abs(level - target)
                    else:
                        current_overshoot = abs(level - target)
                        if current_overshoot > self.max_overshoot:
                            self.max_overshoot = current_overshoot

            self.prev_derivative = error_derivative

        self.overshoot_label.setText(f"Перерегулирование: {self.max_overshoot:.1f}%")
        self.previous_error = signed_error

        failure_relative_time = None
        if self.failure_active and self.failure_start_sim_time is not None:
            failure_relative_time = current_time - self.failure_start_sim_time

        if self.failure_active:
            elapsed = time.time() - self.failure_start_time
            remaining = max(0, self.failure_duration - elapsed)
            self.failure_button.setText(f"Авария: {remaining:.0f} c")

            self.best_overshoot = min(self.best_overshoot, self.max_overshoot)

            if self.final_settling_time is not None:
                self.best_settling = min(self.best_settling, self.final_settling_time)

            if self.settled or remaining <= 0:
                current_score = self.calculate_score(self.max_overshoot, self.final_settling_time)
                self.best_score = max(self.best_score, current_score)

            if remaining <= 0:
                self.failure_active = False
                self.failure_button.setText("Авария системы")
                self.show_failure_results()

        # Отслеживание времени стабилизации
        if not self.settled:
            if error < 3:
                if self.settling_time is None:
                    self.settling_time = failure_relative_time if self.failure_active else current_time
                else:
                    check_time = failure_relative_time if self.failure_active else current_time
                    if check_time - self.settling_time > 3:
                        self.settled = True
                        if self.failure_active and self.failure_start_sim_time is not None:
                            self.final_settling_time = check_time - self.unstable_since
                        else:
                            self.final_settling_time = current_time - self.unstable_since
            else:
                self.settling_time = None
        else:
            if error > 5:
                self.settling_time = None
                self.settled = False
                self.unstable_since = failure_relative_time if self.failure_active else current_time
                self.has_crossed_target = False
                self.prev_derivative = None
                self.max_overshoot = 0

        if self.settled:
            self.settling_label.setText(f"Время стабилизации: {self.final_settling_time:.1f} c")
        else:
            self.settling_label.setText("Время стабилизации: ...")

        if self.has_crossed_target:
            if self.max_overshoot < 5:
                quality = "Отличное"
            elif self.max_overshoot < 10:
                quality = "Хорошее"
            elif self.max_overshoot < 15:
                quality = "Удовлетворительно"
            elif self.max_overshoot < 25:
                quality = "Посредственное"
            else:
                quality = "Нестабильное"
        else:
            if error < 3:
                quality = "Отличное (без колебаний)"
            else:
                quality = "В процессе..."

        self.quality_label.setText(f"Оценка: {quality}")

        outflow_percent = self.controller.model.outflow * 10
        self.outflow_label.setText(f"Отдача: {outflow_percent:.1f}%")

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

    def show_failure_results(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Результаты восстановления")

        best_settling_text = f"{self.best_settling:.2f} с" if self.best_settling <= 35 else "Не стабилизировано"

        final_score = self.calculate_score(self.best_overshoot, self.best_settling)

        if final_score >= 9000:
            score_rating = "S - Превосходно!"
        elif final_score >= 7500:
            score_rating = "A - Отлично"
        elif final_score >= 6000:
            score_rating = "B - Хорошо"
        elif final_score >= 4000:
            score_rating = "C - Удовлетворительно"
        elif final_score >= 2000:
            score_rating = "D - Плохо"
        else:
            score_rating = "F - Критически плохо"

        msg.setText(
            f"Результаты аварийного режима:\n\n"
            f"Макс. перерегулирование: {self.max_overshoot:.2f}%\n"
            f"Время стабилизации: {best_settling_text}\n"
            f"Итоговые баллы: {final_score} / 10000\n"
            f"Рейтинг: {score_rating}\n\n"
        )

        msg.exec()

    def update_kp(self, value):
        kp = value / 100
        self.controller.pid.kp = kp
        self.kp_label.setText(f"Kp: {kp:.2f}")

    def update_ki(self, value):
        ki = value / 100
        self.controller.pid.ki = ki
        self.ki_label.setText(f"Ki: {ki:.2f}")

    def update_kd(self, value):
        kd = value / 100
        self.controller.pid.kd = kd
        self.kd_label.setText(f"Kd: {kd:.2f}")

    def trigger_failure(self):
        self.failure_active = True
        self.failure_start_time = time.time()

        self.failure_start_sim_time = time.time() - self.controller.start_time

        self.controller.model.level = random.choice((0, 100))

        self.max_overshoot = 0
        self.previous_error = None
        self.has_crossed_target = False
        self.prev_derivative = None  # Предыдущее значение производной

        self.settled = False
        self.settling_time = None
        self.final_settling_time = None

        self.unstable_since = 0

        self.best_error = 999999
        self.best_overshoot = 999999
        self.best_settling = 999999
        self.best_score = 0  # Сбрасываем лучший счет при новой аварии


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

        level = self.controller.model.level
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
        error = abs(level - 50)
        if error > 30:
            text_color = QColor(255, 80, 80)
        elif error > 15:
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