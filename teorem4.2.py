import math

def squares(N):
    if N <= 1:
        print(f"\nЧисло {N} ≤ 1 — не считается простым.")
        return False
    if N == 2:
        print(f"\nЧисло {N} — простое (единственное четное простое число).")
        return True
    if N % 2 == 0:
        print(f"\nЧисло {N} — четное и больше 2 ⇒ составное.")
        return False

    representations = [] # кол-во разложений
    max_b = int(math.isqrt(N)) + 1

    print(f"\nПроверка числа {N}:")
    for b in range(1, max_b):  # b > 0, как в условии (21)
        if N % b == 0:  # Проверяем является ли b делителем N
            a = N // b
            if a < b:
                continue  # Исключаем случаи, где a < b (по условию a ≥ b)
            # Преобразуем разложение N = a*b в разность квадратов по формуле (22)
            x = ((a + b) // 2)
            y = ((a - b) // 2)
            if (a + b) % 2 != 0 or (a - b) % 2 != 0:
                continue  # x и y должны быть целыми
            representations.append((x, y))
            print(f"  Найдено разложение: {N} = {a} * {b} → {x}² - {y}² = {x**2 - y**2}")

    if len(representations) == 1:
        print(f"  У числа {N} ровно одно разложение - оно простое.")
        return True
    else:
        print(f"  У числа {N} найдено {len(representations)} разложений - оно составное.")
        return False

# Пример использования
numbers_to_test = [2, 3, 5, 7, 9, 11, 13, 15, 17, 21]
for num in numbers_to_test:
    print("-" * 50)
    is_prime = squares(num)
    print(f"Итог: {num} — {'простое' if is_prime else 'составное'} число.")