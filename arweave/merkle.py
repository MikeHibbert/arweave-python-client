import hashlib
import struct
import functools
from jose.utils import base64url_encode, base64url_decode
from .file_io import read_file_chunks
from .utils import concat_buffers

CHUNK_SIZE = 256 * 1024
NOTE_SIZE = 32
HASH_SIZE = 32
MAX_CHUNK_SIZE = 256 * 1024
MIN_CHUNK_SIZE = 32 * 1024


class NodeTypeException(Exception):
    pass


class Node:
    def __init__(self, id, type=None, byte_range=0, max_byte_range=0):
        self.id = id
        self.type = type
        self.byte_range = byte_range
        self.max_byte_range = max_byte_range


class BranchNode(Node):
    def __init__(self, *args, **kwargs):
        super(BranchNode, self).__init__(*args, **kwargs)
        self.type = "branch"
        self.left_child = kwargs.get("left_child", None)
        self.right_child = kwargs.get("right_child", None)


class LeafNode(Node):
    def __init__(self, *args, **kwargs):
        super(BranchNode, self).__init__(*args, **kwargs)
        self.id = hash([hash(self.data_hash), hash(int_to_buffer(self.max_byte_range))])
        self.type = "leaf"
        self.data_hash = kwargs.get('data_hash', None)


class TaggedChunk:
    def __init__(self, tc_id, end):
        self.id = tc_id
        self.end = end


class Chunk:
    def __init__(self, data_hash, min_byte_range, max_byte_range):
        self.data_hash = data_hash
        self.min_byte_range = min_byte_range
        self.max_byte_range = max_byte_range


class HashNode:
    def __init__(self, hn_id, max):
        self.id = hn_id
        self.max = max


class Proof:
    def __init__(self, offset, proof):
        self.offset = offset
        self.proof = proof


class ValidatedPathResult:
    def __init__(self, offset, left_bound, right_bound, chunk_size):
        self.offset = offset
        self.left_bound = left_bound
        self.right_bound = right_bound
        self.chunk_size = chunk_size


def chunk_data(file_handler):
    """
    Takes the input data and chunks it into (mostly) equal sized chunks.
    The last chunk will be a bit smaller as it contains the remainder
    from the chunking process.
    :param file_handler:
    :return: chunks
    """
    chunks = []; chadd = chunks.append

    rest = data
    cursor = 0

    for chunk in read_file_chunks(file_handler, MAX_CHUNK_SIZE):
        data_hash = hashlib.sha256(chunk).digest()

        cursor += len(chunk)
        chadd(
            Chunk(
                data_hash,
                min_byte_range=cursor - len(chunk),
                max_byte_range=cursor
            )
        )

    return tuple(chunks)  # lets make this a fast processing tuple for later!


def compute_root_hash(file_handler):
    root_node = generate_tree(file_handler)

    return root_node.id


def generate_leaves(chunks):
    leaves = (
        LeafNode(
            data_hash=chunk.data_hash,
            min_byte_range=chunk.min_byte_range,
            max_byte_range=chunk.max_byte_range
        )
        for chunk in chunks
    )

    return leaves


def generate_tree(file_handler):
    root_node = build_layers(generate_leaves(chunk_data(file_handler)))

    return root_node


def build_layers(nodes, level=0):
    nodes_lenth = len(nodes)

    if nodes_lenth < 2:
        root = hash_branch(nodes[0], nodes[1])

        return root

    next_layer = []; nadd = next_layer.append

    for i in range(0, nodes_lenth, 2):
        left = nodes[i]
        right = None if i+1 > (nodes_lenth-1) else nodes[i+1]

        nadd(hash_branch(left, right))

    return build_layers(next_layer, level + 1)


def generate_proofs(root):
    proofs = resolve_branch_proofs(root)

    if type(proofs) != tuple:
        return (proofs,)

    return flatten_tuple(proofs)


def flatten_tuple(inputs):
    flat = []; fadd = flat.append

    for input in inputs:
        if type(input) == tuple:
            fadd(flatten_tuple(input))
        else:
            fadd(input)

    return tuple(flat)


def resolve_branch_proofs(node, proof=b'', depth=0):
    if node.type == "leaf":
        return Proof(
            node.max_byte_range - 1,
            concat_buffers([proof, node.data_hash, int_to_buffer(node.max_byte_range)])
        )

    if node.type == "branch":
        partial_proof = concat_buffers([
            proof,
            node.left_child.id,
            node.right_child.id,
            int_to_buffer(node.byte_range)
        ])

        return [
            resolve_branch_proofs(node.left_child, partial_proof, depth + 1),
            resolve_branch_proofs(node.right_child, partial_proof, depth + 1),
        ]

    raise NodeTypeException("Unexpected node type")


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


def int_to_buffer(note):
    buffer = b"\x00" * NOTE_SIZE
    buffer = bytearray(buffer)

    for i in range(NOTE_SIZE - 1, 0, -1):
        byte_val = note % 256
        buffer[i] = byte_val
        note = (note - byte_val) / 256

    return buffer


def buffer_to_int(buffer):
    value = 0

    for byte_val in buffer:
        value *= 256
        value += byte_val

    return value


def array_compare(a, b):
    functools.reduce(lambda x, y: x and y, map(lambda p, q: p == q, a, b), True)


def validate_path(id, dest, left_bound, right_bound, path):
    if right_bound < 0:
        return False

    if dest > right_bound:
        return validate_path(id, 0, right_bound - 1, right_bound, path)

    if dest < 0:
        return validate_path(id, 0, 0, right_bound, path)

    if len(path) == HASH_SIZE + NOTE_SIZE:
        path_data = path[0:HASH_SIZE]
        path_data_length = len(path_data)
        end_offset_buffer = path[path_data_length:path_data_length + NOTE_SIZE]

        path_data_hash = hash(
            hash(path_data),
            hash(end_offset_buffer)
        )

        result = array_compare(id, path_data_hash)

        if result:
            return ValidatedPathResult(right_bound-1, left_bound, right_bound, right_bound - left_bound)

        return False

    left = path[:HASH_SIZE]
    left_length = len(left)
    right = path[left_length: left_length + HASH_SIZE]
    right_length = len(right)
