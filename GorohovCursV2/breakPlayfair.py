import playfairCipher
import datetime
import random
import pickle
import math
import os
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from threading import Thread
import mysql.connector
from mysql.connector import Error
import hashlib

# Загрузка триграмм
with open('trigrams', 'rb') as f:
    ENGLISH_TRIGRAMS = pickle.load(f)


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host='127.0.0.1',
                user='root',
                password='root',
                database='cipher_breaker',
                autocommit=True
            )
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            self.connection = None

    def log_operation_start(self, input_file_path):
        if not self.connection:
            print("Database connection not established")
            return None

        query = """
        INSERT INTO cracking_operations 
        (input_file_path)
        VALUES (%s)
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (input_file_path,))
            operation_id = cursor.lastrowid
            print(f"Operation started with ID: {operation_id}")
            return operation_id
        except Error as e:
            print(f"Error logging operation start: {e}")
            return None
        finally:
            cursor.close()

    def log_operation_end(self, operation_id, **kwargs):
        if not self.connection or operation_id is None:
            print("Invalid operation_id or no connection")
            return False

        # Подготавливаем параметры для обновления
        set_clauses = []
        params = []

        set_clauses.append("end_time = NOW()")

        if 'status' in kwargs:
            set_clauses.append("status = %s")
            params.append(kwargs['status'])

        if 'encrypted_file_path' in kwargs:
            set_clauses.append("encrypted_file_path = %s")
            params.append(kwargs['encrypted_file_path'])

        if 'decrypted_file_path' in kwargs:
            set_clauses.append("decrypted_file_path = %s")
            params.append(kwargs['decrypted_file_path'])

        if 'best_key' in kwargs:
            set_clauses.append("best_key = %s")
            params.append(kwargs['best_key'])

        if 'best_score' in kwargs:
            set_clauses.append("best_score = %s")
            params.append(kwargs['best_score'])

        if 'iterations' in kwargs:
            set_clauses.append("iterations = %s")
            params.append(kwargs['iterations'])

        if 'restarts' in kwargs:
            set_clauses.append("restarts = %s")
            params.append(kwargs['restarts'])

        params.append(operation_id)

        query = f"""
        UPDATE cracking_operations 
        SET {', '.join(set_clauses)}
        WHERE operation_id = %s
        """

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            print(f"Operation {operation_id} updated successfully")
            return True
        except Error as e:
            print(f"Error logging operation end: {e}")
            return False
        finally:
            cursor.close()

    def log_intermediate_result(self, operation_id, iteration, current_key, current_score):
        if not self.connection or operation_id is None:
            print("Invalid parameters for intermediate result")
            return False

        query = """
        INSERT INTO intermediate_results 
        (operation_id, iteration, current_key, current_score)
        VALUES (%s, %s, %s, %s)
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (operation_id, iteration, current_key, current_score))
            print(f"Logged intermediate result for operation {operation_id}")
            return True
        except Error as e:
            print(f"Error logging intermediate result: {e}")
            return False
        finally:
            cursor.close()

    def get_cached_decrypt(self, key, ciphertext):
        if not self.connection:
            return None

        key_hash = hashlib.sha256(key.encode()).hexdigest()
        ciphertext_hash = hashlib.sha256(ciphertext.encode()).hexdigest()

        query = """
        SELECT decrypted_text FROM decrypt_cache
        WHERE key_hash = %s AND ciphertext_hash = %s
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (key_hash, ciphertext_hash))
            result = cursor.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Error getting cached decrypt: {e}")
            return None
        finally:
            cursor.close()

    def cache_decrypt(self, key, ciphertext, decrypted_text):
        if not self.connection:
            return False

        key_hash = hashlib.sha256(key.encode()).hexdigest()
        ciphertext_hash = hashlib.sha256(ciphertext.encode()).hexdigest()

        query = """
        INSERT INTO decrypt_cache 
        (key_hash, ciphertext_hash, decrypted_text)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            decrypted_text = VALUES(decrypted_text),
            timestamp = NOW()
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (key_hash, ciphertext_hash, decrypted_text))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error caching decrypt: {e}")
            return False
        finally:
            cursor.close()

    def close(self):
        if self.connection:
            self.connection.close()

    def get_operations(self, operation_id=None, status_filter=None):
        """Получает операции из БД с возможностью фильтрации"""
        try:
            cursor = self.connection.cursor(dictionary=True)

            query = "SELECT * FROM cracking_operations"
            params = []

            conditions = []
            if operation_id:
                conditions.append("operation_id = %s")
                params.append(operation_id)
            if status_filter:
                conditions.append("status = %s")
                params.append(status_filter)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY start_time DESC"

            cursor.execute(query, params)
            return cursor.fetchall()

        except Error as e:
            print(f"Error getting operations: {e}")
            return []
        finally:
            cursor.close()

    def delete_operation(self, operation_id):
        """Удаляет операцию из БД"""
        try:
            cursor = self.connection.cursor()

            # Сначала удаляем промежуточные результаты
            cursor.execute("DELETE FROM intermediate_results WHERE operation_id = %s", (operation_id,))

            # Затем удаляем саму операцию
            cursor.execute("DELETE FROM cracking_operations WHERE operation_id = %s", (operation_id,))

            self.connection.commit()
            return cursor.rowcount > 0

        except Error as e:
            print(f"Error deleting operation: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def get_operation_cache(self, operation_id):
        """Получает кэш для указанной операции"""
        try:
            cursor = self.connection.cursor(dictionary=True)

            # Получаем информацию об операции
            cursor.execute("SELECT * FROM cracking_operations WHERE operation_id = %s", (operation_id,))
            operation = cursor.fetchone()
            if not operation:
                return None

            # Получаем промежуточные результаты
            cursor.execute("""
                SELECT * FROM intermediate_results 
                WHERE operation_id = %s 
                ORDER BY iteration DESC
                LIMIT 100
            """, (operation_id,))
            intermediates = cursor.fetchall()

            # Получаем кэш для лучшего ключа
            best_key_cache = None
            if operation['best_key']:
                cursor.execute("""
                    SELECT * FROM decrypt_cache
                    WHERE key_hash = %s
                    LIMIT 1
                """, (hashlib.sha256(operation['best_key'].encode()).hexdigest(),))
                best_key_cache = cursor.fetchone()

            return {
                'operation': operation,
                'intermediates': intermediates,
                'best_key_cache': best_key_cache
            }

        except Error as e:
            print(f"Error getting operation cache: {e}")
            return None
        finally:
            cursor.close()


class CacheViewWindow(tk.Toplevel):
    """Окно для просмотра кэша операции"""

    def __init__(self, parent, cache_data):
        super().__init__(parent)
        self.title(f"Кэш операции #{cache_data['operation']['operation_id']}")
        self.geometry("800x600")

        self.create_widgets(cache_data)

    def create_widgets(self, cache_data):
        # Основные сведения об операции
        info_frame = tk.LabelFrame(self, text="Информация об операции")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        info_text = tk.Text(info_frame, height=6, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        op = cache_data['operation']
        info_text.insert(tk.END, f"ID: {op['operation_id']}\n")
        info_text.insert(tk.END, f"Файл: {op['input_file_path']}\n")
        info_text.insert(tk.END, f"Статус: {op['status']}\n")
        info_text.insert(tk.END, f"Лучший ключ: {op['best_key']}\n")
        info_text.insert(tk.END, f"Оценка: {op['best_score']}\n")
        info_text.insert(tk.END, f"Итерации: {op['iterations']}, Рестарты: {op['restarts']}\n")
        info_text.config(state=tk.DISABLED)

        # Кэш лучшего ключа
        if cache_data['best_key_cache']:
            cache_frame = tk.LabelFrame(self, text="Кэш лучшего ключа")
            cache_frame.pack(fill=tk.X, padx=5, pady=5)

            cache_text = tk.Text(cache_frame, height=4, wrap=tk.WORD)
            cache_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

            cache = cache_data['best_key_cache']
            cache_text.insert(tk.END, f"Хэш ключа: {cache['key_hash']}\n")
            cache_text.insert(tk.END, f"Хэш текста: {cache['ciphertext_hash']}\n")
            cache_text.insert(tk.END,
                              f"Расшифрованный текст (первые 200 символов):\n{cache['decrypted_text'][:200]}...\n")
            cache_text.config(state=tk.DISABLED)

        # Промежуточные результаты
        inter_frame = tk.LabelFrame(self, text="Последние 100 промежуточных результатов")
        inter_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        columns = ("Итерация", "Ключ", "Оценка")
        self.tree = ttk.Treeview(inter_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        self.tree.column("Ключ", width=200)

        scroll_y = tk.Scrollbar(inter_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = tk.Scrollbar(inter_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Заполняем таблицу промежуточными результатами
        for item in cache_data['intermediates']:
            self.tree.insert("", tk.END, values=(
                item['iteration'],
                item['current_key'],
                item['current_score']
            ))


class OperationsWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.title("Управление операциями")
        self.geometry("1300x600")
        self.db = db_manager

        self.create_widgets()
        self.load_operations()

    def create_widgets(self):
        # Панель управления
        control_frame = tk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Поиск по ID
        tk.Label(control_frame, text="Поиск по ID:").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(control_frame, width=10)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Найти", command=self.search_by_id).pack(side=tk.LEFT)

        # Фильтр по статусу
        tk.Label(control_frame, text="Фильтр по статусу:").pack(side=tk.LEFT, padx=(10, 0))
        self.status_filter = ttk.Combobox(control_frame,
                                          values=["Все", "running", "completed", "failed", "cancelled"],
                                          state="readonly")
        self.status_filter.set("Все")
        self.status_filter.pack(side=tk.LEFT)
        self.status_filter.bind("<<ComboboxSelected>>", self.apply_filters)

        # Кнопка обновления
        tk.Button(control_frame, text="Обновить", command=self.load_operations).pack(side=tk.RIGHT)

        # Таблица операций
        columns = ("ID", "Файл", "Статус", "Начало", "Завершение", "Ключ", "Оценка", "Итерации", "Рестарты")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        self.tree.column("Файл", width=150)
        self.tree.column("Начало", width=120)
        self.tree.column("Завершение", width=120)

        scroll_y = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Панель действий
        action_frame = tk.Frame(self)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(action_frame, text="Удалить выбранное", command=self.delete_selected,
                  bg="#ffcccc").pack(side=tk.LEFT)

        # Новая кнопка для просмотра кэша
        tk.Button(action_frame, text="Показать кэш", command=self.show_cache,
                  bg="#ccffcc").pack(side=tk.LEFT, padx=5)

        # Детали операции
        self.details_text = tk.Text(self, height=10, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, padx=5, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.show_details)

    def load_operations(self, status_filter=None):
        """Загружает операции из БД"""
        self.tree.delete(*self.tree.get_children())

        if status_filter == "Все":
            status_filter = None

        operations = self.db.get_operations(status_filter=status_filter)

        for op in operations:
            self.tree.insert("", tk.END, values=(
                op["operation_id"],
                op["input_file_path"],
                op["status"],
                op["start_time"].strftime("%Y-%m-%d %H:%M:%S") if op["start_time"] else "",
                op["end_time"].strftime("%Y-%m-%d %H:%M:%S") if op["end_time"] else "",
                op["best_key"],
                op["best_score"],
                op["iterations"],
                op["restarts"]
            ))

    def search_by_id(self):
        """Поиск операции по ID"""
        op_id = self.search_entry.get()
        if not op_id.isdigit():
            messagebox.showwarning("Ошибка", "Введите числовой ID операции")
            return

        operations = self.db.get_operations(operation_id=int(op_id))
        self.tree.delete(*self.tree.get_children())

        if operations:
            op = operations[0]
            self.tree.insert("", tk.END, values=(
                op["operation_id"],
                op["input_file_path"],
                op["status"],
                op["start_time"].strftime("%Y-%m-%d %H:%M:%S") if op["start_time"] else "",
                op["end_time"].strftime("%Y-%m-%d %H:%M:%S") if op["end_time"] else "",
                op["best_key"],
                op["best_score"],
                op["iterations"],
                op["restarts"]
            ))
        else:
            messagebox.showinfo("Результат", "Операция не найдена")

    def apply_filters(self, event=None):
        """Применяет фильтры к списку операций"""
        status = self.status_filter.get()
        self.load_operations(status_filter=status if status != "Все" else None)

    def show_details(self, event):
        """Показывает детали выбранной операции"""
        selected = self.tree.focus()
        if not selected:
            return

        op_id = self.tree.item(selected)["values"][0]

        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"Детали операции ID: {op_id}\n\n")

        operation = self.db.get_operations(operation_id=op_id)[0]
        for key, value in operation.items():
            self.details_text.insert(tk.END, f"{key}: {value}\n")

    def delete_selected(self):
        """Удаляет выбранную операцию"""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите операцию для удаления")
            return

        op_id = self.tree.item(selected)["values"][0]

        if messagebox.askyesno("Подтверждение",
                               f"Вы уверены, что хотите удалить операцию ID {op_id}?\nЭто действие нельзя отменить."):
            if self.db.delete_operation(op_id):
                messagebox.showinfo("Успех", "Операция успешно удалена")
                self.load_operations()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить операцию")

    def show_cache(self):
        """Показывает кэш выбранной операции"""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите операцию для просмотра кэша")
            return

        op_id = self.tree.item(selected)["values"][0]
        cache_data = self.db.get_operation_cache(op_id)

        if not cache_data:
            messagebox.showinfo("Информация", "Нет данных кэша для этой операции")
            return

        CacheViewWindow(self, cache_data)


class CipherBreakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Взломщик шифра Плейфера")
        self.root.geometry("600x450")

        self.running = False
        self.current_process = None
        self.total_iterations = 0
        self.current_iteration = 0
        self.db = DatabaseManager()
        self.current_operation_id = None

        self.create_widgets()

    def create_widgets(self):
        # Файл для расшифровки
        tk.Label(self.root, text="Файл для расшифровки:").pack(pady=(10, 0))

        self.file_frame = tk.Frame(self.root)
        self.file_frame.pack(pady=5)

        self.file_entry = tk.Entry(self.file_frame, width=40)
        self.file_entry.pack(side=tk.LEFT, padx=5)

        self.browse_btn = tk.Button(self.file_frame, text="Обзор...", command=self.browse_file)
        self.browse_btn.pack(side=tk.LEFT)

        # Кнопки управления
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)

        self.break_btn = tk.Button(self.btn_frame, text="Взломать шифр", command=self.start_breaking)
        self.break_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = tk.Button(self.btn_frame, text="Отмена", state=tk.DISABLED, command=self.cancel_breaking)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        # Прогресс бар
        self.progress_label = tk.Label(self.root, text="Прогресс: 0%")
        self.progress_label.pack(pady=(10, 0))

        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=5)

        # Статус
        self.status_label = tk.Label(self.root, text="Готов к работе")
        self.status_label.pack(pady=5)

        # Результаты
        self.result_frame = tk.LabelFrame(self.root, text="Результаты")
        self.result_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(self.result_frame, height=8, wrap=tk.WORD)
        self.result_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.result_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.result_text.yview)

        tk.Button(self.root, text="Операции с БД", command=self.show_operations_window,
                  bg="#e0e0e0").pack(side=tk.BOTTOM, pady=10)

    def show_operations_window(self):
        """Открывает окно управления операциями"""
        if not self.db.connection:
            messagebox.showerror("Ошибка", "Нет подключения к базе данных")
            return

        OperationsWindow(self.root, self.db)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)

    def start_breaking(self):
        if not self.file_entry.get():
            messagebox.showerror("Ошибка", "Выберите файл для расшифровки")
            return

        self.running = True
        self.break_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="Взлом шифра...")
        self.progress['value'] = 0
        self.progress_label.config(text="Прогресс: 0%")

        # Запуск в отдельном потоке
        self.current_process = Thread(target=self.break_cipher_thread)
        self.current_process.start()

    def cancel_breaking(self):
        self.running = False
        self.status_label.config(text="Отмена...")

    def update_progress(self, current, total):
        progress = int((current / total) * 100)
        self.progress['value'] = progress
        self.progress_label.config(text=f"Прогресс: {progress}%")
        self.root.update_idletasks()

    def break_cipher_thread(self):
        try:
            input_file = self.file_entry.get()
            base_name = os.path.splitext(input_file)[0]
            encrypted_file = f"{base_name}_encrypted.txt"
            output_file = f"{base_name}_decrypted.txt"

            # Логируем начало операции в БД
            self.current_operation_id = self.db.log_operation_start(input_file)

            # Чтение файла
            message = playfairCipher.readfile(input_file)
            key = playfairCipher.Playfair.buildtable('CHARITY')
            ciphertext = playfairCipher.Playfair.encrypt(message, key)

            # Сохранение зашифрованного текста
            with open(encrypted_file, 'w', encoding='utf-8') as f:
                f.write(ciphertext)

            self.append_result("--- Взлом шифра Плейфера ---\n")
            self.append_result(f"Первые 100 символов зашифрованного текста: {ciphertext[:100]}...\n")
            self.append_result(f"Оценка триграмм для зашифрованного текста: {log_trigram_fitness(ciphertext)}\n\n")

            # Настройки для прогресс-бара
            restarts = 20
            max_iter = 20000
            self.total_iterations = restarts * max_iter
            self.current_iteration = 0

            best_text, best_key, best_score = self.simulated_annealing(ciphertext, max_iter, restarts)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(best_text)

            self.append_result("\n--- Лучший результат ---\n")
            self.append_result(f"Ключ: {best_key}\n")
            self.append_result(f"Оценка триграмм: {best_score}\n")
            self.append_result(f"Первые 200 символов:\n{best_text[:200]}...\n")

            self.status_label.config(text="Готово")
            messagebox.showinfo("Данные сохранены в БД",
                                "Алгоритм завершен!"
                                )
            # Логируем успешное завершение операции
            self.db.log_operation_end(
                operation_id=self.current_operation_id,
                status='completed',
                encrypted_file_path=encrypted_file,
                decrypted_file_path=output_file,
                best_key=best_key,
                best_score=best_score,
                iterations=max_iter,
                restarts=restarts
            )

        except Exception as e:
            self.append_result(f"Ошибка: {str(e)}\n")
            self.status_label.config(text="Ошибка")
            messagebox.showerror("Ошибка", str(e))

            # Логируем ошибку в БД
            if self.current_operation_id:
                self.db.log_operation_end(
                    operation_id=self.current_operation_id,
                    status='failed',
                    encrypted_file_path=encrypted_file if 'encrypted_file' in locals() else None,
                    decrypted_file_path=output_file if 'output_file' in locals() else None
                )

        finally:
            self.running = False
            self.break_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
            self.progress['value'] = 100
            self.progress_label.config(text="Прогресс: 100%")

    def simulated_annealing(self, ciphertext, max_iter, restarts):
        best_key = None
        best_score = -float('inf')
        best_decrypted = ""

        for i in range(restarts):
            if not self.running:
                break

            current_key = ''.join(random.sample(playfairCipher.ALPHABET.replace('J', ''), 25))
            decrypted = self.db.get_cached_decrypt(current_key, ciphertext)
            if decrypted is None:
                decrypted = playfairCipher.Playfair.decrypt(ciphertext, current_key)
                self.db.cache_decrypt(current_key, ciphertext, decrypted)
            current_score = log_trigram_fitness(decrypted)

            T = 10.0
            cooling_rate = 0.9995

            for j in range(max_iter):
                if not self.running:
                    break

                self.current_iteration = i * max_iter + j
                self.update_progress(self.current_iteration, self.total_iterations)

                # Логируем промежуточные результаты каждые 100 итераций
                if j % 100 == 0:
                    self.db.log_intermediate_result(
                        self.current_operation_id,
                        self.current_iteration,
                        current_key,
                        current_score
                    )

                new_key = playfair_key_transformation(current_key)

                # Проверяем кэш в БД
                decrypted = self.db.get_cached_decrypt(new_key, ciphertext)
                if decrypted is None:
                    decrypted = playfairCipher.Playfair.decrypt(ciphertext, new_key)
                    self.db.cache_decrypt(new_key, ciphertext, decrypted)

                new_score = log_trigram_fitness(decrypted)

                if new_score > best_score:
                    best_score = new_score
                    best_key = new_key
                    best_decrypted = decrypted

                if new_score > current_score or random.random() < math.exp((new_score - current_score) / T):
                    current_score = new_score
                    current_key = new_key

                T *= cooling_rate

        return best_decrypted, best_key, best_score

    def append_result(self, text):
        self.result_text.insert(tk.END, text)
        self.result_text.see(tk.END)
        self.root.update_idletasks()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


