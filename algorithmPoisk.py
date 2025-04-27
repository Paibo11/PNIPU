def sequential_search_ordered(keys, target):
    """
    Последовательный поиск в упорядоченной таблице.

    Параметры:
        keys (list): Упорядоченный список ключей (K_1 < K_2 < ... < K_N)
        target: Искомый ключ K

    Возвращает:
        tuple: (индекс найденного элемента, статус поиска)
               где статус: True - успешно, False - неудачно
    """
    # Добавляем "фиктивную" запись с бесконечным ключом в конец
    extended_keys = keys + [float('inf')]

    i = 0  # T1. Инициализация (начинаем с первого элемента)

    while True:
        # T2. Сравнение с текущим ключом
        if target <= extended_keys[i]:
            # T4. Проверяем на равенство
            if target == extended_keys[i]:
                # Успешное завершение, если нашли элемент
                # Проверяем, не является ли найденный элемент фиктивным
                if i < len(keys):
                    return (i, True)
                else:
                    return (-1, False)
            else:
                # Неудачное завершение, если ключ не найден
                return (-1, False)

        # T3. Переход к следующему элементу
        i += 1


# Пример использования
if __name__ == "__main__":
    # Упорядоченный список ключей
    test_keys = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    test_targets = [5, 16, 40, 91, 100]

    print("Упорядоченная таблица ключей:", test_keys)
    print("Фиктивная запись добавлена автоматически (бесконечность)")
    print("\nТестирование поиска:")

    for target in test_targets:
        index, found = sequential_search_ordered(test_keys, target)
        if found:
            print(f"Ключ {target} найден по индексу {index}")
        else:
            print(f"Ключ {target} не найден в таблице")