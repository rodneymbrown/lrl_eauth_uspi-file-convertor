import zipfile
import boto3
import io
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import QName

s3 = boto3.client('s3')

class XMLToDocxConverter:
    """Class to convert an XML structure back into a DOCX file using S3."""

    def __init__(self, xml_content, s3_output_bucket, s3_output_key):
        """Initialize with the given XML content and S3 output location."""
        self.xml_content = xml_content
        self.s3_output_bucket = s3_output_bucket
        self.s3_output_key = s3_output_key
        self.namespaces = self.extract_namespaces()
        self.output_buffer = io.BytesIO()  # In-memory buffer for the DOCX file structure

    def extract_namespaces(self):
        """Extract namespaces dynamically from the provided XML content."""
        namespaces = {}
        root = ET.fromstring(self.xml_content)
        for ns in root.attrib:
            if "xmlns" in ns:
                prefix = ns.split("}")[0].split("{")[-1] if "}" in ns else ns.replace("xmlns:", "")
                namespaces[prefix] = root.attrib[ns]
        return namespaces

    def create_docx_structure(self):
        """Create the basic DOCX folder structure in memory."""
        self.zipfile = zipfile.ZipFile(self.output_buffer, 'w')

        # Add folders necessary for a DOCX file
        self.zipfile.writestr('_rels/.rels', self.generate_rels_content())
        self.zipfile.writestr('word/_rels/document.xml.rels', self.generate_document_rels_content())
        self.zipfile.writestr('docProps/core.xml', self.generate_core_properties())
        self.zipfile.writestr('[Content_Types].xml', self.generate_content_types())
        self.zipfile.writestr('word/document.xml', self.xml_content)

    def generate_rels_content(self):
        """Generate the _rels/.rels file content."""
        rels_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
'''
        return rels_content

    def generate_document_rels_content(self):
        """Generate the word/_rels/document.xml.rels file dynamically."""
        document_rels_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
'''
        for prefix, uri in self.namespaces.items():
            if 'officeDocument' in uri or 'wordprocessingml' in uri:
                document_rels_content += f'    <Relationship Id="rId{prefix}" Type="{uri}" Target="word/document.xml"/>\n'

        document_rels_content += '</Relationships>'
        return document_rels_content

    def generate_core_properties(self):
        """Generate the core.xml file containing document properties with proper namespaces."""
        core_props_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <dc:title>Rebuilt Document</dc:title>
    <dc:creator>Auto-generated</dc:creator>
    <cp:lastModifiedBy>Auto-generator</cp:lastModifiedBy>
    <dcterms:created xsi:type="dcterms:W3CDTF">2024-09-07T12:00:00Z</dcterms:created>
    <dcterms:modified xsi:type="dcterms:W3CDTF">2024-09-07T12:00:00Z</dcterms:modified>
</cp:coreProperties>
'''
        return core_props_content

    def generate_content_types(self):
        """Generate the [Content_Types].xml file needed for DOCX packaging."""
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>
'''
        return content_types

    def convert_to_docx(self):
        """Main method to convert the XML back into a DOCX file and upload it to S3."""
        # Create the folder structure and add XML contents
        self.create_docx_structure()

        # Close the in-memory zip file
        self.zipfile.close()

        # Upload the ZIP file as DOCX to S3
        self.output_buffer.seek(0)  # Move to the start of the buffer
        s3.put_object(Bucket=self.s3_output_bucket, Key=self.s3_output_key, Body=self.output_buffer.getvalue(), ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

        return {
            'message': f"Converted DOCX uploaded successfully to s3://{self.s3_output_bucket}/{self.s3_output_key}"
        }

# Example Usage
# def lambda_handler(event, context):
#     s3_bucket = 'your-s3-bucket'
#     xml_key = 'path/to/xml/document.xml'
#     output_docx_key = 'path/to/output/document.docx'

    # Fetch the XML content from S3
    # xml_obj = s3.get_object(Bucket=s3_bucket, Key=xml_key)
    # xml_content = xml_obj['Body'].read().decode('utf-8')

    # Initialize the converter with the XML content and output S3 details
    # converter = XMLToDocxConverter(xml_content, s3_bucket, output_docx_key)

    # Convert the XML to DOCX and upload to S3
    # result = converter.convert_to_docx()

    # return result
