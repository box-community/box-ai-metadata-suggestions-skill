import base64
import hashlib
import hmac
import os
from datetime import datetime
import json
from typing import Dict, List, Optional

from box_sdk_gen.client import BoxClient
from box_sdk_gen import (
    AiExtractResponse,
    AiItemBase,
    BoxAPIError,
    BoxClient,
    BoxDeveloperTokenAuth,
    BoxJWTAuth,
    CreateAiExtractStructuredMetadataTemplate,
    CreateMetadataTemplateFields,
    CreateMetadataTemplateFieldsOptionsField,
    CreateMetadataTemplateFieldsTypeField,
    DeleteMetadataTemplateScope,
    GetFileMetadataByIdScope,
    GetMetadataTemplateScope,
    JWTConfig,
    MetadataTemplate,
    UpdateFileMetadataByIdRequestBody,
    UpdateFileMetadataByIdRequestBodyOpField,
    UpdateFileMetadataByIdScope,
    UpdateMetadataTemplateScope
)

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

    def __init__(self, read_token, write_token, logger):
        self.logger = logger

        self.client_id = os.environ.get('BOX_CLIENT_ID', None)
        self.primary_key = os.environ.get('BOX_KEY_1', None)
        self.secondary_key = os.environ.get('BOX_KEY_2', None)

        self.read_client = self._get_basic_client(read_token)
        self.write_client = self._get_basic_client(write_token)

        self.jwt_client = self._get_jwt_client()

    def _get_basic_client(self,token):

        auth = BoxDeveloperTokenAuth(token=token)

        return BoxClient(auth)
    
    def _get_jwt_client(self):

        jwt_config = JWTConfig.from_config_file(config_file_path="./metadata-extraction-jwt.json")
        auth = BoxJWTAuth(config=jwt_config)

        return BoxClient(auth=auth)
    
    def is_launch_safe(self, body, headers):
        primary_signature = self._compute_signature(body, headers, self.primary_key)
        if primary_signature is not None and hmac.compare_digest(primary_signature, headers.get('box-signature-primary')):
            return True

        if self.secondary_key:
            secondary_signature = self._compute_signature(body, headers, self.secondary_key)
            if secondary_signature is not None and hmac.compare_digest(secondary_signature, headers.get('box-signature-secondary')):
                return True
            return False

        return False
    
    def _compute_signature(self, body: bytes, headers: dict, signature_key: str) -> Optional[str]:
        """
        Computes the Hmac for the webhook notification given one signature key.

        :param body:
            The encoded webhook body.
        :param headers:
            The headers for the `Webhook` notification.
        :param signature_key:
            The `Webhook` signature key for this application.
        :return:
            An Hmac signature.
        """
        if signature_key is None:
            return None
        if headers.get('box-signature-version') != '1':
            return None
        if headers.get('box-signature-algorithm') != 'HmacSHA256':
            return None

        encoded_signature_key = signature_key.encode('utf-8')
        encoded_delivery_time_stamp = headers.get('box-delivery-timestamp').encode('utf-8')
        new_hmac = hmac.new(encoded_signature_key, digestmod=hashlib.sha256)
        new_hmac.update(body + encoded_delivery_time_stamp)
        signature = base64.b64encode(new_hmac.digest()).decode()
        return signature
    
    def get_template_by_key(self, template_key: str) -> MetadataTemplate:
        """Get a metadata template by key"""

        try:
            template = self.read_client.metadata_templates.get_metadata_template(
                scope=GetMetadataTemplateScope.ENTERPRISE.value, template_key=template_key
            )
        except BoxAPIError as err:
            if err.status == 404:
                template = None
            else:
                raise err

        return template


    def delete_template_by_key(self, template_key: str):
        """Delete a metadata template by key"""

        try:
            self.write_client.metadata_templates.delete_metadata_template(
                scope=DeleteMetadataTemplateScope.ENTERPRISE.value, template_key=template_key
            )
        except BoxAPIError as err:
            if err.status == 404:
                pass
            else:
                raise err


    def create_invoice_po_template(
        self, template_key: str, display_name: str
    ) -> MetadataTemplate:
        """Create a metadata template"""

        fields = []

        # Policy Name
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.STRING,
                key="policyName",
                display_name="Policy Name"
            )
        )

        # Policy Number
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.STRING,
                key="policyNumber",
                display_name="Policy Number",
                description="example: \"BOX-POL-15\"",
            )
        )

        # Policy Version
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.STRING,
                key="policyVersion",
                display_name="Policy Version",
                description="example: \"BOX-POL-123.52\"",
            )
        )

        # Revision
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.STRING,
                key="revision",
                display_name="Revision",
                description="Revision is a number. Example: for \"BOX-POL-123.02\", the revision is \"123.02\"",
            )
        )

        # Effective Date
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.DATE,
                key="effectiveDate",
                display_name="Effective Date",
                description="Effective date is the last signature"
            )
        )

        # Author
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.STRING,
                key="author",
                display_name="Author"
            )
        )

        # Approvers
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.STRING,
                key="approvers",
                display_name="Approvers",
                description="Names of people who signed as a string",
            )
        )

        # Status
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.ENUM,
                key="status",
                display_name="Status",
                options=[
                    CreateMetadataTemplateFieldsOptionsField(key="Approved"),
                    CreateMetadataTemplateFieldsOptionsField(key="In Review"),
                    CreateMetadataTemplateFieldsOptionsField(key="Signed"),
                    CreateMetadataTemplateFieldsOptionsField(key="Expired"),
                ],
            )
        )

        # Review Date
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.DATE,
                key="reviewDate",
                display_name="Review Date",
                description="Review Date"
            )
        )

        # Doc Owner
        fields.append(
            CreateMetadataTemplateFields(
                type=CreateMetadataTemplateFieldsTypeField.MULTISELECT,
                key="docOwner",
                display_name="Doc Owner",
                description="if the document is related to company risk, then choose \"Aaron\". If the document is related to legal policies, choose \"David\"",
                options=[
                    CreateMetadataTemplateFieldsOptionsField(key="Physical Security"),
                    CreateMetadataTemplateFieldsOptionsField(key="Enterprise Security"),
                    CreateMetadataTemplateFieldsOptionsField(key="Compliance, GRC"),
                    CreateMetadataTemplateFieldsOptionsField(key="Aaron"),
                    CreateMetadataTemplateFieldsOptionsField(key="David"),
                ],
            )
        )

        template = self.write_client.metadata_templates.create_metadata_template(
            scope=UpdateMetadataTemplateScope.ENTERPRISE.value,
            template_key=template_key,
            display_name=display_name,
            fields=fields,
        )

        return template


    def get_metadata_suggestions_for_file(
        self, file_id: str, template_key: str
    ) -> AiExtractResponse:
        print(
            f"file id {file_id} file_id_type {type(file_id)} "
        )
        return self.jwt_client.ai.create_ai_extract_structured(
            [AiItemBase(id=file_id, type="file")],
            metadata_template=CreateAiExtractStructuredMetadataTemplate(
                template_key=template_key, scope=GetMetadataTemplateScope.ENTERPRISE.value
            ),
        )

    def apply_template_to_file(
        self, file_id: str, template_key: str, data: Dict[str, str], existing_data: Dict[str,str]
    ):
        # remove empty values
        data = {k: v for k, v in data.items() if v}

        if "docOwner" in data:
            docOwner = data["docOwner"]
            if docOwner[0] != "[":
                docOwner = f"[ {docOwner}"
            
            if docOwner[-1] != "]":
                docOwner = f"{docOwner} ]"
            
            data["docOwner"] = docOwner


        self.logger.log_text(f"data {data}")

        # Check if data has a date
        if "effectiveDate" in data:
            try:
                date_string = data["effectiveDate"]
                date2 = datetime.fromisoformat(date_string).replace(hour=0).replace(minute=0).replace(second=0)
                data["effectiveDate"] = (
                    date2.isoformat().replace("+00:00", "") + "Z"
                )
            except ValueError:
                data["effectiveDate"] = "1900-01-01T00:00:00Z"

        # Check if data has a date
        if "reviewDate" in data:
            try:
                date_string = data["reviewDate"]
                date2 = datetime.fromisoformat(date_string).replace(hour=0).replace(minute=0).replace(second=0)
                data["reviewDate"] = (
                    date2.isoformat().replace("+00:00", "") + "Z"
                )
            except ValueError:
                data["reviewDate"] = "1900-01-01T00:00:00Z"

        self.logger.log_text(f"merge data {data} and existing_data {existing_data}")
        
        try:

            self.logger.log_text(f"create file metadata")
            self.write_client.file_metadata.create_file_metadata_by_id(
                file_id=file_id,
                scope=UpdateMetadataTemplateScope.ENTERPRISE,
                template_key=template_key,
                request_body=data,
            )
        except BoxAPIError as error_a:
            self.logger.log_text(f"error_a {error_a}")
            if error_a.status == 409:
                # Update the metadata
                update_data = []
                self.logger.log_text(f"Merge data")
                for key, value in data.items():
                    update_item = UpdateFileMetadataByIdRequestBody(
                        op=UpdateFileMetadataByIdRequestBodyOpField.REPLACE.value,
                        path=f"/{key}",
                        value=value,
                    )
                    update_data.append(update_item)
                try:
                    self.logger.log_text(f"try to update data again.")
                    self.write_client.file_metadata.update_file_metadata_by_id(
                        file_id=file_id,
                        scope=UpdateFileMetadataByIdScope.ENTERPRISE.value,
                        template_key=template_key,
                        request_body=update_data,
                    )
                except BoxAPIError as error_b:
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
                scope=GetFileMetadataByIdScope.ENTERPRISE,
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

        from_ = GetFileMetadataByIdScope.ENTERPRISE.value + "." + template_key

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
    