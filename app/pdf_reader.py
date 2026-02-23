from pypdf import PdfReader


class PDFReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def extract_text(self):
        reader = PdfReader(self.file_path)
        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

        return text
        