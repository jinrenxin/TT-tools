#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


def extract_quick_binary_from_lsb(
    image_array: np.ndarray, bits_needed: int = 40
) -> str | None:
    height, _, _ = image_array.shape
    top_skip = int(height * 0.2)
    bottom_skip = int(height * 0.2)
    available_image = image_array[top_skip : height - bottom_skip, :, :]
    lsb_reshaped = (available_image & 1).transpose(0, 1, 2).reshape(-1)
    if len(lsb_reshaped) < bits_needed:
        return None
    return "".join(lsb_reshaped[:bits_needed].astype(str))


def extract_binary_from_lsb(image_array: np.ndarray) -> str | None:
    height, _, _ = image_array.shape
    top_skip = int(height * 0.2)
    bottom_skip = int(height * 0.2)
    available_image = image_array[top_skip : height - bottom_skip, :, :]
    lsb_reshaped = (available_image & 1).transpose(0, 1, 2).reshape(-1)
    binary_data = "".join(lsb_reshaped.astype(str))

    if len(binary_data) < 32:
        return None

    try:
        header_length = int(binary_data[:32], 2)
    except ValueError:
        return None

    total_bits_needed = 32 + header_length * 8
    if len(binary_data) < total_bits_needed:
        return None
    return binary_data[:total_bits_needed]


def binary_to_bytes(binary_string: str) -> bytes:
    if len(binary_string) % 8 != 0:
        binary_string = binary_string[: -(len(binary_string) % 8)]
    bit_array = np.array([int(bit) for bit in binary_string], dtype=np.uint8)
    byte_values = np.packbits(bit_array.reshape(-1, 8))
    return bytes(byte_values)


def verify_password(password: str, salt: bytes, stored_hash: bytes) -> bool:
    password_hash = hashlib.sha256((password + salt.hex()).encode("utf-8")).digest()
    return password_hash == stored_hash


def generate_key_stream(password: str, salt: bytes, length: int) -> bytes:
    key_material = (password + salt.hex()).encode("utf-8")
    hashes_needed = (length + 31) // 32
    key_stream = bytearray(length)

    for i in range(hashes_needed):
        hash_result = hashlib.sha256(key_material + str(i).encode("utf-8")).digest()
        start = i * 32
        end = min(start + 32, length)
        key_stream[start:end] = hash_result[: end - start]

    return bytes(key_stream)


def decrypt_data(encrypted_data: bytes, password: str, salt: bytes) -> bytes:
    key_stream = generate_key_stream(password, salt, len(encrypted_data))
    encrypted_array = np.frombuffer(encrypted_data, dtype=np.uint8)
    key_array = np.frombuffer(key_stream, dtype=np.uint8)
    return np.bitwise_xor(encrypted_array, key_array).tobytes()


def parse_file_header_normal(file_header: bytes) -> tuple[bytes | None, str | None]:
    if len(file_header) < 5:
        return None, None
    ext_len = file_header[0]
    if len(file_header) < 1 + ext_len + 4:
        return None, None
    ext = file_header[1 : 1 + ext_len].decode("utf-8")
    data = file_header[1 + ext_len + 4 :]
    return data, ext


def parse_file_header_with_password(
    file_header: bytes, password: str
) -> tuple[bytes | None, str | None]:
    if len(file_header) < 1:
        return None, None

    has_password = file_header[0] == 1
    if has_password:
        if len(file_header) < 50:
            return None, None
        password_hash = file_header[1:33]
        salt = file_header[33:49]
        if not verify_password(password, salt, password_hash):
            return None, None
        offset = 49
    else:
        offset = 1

    if len(file_header) < offset + 1:
        return None, None
    ext_len = file_header[offset]
    if len(file_header) < offset + 1 + ext_len + 4:
        return None, None

    ext = file_header[offset + 1 : offset + 1 + ext_len].decode("utf-8")
    data = file_header[offset + 1 + ext_len + 4 :]
    if has_password:
        data = decrypt_data(data, password, salt)
    return data, ext


def extract_file_data_from_image(
    image_array: np.ndarray, password: str = ""
) -> tuple[bytes | None, str | None]:
    if len(image_array.shape) != 3 or image_array.shape[2] not in (3, 4):
        return None, None

    if image_array.shape[2] == 4:
        image_array = image_array[:, :, :3]

    quick_binary = extract_quick_binary_from_lsb(image_array, bits_needed=40)
    if not quick_binary:
        return None, None

    try:
        header_length = int(quick_binary[:32], 2)
    except ValueError:
        return None, None

    first_byte = int(quick_binary[32:40], 2)
    if first_byte == 1 and not password:
        return None, None

    binary_data = extract_binary_from_lsb(image_array)
    if not binary_data or len(binary_data) < 32 + header_length * 8:
        return None, None

    file_header = binary_to_bytes(binary_data[32 : 32 + header_length * 8])

    if first_byte == 1:
        return parse_file_header_with_password(file_header, password)
    if first_byte == 0 or 3 <= first_byte <= 255:
        return parse_file_header_normal(file_header)
    return None, None


def decode_image(
    input_path: Path, password: str = "", output_path: Path | None = None
) -> Path:
    image = Image.open(input_path)
    image_array = np.array(image)
    file_data, file_ext = extract_file_data_from_image(image_array, password)
    if file_data is None or not file_ext:
        raise RuntimeError("decode failed; check password or image format")

    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_decoded.{file_ext}")

    output_path.write_bytes(file_data)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recovered decoder from latest TT_Img_Loc.exe"
    )
    parser.add_argument("image_path")
    parser.add_argument("password", nargs="?", default="")
    parser.add_argument("output_path", nargs="?")
    args = parser.parse_args()

    out = decode_image(
        Path(args.image_path),
        args.password,
        Path(args.output_path) if args.output_path else None,
    )
    print(f"decoded -> {out}")


if __name__ == "__main__":
    main()
