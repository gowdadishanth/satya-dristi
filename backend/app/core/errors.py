from fastapi import HTTPException, status

class SatyaDristiError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None):
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": message,
                "details": details or {}
            }
        )

class InvalidLocationError(SatyaDristiError):
    def __init__(self, message: str = "Invalid coordinates or location geometry provided.", details: dict = None):
        super().__init__("INVALID_LOCATION", message, status.HTTP_400_BAD_REQUEST, details)

class InvalidAOIError(SatyaDristiError):
    def __init__(self, message: str = "Area of Interest (AOI) geometry is invalid or out of acceptable bounds.", details: dict = None):
        super().__init__("INVALID_AOI", message, status.HTTP_400_BAD_REQUEST, details)

class NoSceneFoundError(SatyaDristiError):
    def __init__(self, message: str = "No satellite scenes found matching the specified criteria.", details: dict = None):
        super().__init__("NO_SCENE_FOUND", message, status.HTTP_404_NOT_FOUND, details)

class NoSuitableImageryError(SatyaDristiError):
    def __init__(self, message: str = "No suitable imagery available (e.g., cloud cover too high or missing bands).", details: dict = None):
        super().__init__("NO_SUITABLE_IMAGERY", message, status.HTTP_404_NOT_FOUND, details)

class SceneIncompatibleError(SatyaDristiError):
    def __init__(self, message: str = "Selected scenes/images are incompatible (mismatched CRS, spatial extents, or temporal resolution).", details: dict = None):
        super().__init__("SCENE_INCOMPATIBLE", message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)

class ImageRetrievalFailedError(SatyaDristiError):
    def __init__(self, message: str = "Failed to retrieve imagery from Earth observation provider.", details: dict = None):
        super().__init__("IMAGE_RETRIEVAL_FAILED", message, status.HTTP_502_BAD_GATEWAY, details)

class ModelUnavailableError(SatyaDristiError):
    def __init__(self, message: str = "Required remote sensing model is currently unavailable or resource constrained.", details: dict = None):
        super().__init__("MODEL_UNAVAILABLE", message, status.HTTP_503_SERVICE_UNAVAILABLE, details)

class AnalysisFailedError(SatyaDristiError):
    def __init__(self, message: str = "Remote-sensing model analysis failed during processing.", details: dict = None):
        super().__init__("ANALYSIS_FAILED", message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)

class InsufficientEvidenceError(SatyaDristiError):
    def __init__(self, message: str = "The provided imagery contains insufficient evidence to reliably answer the query.", details: dict = None):
        super().__init__("INSUFFICIENT_EVIDENCE", message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)

class ReportGenerationFailedError(SatyaDristiError):
    def __init__(self, message: str = "Failed to generate report PDF or export JSON.", details: dict = None):
        super().__init__("REPORT_GENERATION_FAILED", message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)

class UnauthorizedError(SatyaDristiError):
    def __init__(self, message: str = "Authentication required. Missing or invalid Firebase ID token.", details: dict = None):
        super().__init__("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED, details)

class ForbiddenError(SatyaDristiError):
    def __init__(self, message: str = "You do not have permission to access this resource.", details: dict = None):
        super().__init__("FORBIDDEN", message, status.HTTP_403_FORBIDDEN, details)

class NotFoundError(SatyaDristiError):
    def __init__(self, message: str = "The requested resource was not found.", details: dict = None):
        super().__init__("NOT_FOUND", message, status.HTTP_404_NOT_FOUND, details)

class PayloadTooLargeError(SatyaDristiError):
    def __init__(self, message: str = "Uploaded file exceeds maximum allowed size.", details: dict = None):
        super().__init__("PAYLOAD_TOO_LARGE", message, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, details)

class ValidationError(SatyaDristiError):
    def __init__(self, message: str = "Validation failed for request parameters or payload.", details: dict = None):
        super().__init__("VALIDATION_ERROR", message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)
