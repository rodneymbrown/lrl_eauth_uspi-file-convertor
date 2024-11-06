import json
import logging
import os
import boto3
import io
from services.docx_to_xml import extract_xml_from_docx  # Assuming this function handles DOCX to XML
from services.xml_to_docx import XMLToDocxConverter

# Initialize S3 client
s3 = boto3.client('s3')

# Get environment variables
BUCKET_NAME = os.environ.get('BUCKET_NAME') 
OUTPUT_BUCKET_NAME = os.environ.get('BUCKET_NAME') #Add unique output bucket for if necessary
UPLOAD_DOCX_PATH = os.environ.get('UPLOAD_DOCX_PATH')
EXTRACTED_FOLDER = os.environ.get('EXTRACTED_FOLDER')
GENERATED_FOLDER = os.environ.get('GENERATED_FOLDER')

def lambda_handler(event, context):
    # Safely extract the HTTP method and path
    http_method = event.get('httpMethod')
    resource_path = event.get('path')
    logging.info(f"Event received: {json.dumps(event)}")

    # Dispatch based on the API resource path
    if resource_path == '/docx_to_xml' and http_method == 'POST':
        return handle_docx_to_xml(event) 
    elif resource_path == '/xml_to_docx' and http_method == 'POST':
        return handle_xml_to_docx(event)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps(
                {'error': 'Endpoint Not Found',
                'httpMethod': http_method, 
                'endpoint': resource_path,
                })
        }

def handle_docx_to_xml(event):
    try:
        # Parse the incoming request body
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'humalog-pen-pi.docx')  # Default hardcoded for testing

        if not filename:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No filename provided'})
            }

        # Step 1: Construct the S3 key for the uploaded DOCX file
        s3_key = f"{UPLOAD_DOCX_PATH}/{filename}"
        print(f"Downloading DOCX from S3 bucket: {BUCKET_NAME}, key: {s3_key}")

        # Step 2: Download the DOCX file from S3
        docx_object = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        docx_data = io.BytesIO(docx_object['Body'].read())  # Load the DOCX file into memory

        # Step 3: Define the S3 path where extracted files will be stored
        output_s3_prefix = f"{EXTRACTED_FOLDER}/{os.path.splitext('extracted')[0]}"  # Use filename (without extension) as folder

        # Step 4: Extract the DOCX contents and upload them to S3
        result = extract_xml_from_docx(BUCKET_NAME, s3_key, OUTPUT_BUCKET_NAME, output_s3_prefix)

        if result is None:
            raise Exception("Failed to extract and upload DOCX contents to S3.")

        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DOCX processed successfully and contents uploaded to S3.',
                'details': result  # You can add more details like output folder path or file count if needed
            })
        }

    except Exception as e:
        print(f"Error in handle_docx_to_xml: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Error handling DOCX upload', 'details': str(e)})
        }

def handle_xml_to_docx(event):
    try:
        # Fetch the XML file from S3
        xml_key = f"{EXTRACTED_FOLDER}/extracted/modified_document.xml"
        response = s3.get_object(Bucket=BUCKET_NAME, Key=xml_key)
        xml_content = response['Body'].read().decode('utf-8')  # Read as bytes and decode
    
        output_docx_key = f"{GENERATED_FOLDER}/document.docx"
        
        # Convert the XML to DOCX
        converter = XMLToDocxConverter(xml_content, BUCKET_NAME, output_docx_key)
        result = converter.convert_to_docx()  # No need to pass `docx_path` as the conversion and upload are handled within the method.

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'XML converted to DOCX and uploaded successfully',
                'file_url': f"https://{BUCKET_NAME}.s3.amazonaws.com/{output_docx_key}"
            })
        }

    except Exception as e:
        logging.error(f"Error handling XML to DOCX conversion: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Error handling XML to DOCX conversion', 'details': str(e)})
        }

    try:
        # Fetch the XML file from S3
        xml_key = f"{EXTRACTED_FOLDER}/extracted/modified_document.xml"
        response = s3.get_object(Bucket=BUCKET_NAME, Key=xml_key)
        xml_content = response['Body'].read().decode('utf-8')  # Read as bytes and decode
    
        ouput_docx_key = f"{GENERATED_FOLDER}/document.docx"
        # Convert the XML to DOCX
        converter = XMLToDocxConverter(xml_content, BUCKET_NAME, ouput_docx_key)
        docx_filename = 'document.docx'
        docx_path = f"/tmp/{docx_filename}"
        converter.convert_to_docx(docx_path)

        # Upload the DOCX file back to S3
        with open(docx_path, 'rb') as docx_file:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=f"{DOCX_FOLDER}/{docx_filename}",
                Body=docx_file,
                ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'XML converted to DOCX and uploaded successfully',
                'file_url': f"https://{BUCKET_NAME}.s3.amazonaws.com/{DOCX_FOLDER}/{docx_filename}"
            })
        }

    except Exception as e:
        logging.error(f"Error handling XML to DOCX conversion: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Error handling XML to DOCX conversion', 'details': str(e)})
        }