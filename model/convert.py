from fpdf import FPDF

import zipfile
import os


class Converter:
    def __init__(self):
        self.pdf = FPDF(orientation='P', unit='mm', format='A4')
        # Регистрация шрифта
        self.pdf.add_font('N', '', '../Unigeo32/N.ttf', uni=True)

    def convert_to_pdf_base(self, name, collection_id, images_list):
        print(images_list)
        self.pdf.add_page()
        self.add_title(name)

        x, y = 10, 20  # Начальные координаты
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

    def convert_to_pdf_ext(self, name_collection, collection_id, images_list, name_list, count_list):
        self.pdf.add_page()
        self.add_title(name_collection)  # Добавляем заголовок на первую страницу

        x_start, y_start = 10, 30  # Начальные координаты
        x, y = x_start, y_start
        max_w, max_h = 200, 287  # Максимальные размеры страницы
        img_w, img_h = 30, 30  # Размер изображения
        margin = 10  # Отступ между изображениями
        row_height = 70  # Высота строки (название + картинка + количество + отступ)

        total_count = sum(int(count[0]) for count in count_list)  # Общее количество значков

        # Добавление общего количества в правый верхний угол первой страницы
        self.pdf.set_font("N", '', 10)
        self.pdf.set_xy(self.pdf.w - 50, 10)
        self.pdf.cell(0, 25, f"Общее количество: {total_count}", 0, 0, 'C')
        self.pdf.ln(20)  # Добавить отступ после общего количества

        for image_paths, title, count in zip(images_list, name_list, count_list):
            # Разбиение названия на строки, если оно длиннее 10 символов
            lines = self.split_string(title, 14)

            # Проверка если ширина выходит за границы
            if x + img_w > max_w:
                x = x_start  # Перенос на новую строку
                y += row_height  # Увеличиваем y для следующего ряда

            if y + row_height > max_h:  # Проверка если высота выходит за границы (учитываем текст и количество)
                self.pdf.add_page()
                x, y = x_start, y_start  # Сброс координат

            self.pdf.rect(x, y, img_w, img_h)
            # Добавляем картинку
            self.pdf.image(image_paths[0], x=x, y=y, w=img_w, h=img_h)

            self.pdf.rect(x-5, y + img_h, img_w+10, len(lines) * 10)

            # Добавляем название (с учетом разбиения на строки)
            self.pdf.set_xy(x-5, y + 30)
            self.pdf.set_font("N", '', 12)
            for line in lines:
                for char in line:
                    self.pdf.cell(img_w + margin, 10, char, 0, 2, 'C')

                # После каждой строки, смещаем y на 10
                y += 10

            # Возвращаем y на начальную позицию для следующей строки
            y -= len(lines) * 10  # Возвращаемся на количество строк, умноженное на высоту строки

            # Добавляем количество значков
            self.pdf.set_font("N", '', 10)
            self.pdf.set_xy(x - 5, y=y + 30 + (len(lines) * 10))
            self.pdf.cell(img_w + margin, 10, f"{int(count[0])} значков", 1, 1, 'C')

            x += img_w + margin  # Смещаем x вправо для следующего значка

        output_path = f"../Photo/PDF/{name_collection}_{collection_id}.pdf"
        self.pdf.output(output_path)

        return output_path

    def add_title(self, title):
        self.pdf.set_font("N", '', 16)
        self.pdf.cell(0, 10, title, 0, 1, 'C')
        self.pdf.ln(10)  # Добавить отступ после заголовка

    def split_string(self, text, max_len):
        lines = []
        while len(text) > max_len:
            split_idx = text.rfind(' ', 0, max_len)
            if split_idx == -1:
                split_idx = max_len
            lines.append(text[:split_idx])
            text = text[split_idx:].strip()
        lines.append(text)
        return lines

    def convert_to_zip(self, photo_id, num_objects, zip_path):
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for obj_num in range(num_objects):
                file_name = f"{photo_id}_{obj_num}.png"
                file_path = os.path.join(f"../Photo/noBg", file_name)
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=file_name)
