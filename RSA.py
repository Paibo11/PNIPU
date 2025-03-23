import random

def power(base, expo, m):
    res = 1
    base = base % m
    while expo > 0:
        if expo & 1:
            res = (res * base) % m
        base = (base * base) % m
        expo //= 2
    return res

def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)


def modInverse(e, phi):
    def extended_gcd(a, b):
        if a == 0:
            return b, 0, 1
        g, x1, y1 = extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return g, x, y

    g, x, _ = extended_gcd(e, phi)
    if g != 1:
        raise ValueError("Обратного элемента не существует")
    return x % phi

def is_prime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6

    return True


# Генерация случайного простого числа заданной длины (бит)
def generate_large_prime(bits=25):
    while True:
        num = random.getrandbits(bits) | (1 << bits - 1) | 1  # Устанавливаем старший и младший биты
        if is_prime(num):
            return num

def find_largest_coprime(phi):
    for e in range(phi - 2, 1, -1): 
        if gcd(e, phi) == 1:
            return e
    return -1

def generateKeys():
    p = generate_large_prime()
    q = generate_large_prime()
    n = p * q
    phi = (p - 1) * (q - 1)
    e = find_largest_coprime(phi)
    d = modInverse(e, phi)
    return e, d, n

def encrypt_message(message, e, n):
    encrypted = [power(m, e, n) for m in message.encode('utf-8')]
    return encrypted

def decrypt_message(encrypted, d, n):
    decrypted = [power(c, d, n) for c in encrypted]
    decrypted_bytes = bytes(decrypted)
    
    try:
        decrypted_message = decrypted_bytes.decode('utf-8')
        return decrypted_message
    except UnicodeDecodeError:
        return "Ошибка при декодировании сообщения"



# Main execution
if __name__ == "__main__":
    # Key Generation
    e, d, n = generateKeys()
    print(f"Публичный ключ (e, n): ({e}, {n})")
    print(f"Приватный ключ (d, n): ({d}, {n})")

    # Message
    message = "if 14 - wr fso "
    print(f"Оригинальное сообщение: {message}")

    # Encrypt the message
    encrypted_message = encrypt_message(message, e, n)
    # print(f"Закодированное сообщение: {encrypted_message}")
    print(encrypted_message)
    # Decrypt the message
    decrypted_message = decrypt_message(encrypted_message, d, n)
    print(f"Дэкодированное сообщение: {decrypted_message}")
