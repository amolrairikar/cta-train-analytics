import io
import os
import unittest
from unittest.mock import MagicMock, patch
import zipfile

import boto3
import botocore
from moto import mock_aws
import requests

from lambdas.get_gtfs_data.main import lambda_handler


class MockLambdaContext:
    """Mock class for AWS Lambda context."""

    def __init__(self):
        """Initializes mock Lambda context with constant attributes for tests."""
        self.aws_request_id = 'test-request-id'
        self.function_name = 'test-function-name'
        self.function_version = 'test-function-version'


class TestLambdaHandler(unittest.TestCase):
    """Tests the lambda handler function for get_gtfs_data/main.py."""

    def setUp(self):
        """Patch environment variables and common dependencies before each test."""
        self.mock_event = {
            'eventType': 'test-event'
        }
        self.mock_context = MockLambdaContext()
        self.env_patcher = patch.dict(
            os.environ,
            {
                'S3_BUCKET': 'test-bucket'
            }
        )
        self.env_patcher.start()


    def tearDown(self):
        """Stop all patches after each test."""
        self.env_patcher.stop()

    def _create_mock_zip(self, files):
        """Helper method to create a mock zip file."""

        mock_zip = io.BytesIO()
        with zipfile.ZipFile(mock_zip, 'w') as z:
            for filename, content in files.items():
                z.writestr(filename, content)
        mock_zip.seek(0)
        return mock_zip.getvalue()

    @mock_aws
    @patch('lambdas.get_gtfs_data.main.requests.get')
    def test_lambda_success(self, mock_requests_get):
        """Tests the happy path of the get_gtfs_data lambda handler."""
        # Initialize AWS resources to be mocked using moto
        s3 = boto3.client('s3')
        s3.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-east-2'}
        )

        # Mock the GET request response
        mock_response = MagicMock()
        mock_response.content = self._create_mock_zip(
            files={
                'agency.txt': b'mock agency',
                'stops.txt': b'mock content'
            }
        )
        mock_requests_get.return_value = mock_response

        # Call lambda handler
        response = lambda_handler(event=self.mock_event, context=self.mock_context)
        s3_response = s3.get_object(
            Bucket='test-bucket',
            Key='stops.txt'
        )

        # Assert function behaved as expected
        mock_requests_get.assert_called_once_with(
            url='https://www.transitchicago.com/downloads/sch_data/google_transit.zip'
        )
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['body'], 'Download and save to S3 successful.')

        # Assert valid object was created in S3
        assert s3_response['ResponseMetadata']['HTTPStatusCode'] == 200
        content = s3_response['Body'].read()
        assert isinstance(content, bytes)
        assert len(content) > 0

    @patch('lambdas.get_gtfs_data.main.requests.get')
    def test_missing_stops_file(self, mock_requests_get):
        """Tests the get_gtfs_data lambda handler raises an exception if the 
            stops.txt file is missing."""
        # Mock the GET request response
        mock_response = MagicMock()
        mock_response.content = self._create_mock_zip(
            files={
                'agency.txt': b'mock agency'
            }
        )
        mock_requests_get.return_value = mock_response

        # Call lambda handler
        with self.assertRaises(Exception) as context:
            response = lambda_handler(event=self.mock_event, context=self.mock_context)

        # Assert function behaved as expected
        self.assertEqual(str(context.exception), 'Did not find stops.txt file')

    @mock_aws
    @patch('lambdas.get_gtfs_data.main.requests.get')
    def test_retry_get_request(self, mock_requests_get):
        """Tests the get_gtfs_data lambda handler retries the GET request if it fails initially."""
        # Initialize AWS resources to be mocked using moto
        s3 = boto3.client('s3')
        s3.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-east-2'}
        )

        # Mock the GET request response error on first try
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        http_error = requests.exceptions.HTTPError(
            '429 Client Error: Too many requests'
        )
        http_error.response = mock_error_response
        mock_error_response.raise_for_status.side_effect = http_error

        # Mock the GET request response success on second try
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.content = self._create_mock_zip(
            files={
                'agency.txt': b'mock agency',
                'stops.txt': b'mock content'
            }
        )
        mock_success_response.raise_for_status.return_value = None

        # Combine both mocked requests
        mock_requests_get.side_effect = [
            mock_error_response,
            mock_success_response
        ]

        # Call lambda handler
        response = lambda_handler(event=self.mock_event, context=self.mock_context)
        s3_response = s3.get_object(
            Bucket='test-bucket',
            Key='stops.txt'
        )

        # Assert function behaved as expected
        mock_requests_get.assert_called_with(
            url='https://www.transitchicago.com/downloads/sch_data/google_transit.zip'
        )
        self.assertEqual(mock_requests_get.call_count, 2)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['body'], 'Download and save to S3 successful.')

        # Assert valid object was created in S3
        assert s3_response['ResponseMetadata']['HTTPStatusCode'] == 200
        content = s3_response['Body'].read()
        assert isinstance(content, bytes)
        assert len(content) > 0