def count_trigrams(text):
    return max(1, len(text) - 2)


def trigram_frequency(text, trigram):
    return text.count(trigram) / count_trigrams(text)


def log_trigram_fitness(text):
    score = 0.0
    for trigram, prob in ENGLISH_TRIGRAMS.items():
        freq = trigram_frequency(text, trigram)
        if freq > 0 and prob > 0:
            score += freq * math.log(prob)
    return score


def playfair_key_transformation(key):
    key = list(key)
    mutation_type = random.choices(
        ["swap_letters", "swap_rows", "swap_cols", "reverse", "transpose"],
        weights=[0.8, 0.05, 0.05, 0.05, 0.05],
        k=1
    )[0]

    if mutation_type == "swap_letters":
        i, j = random.sample(range(25), 2)
        key[i], key[j] = key[j], key[i]
    elif mutation_type == "swap_rows":
        i, j = random.sample(range(5), 2)
        for k in range(5):
            key[i * 5 + k], key[j * 5 + k] = key[j * 5 + k], key[i * 5 + k]
    elif mutation_type == "swap_cols":
        i, j = random.sample(range(5), 2)
        for k in range(5):
            key[k * 5 + i], key[k * 5 + j] = key[k * 5 + j], key[k * 5 + i]
    elif mutation_type == "reverse":
        key.reverse()
    elif mutation_type == "transpose":
        new_key = [key[j * 5 + i] for i in range(5) for j in range(5)]
        key = new_key
    return ''.join(key)


if __name__ == "__main__":
    root = tk.Tk()
    app = CipherBreakerApp(root)
    root.mainloop()