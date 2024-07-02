from ultralytics import YOLO
import numpy as np
import cv2
from rembg import remove
from PIL import Image


class Segmenter:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def segment_image(self, image_path, photo_id):
        # Загрузка изображения
        model = YOLO('../v3-965photo-100ep.pt')
        image = cv2.imread(image_path)
        results = model(image)[0]

        # Получение оригинального изображения и результатов
        image = results.orig_img
        classes_names = results.names
        classes = results.boxes.cls.cpu().numpy()
        boxes = results.boxes.xyxy.cpu().numpy().astype(np.int32)

        # Подготовка словаря для группировки результатов по классам
        grouped_objects = {}

        # Группировка результатов
        for class_id, box in zip(classes, boxes):
            class_name = classes_names[int(class_id)]
            if class_name not in grouped_objects:
                grouped_objects[class_name] = []
            grouped_objects[class_name].append(box)

        # Сохранение данных в текстовый файл
        text_file_path = f"../Photo/temp/{photo_id}.txt"
        with open(text_file_path, 'w') as f:
            for class_name, details in grouped_objects.items():
                f.write(f"{class_name}:\n")
                for detail in details:
                    f.write(f"Coordinates: ({detail[0]}, {detail[1]}, {detail[2]}, {detail[3]})\n")

        image = cv2.imread(image_path)
        # Нарезка изображений по координатам
        for idx, detail in enumerate(details):
            x1, y1, x2, y2 = detail
            cropped_img = image[y1 - 15:y2 + 15, x1 - 15:x2 + 15]
            cropped_img_path = f"../Photo/cut/{photo_id}_{idx}.png"
            cv2.imwrite(cropped_img_path, cropped_img)
            # Удаление фона
            input_image = Image.open(cropped_img_path)
            output_image = remove(input_image)
            output_image_path = f"../Photo/noBg/{photo_id}_{idx}.png"
            output_image.save(output_image_path)

        return text_file_path, len(details)
