import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from backend.app.lib.kis.client import KISClient


class TestKISClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Patch external dependencies
        self.mock_read_data = patch("backend.app.core.config.read_data").start()
        self.mock_save_data = patch("backend.app.core.config.save_data").start()
        self.mock_post = patch("backend.app.core.http.post").start()
        self.mock_get = patch("backend.app.core.http.get").start()

        # Mock KIS Property values
        self.mock_read_data.side_effect = self._mock_read_data_side_effect

        self.client = KISClient(env="V")  # Test in virtual environment

        # Mock hashing method, as it's an internal dependency of KISClient
        # If hashing were an external dependency (e.g., in another module), it would be patched similarly
        self.client.hashing = AsyncMock(return_value="mock_hash_key")

    async def asyncTearDown(self):
        patch.stopall() # Stop all active patches

    def _mock_read_data_side_effect(self, key):
        if key == "virtual_app_key":
            return "mock_app_key"
        if key == "virtual_app_secret":
            return "mock_app_secret"
        if key == "virtual_account":
            return "mock_account_num"
        if key == "auth_token":
            return "mock_auth_token"
        if key == "token_type":
            return "Bearer"
        if key == "expired_time":
            # Return an expired time to ensure token refresh is triggered for test_load_auth_token_expired
            if self._testMethodName == "test_load_auth_token_expired":
                return (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            # For other tests, return a valid future time
            return (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        if key == "ws_token":
            return "mock_ws_token"
        # Ensure app_key and app_secret are explicitly returned for KISRequestHeader validation
        if key == "app_key":
            return "mock_app_key"
        if key == "app_secret":
            return "mock_app_secret"
        return None

    async def test_load_auth_token_valid(self):
        """기존에 유효한 토큰이 있을 때 토큰을 다시 로드하지 않는지 테스트"""
        # setUp에서 이미 유효한 토큰이 설정되도록 read_data를 모의(mock)했음
        response = await self.client.load_auth_token()
        assert response.rt_cd == "0"
        assert response.msg1 == "Valid Token"
        assert response.access_token == "mock_auth_token"
        self.mock_post.assert_not_called()  # 유효한 토큰이므로 API 호출 없음

    async def test_load_auth_token_expired(self):
        """토큰이 만료되었을 때 새 토큰을 발급받아 저장하는지 테스트"""
        # _mock_read_data_side_effect에서 이 테스트를 위해 만료된 시간을 반환하도록 설정
        mock_response_json = {
            "access_token": "new_mock_auth_token",
            "access_token_token_expired": (
                datetime.now() + timedelta(hours=1)
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "expires_in": 3600,
            "token_type": "Bearer",
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다.",
        }
        self.mock_post.return_value = mock_response_json

        response = await self.client.load_auth_token()
        assert response.rt_cd == "0"
        assert response.access_token == "new_mock_auth_token"
        self.mock_post.assert_called_once()  # 만료되었으므로 API 호출 발생
        # save_data가 auth_token, token_type, expired_time 순서로 호출될 것으로 예상
        self.mock_save_data.assert_any_call("auth_token", "new_mock_auth_token")
        self.mock_save_data.assert_any_call("token_type", "Bearer")
        self.mock_save_data.assert_any_call("expired_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) # 대략적인 시간 비교
        assert self.mock_save_data.call_count >= 3

    async def test_dispose_auth_token(self):
        """접근 토큰을 폐기하고 저장된 정보를 초기화하는지 테스트"""
        self.client.auth_token = "mock_auth_token"  # 테스트를 위해 유효한 토큰 설정
        mock_response_json = {
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다.",
        }
        self.mock_post.return_value = mock_response_json

        response = await self.client.dispose_auth_token()
        assert response.rt_cd == "0"
        assert response.msg1 == "정상 처리 되었습니다."
        self.mock_post.assert_called_once()  # API 호출 발생
        # save_data가 auth_token, token_type, expired_time 순서로 빈 값으로 호출될 것으로 예상
        self.mock_save_data.assert_any_call("auth_token", "")
        self.mock_save_data.assert_any_call("token_type", "")
        self.mock_save_data.assert_any_call("expired_time", "")
        assert self.client.auth_token == ""
        assert self.client.expired_time is None


if __name__ == "__main__":
    unittest.main()
