import pymupdf
import re
from pathlib import Path
import pytesseract
from PIL import Image
import os
import cv2
import tkinter as tk
from tkinter import scrolledtext
from tkinter import filedialog
import threading

import traceback


pytesseract.pytesseract.tessepract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class PDFRENAME:
    def __init__(self, root):
        self.root = root
        self.root.title("PDFRENAME")
        self.root.geometry("800x600")

        self.flag_stop = False
        self.proccesing=False
        self.result = {'renamed': 0, 'skipped': 0, 'errors': 0, 'duplicates': 0}
        self.used_name=[]

        self.setup()
    def setup(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)
        self.btn_start = tk.Button(
            top_frame,
            text="▶  Запустить обработку",
            command=self.start_processing,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=8
        )
        self.btn_start.pack(side='left', padx=5)

        self.btn_stop = tk.Button(
            top_frame,
            text="⏹  Остановить",
            command=self.stop_processing,
            bg="#f44336",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=8,
            state="disabled"
        )
        self.btn_stop.pack(side='left', padx=5)
        self.log = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Courier New", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            height=25
        )
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

        self.status = tk.Label(self.root, text="Готов")# создание поля для состояния программы

    def start_processing(self):
        if self.proccesing:
            return
        self.result = {'renamed': 0, 'skipped': 0, 'errors': 0, 'duplicates': 0}
        self.processing = True
        self.flag_stop = False
        self.log.insert(tk.END, " Начинаем обработку...\n")

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state='normal')
        self.set_status("🔄 Обработка...", "orange")

        thread = threading.Thread(target=self._process_files, daemon=True)
        thread.start()

    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def stop_processing(self):
        self.flag_stop = True
        self.log_message("Остановка по запросу пользователя...")
        self.set_status("Останавливается...", "red")


    def set_status(self, text, color="green"):
        self.status.config(text=text, fg=color)
    def _process_files(self):
        try:
            folder = self.file_folder()
            if not folder:
                self.log_message("Папка не выбрана")
                return
            self.log_message(f"Папка выбрана: {folder}")
            files = self.search_files(folder)
            if not files:
                self.log_message("Файлы не найдены")
                return
            self.log_message(f"Колличество найденых файлов: {len(files)}")
            for f in files:
                self.log_message(f" - {f.name}")
            for f in files:
                if self.flag_stop:
                    self.log_message("\n⏹ Остановлено пользователем")
                    break

                number = self.find_number_conteiner(f)
                if not number:
                    self.log_message("Пропуск")
                    continue
                self.rename_SMGS(number, f)
            self.log_message("\n" + "=" * 60)
            self.log_message(" РЕЗУЛЬТАТЫ:")
            self.log_message(f"  Переименовано: {self.result['renamed']}")
            self.log_message(f"   Пропущено: {self.result['skipped']}")
            self.log_message(f"   Ошибок: {self.result['errors']}")
            self.log_message(f"   Дубликатов: {self.result['duplicates']}")
            self.log_message("=" * 60)

            if not self.flag_stop:
                self.log_message("\n ОБРАБОТКА ЗАВЕРШЕНА!")
                self.set_status(" Готово!", "green")
            else:
                self.set_status(" Остановлено", "red")
        except ImportError as e:
            self.log_message(f"\n КРИТИЧЕСКАЯ ОШИБКА: {e}")
            self.log_message(traceback.format_exc())
            self.set_status(" Ошибка", "red")
        finally:
            self.is_processing = False
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)


    def search_files(self,g):
        input_path = Path(g)
        pdf_files = list(input_path.glob("*.pdf"))

        pdf_files = list(set(pdf_files))
        if not pdf_files:
            self.log_message("PDF файлы не найдены!")
            return
        pdf_files_new=[]
        pattern = r'[A-Z]{4}\d{7}'
        sort_matches = []
        for i in pdf_files:
            if re.match(pattern, i.name):
                self.log_message(f"файл уже правильно назван{i.name}")
                continue
            else:pdf_files_new.append(i)
        if not pdf_files_new:
            self.log_message("PDF файлы для изменений не найдены!")
            return
        return pdf_files_new


    def clear_log(self):
        self.log.delete(1.0, tk.END)
        self.log_message("Лог очищен")


    def file_folder(self):
        tk_root = tk.Tk()
        tk_root.withdraw()

        folder_path = filedialog.askdirectory(
            title="Выберите папку с PDF файлами",
            initialdir=os.path.expanduser("~")
        )
        tk_root.destroy()
        return folder_path

    def find_number_conteiner(self, pdf):
        try:
            self.log_message(f"Обработка{pdf.name}")
            doc = pymupdf.open(pdf)
            page = doc[0]

            pix = page.get_pixmap(dpi=300)
            img_path = "temp_page_0.png"
            pix.save(img_path)

            image = self.crop_img(img_path, x=0, y=1800, width=1240, height=550)
            ocr_text = pytesseract.image_to_string(
                image,
                lang="eng",
                config="--psm 6"
            )
            text = ocr_text
            doc.close()

            patterns = [
                r'\b[A-Z]{4}\d{7}\b',
                r'[A-Z]{4}\s*\d{7}',
                r'[A-Z]{4}[-_\s]?\d{7}',
                r'[A-Z]{4}\s*-\s*\d{7}',
            ]
            sort_matches = []
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    for i in matches:
                        if not (" " in i):
                            if len(i) == 11:
                                sort_matches.append(i)
            if sort_matches:
                self.log_message(f"Найден: {sort_matches[0]}")
                return sort_matches[0]
            else:
                self.log_message("Ничего не найдено")
                self.result["skipped"] += 1

        except Exception as e:
            self.log_message(f"  Ошибка: {e}")
            return None
    def crop_img(self, image_path, x=0, y=1752, width=1240, height=400):
        try:
            img = cv2.imread(str(image_path))
            height_img, width_img = img.shape[:2]

            x = min(x, width_img - 1)
            y = min(y, height_img - 1)
            width = min(width, width_img - x)
            height = min(height, height_img - y)

            cropped = img[y:y + height, x:x + width]

            cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            cropped_pil = Image.fromarray(cropped_rgb)
            return cropped_pil
        except Exception as e:
            self.log_message(f'Ошибка обрезки изображения {e}')

    def rename_SMGS(self, container, file):
        try:
            new_name = f"{container}.pdf"
            new_path = file.parent / new_name  #  Полный путь в той же папке!

            # Проверка дубликатов
            counter = 1
            original_name = new_name
            while new_path.exists() or new_name in self.used_name:
                new_name = f"{container}_{counter}.pdf"
                new_path = file.parent / new_name  # ← В той же папке!
                counter += 1
                self.result['duplicates'] += 1

            if new_name != original_name:
                self.log_message(f"  ️ Файл {original_name} уже существует, используем {new_name}")
            file.rename(new_path)
            self.used_name.append(new_name)
            self.result['renamed'] += 1
            self.log_message(f"   {file.name} -> {new_name}")
        except Exception as e:
            self.log_message(f"  Ошибка: {e}")
            self.result['errors'] += 1
root = tk.Tk()
app = PDFRENAME(root)
root.mainloop()