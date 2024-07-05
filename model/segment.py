import os

from ultralytics import YOLO
import numpy as np
import cv2
from rembg import remove
from PIL import Image


def rotate_image(image_path, angle):
    if angle == 90 or angle == -90:
        image = Image.open(image_path)
        rotated_image = image.rotate(angle, resample=Image.BICUBIC, expand=True)
        rotated_image.save(image_path)
    else:
        image = Image.open(image_path)
        rotated_image = image.rotate(angle, resample=Image.BICUBIC)
        rotated_image.save(image_path)


class Segmenter:
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

    def segment_image(self, image_path, photo_id):
        results = self.model(image_path)
        image = Image.open(image_path)
        width, height = image.size
        objects = results[0].boxes
        num_objects = len(objects)
        padding = 15

        image = cv2.imread(image_path)
        # Нарезка изображений и удаление фона по координатам
        for idx, box in enumerate(objects):
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(width, x2 + padding)
            y2 = min(height, y2 + padding)

            cropped_img = image[y1:y2, x1:x2]
            cropped_img_path = f"../Photo/cut/{photo_id}_{idx}.png"
            cv2.imwrite(cropped_img_path, cropped_img)
            # Удаление фона
            input_image = Image.open(cropped_img_path)
            output_image = remove(input_image)
            output_image_path = f"../Photo/noBg/{photo_id}_{idx}.png"
            output_image.save(output_image_path)

            # self.clear_cut_folder()

        return num_objects

    def clear_cut_folder(self):
        cut_folder_path = "../Photo/cut"
        for filename in os.listdir(cut_folder_path):
            file_path = os.path.join(cut_folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Удаление файла
            except Exception as e:
                print(f"Не удалось удалить {file_path}. Причина: {e}")
