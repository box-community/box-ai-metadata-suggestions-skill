import os
import datetime
import json
from typing import Dict, List

from box_sdk_gen.client import BoxClient
from box_sdk_gen.developer_token_auth import BoxDeveloperTokenAuth
from box_sdk_gen.jwt_auth import BoxJWTAuth, JWTConfig
    
from box_sdk_gen.utils import ByteStream

from box_sdk_gen.fetch import APIException

from box_sdk_gen.schemas import MetadataTemplate

from box_sdk_gen.managers.metadata_templates import (
    CreateMetadataTemplateSchemaFieldsArg, #CreateMetadataTemplateFields,
    CreateMetadataTemplateSchemaFieldsArgTypeField, #CreateMetadataTemplateFieldsTypeField,
    CreateMetadataTemplateSchemaFieldsArgOptionsField #CreateMetadataTemplateFieldsOptionsField
)

from box_sdk_gen.managers.search import (
    CreateMetadataQueryExecuteReadOrderByArg, #SearchByMetadataQueryOrderBy,
    CreateMetadataQueryExecuteReadOrderByArgDirectionField #SearchByMetadataQueryOrderByDirectionField,
)

from box_sdk_gen.managers.file_metadata import (
    CreateFileMetadataByIdScopeArg, #CreateFileMetadataByIdScope,
    UpdateFileMetadataByIdScopeArg, #UpdateFileMetadataByIdScope,
    UpdateFileMetadataByIdRequestBodyArg, #UpdateFileMetadataByIdRequestBody,
    UpdateFileMetadataByIdRequestBodyArgOpField #UpdateFileMetadataByIdRequestBodyOpField,
)

from boxsdk import OAuth2, Client, JWTAuth
from boxsdk.object.webhook import Webhook

from ai_schemas import IntelligenceMetadataSuggestions
from intelligence import IntelligenceManager

ENTERPRISE_SCOPE="enterprise_899905961"

