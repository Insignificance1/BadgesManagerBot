from PIL import Image
from fpdf import FPDF

import aspose.zip as az
import os

class Converter:
    def __init__(self):
        self.pdf = FPDF()

    def convert_to_pdf(self, name, collection_id, images_list):
        self.pdf.add_page()
        x, y = 10, 10  # Начальные координаты
        max_w, max_h = 200, 287  # Максимальные размеры страницы
        img_w, img_h = 30, 30  # Размер изображения
        margin = 10  # Отступ между изображениями

        for image_paths in images_list:
            for image_path in image_paths:
                if x + img_w > max_w:  # Проверка если ширина выходит за границы
                    x = 10  # Перенос на новую строку
                    y += img_h + margin

                if y + img_h > max_h:  # Проверка если высота выходит за границы
                    self.pdf.add_page()
                    x, y = 10, 10  # Сброс координат

                self.pdf.image(image_path, x=x, y=y, w=img_w, h=img_h)
                x += img_w + margin

        output_path = f"../Photo/PDF/{name}_{collection_id}.pdf"
        self.pdf.output(output_path)

        return output_path

    def convert_to_zip(self, photo_id, num_objects, zip_path):
        with az.Archive() as archive:
            for obj_num in range(num_objects):
                file_name = f"{photo_id}_{obj_num}.png"
                file_path = os.path.join(f"../Photo/noBg", file_name)
                if os.path.isfile(file_path):
                    archive.create_entry(file_name, file_path)
            archive.save(zip_path)