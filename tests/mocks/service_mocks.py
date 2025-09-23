from unittest.mock import Mock
from services.base.service_factory import ServiceFactory


class MockServiceFactory:
    @staticmethod
    def setup_mocks():
        ServiceFactory.get_monday_client = Mock(return_value=Mock())
        ServiceFactory.get_sheets_client = Mock(return_value=Mock())
