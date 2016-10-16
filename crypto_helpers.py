from Crypto.Cipher import AES
from Crypto import Random
import random
import struct
import hashlib


def generate_token(used_keys_collection = [], length = 32, allowed_characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_'):
    result = ''
    for i in range(length):
        result += random.choice(allowed_characters)

    if result in used_keys_collection:
        return generate_token()
    else:
        return result


def aes_encrypt(message, key):
    checksum = hashlib.md5(message).digest()
    original_message = message
    message = checksum + struct.pack('>I', len(original_message)) + original_message

    # add empty spaces to round up to AES.block_size
    empty_bytes = AES.block_size - (len(message) % AES.block_size)
    if (empty_bytes == AES.block_size):
        empty_bytes = 0
    for i in range(empty_bytes):
        message += b'\0'

    key = key[0:32] # 256-bit key
    cbc_iv = Random.new().read(AES.block_size)


    encryptor = AES.new(key, AES.MODE_CBC, cbc_iv)
    cyphertext = encryptor.encrypt(message)

    output = cbc_iv + cyphertext
    return output


def aes_decrypt(to_decrypt, key):
    cbc_iv = to_decrypt[:AES.block_size]
    cyphertext = to_decrypt[AES.block_size:]

    decryptor = AES.new(key, AES.MODE_CBC, cbc_iv)
    message = decryptor.decrypt(cyphertext)
    expected_checksum = message[:16]
    message_length = struct.unpack(">I", message[16:20])[0]
    original_message = message[20:20+message_length]

    checksum = hashlib.md5(original_message).digest()
    if expected_checksum != checksum:
        # Incorrect key
        return None
    else:
        return original_message