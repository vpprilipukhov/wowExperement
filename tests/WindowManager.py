import win32gui
import win32process
import win32con
import time
import os
from mss import mss
import numpy as np
import cv2
import logging
import psutil
from typing import Optional, Tuple, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('window_manager.log'),
        logging.StreamHandler()
    ]
)


class WowWindowDetector:
    def __init__(self, screenshots_dir: str = "screenshots"):
        """Инициализация детектора окон WoW"""
        self.sct = mss()
        self.screenshots_dir = screenshots_dir
        os.makedirs(self.screenshots_dir, exist_ok=True)

        self.current_handle = None
        self.last_scan = 0
        self.scan_interval = 2  # Проверка активности каждые 2 секунды
        self.wow_process_names = [
            'wow.exe', 'wow-64.exe',
            'wowclassic.exe', 'PandaWoW-64.exe'
        ]

    def _get_process_info(self, hwnd: int) -> Tuple[Optional[int], Optional[str]]:
        """Получает PID и имя процесса по handle окна"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = psutil.Process(pid).name() if pid else None
            return pid, process_name
        except Exception:
            return None, None

    def _is_wow_window(self, hwnd: int) -> bool:
        """Проверяет, является ли окно клиентом WoW"""
        if not win32gui.IsWindowVisible(hwnd):
            return False

        pid, process_name = self._get_process_info(hwnd)
        if not process_name:
            return False

        return process_name.lower() in self.wow_process_names

    def _get_active_wow_window(self) -> Optional[int]:
        """Находит активное окно WoW"""
        try:
            # Проверяем текущее активное окно
            foreground_hwnd = win32gui.GetForegroundWindow()
            if self._is_wow_window(foreground_hwnd):
                return foreground_hwnd

            # Если активное окно не WoW, ищем любое окно WoW
            def enum_windows_callback(hwnd, wow_handles):
                if self._is_wow_window(hwnd):
                    wow_handles.append(hwnd)

            wow_handles = []
            win32gui.EnumWindows(enum_windows_callback, wow_handles)
            return wow_handles[0] if wow_handles else None

        except Exception as e:
            logging.error(f"Ошибка поиска окна: {str(e)}")
            return None

    def is_active(self) -> bool:
        """Проверяет, активно ли окно WoW прямо сейчас"""
        current_time = time.time()
        if current_time - self.last_scan < self.scan_interval:
            return bool(self.current_handle)

        self.last_scan = current_time
        self.current_handle = self._get_active_wow_window()
        return bool(self.current_handle)

    def _get_client_region(self) -> Optional[Dict]:
        """Получает координаты клиентской области без рамок"""
        try:
            if not self.current_handle:
                return None

            # Получаем размер клиентской области
            client_rect = win32gui.GetClientRect(self.current_handle)

            # Конвертируем в экранные координаты
            client_left, client_top = win32gui.ClientToScreen(
                self.current_handle,
                (client_rect[0], client_rect[1])
            )
            client_right, client_bottom = win32gui.ClientToScreen(
                self.current_handle,
                (client_rect[2], client_rect[3])
            )

            return {
                'left': client_left,
                'top': client_top,
                'width': client_right - client_left,
                'height': client_bottom - client_top
            }
        except Exception as e:
            logging.error(f"Ошибка получения региона: {str(e)}")
            return None

    def capture_active_client_area(self) -> Optional[Tuple[np.ndarray, Dict]]:
        """Захватывает ТОЛЬКО клиентскую область активного окна WoW"""
        if not self.is_active():
            logging.warning("Нельзя сделать скриншот: WoW не активно")
            return None

        try:
            region = self._get_client_region()
            if not region:
                return None

            # Захват только клиентской области
            screenshot = self.sct.grab(region)
            img = np.array(screenshot)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Сохранение скриншота
            timestamp = int(time.time())
            filename = os.path.join(self.screenshots_dir, f"wow_{timestamp}.jpg")
            cv2.imwrite(filename, img_bgr)

            # Метаданные
            pid, process_name = self._get_process_info(self.current_handle)
            metadata = {
                'filename': filename,
                'hwnd': self.current_handle,
                'timestamp': timestamp,
                'window_region': region,
                'process_id': pid,
                'process_name': process_name,
                'is_active': self.is_active()
            }

            logging.info(f"Скриншот сохранён: {filename}")
            return img_bgr, metadata

        except Exception as e:
            logging.error(f"Ошибка захвата: {str(e)}", exc_info=True)
            return None

    def run_test(self, duration: int = 30):
        """Тест: делает скриншоты только когда WoW активно"""
        print(f"Тест работы на {duration} секунд...")
        end_time = time.time() + duration

        while time.time() < end_time:
            if self.is_active():
                result = self.capture_active_client_area()
                if result:
                    print(f"Сделан скриншот: {result[1]['filename']}")
                else:
                    print("Ошибка захвата области")
            else:
                print("WoW не активно - скриншот не сделан")

            time.sleep(1)

        print("Тест завершен")


if __name__ == "__main__":
    detector = WowWindowDetector()
    detector.run_test()