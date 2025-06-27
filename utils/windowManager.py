"""
WowWindowDetector_DPI_Fixed.py - корректный захват окна с учетом DPI масштабирования.
Теперь точно соответствует видимому размеру окна.
"""

import os
import win32gui
import win32ui
import win32con
from PIL import Image
import logging
import time
import sys
import ctypes

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/wow_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WowWindowDetector:
    def __init__(self):
        self.hwnd = None
        self.screenshots_dir = "../screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        logger.info("Инициализация детектора окна WOW")

        # Настройка DPI awareness
        self._set_dpi_awareness()

    def _set_dpi_awareness(self):
        """Устанавливаем правильный режим DPI для точных размеров."""
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per monitor v2
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            logger.debug(f"Установлен режим DPI awareness: {awareness.value}")
        except:
            logger.warning("Не удалось установить DPI awareness (Windows < 8.1?)")

    def find_main_wow_window(self):
        """Находит главное окно WOW с проверкой DPI."""
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                class_name = win32gui.GetClassName(hwnd)
                if class_name == "GxWindowClass":
                    hwnds.append(hwnd)
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)

        if not hwnds:
            logger.error("Не найдено ни одного окна WOW")
            return None

        # Выбираем окно с максимальной площадью
        main_window = max(hwnds, key=lambda h: self._get_window_area(h))
        logger.debug(f"Найдено окно WOW (Handle: {main_window})")
        return main_window

    def _get_window_area(self, hwnd):
        """Вычисляет площадь окна с учетом DPI."""
        try:
            # Получаем реальные физические пиксели
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            return (right - left) * (bottom - top)
        except:
            return 0

    def _get_real_window_size(self):
        """Возвращает реальные размеры окна с учетом DPI."""
        try:
            # Получаем прямоугольник окна в физических пикселях
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top

            # Корректировка для рамок окна
            client_rect = win32gui.GetClientRect(self.hwnd)
            border_width = (width - client_rect[2]) // 2
            title_height = height - client_rect[3] - border_width

            logger.debug(f"Реальные размеры: {width}x{height} (рамка: {border_width}, заголовок: {title_height})")
            return width, height
        except Exception as e:
            logger.error(f"Ошибка получения размеров: {str(e)}")
            return 0, 0

    def capture_full_window(self):
        """Захватывает окно с точными физическими размерами."""
        try:
            # Получаем реальные размеры
            width, height = self._get_real_window_size()
            if width == 0 or height == 0:
                logger.error("Некорректные размеры окна")
                return None

            logger.debug(f"Захват окна: {width}x{height} физических пикселей")

            # Создаем контекст устройства
            hwndDC = win32gui.GetWindowDC(self.hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # Создаем битмап с реальными размерами
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # Выполняем захват
            result = saveDC.BitBlt(
                (0, 0),
                (width, height),
                mfcDC,
                (0, 0),
                win32con.SRCCOPY
            )

            if result is None:
                # Конвертируем в PIL Image
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)

                im = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )

                # Сохраняем с проверкой размера
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"wow_{timestamp}.png"
                screenshot_path = os.path.join(self.screenshots_dir, filename)
                im.save(screenshot_path)

                # Проверка результата
                if os.path.exists(screenshot_path):
                    img = Image.open(screenshot_path)
                    logger.info(f"Скриншот сохранен: {screenshot_path} ({img.size[0]}x{img.size[1]})")
                    return im
                else:
                    logger.error("Файл скриншота не был создан")
                    return None
            else:
                logger.error(f"Ошибка BitBlt: {result}")
                return None

        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
            return None
        finally:
            self._cleanup_resources(locals())

    def _cleanup_resources(self, locals_dict):
        """Безопасное освобождение ресурсов."""
        resources = ['saveBitMap', 'saveDC', 'mfcDC', 'hwndDC']
        for res in resources:
            if res in locals_dict and locals_dict[res]:
                try:
                    if res == 'saveBitMap':
                        win32gui.DeleteObject(locals_dict[res].GetHandle())
                    elif res == 'hwndDC':
                        win32gui.ReleaseDC(self.hwnd, locals_dict[res])
                    else:
                        locals_dict[res].DeleteDC()
                except Exception as e:
                    logger.warning(f"Ошибка освобождения {res}: {str(e)}")

    def run(self):
        """Основной рабочий процесс."""
        self.hwnd = self.find_main_wow_window()
        if not self.hwnd:
            sys.exit(1)

        screenshot = self.capture_full_window()
        if not screenshot:
            sys.exit(1)

        # Дополнительная проверка размера
        expected_size = self._get_real_window_size()
        if screenshot.size[0] != expected_size[0] or screenshot.size[1] != expected_size[1]:
            logger.warning(f"Размер скриншота {screenshot.size} не соответствует ожидаемому {expected_size}")

        sys.exit(0)

if __name__ == "__main__":
    detector = WowWindowDetector()
    detector.run()