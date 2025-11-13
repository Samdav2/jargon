import aiohttp
import json
from fastapi import HTTPException, status
import logging
import os
from dotenv import load_dotenv
import asyncio
from typing import Dict, Any


load_dotenv()


BASE_URL = os.getenv("GEMINI_URL")
API_KEY = os.getenv("GEMINI_API_KEY")

if not BASE_URL or not API_KEY:
    logging.warning("GEMINI_URL or GEMINI_API_KEY not set in .env file.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIOracleService:
    """
    AI-Powered Compliance Oracle using the Gemini API.

    This service validates compliance and translates requests
    into plain language using structured JSON outputs.
    """

    async def _call_gemini_api(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Helper function to make asynchronous calls to the Gemini API,
        forcing a JSON object response matching the provided schema.
        """

        payload = {
            "contents": [
                {"parts": [{"text": user_prompt}]}
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
                "responseSchema": response_schema
            }
        }

        api_url_with_key = f"{BASE_URL}?key={API_KEY}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(api_url_with_key, json=payload, headers={'Content-Type': 'application/json'}) as response:

                    if response.status != 200:
                        logger.error(f"Gemini API Error: {response.status} {await response.text()}")
                        return {"title":"AI Oracle is currently on available", "plain_language_purpose": "Null", "data_usage_details": "Null" }

                    result = await response.json()

                    candidate = result.get("candidates", [{}])[0]
                    # Check for safety ratings
                    if candidate.get("finishReason") != "STOP":
                        safety_ratings = candidate.get("safetyRatings", [])
                        logger.warning(f"Gemini API blocked response. Reason: {candidate.get('finishReason')}, Ratings: {safety_ratings}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"AI Oracle blocked request for safety reasons: {safety_ratings}"
                        )

                    content = candidate.get("content", {}).get("parts", [{}])[0]
                    text_response = content.get("text", "").strip()

                    if not text_response:
                        logger.warning(f"Gemini API returned empty response: {result}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="AI Oracle returned an empty response."
                        )

                    try:
                        return json.loads(text_response)
                    except json.JSONDecodeError:
                        logger.error(f"Gemini API returned invalid JSON: {text_response}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="AI Oracle returned an invalid data structure."
                        )

            except aiohttp.ClientError as e:
                logger.error(f"AIOHTTP Client Error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"AI Oracle is unreachable: {e}"
                )
            except Exception as e:
                logger.error(f"Error during Gemini call: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred with the AI Oracle: {e}"
                )

    async def validate_request_compliance(self, purpose: str, data_type: str, org_name: str) -> Dict[str, Any]:
        """
        [JOB 1] Acts as an expert NDPA Auditor.
        Returns a rich JSON object with a decision and a detailed rationale.
        """

        system_prompt = (
            "You are an expert Compliance Auditor for the Nigeria Data Protection Commission (NDPC). "
            "Your sole duty is to analyze data access requests for strict compliance with the Nigeria Data Protection Act (NDPA) 2023. "
            "You must evaluate the request based on these core NDPA principles: "
            "1.  **Purpose Limitation (Section 24(1)(b)):** Is the purpose specific, legitimate, and clearly stated? "
            "2.  **Data Minimisation (Section 24(1)(c)):** Is the data requested ('data_type') adequate, relevant, and *limited to what is necessary* for the stated 'purpose'? "
            "3.  **Lawfulness (Section 25):** Does the purpose seem lawful? "
            "Your analysis must be professional, rigorous, and cite these principles. "
            "You MUST respond with only a valid JSON object matching the provided schema. Do not add any text before or after the JSON."
        )

        user_prompt = (
            f"Organization: '{org_name}'\n"
            f"Data Type Requested: '{data_type}'\n"
            f"Stated Purpose: '{purpose}'"
        )

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "is_compliant": {"type": "BOOLEAN"},
                "risk_level": {"type": "STRING", "enum": ["Low", "Medium", "High", "Critical"]},
                "rationale": {"type": "STRING"}
            },
            "required": ["is_compliant", "risk_level", "rationale"]
        }

        response_schema["properties"]["rationale"]["description"] = (
            "A full, professional explanation for the decision, citing NDPA principles. "
            "If NON-COMPLIANT, explain exactly which principle was violated and why."
        )

        response_json = await self._call_gemini_api(system_prompt, user_prompt, response_schema)

        if not response_json.get("is_compliant", False):
            logger.warning(
                f"AI Oracle rejected NON-COMPLIANT request. "
                f"Purpose: {purpose}, Data: {data_type}, Rationale: {response_json.get('rationale')}"
            )

        return response_json

    async def translate_request_for_user(self, purpose: str, data_type: str, org_name: str) -> Dict[str, str]:
        """
        [JOB 2] Acts as a "Simple Translator".
        Translates a technical request into a structured JSON object for the user's app.
        """

        system_prompt = (
            "You are a professional UX writer for a high-security Nigerian financial app (like OPay or Kuda). "
            "Your job is to translate a technical data request into a simple, clear, and friendly JSON object for the user's consent screen. "
            "The tone must be trustworthy, direct, and appropriate for a Nigerian audience. "
            "You MUST respond with only a valid JSON object matching the provided schema. Do not add any text before or after the JSON."
        )

        user_prompt = (
            f"Organization: '{org_name}'\n"
            f"Data Type Requested: '{data_type}' (e.g., 'CORE_PII' means 'Full Name, NIN, BVN', 'FINANCIALS' means 'Bank Statements')\n"
            f"Stated Purpose: '{purpose}'"
        )

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "plain_language_purpose": {"type": "STRING"},
                "data_usage_details": {"type": "STRING"}
            },
            "required": ["title", "plain_language_purpose", "data_usage_details"]
        }

        response_schema["properties"]["title"]["description"] = (
            "A short, clear title. Start directly with the organization's name. "
            "Example: 'OPay needs to see your NIN'"
        )
        response_schema["properties"]["plain_language_purpose"]["description"] = (
            "A single, simple sentence explaining *why* they need the data. "
            "Example: 'This is to verify your identity for your new account.'"
        )
        response_schema["properties"]["data_usage_details"]["description"] = (
            "A 1-2 sentence explanation of *how* the data will be used. "
            "Example: 'This is a one-time check. OPay will not store this data after verification.'"
        )

        response_json = await self._call_gemini_api(system_prompt, user_prompt, response_schema)

        return response_json
