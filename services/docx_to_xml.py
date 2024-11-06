import zipfile
import boto3
import io
import os

s3 = boto3.client('s3')

def extract_xml_from_docx(s3_docx_bucket, s3_docx_key, s3_output_bucket, s3_output_prefix):
    """
    Extracts the DOCX file's structure, uploads all its internal components to S3,
    and preserves the folder structure (e.g., 'word/', '_rels/', 'docProps/').
    
    Parameters:
    - s3_docx_bucket: The S3 bucket where the DOCX file is stored.
    - s3_docx_key: The S3 key (path) to the DOCX file.
    - s3_output_bucket: The S3 bucket where extracted files will be uploaded.
    - s3_output_prefix: The S3 prefix (folder path) where the extracted files will be stored.
    """
    try:
        # Step 1: Download the DOCX file from S3 into an in-memory buffer
        print(f"Downloading DOCX from S3 bucket: {s3_docx_bucket}, key: {s3_docx_key}")
        docx_object = s3.get_object(Bucket=s3_docx_bucket, Key=s3_docx_key)
        
        # Check if the object has a 'Body' key to avoid KeyError
        if 'Body' not in docx_object:
            raise Exception("Failed to download DOCX file. No 'Body' in the response.")
        
        docx_data = io.BytesIO(docx_object['Body'].read())  # Load DOCX into memory
        if docx_data.getbuffer().nbytes == 0:
            raise Exception("Downloaded DOCX file is empty.")

        # Step 2: Open the DOCX file as a zip and extract all components
        with zipfile.ZipFile(docx_data, 'r') as docx:
            for file_name in docx.namelist():
                print(f"Processing file: {file_name}")

                # Read the content of each file in the DOCX structure
                try:
                    file_content = docx.read(file_name)
                except KeyError:
                    print(f"Warning: Could not read file {file_name} from the DOCX archive.")
                    continue

                # Check if file content is valid
                if not file_content:
                    print(f"Warning: File content for {file_name} is empty. Skipping upload...")
                    continue

                # Step 4: Determine the S3 key for the extracted file (preserving the folder structure)
                s3_key = f"{s3_output_prefix}/{file_name}"

                # Determine the content type based on the file extension
                content_type = 'application/xml' if file_name.endswith('.xml') else 'application/octet-stream'

                try:
                    # Step 5: Upload each file to S3, preserving the folder structure
                    s3.put_object(
                        Bucket=s3_output_bucket,
                        Key=s3_key,
                        Body=file_content,
                        ContentType=content_type
                    )
                    print(f"Uploaded {file_name} to {s3_output_bucket}/{s3_key}")
                except Exception as upload_error:
                    print(f"Error uploading {file_name} to S3: {upload_error}")

        return f"Successfully extracted and uploaded DOCX structure to S3 under {s3_output_prefix}"

    except zipfile.BadZipFile:
        print("Error: The file is not a valid DOCX (ZIP) file or is corrupt.")
        return None
    except Exception as e:
        print(f"Error during extraction: {e}")
        return None

# Example usage:
# extract_xml_from_docx('input-bucket', 'path/to/your/docx-file.docx', 'output-bucket', 'path/to/store/extracted/files')
