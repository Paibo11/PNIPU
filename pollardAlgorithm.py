import math
import random
from math import gcd, sqrt, log


def pollards_rho_algorithm(N, epsilon):
    """
    Реализация алгоритма Полларда (метод "rho") для факторизации числа N.

    Параметры:
    N - составное число, которое нужно факторизовать
    epsilon - параметр точности (0 < epsilon < 1)

    Возвращает:
    Нетривиальный делитель N или None, если делитель не найден
    """
    if N % 2 == 0:
        return 2

    # Шаг 1: Вычисляем T2
    T2 = int(sqrt(2 * sqrt(N) * log(1 / epsilon))) + 1
    print(f"Вычислено T2 = {T2}")

    while True:
        # Шаг 2: Выбираем случайный многочлен f(x) = x^2 + c
        c = random.randint(1, N - 1)
        f = lambda x: (x ** 2 + c) % N
        print(f"Выбран многочлен f(x) = x^2 + {c}")

        # Шаг 3: Выбираем случайное начальное значение x0
        x0 = random.randint(0, N - 1)
        print(f"Выбрано начальное значение x0 = {x0}")

        # Инициализация последовательности
        x = [x0]

        for i in range(1, T2 + 1):
            # Вычисляем следующий элемент последовательности
            x_next = f(x[-1])
            x.append(x_next)

            # Шаг 4: Проверяем все предыдущие элементы
            for k in range(i):
                d_k = gcd(x[i] - x[k], N)

                if 1 < d_k < N:
                    print(f"Найден делитель: d_{k} = {d_k} (x_{i} = {x[i]}, x_{k} = {x[k]})")
                    return d_k

                elif d_k == N:
                    print(f"Обнаружен период (d_k = N). Прерываем текущую итерацию.")
                    break  # Прерываем внутренний цикл

            else:
                print(f"Обнаружен период (d_k = 1). Вычисляем следующее x[i] .") # Неявная проверка на d_k = 1
                continue
            break

        else:
            print(f"Достигнут предел T2 = {T2} без нахождения делителя. Повторяем с новыми параметрами.")
            continue
        # Если был период, продолжаем с новыми параметрами
        continue


if __name__ == "__main__":
    N = 2415
    epsilon = 0.1

    print(f"Пытаемся найти делитель числа N = {N} с epsilon = {epsilon}")
    divisor = pollards_rho_algorithm(N, epsilon)

    if divisor:
        print(f"\nУспех! Найден нетривиальный делитель числа {N}: {divisor}")
        print(f"Проверка: {N} / {divisor} = {N // divisor}")
    else:
        print(f"\nНе удалось найти делитель для числа {N} с заданными параметрами.")