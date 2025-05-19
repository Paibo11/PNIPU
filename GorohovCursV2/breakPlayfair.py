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
                password='1488',
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