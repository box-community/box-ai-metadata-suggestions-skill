import functions_framework
from google.cloud import logging

import base64
import json
import os
from pprint import pformat
from urllib.parse import parse_qsl

import box_util

log_client = logging.Client()
logger = log_client.logger('box-ai-metadata-suggestions')

def get_file_context(body):
    
    file_context = {}

    file_context['request_id'] = body['id']
    file_context['skill_id'] = body['skill']['id']
    file_context['file_id'] = body['source']['id']
    file_context['file_name'] = body['source']['name']
    file_context['file_size'] = body['source']['size']
    file_context['file_read_token'] = body['token']['read']['access_token']
    file_context['file_write_token'] = body['token']['write']['access_token']
    
    return file_context

@functions_framework.http
def main(request):

    try:
        
        body = request.json
        body_bytes = bytes(request.get_data(as_text=True), 'utf-8')
        headers = request.headers

        file_context = get_file_context(body)

        boxsdk = box_util.box_util(
            file_context['file_read_token'],
            file_context['file_write_token'],
            logger
        )

        if not boxsdk.is_launch_safe(body_bytes,headers):
            logger.log_text("launch invalid")

            return {
                "statusCode": 403,
                "body": "Error validating launch",
                "headers": {
                    "Content-Type": "application/json",
                }
            }
        
        file_name, file_extension = os.path.splitext(file_context['file_name'])

        logger.log_text("launch valid")

        # check if template exists
        template_key = "InvoicePO"
        template_display_name = "Invoices & POs"
        logger.log_text(f"get template by key")
        template = boxsdk.get_template_by_key(template_key)

        if template:
            logger.log_text(
                f"\nMetadata template created: {template.display_name},[{template.id}]",
            )
        else:
            logger.log_text(f"create template")
            # create a metadata template
            template = boxsdk.create_invoice_po_template(
                template_key, template_display_name
            )
            logger.log_text(
                f"\nMetadata template created: {template.display_name},[{template.id}]",
            )

        logger.log_text(f"get metadata")
        # get metadata for a file
        existing_metadata = boxsdk.get_file_metadata(
            file_context['file_id'], template_key
        )
        if existing_metadata is not None:
            logger.log_text(f"\nMetadata for file: {existing_metadata}")
        else:
            logger.log_text(f"\nNo Metadata associated with this file")

        suggestions = boxsdk.get_metadata_suggestions_for_file(
            file_context['file_id'], template_key
        )
        logger.log_text(f"Suggestions: {suggestions.suggestions}")
        metadata = suggestions.suggestions
        logger.log_text(f"metadata suggestion {metadata}")
        boxsdk.apply_template_to_file(
            file_context['file_id'],
            template_key,
            metadata,
            existing_metadata
        )

        return {
            "statusCode": 200,
            "body": "Metadata successfully processed",
            "headers": {
                "Content-Type": "application/json",
            }
        }
        
    except Exception as e:
        logger.log_text(f"skill: Exception: {e}")

        return {
            'statusCode' : 500,
            'body' : str(e),
            "headers": {
                "Content-Type": "text/plain"
            }
        }
