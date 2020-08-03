def read_file_chunks(file_handler, chunk_size, seek_to=0):
    """A generator function to read files one chunk at a time"""
    while True:
        data = file_handler.read(chunk_size)

        if not data:
            break

        yield data
