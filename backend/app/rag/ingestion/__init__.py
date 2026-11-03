"""Reading a book: file -> pages of text -> structure -> labelled chunks.

The pure parts (extraction, structure detection, chunking) know nothing about the database;
`pipeline.py` runs them in order and stores the result.
"""
