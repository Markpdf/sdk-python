import os

from markpdf import MarkpdfClient, MarkpdfError

client = MarkpdfClient(api_key=os.environ["MARKPDF_API_KEY"])

try:
    markdown = client.convert_file("report.pdf", mode="fast", clean=True)
    print(markdown)
except MarkpdfError as exc:
    print(f"Conversion failed ({exc.status_code}): {exc}")
finally:
    client.close()
