import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.lib.kis.client import KISWsClient
from app.lib.kis.model import (
    RealtimeQuoteResponse,
)


class TestKISWsClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock config read_data
        self.patcher_read_data = patch("app.lib.kis.client.read_data")
        self.mock_read_data = self.patcher_read_data.start()
        self.mock_read_data.side_effect = self._mock_read_data

        # Mock config save_data
        self.patcher_save_data = patch("app.lib.kis.client.save_data")
        self.mock_save_data = self.patcher_save_data.start()

        # Mock CSSWebSocket
        self.patcher_ws = patch("app.lib.kis.client.CSSWebSocket")
        self.mock_ws_class = self.patcher_ws.start()
        self.mock_ws_instance = self.mock_ws_class.return_value
        self.mock_ws_instance.start = AsyncMock()
        self.mock_ws_instance.stop = AsyncMock()
        self.mock_ws_instance.publish_to_subscribers = AsyncMock()

        # Mock http post
        self.patcher_post = patch("app.lib.kis.client.post", new_callable=AsyncMock)
        self.mock_post = self.patcher_post.start()

        self.ws_client = KISWsClient(env="V")

    def tearDown(self):
        self.patcher_read_data.stop()
        self.patcher_save_data.stop()
        self.patcher_ws.stop()
        self.patcher_post.stop()

    def _mock_read_data(self, key):
        data = {
            "virtual_app_key": "v_app_key",
            "virtual_app_secret": "v_app_secret",
            "virtual_account": "12345678",
            "virtual_prod": "01",
            "ws_token": "old_ws_token",
        }
        return data.get(key)

    async def test_load_websocket_approval_key_valid(self):
        # Key already exists
        response = await self.ws_client.load_websocket_approval_key()
        self.assertEqual(response.approval_key, "old_ws_token")
        self.mock_post.assert_not_called()

    async def test_load_websocket_approval_key_new(self):
        # Force reload
        self.ws_client.approval_key = None

        mock_resp = {
            "approval_key": "new_ws_token",
        }
        self.mock_post.return_value = mock_resp

        response = await self.ws_client.load_websocket_approval_key()
        self.assertEqual(response.approval_key, "new_ws_token")
        self.mock_post.assert_called_once()
        self.mock_save_data.assert_any_call("ws_token", "new_ws_token")

    async def test_start(self):
        await self.ws_client.start()
        self.mock_ws_instance.start.assert_called_once()

    async def test_stop(self):
        await self.ws_client.stop()
        self.mock_ws_instance.stop.assert_called_once()

    def test_register_price_realtime(self):
        self.ws_client.register_price_realtime(["005930"])
        self.mock_ws_instance.add_message.assert_called()
        self.mock_ws_instance.send_message.assert_called()

    async def test_message_handler_quote(self):
        # Mocking _process_websocket_message is easier than providing raw string
        mock_parsed = MagicMock(spec=RealtimeQuoteResponse)
        mock_parsed.tr_key = "005930"

        with patch.object(
            self.ws_client, "_process_websocket_message", return_value=({}, mock_parsed)
        ):
            await self.ws_client._message_handler("raw_message")
            self.mock_ws_instance.publish_to_subscribers.assert_called_with(
                "quote.005930", mock_parsed
            )


if __name__ == "__main__":
    unittest.main()
