import os
import shutil

from ultralytics import YOLO
import numpy as np
import cv2
from rembg import remove
from PIL import Image


# Вращение изображения
def rotate_image(image_path, angle):
    if angle == 90 or angle == -90:
        image = Image.open(image_path)
        rotated_image = image.rotate(angle, resample=Image.BICUBIC, expand=True)
        rotated_image.save(image_path)
    else:
        image = Image.open(image_path)
        rotated_image = image.rotate(angle, resample=Image.BICUBIC)
        rotated_image.save(image_path)


class Detector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.model = YOLO('../v3-965photo-100ep.pt')

    def get_count(self, image_path):
        # Загрузка изображения
        image = cv2.imread(image_path)
        results = self.model(image)[0]

        # Получение результатов
        boxes = results.boxes.xyxy.cpu().numpy().astype(np.int32)

        # Возвращение количества боксов
        return len(boxes)


    #детекция и обрезка фона на изображении
    def detect_image(self, image_path, photo_id):
        results = self.model(image_path)
        image = Image.open(image_path)
        width, height = image.size
        objects = results[0].boxes
        num_objects = len(objects)
        padding = 15  # отступ для изначального обрезания
        os.makedirs('../Photo/cut/', exist_ok=True)
        image = cv2.imread(image_path)

        for idx, box in enumerate(objects):
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            # Добавление отступа вокруг оригинального обрезанного объекта
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(width, x2 + padding)
            y2 = min(height, y2 + padding)

            # Обрезка изображения
            cropped_img = image[y1:y2, x1:x2]
            cropped_img_path = f"../Photo/cut/{photo_id}_{idx}.png"
            cv2.imwrite(cropped_img_path, cropped_img)
            # Удаление фона
            input_image = Image.open(cropped_img_path)
            output_image = remove(input_image)
            output_image_path = f"../Photo/noBg/{photo_id}_{idx}.png"
            # Минимальный квадрат
            min_square_image = self.find_minimal_square(output_image)
            # Добавление дополнительных отступов вокруг минимального квадрата
            final_image = self.add_padding(min_square_image, padding)
            final_image.save(output_image_path)
        return num_objects


    #Увеличение размера изображения
    def add_padding(self, image, padding):
        width, height = image.size
        # Создание нового изображения b более крупного размера
        new_width = width + 2 * padding
        new_height = height + 2 * padding
        # Новое пустое изображение с прозрачным фоном
        new_image = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
        # Вставка оригинального изображения посередине нового
        new_image.paste(image, (padding, padding))
        return new_image


    # Очистка папки cut
    def clear_cut_folder(self):
        cut_folder_path = "../Photo/cut"
        for filename in os.listdir(cut_folder_path):
            file_path = os.path.join(cut_folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Не удалось удалить {file_path}. Причина: {e}")


    # Получение площади изображения
    def get_bounding_square(self, image: Image.Image) -> int:
        w, h = image.size
        return max(w, h)


    # Обрезка фона(пустого пространства)
    def trim_whitespace(self, img):
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        return img


    # Вращение изображение до достижения минимальной площади изображения
    def find_minimal_square(self, image: Image.Image):
        os.makedirs('../Photo/auto_rotated/', exist_ok=True)
        min_size = float('inf')
        optimal_img = image

        for angle in range(0, 360, 3):
            rotated = self.trim_whitespace(image.rotate(angle, expand=True))
            open('../Photo/auto_rotated/rotated_' + str(angle) + '.png', 'a').close()
            rotated.save('../Photo/auto_rotated/rotated_' + str(angle) + '.png')
            width, height = rotated.size
            area = width * height
            if area < min_size:
                min_size = area
                optimal_img = rotated
            else:
                return optimal_img

        return optimal_img


    #сохранение изображения
    def save_image(self, image: Image.Image, path: str):
        image.save(path)