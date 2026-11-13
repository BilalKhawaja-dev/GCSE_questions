"""
UploadLambda - Handle PDF uploads directly (no pre-signed URLs)
"""

import json
import logging
import os
import boto3
import base64
from datetime import datetime
from src.utils.security import get_cors_response_headers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
KNOWLEDGE_BUCKET = os.environ.get('KNOWLEDGE_BUCKET_NAME')

def lambda_handler(event, context):
    """Handle direct file upload to S3."""
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        file_content_base64 = body.get('file_content')
        content_type = body.get('content_type', 'application/pdf')
        
        if not filename or not file_content_base64:
            return {
                'statusCode': 400,
                'headers': get_cors_response_headers(methods='POST,OPTIONS'),
                'body': json.dumps({'error': 'Filename and file_content required'})
            }
        
        # Decode base64 file content
        file_content = base64.b64decode(file_content_base64)
        
        # Generate unique key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Determine folder based on filename
        if 'mark' in filename.lower() or 'scheme' in filename.lower():
            folder = 'mark-schemes'
        elif 'spec' in filename.lower():
            folder = 'specifications'
        elif 'paper' in filename.lower() or 'exam' in filename.lower():
            folder = 'past-papers'
        else:
            folder = 'general'
        
        key = f'{folder}/{timestamp}_{filename}'
        
        # Upload to S3
        s3_client.put_object(
            Bucket=KNOWLEDGE_BUCKET,
            Key=key,
            Body=file_content,
            ContentType=content_type
        )
        
        logger.info(f"Uploaded file: {key}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_response_headers(methods='POST,OPTIONS'),
            'body': json.dumps({
                'success': True,
                'key': key,
                'message': 'File uploaded successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_response_headers(methods='POST,OPTIONS'),
            'body': json.dumps({'error': str(e)})
        }
