import cv2
import numpy as np
import os

# Создаем папку если ее нет
os.makedirs('templates', exist_ok=True)

# 1. Создаем простой шаблон NPC (желтый круг)
npc_template = np.zeros((30, 30, 3), dtype=np.uint8)
cv2.circle(npc_template, (15, 15), 10, (0, 255, 255), -1)  # Желтый
cv2.imwrite('templates/npc_template.png', npc_template)

# 2. Создаем шаблон врага (красный квадрат)
enemy_template = np.zeros((30, 30, 3), dtype=np.uint8)
cv2.rectangle(enemy_template, (5, 5), (25, 25), (0, 0, 255), -1)  # Красный
cv2.imwrite('templates/enemy_template.png', enemy_template)

print("Шаблоны созданы в папке templates/")