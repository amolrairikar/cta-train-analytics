from functools import wraps
import io
import logging
import os
from typing import Any, Dict
import zipfile

import backoff
import boto3
import botocore
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger('cta-train-analytics-fetch-gtfs-data')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def is_retryable_exception(e: botocore.exceptions.ClientError | requests.exceptions.HTTPError) -> bool:
    """Checks if the returned exception is retryable."""
    if isinstance(e, botocore.exceptions.ClientError):
        return e.response['Error']['Code'] in [
            'InternalServerError'
        ] 
    elif isinstance(e, requests.exceptions.HTTPError):
        return e.response.status_code in [
            429, 500, 501, 502, 503, 504
        ]
    return False


def backoff_on_client_error(func):
    """Reusable decorator to retry API calls for server errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        instance_or_class = None

        # If the function is a method, extract `self` or `cls`
        if args and hasattr(args[0], func.__name__):
            instance_or_class, *args = args

        @backoff.on_exception(
            backoff.expo,
            (botocore.exceptions.ClientError, requests.exceptions.HTTPError),
            max_tries=3,
            giveup=lambda e: not is_retryable_exception(e),
            on_success=lambda details: logger.info(f"Success after {details['tries']} tries"),
            on_giveup=lambda details: logger.info(f"Giving up after {details['tries']} tries"),
            on_backoff=lambda details: logger.info(f"Backing off after {details['tries']} tries due to {details['exception']}")
        )
        def retryable_call(*args, **kwargs):
            if instance_or_class:
                return func(instance_or_class, *args, **kwargs)  # Call method
            return func(*args, **kwargs)  # Call standalone function

        return retryable_call(*args, **kwargs)

    return wrapper


@backoff_on_client_error
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler function for the Lambda fetching GTFS data."""
    # Log basic information about the Lambda function
    logger.info('Begin Lambda execution')
    logger.info(f'Lambda request ID: {context.aws_request_id}')
    logger.info(f'Lambda function name: {context.function_name}')
    logger.info(f'Lambda function version: {context.function_version}')
    logger.info(f'Event: {event}')

    logger.info('Fetching GTFS zip data')
    url = 'https://www.transitchicago.com/downloads/sch_data/google_transit.zip'
    response = requests.get(url=url)
    response.raise_for_status()
    logger.info('Successfully retrieved GTFS zip data')

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        logger.info('Files in downloaded zip: %s', z.namelist())
        for filename in z.namelist():
            if filename == 'stops.txt':
                logger.info('Found stops.txt file')
                file_data = z.read(filename).decode(encoding='utf-8')
                s3 = boto3.client('s3')
                s3.put_object(
                    Bucket=os.environ['S3_BUCKET'],
                    Key=filename,
                    Body=file_data
                )
                logger.info('Successfully wrote stops.txt to S3')
                return {
                    'statusCode': 200,
                    'body': 'Download and save to S3 successful.'
                }
        raise Exception('Did not find stops.txt file')
