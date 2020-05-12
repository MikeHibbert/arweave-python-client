import hashlib
import struct
from jose.utils import base64url_encode, base64url_decode

CHUNK_SIZE = 256 * 1024
NOTE_SIZE = 32


class TaggedChunk:
    def __init__(self, tc_id, end):
        self.id = tc_id
        self.end = end


class HashNode:
    def __init__(self, hn_id, max):
        self.id = hn_id
        self.max = max


def compute_root_hash(data):
    tagged_chunks = []

    if type(data) != bytes:
        data = data.encode()

    rest = data
    pos = 0

    while len(rest) >= CHUNK_SIZE:
        chunk = rest[:CHUNK_SIZE]
        chunk_id = hashlib.sha256(chunk).digest()

        pos += len(chunk)

        tagged_chunks.append(TaggedChunk(chunk_id, pos))

        rest = rest[CHUNK_SIZE:]

    tagged_chunks.append(TaggedChunk(
        hashlib.sha256(rest).digest(),
        pos + len(rest)
    ))

    nodes = [hash_leaf(tc.id, tc.end) for tc in tagged_chunks]

    while len(nodes) > 1:
        next_nodes = []
        for i in range(0, len(nodes), 2):
            next_nodes.append(
                hash_branch(nodes[i], nodes[i+1])
            )

        nodes = next_nodes

    return nodes[0].id


def hash_branch(left, right=None):
    if not right:
        return left

    return HashNode(
        hash(
            [
                hash(left.id),
                hash(right.id),
                hash(note_to_buffer(left.max))
            ]
        ),
        right.max
    )


def hash_leaf(data, note):
    return HashNode(
        hash([hash(data), hash(note_to_buffer(note))]),
        note
    )


def hash(data):
    if type(data) == list:
        byte_str = b''
        for line in data:
            byte_str += line

        data = byte_str

    digest = hashlib.sha256(data).digest()
    b64_str = base64url_encode(digest)
    return digest


def note_to_buffer(note):
    buffer = b"\x00" * NOTE_SIZE
    buffer = bytearray(buffer)

    for i in range(NOTE_SIZE-1, 0, -1):
        if i > 0:
            if note > 0:
                buffer[i] = note.to_bytes(4, byteorder='big')[-1]
                note = note >> 8
            else:
                break
        else:
            break

    return bytes(buffer)
