from PyPDF2 import PdfReader

# Load the PDF file
reader = PdfReader("DataFormats.pdf")
text = ""

# Extract text from each page
for page in reader.pages:
    text += page.extract_text()

with open("DataFormats.txt", "w", encoding = "utf-8") as file:
    file.write(text)
