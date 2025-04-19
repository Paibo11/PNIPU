import random
import math


def miller_rabin_test(N, s, verbose=False):
    """
    Тест Миллера-Рабина с подробным выводом.

    Параметры:
    N - число для проверки на простоту
    s - количество различных случайных чисел a для тестирования
    verbose - если True, выводит подробные шаги

    Возвращает:
    "составное" - если N точно составное
    "вероятно простое" - если N прошло все тесты
    """
    if verbose:
        print(f"\nПроверяем число N = {N} на простоту")

    if N == 2:
        if verbose:
            print("N = 2 — простое число.")
        return "Неизвестно"
    if N % 2 == 0 or N < 2:
        if verbose:
            print("N чётное или меньше 2 — составное.")
        return "составное"

    # Шаг 1: Разложить N-1 в виде 2^t * u
    u = N - 1
    t = 0
    while u % 2 == 0:
        u //= 2
        t += 1

    if verbose:
        print(f"Разложение N-1 = 2^{t} * {u}")

    for i in range(s):
        if verbose:
            print(f"\n--- Попытка {i + 1} ---")

        # Шаг 1: Выбрать случайное a ∈ [1, N-1]
        a = random.randint(1, N - 1)
        if verbose:
            print(f"Выбрано случайное a = {a}")

        # Проверить НОД(a, N)
        d = math.gcd(a, N)
        if d > 1:
            if verbose:
                print(f"НОД({a}, {N}) = {d} > 1 ⇒ N - составное.")
            return "составное"
        else:
            if verbose:
                print(f"НОД({a}, {N}) = 1 ⇒ продолжаем тест.")

        # Шаг 2: Вычислить последовательность a^(2^k * u) mod N
        x = pow(a, u, N)
        if verbose:
            print(f"Вычисляем x = {a}^{u} mod {N} = {x}")

        if x == 1 or x == N - 1:
            if verbose:
                print(f"x = {x} (равно 1 или N-1) ⇒ тест пройден для a = {a}.")
            continue

        composite = True
        if verbose:
            print(f"x = {x} (не равно 1 или N-1), проверяем квадраты...")

        for k in range(1, t):
            x_prev = x
            x = pow(x, 2, N)
            if verbose:
                print(f"Шаг {k}: {x_prev}^2 mod {N} = {x}")

            if x == 1:
                if verbose:
                    print(f"Найдено x = {x} ⇒ тест пройден для a = {a}.")
                composite = False
                break

            if x == N - 1:
                if verbose:
                    print(f"Найдено x = {x} (равно N-1) ⇒ тест пройден для a = {a}.")
                composite = False
                break

        if composite:
            if verbose:
                print(f"Не найдено x ≡ -1 mod {N} ⇒ N - составное.")
            return "составное"

    if verbose:
        print(f"\nВсе {s} попыток завершены: N прошло тест Миллера-Рабина.")
    return "Неизвестно"


# Пример использования
if __name__ == "__main__":
    numbers_to_test = [5, 9, 15, 17, 21, 29, 561]
    for num in numbers_to_test:
        print(f"\n=== Тестируем число {num} ===")
        result = miller_rabin_test(num, s=3, verbose=True)
        print(f"\nИтог: {num} — {result}")