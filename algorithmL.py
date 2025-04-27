def knuth_list_insertion_sort(keys):
    """
    Алгоритм L (Сортировка вставками в список) из тома 3 "Искусства программирования" Кнута.
    Сортирует записи, используя поля связи, без физического перемещения данных.

    Параметры:
        keys (list): Список ключей для сортировки (K_1, ..., K_N)

    Возвращает:
        list: Отсортированный список
    """
    N = len(keys)
    if N == 0:
        return []

    # Инициализация связей (L_0, L_1, ..., L_N)
    LINK = [0] * (N + 1)  # L[0] - искусственная запись R_0
    LINK[0] = N  # L_0 ← N (шаг L1)
    LINK[N] = 0  # L_N ← 0 (шаг L1)

    print(f"\nИсходный массив: {keys}")
    print(f"Инициализация: LINK[0] = {LINK[0]}, LINK[{N}] = {LINK[N]}")

    # Основной цикл (j от N-1 до 1)
    for j in range(N - 1, 0, -1):  # Шаг L1
        p = LINK[0]  # p ← L_0 (шаг L2)
        q = 0  # q ← 0 (шаг L2)
        K = keys[j - 1]  # K ← K_j

        # Поиск места для вставки (шаги L3-L4)
        while p > 0 and keys[p - 1] < K:  # K_p < K (пока не найдём K ≤ K_p)
            q = p
            p = LINK[p]

        # Вставка (шаг L5)
        LINK[q] = j  # L_q ← j
        LINK[j] = p  # L_j ← p

    print("\nФинальное состояние связей:")
    current = LINK[0]
    path = []
    while current != 0:
        path.append(f"R_{current}(K={keys[current - 1]})")
        current = LINK[current]
    print( " → ".join(path))

    # Сбор отсортированного списка (начиная с L_0)
    sorted_list = []
    current = LINK[0]
    while current > 0:
        sorted_list.append(keys[current - 1])
        current = LINK[current]

    print(f"\nРезультат: {sorted_list}")
    return sorted_list


keys = [3, 1, 4, 1, 5, 9, 2, 6]
sorted_keys = knuth_list_insertion_sort(keys)