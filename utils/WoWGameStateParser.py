import json
import re
import logging
from typing import Dict, Any, List, Optional, Union

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("WoWGameStateParser")


def safe_get(data, *keys, default=None):
    """
    Безопасное получение значения из вложенных структур данных.
    Работает со словарями и списками.

    Пример:
    safe_get(response, "results", 0, "textDetection", default={})
    """
    current = data
    for key in keys:
        try:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
                current = current[key]
            else:
                return default
        except Exception as e:
            logger.debug(f"Ошибка доступа к ключу {key}: {str(e)}")
            return default
    return current


class WoWGameStateParser:
    """Парсер состояния игры World of Warcraft из ответа Yandex Vision API"""

    def __init__(self, api_response: Dict[str, Any]):
        """
        Инициализация парсера с ответом от Yandex Vision API.

        :param api_response: Словарь с ответом от Vision API
        """
        self.api_response = api_response
        self.text_blocks = self.extract_all_text_blocks()
        self.screen_width, self.screen_height = self.detect_screen_size()
        logger.info(f"Инициализирован парсер для экрана {self.screen_width}x{self.screen_height}")
        logger.info(f"Найдено текстовых блоков: {len(self.text_blocks)}")

    def detect_screen_size(self) -> tuple:
        """
        Определяет размеры экрана из метаданных ответа.
        Возвращает значения по умолчанию (1920x1080) при ошибке.
        """
        try:
            page = safe_get(
                self.api_response,
                "results", 0, "results", 0, "textDetection", "pages", 0,
                default={}
            )
            width = int(safe_get(page, "width", default=1920))
            height = int(safe_get(page, "height", default=1080))
            return width, height
        except Exception as e:
            logger.error(f"Ошибка определения размера экрана: {str(e)}")
            return 1920, 1080

    def extract_all_text_blocks(self) -> List[Dict[str, Any]]:
        """
        Извлекает все текстовые блоки с их координатами и текстом.

        Возвращает список словарей с ключами:
        - text: распознанный текст
        - x_min, x_max, y_min, y_max: границы блока
        - center_x, center_y: центр блока
        """
        blocks = []

        try:
            # Безопасное извлечение структуры страниц
            pages = safe_get(
                self.api_response,
                "results", 0, "results", 0, "textDetection", "pages",
                default=[]
            )

            for page in pages:
                # Обработка блоков на странице
                for block in safe_get(page, "blocks", default=[]):
                    # Обработка линий в блоке
                    for line in safe_get(block, "lines", default=[]):
                        # Объединение слов в строку
                        words = safe_get(line, "words", default=[])
                        text = " ".join(safe_get(word, "text", default="") for word in words)

                        # Пропуск пустых текстов
                        if not text.strip():
                            continue

                        # Извлечение координат
                        vertices = safe_get(line, "boundingBox", "vertices", default=[])
                        if len(vertices) < 4:
                            continue

                        # Конвертация координат в числа
                        x_coords = []
                        y_coords = []
                        for vertex in vertices:
                            x = safe_get(vertex, "x", default="0")
                            y = safe_get(vertex, "y", default="0")
                            try:
                                x_coords.append(int(x))
                                y_coords.append(int(y))
                            except (ValueError, TypeError):
                                logger.debug(f"Ошибка конвертации координат: x={x}, y={y}")
                                x_coords.append(0)
                                y_coords.append(0)

                        if not x_coords or not y_coords:
                            continue

                        blocks.append({
                            "text": text,
                            "x_min": min(x_coords),
                            "x_max": max(x_coords),
                            "y_min": min(y_coords),
                            "y_max": max(y_coords),
                            "center_x": sum(x_coords) / len(x_coords),
                            "center_y": sum(y_coords) / len(y_coords)
                        })
        except Exception as e:
            logger.error(f"Критическая ошибка извлечения текстовых блоков: {str(e)}")

        return blocks

    def is_in_top_right(self, block: Dict) -> bool:
        """Определяет, находится ли блок в правом верхнем углу (зона локации)"""
        return (
                block["center_x"] > self.screen_width * 0.7 and
                block["center_y"] < self.screen_height * 0.15
        )

    def is_in_player_info_area(self, block: Dict) -> bool:
        """Определяет, находится ли блок в зоне информации о игроке (левый верхний угол)"""
        return (
                block["center_x"] < self.screen_width * 0.3 and
                block["center_y"] < self.screen_height * 0.3
        )

    def is_in_bottom_action_bar(self, block: Dict) -> bool:
        """Определяет, находится ли блок в зоне панели действий (нижняя часть экрана)"""
        return (
                block["center_y"] > self.screen_height * 0.85 and
                block["center_x"] > self.screen_width * 0.1 and
                block["center_x"] < self.screen_width * 0.9
        )

    def is_health_mana_value(self, text: str) -> bool:
        """Определяет, является ли текст значением здоровья или маны"""
        # Форматы: 100/100, 100, 100%
        return (
                bool(re.match(r"^\d+/\d+$", text)) or
                bool(re.match(r"^\d+%$", text)) or
                text.isdigit()
        )

    def is_player_name(self, text: str) -> bool:
        """Определяет, может ли текст быть именем игрока"""
        # Имена обычно состоят из букв, могут содержать пробелы и апострофы
        return bool(re.match(r"^[\w'\s-]{2,20}$", text)) and not any(char.isdigit() for char in text)

    def is_time(self, text: str) -> bool:
        """Определяет, является ли текст игровым временем"""
        return bool(re.match(r"^\d{1,2}:\d{2}$", text))

    def is_level(self, text: str) -> bool:
        """Определяет, является ли текст уровнем персонажа"""
        return text.isdigit() and 1 <= int(text) <= 70

    def is_entity_name(self, text: str) -> bool:
        """Определяет, может ли текст быть именем сущности (NPC, игрок)"""
        # Фильтруем слишком короткие тексты и числа
        return (
                len(text) > 2 and
                not text.isdigit() and
                not re.match(r"^\d+/\d+$", text) and
                not self.is_time(text)
        )

    def parse_game_state(self) -> Dict[str, Any]:
        """
        Анализирует все текстовые блоки и извлекает состояние игры.

        Возвращает словарь с ключами:
        - location: текущая локация
        - player_name: имя игрока
        - health: значение здоровья
        - mana: значение маны
        - level: уровень игрока
        - time: игровое время
        - in_combat: находится ли в бою (True/False)
        - nearby_entities: список объектов рядом
        """
        game_state = {
            "location": None,
            "player_name": None,
            "health": None,
            "mana": None,
            "level": None,
            "time": None,
            "in_combat": False,
            "nearby_entities": []
        }

        # Временные контейнеры
        location_candidates = []
        health_candidates = []
        mana_candidates = []
        level_candidates = []
        combat_indicators = []

        for block in self.text_blocks:
            text = block["text"]

            # 1. Локация (правый верхний угол)
            if self.is_in_top_right(block):
                location_candidates.append((block["center_y"], text))

            # 2. Информация о игроке (левый верхний угол)
            elif self.is_in_player_info_area(block):
                # Имя игрока
                if not game_state["player_name"] and self.is_player_name(text):
                    game_state["player_name"] = text

                # Уровень
                elif self.is_level(text):
                    level_candidates.append((block["center_y"], text))

                # Здоровье/мана
                elif self.is_health_mana_value(text):
                    # Сортируем по вертикали: здоровье обычно выше маны
                    if not health_candidates or block["center_y"] < health_candidates[0][0]:
                        health_candidates.append((block["center_y"], text))
                    else:
                        mana_candidates.append((block["center_y"], text))

            # 3. Время (может быть в разных местах)
            elif self.is_time(text):
                game_state["time"] = text

            # 4. Индикаторы боя
            elif "бой" in text.lower() or "combat" in text.lower():
                combat_indicators.append(text)

            # 5. Панель действий (фильтруем тексты на кнопках)
            elif self.is_in_bottom_action_bar(block):
                # Пропускаем тексты на панели действий
                continue

            # 6. Другие тексты (возможные сущности)
            elif self.is_entity_name(text):
                # Фильтруем повторяющиеся имена
                if text not in game_state["nearby_entities"]:
                    game_state["nearby_entities"].append(text)

        # Обработка кандидатов на локацию
        if location_candidates:
            # Выбираем самый верхний текст в зоне (локация обычно выше всего)
            location_candidates.sort(key=lambda x: x[0])
            game_state["location"] = location_candidates[0][1]

        # Обработка здоровья
        if health_candidates:
            # Выбираем самое верхнее значение (основное здоровье)
            health_candidates.sort(key=lambda x: x[0])
            game_state["health"] = health_candidates[0][1]

        # Обработка маны
        if mana_candidates:
            # Выбираем самое верхнее значение (основная мана)
            mana_candidates.sort(key=lambda x: x[0])
            game_state["mana"] = mana_candidates[0][1]

        # Обработка уровня
        if level_candidates:
            # Выбираем самое верхнее значение (уровень обычно рядом с именем)
            level_candidates.sort(key=lambda x: x[0])
            game_state["level"] = level_candidates[0][1]

        # Определение состояния боя
        game_state["in_combat"] = len(combat_indicators) > 0

        return game_state


