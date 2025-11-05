async def format_oracle_response(oracle_data: dict) -> str:
    """
    Takes an AI Oracle data dictionary and formats it
    into a human-readable string.
    """

    # Use .get() to safely access keys, providing a default
    # value if the key doesn't exist.
    title = oracle_data.get('title', 'No Title Provided')
    purpose = oracle_data.get('plain_language_purpose', 'No Purpose Provided')
    details = oracle_data.get('data_usage_details', 'No Details Provided')

    # Use a triple-quoted f-string to build the multi-line output
    return f"""
    AI ORACLE REQUEST\n


    Title: {title}\n

    Purpose: {purpose}\n

    Data Usage Details: {details}\n

    --------------------------------------------------
    """
