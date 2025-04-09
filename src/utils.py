def compress_bool_list_to_hex(bool_list):
    """Сжимает список bool в строку в шестнадцатеричном формате."""
    if not bool_list:
        return "0"

    byte_array = bytearray()
    current_byte = 0
    bit_pos = 0

    for value in bool_list:
        if value:
            current_byte |= (1 << bit_pos)
        bit_pos += 1
        if bit_pos == 8:
            byte_array.append(current_byte)
            current_byte = 0
            bit_pos = 0

    # Добавляем последний байт, если есть остаток
    if bit_pos > 0:
        byte_array.append(current_byte)

    # Преобразуем байты в шестнадцатеричную строку без префикса '0x'
    return byte_array.hex()


def decompress_bool_list_from_hex(hex_str, original_length):
    """Восстанавливает список bool из шестнадцатеричной строки."""
    # Преобразуем hex-строку обратно в байты
    byte_array = bytes.fromhex(hex_str)
    result = []

    for byte in byte_array:
        for i in range(min(8, original_length - len(result))):
            result.append(bool(byte & (1 << i)))

    return result[:original_length]