class box_util:

    skills_error_enum = {
        "FILE_PROCESSING_ERROR": 'skills_file_processing_error',
        "INVALID_FILE_SIZE": 'skills_invalid_file_size_error',
        "INVALID_FILE_FORMAT": 'skills_invalid_file_format_error',
        "INVALID_EVENT": 'skills_invalid_event_error',
        "NO_INFO_FOUND": 'skills_no_info_found',
        "INVOCATIONS_ERROR": 'skills_invocations_error',
        "EXTERNAL_AUTH_ERROR": 'skills_external_auth_error',
        "BILLING_ERROR": 'skills_billing_error',
        "UNKNOWN": 'skills_unknown_error'
    }

    box_video_formats = set([
        '.3g2',
        '.3gp',
        '.avi',
        '.flv',
        '.m2v',
        '.m2ts',
        '.m4v',
        '.mkv',
        '.mov',
        '.mp4',
        '.mpeg',
        '.mpg',
        '.ogg',
        '.mts',
        '.qt',
        '.ts',
        '.wmv'
    ])

    def __init__(self, read_token, write_token, logger):
        self.logger = logger

        self.client_id = os.environ.get('BOX_CLIENT_ID', None)
        self.primary_key = os.environ.get('BOX_KEY_1', None)
        self.secondary_key = os.environ.get('BOX_KEY_2', None)

        self.read_client = self.get_basic_client(read_token)
        self.write_client = self.get_basic_client(write_token)

        self.old_client = self.get_old_client(read_token)

        self.client = self.jwt_auth()

        self.auth = ""

        self.logger.log_text(f"client_id: {self.client_id} key1: {self.primary_key} key2: {self.secondary_key}")
        
    def get_basic_client(self,token):

        auth = BoxDeveloperTokenAuth(token=token)

        return BoxClient(auth)
    
    def get_old_client(self,token):

        auth = OAuth2(
            client_id=self.client_id, 
            client_secret=self.primary_key,
            access_token=token
        )

        return Client(auth)

    def is_launch_safe(self, body, headers):
        self.logger.log_text(f"body {body}, headers {headers}, self.primary_key {self.primary_key}, self.secondary_key {self.secondary_key}")
        return Webhook.validate_message(body, headers, self.primary_key, self.secondary_key)
    
    def jwt_auth(self):
        try:
            jwt_config = JWTConfig.from_config_file(config_file_path='/config/box-ai-metadata-extraction-skill-jwt')
            self.auth = BoxJWTAuth(config=jwt_config)

            self.logger.log_text("instantiate client")
            self.client = BoxClient(self.auth)
        except Exception as e:
            self.logger.log_text(f"Unable to instantiate Box SDK")

    def get_template_by_key(self, template_key: str) -> MetadataTemplate:
        """Get a metadata template by key"""

        scope = "enterprise"

        if self.client is None:
            self.jwt_auth()

        try:
            template = self.client.metadata_templates.get_metadata_template_schema(
                scope=scope, template_key=template_key
            )
        except APIException as err:
            if err.status_code == 404:
                template = None
            else:
                raise err

        return template


    def delete_template_by_key(self, template_key: str):
        """Delete a metadata template by key"""

        scope = "enterprise"

        try:
            self.client.metadata_templates.delete_metadata_template(
                scope=scope, template_key=template_key
            )
        except APIException as err:
            if err.status_code == 404:
                pass
            else:
                raise err


    def create_invoice_po_template(
        self, template_key: str, display_name: str
    ) -> MetadataTemplate:
        """Create a metadata template"""

        scope = "enterprise"

        fields = []

        # Document type
        fields.append(
            CreateMetadataTemplateSchemaFieldsArg(
                type=CreateMetadataTemplateSchemaFieldsArgTypeField.ENUM,
                key="documentType",
                display_name="Document Type",
                options=[
                    CreateMetadataTemplateSchemaFieldsArgOptionsField(key="Invoice"),
                    CreateMetadataTemplateSchemaFieldsArgOptionsField(key="Purchase Order"),
                    CreateMetadataTemplateSchemaFieldsArgOptionsField(key="Unknown"),
                ],
            )
        )

        # Date
        fields.append(
            CreateMetadataTemplateSchemaFieldsArg(
                type=CreateMetadataTemplateSchemaFieldsArgTypeField.DATE,
                key="documentDate",
                display_name="Document Date",
            )
        )

        # Document total
        fields.append(
            CreateMetadataTemplateSchemaFieldsArg(
                type=CreateMetadataTemplateSchemaFieldsArgTypeField.STRING,
                key="total",
                display_name="Total: $",
                description="Total: $",
            )
        )

        # Supplier
        fields.append(
            CreateMetadataTemplateSchemaFieldsArg(
                type=CreateMetadataTemplateSchemaFieldsArgTypeField.STRING,
                key="vendor",
                display_name="Vendor",
                description="Vendor name or designation",
            )
        )

        # Invoice number
        fields.append(
            CreateMetadataTemplateSchemaFieldsArg(
                type=CreateMetadataTemplateSchemaFieldsArgTypeField.STRING,
                key="invoiceNumber",
                display_name="Invoice Number",
                description="Document number or associated invoice",
            )
        )

        # PO number
        fields.append(
            CreateMetadataTemplateSchemaFieldsArg(
                type=CreateMetadataTemplateSchemaFieldsArgTypeField.STRING,
                key="purchaseOrderNumber",
                display_name="Purchase Order Number",
                description="Document number or associated purchase order",
            )
        )

        template = self.client.metadata_templates.create_metadata_template(
            scope=scope,
            template_key=template_key,
            display_name=display_name,
            fields=fields,
        )

        return template


    def get_metadata_suggestions_for_file(
        self, file_id: str, template_key: str
    ) -> IntelligenceMetadataSuggestions:
        self.logger.log_text(f"getting metadata suggestion")
        intelligence = IntelligenceManager(logger=self.logger, auth=self.auth)
        self.logger.log_text(f"IntelligenceManager instantiated")
        return intelligence.intelligence_metadata_suggestion(
            item=file_id,
            scope=ENTERPRISE_SCOPE,
            template_key=template_key,
            confidence="experimental",
        )

    def apply_template_to_file(
        self, file_id: str, template_key: str, data: Dict[str, str], existing_data: Dict[str,str]
    ):
        self.logger.log_text(f"Applying template to file")
       # remove empty values
        data = {k: v for k, v in data.items() if v}
        self.logger.log_text(f"data {data}")

        # Check if data has a date
        if "documentDate" in data:
            try:
                date_string = data["documentDate"]
                date2 = datetime.fromisoformat(date_string)
                data["documentDate"] = (
                    date2.isoformat().replace("+00:00", "") + "Z"
                )
            except ValueError:
                data["documentDate"] = "1900-01-01T00:00:00Z"

        self.logger.log_text(f"merge data {data} and existing_data {existing_data}")
        # Merge the default data with the data
        #data = {**existing_data, **data}

        try:
            self.logger.log_text(f"create file metadata")
            self.client.file_metadata.create_file_metadata_by_id(
                file_id=file_id,
                scope=CreateFileMetadataByIdScopeArg.ENTERPRISE,
                template_key=template_key,
                request_body=data,
            )
        except APIException as error_a:
            self.logger.log_text(f"error_a {error_a}")
            if error_a.status_code == 409:
                # Update the metadata
                update_data = []
                self.logger.log_text(f"Merge data")
                for key, value in data.items():
                    update_item = UpdateFileMetadataByIdRequestBodyArg(
                        op=UpdateFileMetadataByIdRequestBodyArgOpField.ADD,
                        path=f"/{key}",
                        value=value,
                    )
                    update_data.append(update_item)
                try:
                    self.logger.log_text(f"try to update data again.")
                    self.client.file_metadata.update_file_metadata_by_id(
                        file_id=file_id,
                        scope=UpdateFileMetadataByIdScopeArg.ENTERPRISE,
                        template_key=template_key,
                        request_body=update_data,
                    )
                except APIException as error_b:
                    self.logger.log_text(
                        f"Error updating metadata: {error_b.status}:{error_b.code}:{file_id}"
                    )
            else:
                raise error_a


    def get_file_metadata(self, file_id: str, template_key: str):
        """Get file metadata"""
        try:
            metadata = self.client.file_metadata.get_file_metadata_by_id(
                file_id=file_id,
                scope=CreateFileMetadataByIdScopeArg.ENTERPRISE,
                template_key=template_key,
            )
            return metadata
        except Exception as e:
            return None

    def search_metadata(
        self,
        template_key: str,
        folder_id: str,
        query: str,
        query_params: Dict[str, str],
        order_by: List[Dict[str, str]] = None,
    ):
        """Search for files with metadata"""

        from_ = ENTERPRISE_SCOPE + "." + template_key

        if order_by is None:
            order_by = [
                CreateMetadataQueryExecuteReadOrderByArg(
                    field_key="invoiceNumber",
                    direction=CreateMetadataQueryExecuteReadOrderByArgDirectionField.ASC,
                )
            ]

        fields = [
            "type",
            "id",
            "name",
            "metadata." + from_ + ".invoiceNumber",
            "metadata." + from_ + ".purchaseOrderNumber",
        ]

        search_result = self.client.search.search_by_metadata_query(
            from_=from_,
            query=query,
            query_params=query_params,
            ancestor_folder_id=folder_id,
            order_by=order_by,
            fields=fields,
        )
        return search_result
    