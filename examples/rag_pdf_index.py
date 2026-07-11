"""Navigate a large PDF cheaply for RAG: fetch the index, then convert only the
pages that matter instead of the whole document."""

import os

from markpdf import MarkpdfClient

client = MarkpdfClient(api_key=os.environ["MARKPDF_API_KEY"])

SIGNED_URL = "https://storage.example.com/document.pdf?signature=..."

index = client.pdf_index(SIGNED_URL, filename="document.pdf")
relevant_pages = "47-58"  # decided by your app/agent from index["sections"]

markdown = client.convert_from_url(SIGNED_URL, filename="document.pdf", pages=relevant_pages)
print(markdown)
