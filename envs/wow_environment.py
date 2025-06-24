"""
Модуль для взаимодействия с окном World of Warcraft
"""

import logging
import time
import win32gui
import win32con
import ctypes
import dxcam
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class WoWEnvironment:
    """Класс для работы с окном World of Warcraft"""

    # Максимальные размеры для dxcam
    MAX_WIDTH = 2293
    MAX_HEIGHT = 960

    def __init__(self, window_title: str = "World of Warcraft"):
        self.window_title = window_title
        self.window_handle = None
        self.camera = None
        self.capture_region = None
        self.last_frame_time = 0
        self.frame_rate = 15

        try:
            self._initialize()
        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"Ошибка инициализации: {str(e)}")

    def _initialize(self):
        """Основная инициализация"""
        self._set_dpi_awareness()
        self._find_window()
        self._setup_capture_region()
        self._init_camera()

    def _set_dpi_awareness(self):
        """Установка DPI awareness"""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()

    def _find_window(self):
        """Поиск окна игры с расширенной проверкой"""

        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title.lower() in title.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    if rect[2] - rect[0] > 100 and rect[3] - rect[1] > 100:  # Минимальные размеры
                        extra.append(hwnd)

        windows = []
        win32gui.EnumWindows(callback, windows)

        if not windows:
            raise ValueError(f"Окно '{self.window_title}' не найдено или слишком маленькое")

        self.window_handle = windows[0]
        logger.info(f"Найдено окно: {win32gui.GetWindowText(self.window_handle)}")

    def _setup_capture_region(self):
        """Установка региона захвата"""
        try:
            # Получаем реальные координаты окна
            left, top, right, bottom = win32gui.GetWindowRect(self.window_handle)
            width = right - left
            height = bottom - top

            # Проверяем что окно не свернуто
            if win32gui.IsIconic(self.window_handle):
                win32gui.ShowWindow(self.window_handle, win32con.SW_RESTORE)
                time.sleep(0.5)
                left, top, right, bottom = win32gui.GetWindowRect(self.window_handle)
                width = right - left
                height = bottom - top

            # Применяем ограничения dxcam
            width = min(width, self.MAX_WIDTH)
            height = min(height, self.MAX_HEIGHT)

            # Центрируем регион захвата
            left += (right - left - width) // 2
            top += (bottom - top - height) // 2

            self.capture_region = (left, top, left + width, top + height)
            logger.info(f"Установлен регион захвата: {self.capture_region}")

        except Exception as e:
            raise RuntimeError(f"Ошибка установки региона захвата: {str(e)}")

    def _init_camera(self):
        """Инициализация камеры с обработкой ошибок"""
        try:
            if not self.capture_region:
                raise ValueError("Регион захвата не установлен")

            left, top, right, bottom = self.capture_region
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                raise ValueError("Некорректные размеры региона захвата")

            self.camera = dxcam.create(
                output_idx=0,
                region=(left, top, right, bottom),
                output_color="RGB"
            )

            # Запускаем захват с указанием FPS
            self.camera.start(target_fps=self.frame_rate)

            logger.info("Камера успешно инициализирована")

        except Exception as e:
            raise RuntimeError(f"Ошибка инициализации камеры: {str(e)}")

    def get_game_state(self) -> Dict[str, Any]:
        """Получение состояния игры"""
        frame = self.capture_frame()

        return {
            "resolution": f"{self.capture_region[2] - self.capture_region[0]}x{self.capture_region[3] - self.capture_region[1]}",
            "frame_shape": frame.shape if frame is not None else None,
            "timestamp": time.time(),
            "status": "active" if frame is not None else "error"
        }

    def capture_frame(self) -> Optional[np.ndarray]:
        """Захват текущего кадра"""
        if time.time() - self.last_frame_time < 1 / self.frame_rate:
            return None

        try:
            frame = self.camera.get_latest_frame()
            if frame is None:
                return None

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.last_frame_time = time.time()
            return frame

        except Exception as e:
            logger.error(f"Ошибка захвата кадра: {str(e)}")
            self._restart_camera()
            return None

    def _restart_camera(self):
        """Перезапуск камеры при ошибках"""
        try:
            self._cleanup_camera()
            time.sleep(0.5)
            self._init_camera()
            logger.info("Камера перезапущена")
        except Exception as e:
            logger.error(f"Ошибка перезапуска камеры: {str(e)}")

    def _cleanup_camera(self):
        """Очистка ресурсов камеры"""
        if self.camera is not None:
            try:
                self.camera.stop()
                self.camera.release()
            except Exception as e:
                logger.warning(f"Ошибка освобождения камеры: {str(e)}")
            finally:
                self.camera = None

    def _cleanup(self):
        """Полная очистка ресурсов"""
        self._cleanup_camera()
        logger.info("Ресурсы освобождены")

    def __del__(self):
        """Деструктор"""
        self._cleanup()