def parse_health_mana(value: str) -> Dict[str, Any]:
    """
    Парсит строку здоровья/маны в структурированный формат.

    Поддерживаемые форматы:
    - "100/100" → {"current": 100, "max": 100, "percent": 100}
    - "100" → {"current": 100, "max": None, "percent": None}
    - "50%" → {"current": 50, "max": 100, "percent": 50}
    """
    try:
        # Формат "текущее/максимальное"
        if "/" in value:
            current, max_val = value.split("/")
            current = int(current)
            max_val = int(max_val)
            percent = int(current / max_val * 100) if max_val > 0 else 0
            return {
                "current": current,
                "max": max_val,
                "percent": percent
            }

        # Формат "число%"
        elif "%" in value:
            percent = int(value.replace("%", ""))
            return {
                "current": percent,
                "max": 100,
                "percent": percent
            }

        # Просто число
        elif value.isdigit():
            return {
                "current": int(value),
                "max": None,
                "percent": None
            }
    except Exception as e:
        logger.error(f"Ошибка парсинга значения '{value}': {str(e)}")

    return {
        "current": None,
        "max": None,
        "percent": None
    }


# Пример использования
if __name__ == "__main__":
    # Загрузка сохраненного ответа
    try:
        with open("vision_response.json", "r", encoding="utf-8") as f:
            api_response = json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {str(e)}")
        exit(1)

    # Инициализация парсера
    parser = WoWGameStateParser(api_response)

    # Парсинг состояния игры
    game_state = parser.parse_game_state()

    # Дополнительная обработка здоровья/маны
    if game_state["health"]:
        game_state["health_details"] = parse_health_mana(game_state["health"])
    if game_state["mana"]:
        game_state["mana_details"] = parse_health_mana(game_state["mana"])

    # Вывод результатов
    print("\nРаспознанное состояние игры:")
    print(f"Локация: {game_state.get('location', 'Неизвестно')}")
    print(f"Игрок: {game_state.get('player_name', 'Неизвестно')}")
    print(f"Уровень: {game_state.get('level', 'Неизвестно')}")
    print(f"Здоровье: {game_state.get('health', 'Неизвестно')}")
    if "health_details" in game_state:
        details = game_state["health_details"]
        print(f"  Подробно: {details['current']}/{details['max']} ({details['percent']}%)")
    print(f"Мана: {game_state.get('mana', 'Неизвестно')}")
    if "mana_details" in game_state:
        details = game_state["mana_details"]
        print(f"  Подробно: {details['current']}/{details['max']} ({details['percent']}%)")
    print(f"Время: {game_state.get('time', 'Неизвестно')}")
    print(f"В бою: {'Да' if game_state['in_combat'] else 'Нет'}")
    print(f"Объекты рядом: {', '.join(game_state['nearby_entities'])}")

    # Сохранение структурированного состояния
    with open("parsed_game_state.json", "w", encoding="utf-8") as f:
        json.dump(game_state, f, indent=2, ensure_ascii=False)
    print("\nСтруктурированное состояние сохранено в parsed_game_state.json")