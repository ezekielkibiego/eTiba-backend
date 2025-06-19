from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, NotAuthenticated, PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            "error": {
                "code": "GENERIC_ERROR",
                "message": "An error occurred.",
                "details": []
            }
        }
        error_payload = custom_response_data["error"]

        if isinstance(exc, ValidationError):
            error_payload["code"] = "VALIDATION_ERROR"
            error_payload["message"] = "Invalid input data."
            details = []
            if isinstance(exc.detail, dict):
                for field, messages in exc.detail.items():
                    if isinstance(messages, list):
                        for message in messages:
                            details.append({"field": field, "message": str(message)})
                    else:
                        details.append({"field": field, "message": str(messages)})
            elif isinstance(exc.detail, list):
                for message in exc.detail:
                    details.append({"field": "non_field_errors", "message": str(message)})
            else:
                details.append({"field": "detail", "message": str(exc.detail)})
            error_payload["details"] = details
        elif isinstance(exc, NotAuthenticated):
            error_payload["code"] = "AUTHENTICATION_FAILED"
            error_payload["message"] = "Authentication credentials were not provided or are invalid."
            if hasattr(exc, 'detail') and exc.detail:
                 error_payload["details"] = [{"field": "detail", "message": str(exc.detail)}]
        elif isinstance(exc, PermissionDenied):
            error_payload["code"] = "PERMISSION_DENIED"
            error_payload["message"] = "You do not have permission to perform this action."
            if hasattr(exc, 'detail') and exc.detail:
                 error_payload["details"] = [{"field": "detail", "message": str(exc.detail)}]
        elif isinstance(exc, NotFound):
            error_payload["code"] = "NOT_FOUND"
            error_payload["message"] = "The requested resource was not found."
            if hasattr(exc, 'detail') and exc.detail:
                 error_payload["details"] = [{"field": "detail", "message": str(exc.detail)}]
        else:
            # For other DRF handled exceptions, try to use their detail
            # The default handler might have already structured response.data
            if isinstance(response.data, dict) and 'detail' in response.data:
                error_payload["message"] = str(response.data['detail'])
                error_payload["details"] = [{"field": "detail", "message": str(response.data['detail'])}]
            elif isinstance(response.data, list):
                 error_payload["details"] = [{"field": "detail", "message": str(item)} for item in response.data]
            elif isinstance(response.data, str): # Should ideally be caught by specific handlers above
                 error_payload["details"] = [{"field": "detail", "message": response.data}]


        response.data = custom_response_data
    elif response is None: # Exception was not handled by DRF's default handler
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        custom_response_data = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "A server error occurred. Please try again later.",
                # Avoid exposing raw exception details in production for non-DRF errors
                "details": [{"field": "unexpected_error", "message": "An unexpected error occurred."}]
            }
        }
        if settings.DEBUG: # Provide more detail in DEBUG mode
            custom_response_data["error"]["details"][0]["message"] = str(exc)

        return Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response

