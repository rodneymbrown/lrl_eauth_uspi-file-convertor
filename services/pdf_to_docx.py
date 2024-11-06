import boto3
import io
from pdf2docx import Converter

# Initialize S3 client
s3 = boto3.client('s3')

# Get environment variables (make sure these are set in your Lambda or local environment)
BUCKET_NAME = os.environ.get('BUCKET_NAME')  
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER')

def pdf_to_docx(pdf_key, docx_key):
    try:
        # 1. Download PDF from S3 to memory
        pdf_object = s3.get_object(Bucket=BUCKET_NAME, Key=pdf_key)
        pdf_data = io.BytesIO(pdf_object['Body'].read())

        # 2. Convert PDF to DOCX in memory
        docx_data = io.BytesIO()  # Memory buffer for the output DOCX file
        cv = Converter(pdf_data)  # Use the in-memory PDF data
        cv.convert(docx_data, start=0, end=None)  # Convert entire PDF to DOCX
        cv.close()

        # 3. Upload the DOCX file to S3
        docx_data.seek(0)  # Go back to the start of the buffer before uploading
        s3.put_object(Bucket=BUCKET_NAME, Key=docx_key, Body=docx_data.getvalue(), ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

        print(f"Converted DOCX uploaded to s3://{BUCKET_NAME}/{docx_key}")

    except Exception as e:
        print(f"Error during PDF to DOCX conversion: {e}")
        return None

# Usage example
pdf_key = f"{UPLOAD_FOLDER}/document.pdf"  # S3 key for the input PDF
docx_key = f"{UPLOAD_FOLDER}/pdf2docx.docx"  # S3 key for the output DOCX

pdf_to_docx(pdf_key, docx_key)
