def read_file_chunks(file_handler, chunk_size):
    """A generator function to read files one chunk at a time"""

    chunk = []

    for line in file_handler:
        chunk.append(line)

        if len(chunk) == chunk_size:
            yield chunk
            chunk = []

    # don't forget to yield the last block
    if chunk:
        yield chunk
