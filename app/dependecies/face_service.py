import logging
import uuid
from fastapi import HTTPException, status
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.face import FaceSessionClient
from azure.ai.vision.face.models import (
    CreateLivenessSessionContent,
    CreateLivenessWithVerifySessionContent,
    LivenessOperationMode,
    LivenessWithVerifyImage
)
import io
from dotenv import load_dotenv
import os

load_dotenv()

AZURE_FACE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_FACE_KEY = os.getenv("AZURE_KEY_1")

logger = logging.getLogger(__name__)

class AzureFaceService:
    """
    Service for handling Face Liveness and Verification using Microsoft Azure.
    This service is critical for the Sovereign Data Exchange (SDE) platform
    to ensure high-trust, biometric identity verification.
    """

    def __init__(self):
        if not AZURE_FACE_ENDPOINT or not AZURE_FACE_KEY:
             logger.error("Azure Face credentials not set in .env")
             raise HTTPException(
                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                 detail="Face verification service is currently unavailable due to missing configuration."
             )

        self.endpoint = AZURE_FACE_ENDPOINT
        self.key = AZURE_FACE_KEY


        self.session_client = FaceSessionClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    async def create_enrollment_session(self) -> dict:
        """
        [ENROLL STEP 1] Create a "Liveness-Only" session.
        Used when a user is first registering and we need to capture
        their trusted reference photo.
        """
        try:
            logger.info("Creating Azure Liveness-Only (Enrollment) session...")

            # 'Passive' mode is smoother for the user.
            # We set 'send_results_to_client=False' for security;
            # only our backend should get the final data.
            params = CreateLivenessSessionContent(
                liveness_operation_mode=LivenessOperationMode.PASSIVE,
                device_correlation_id=str(uuid.uuid4()),
                send_results_to_client=False
            )

            session = self.session_client.create_liveness_session(params)
            logger.info(f"Enrollment Session Created. ID: {session.session_id}")

            return {
                "session_id": session.session_id,
                "auth_token": session.auth_token
            }
        except Exception as e:
            logger.error(f"Azure Enrollment Init Failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not initialize face enrollment session with provider."
            )

    async def get_enrollment_result_and_image(self, session_id: str) -> bytes:
        """
        [ENROLL STEP 3] Verify liveness and DOWNLOAD the trusted photo.
        Returns the bytes of the trusted JPEG photo if successful.
        """
        try:
            logger.info(f"Finalizing enrollment for session: {session_id}")
            result = self.session_client.get_liveness_session_result(session_id)

            # 1. Check if the session is even finished
            if result.status in ["NotStarted", "Started"]:
                 raise HTTPException(
                     status_code=status.HTTP_400_BAD_REQUEST,
                     detail="Liveness check not completed yet. Please try again in a moment."
                 )

            # 2. Check Liveness Decision
            # Azure returns 'Real', 'Spoof', or 'Unknown'. We only accept 'Real'.
            if result.liveness_decision is None or result.liveness_decision.lower() != "real":
                 logger.warning(f"Enrollment failed liveness check. Session: {session_id}, Result: {result.liveness_decision}")
                 raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Liveness check failed. Could not verify a real human presence."
                 )

            # 3. Download the Trusted Reference Image
            # This is the high-quality image Azure captured during the successful liveness check.
            # This is the *real* implementation, replacing the placeholder.
            logger.info(f"Liveness verified for {session_id}. Downloading trusted reference image...")

            # The SDK provides a stream for the image. We read it into bytes.
            image_stream = self.session_client.get_liveness_session_image(session_id)
            trusted_photo_bytes = b""
            for chunk in image_stream:
                trusted_photo_bytes += chunk

            if not trusted_photo_bytes:
                logger.error(f"Failed to download image for session {session_id}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Liveness succeeded, but failed to retrieve the trusted reference photo."
                )

            return trusted_photo_bytes

        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Azure Enrollment Result Failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="An unexpected error occurred while finalizing enrollment."
            )



    async def create_verification_session(self, reference_photo_bytes: bytes) -> dict:
        """
        [VERIFY STEP 1] Create a "Liveness + Verify" session.
        This is the completed method, replacing 'pass'.
        """
        try:
            logger.info("Creating Azure LivenessWithVerify session...")

            # We pass the trusted 'reference_photo_bytes' to Azure.
            # Azure will compare the new live scan against THIS specific photo.
            params = CreateLivenessWithVerifySessionContent(
                liveness_operation_mode=LivenessOperationMode.PASSIVE,
                device_correlation_id=str(uuid.uuid4()),
                send_results_to_client=False,
                verify_image=LivenessWithVerifyImage(
                face_image=reference_photo_bytes
                )
            )

            session = self.session_client.create_liveness_with_verify_session(params)
            logger.info(f"Verification Session Created. ID: {session.session_id}")

            return {
                "session_id": session.session_id,
                "auth_token": session.auth_token
            }

        except Exception as e:
            logger.error(f"Failed to create Azure verification session: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not initialize face verification session."
            )

    async def get_session_result(self, session_id: str) -> dict:
        """
        [VERIFY STEP 3] Get the final, definitive result from Azure.
        This is the completed method, replacing 'pass'.
        """
        try:
            logger.info(f"Querying result for verification session: {session_id}")

            # We use the specialized 'get_liveness_with_verify_session_result' method
            result = self.session_client.get_liveness_with_verify_session_result(session_id)

            # 1. Check if session is complete
            if result.status in ["NotStarted", "Started"]:
                 raise HTTPException(
                     status_code=status.HTTP_400_BAD_REQUEST,
                     detail="Verification not completed yet."
                 )

            # 2. Parse Results
            is_live = result.liveness_decision is not None and result.liveness_decision.lower() == "real"

            is_match = False
            confidence = 0.0
            if result.verify_result:
                 is_match = result.verify_result.is_identical
                 confidence = result.verify_result.match_confidence

            # 3. Final Decision
            # User is verified ONLY if they are BOTH live AND a match.
            final_decision = is_live and is_match

            decision_data = {
                "verified": final_decision,
                "details": {
                    "liveness_status": result.liveness_decision, # e.g., 'Real', 'Spoof'
                    "face_match": is_match,                      # True/False
                    "match_confidence": confidence               # e.g., 0.985
                }
            }

            if final_decision:
                logger.info(f"Session {session_id} -> VERIFIED (Conf: {confidence:.4f})")
            else:
                logger.warning(f"Session {session_id} -> FAILED. Details: {decision_data['details']}")

            return decision_data

        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Failed to get verification result: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not retrieve final verification result from provider."
            )
