import unittest
from unittest.mock import MagicMock

import botocore
import requests

from lambdas.get_gtfs_data.main import is_retryable_exception, lambda_handler

class TestIsRetryableException(unittest.TestCase):
    """Class for testing is_retryable_exception method."""

    def test_retryable_aws_error(self):
        """Test a retryable botocore ClientError with InternalServerError."""
        error_response = {'Error': {'Code': 'InternalServerError'}}
        client_error = botocore.exceptions.ClientError(error_response, 'OperationName')
        self.assertTrue(is_retryable_exception(e=client_error))


    def test_non_retryable_aws_error(self):
        """Test a non-retryable botocore ClientError with a different error code."""
        error_response = {'Error': {'Code': 'AccessDenied'}}
        client_error = botocore.exceptions.ClientError(error_response, 'OperationName')
        self.assertFalse(is_retryable_exception(e=client_error))


    def test_retryable_http_error(self):
        """Test a retryable requests HTTPError with status code 502."""
        response_mock = MagicMock()
        response_mock.status_code = 502
        http_error = requests.exceptions.HTTPError(response=response_mock)
        self.assertTrue(is_retryable_exception(e=http_error))


    def test_non_retryable_http_error(self):
        """Test a non-retryable requests HTTPError with status code 404."""
        response_mock = MagicMock()
        response_mock.status_code = 404
        http_error = requests.exceptions.HTTPError(response=response_mock)
        self.assertFalse(is_retryable_exception(e=http_error))

    def test_non_retryable_other_exception(self):
        """Test an exception that is neither ClientError nor HTTPError."""
        other_exception = ValueError('Some other exception')
        self.assertFalse(is_retryable_exception(e=other_exception))
