# screen_capture.py - Модуль для захвата экрана с использованием MSS
# MSS быстрее, чем другие библиотеки захвата экрана, так как использует низкоуровневые API

import numpy as np
from mss import mss
import cv2
import logging

logger = logging.getLogger(__name__)


class ScreenCapture:
    def __init__(self, monitor=1):
        """
        Инициализация захвата экрана
        :param monitor: номер монитора для захвата (по умолчанию 1)
        """
        self.monitor = monitor
        self.sct = mss()
        self.setup_monitor()
        logger.info(f"Инициализирован захват экрана для монитора {monitor}")

    def setup_monitor(self):
        """Определение области захвата на основе выбранного монитора"""
        try:
            if len(self.sct.monitors) > self.monitor:
                self.monitor_info = self.sct.monitors[self.monitor]
                logger.debug(f"Информация о мониторе: {self.monitor_info}")
            else:
                logger.warning(f"Монитор {self.monitor} не найден, используется основной")
                self.monitor_info = self.sct.monitors[0]
        except Exception as e:
            logger.error(f"Ошибка при настройке монитора: {str(e)}")
            raise

    def capture(self):
        """
        Захват текущего изображения экрана
        :return: numpy array с изображением или None в случае ошибки
        """
        try:
            # Захват экрана
            sct_img = self.sct.grab(self.monitor_info)

            # Преобразование в numpy array
            img = np.array(sct_img)

            # Конвертация из BGRA в RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)

            logger.debug("Экран успешно захвачен")
            return img
        except Exception as e:
            logger.error(f"Ошибка при захвате экрана: {str(e)}")
            return None