import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.app.core.config import CUSTOMER_TYPE, TR
from backend.app.lib.kis.client import KISWsClient
from backend.app.lib.kis.model import (
    KISWebSocketHeader,
    KISWebSocketInput,
    RealtimeExecutionResponse,
    RealtimeQuoteResponse,
)


class TestKISWsClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Patch external dependencies
        self.mock_read_data = patch("backend.app.core.config.read_data").start()
        self.mock_save_data = patch("backend.app.core.config.save_data").start()
        self.mock_post = patch("backend.app.core.http.post").start()

        # Mock KIS Property values
        self.mock_read_data.side_effect = self._mock_read_data_side_effect

        self.ws_client = KISWsClient(env="V")  # Test in virtual environment

    async def asyncTearDown(self):
        patch.stopall()  # Stop all active patches

    def _mock_read_data_side_effect(self, key):
        if key == "virtual_app_key":
            return "mock_app_key"
        if key == "virtual_app_secret":
            return "mock_app_secret"
        if key == "virtual_account":
            return "mock_account_num"
        if key == "ws_token":
            # Return an existing ws_token for valid scenario
            if self._testMethodName == "test_load_websocket_approval_key_valid":
                return "existing_approval_key"
            return None # For new token scenario
        if key == "app_key":
            return "mock_app_key"
        if key == "app_secret":
            return "mock_app_secret"
        return None

    async def test_load_websocket_approval_key_valid(self):
        """기존에 유효한 웹소켓 접속 키가 있을 때 다시 발급받지 않는지 테스트"""
        # _mock_read_data_side_effect에서 이 테스트를 위해 기존 키를 반환하도록 설정
        response = await self.ws_client.load_websocket_approval_key()
        assert response.rt_cd == "0"
        assert response.msg1 == "Valid Approval Key"
        assert response.approval_key == "existing_approval_key"
        self.mock_post.assert_not_called()  # 유효한 키이므로 API 호출 없음

    async def test_load_websocket_approval_key_new(self):
        """웹소켓 접속 키가 없을 때 새로 발급받아 저장하는지 테스트"""
        # _mock_read_data_side_effect에서 이 테스트를 위해 None을 반환하도록 설정
        mock_response_json = {
            "approval_key": "new_mock_ws_token",
            "approval_key_token_expired": (
                datetime.now() + timedelta(hours=1)
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "expires_in": 3600,
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다.",
        }
        self.mock_post.return_value = mock_response_json

        response = await self.ws_client.load_websocket_approval_key()
        assert response.rt_cd == "0"
        assert response.approval_key == "new_mock_ws_token"
        self.mock_post.assert_called_once()  # 키가 없으므로 API 호출 발생
        self.mock_save_data.assert_called_once_with("ws_token", "new_mock_ws_token")

    def test_send_websocket_request_quote(self):
        """실시간 호가 구독 요청 메시지 생성 테스트"""
        self.ws_client.approval_key = "mock_ws_token"
        stock_code = "005930"
        tr_id = self.ws_client.TR.TR_KS_RT_PRICE_R.value
        tr_type = "2"

        expected_header = KISWebSocketHeader(
            approval_key="mock_ws_token", custtype=CUSTOMER_TYPE, tr_type=tr_type,
        ).model_dump(by_alias=True)
        expected_body = {"input": KISWebSocketInput(tr_id=tr_id, tr_key=stock_code).model_dump()}
        expected_request = {
            "header": expected_header,
            "body": expected_body,
            "REQUSET_TYPE": "0",
        }

        request_message = self.ws_client.subscribe_realtime_quote(stock_code)
        parsed_message = json.loads(request_message)

        assert parsed_message == expected_request

    def test_subscribe_realtime_execution(self):
        """실시간 체결 통보 구독 요청 메시지 생성 테스트 (모의투자) """
        self.ws_client.approval_key = "mock_ws_token"
        account_num = "mock_account_num"
        # KISWsClient는 env에 따라 TR_ID를 선택하므로, V 환경을 가정함
        tr_id = TR.TR_KS_ORDER_CHECK_V.value
        tr_type = "1"

        expected_header = KISWebSocketHeader(
            approval_key="mock_ws_token", custtype=CUSTOMER_TYPE, tr_type=tr_type,
        ).model_dump(by_alias=True)
        expected_body = {"input": KISWebSocketInput(tr_id=tr_id, tr_key=account_num).model_dump()}
        expected_request = {
            "header": expected_header,
            "body": expected_body,
            "REQUSET_TYPE": "0",
        }

        request_message = self.ws_client.subscribe_realtime_execution(account_num)
        parsed_message = json.loads(request_message)

        assert parsed_message == expected_request

    def test_unsubscribe_realtime_data(self):
        """실시간 데이터 구독 해지 요청 메시지 생성 테스트"""
        self.ws_client.approval_key = "mock_ws_token"
        tr_id = TR.TR_KS_RT_PRICE_R.value
        tr_key = "005930"
        tr_type = "2"

        expected_header = KISWebSocketHeader(
            approval_key="mock_ws_token", custtype=CUSTOMER_TYPE, tr_type=tr_type,
        ).model_dump(by_alias=True)
        expected_body = {"input": KISWebSocketInput(tr_id=tr_id, tr_key=tr_key).model_dump()}
        expected_request = {
            "header": expected_header,
            "body": expected_body,
            "REQUSET_TYPE": "1",  # Unsubscribe type
        }

        request_message = self.ws_client.unsubscribe_realtime_data(
            tr_id, tr_key, tr_type,
        )
        parsed_message = json.loads(request_message)

        assert parsed_message == expected_request

    def test_process_websocket_message_quote_parsing(self):
        """실시간 호가 메시지 파싱 테스트"""
        tr_id = TR.TR_KS_RT_PRICE_R.value  # H0STASP0
        tr_key = "005930"

        sample_data_part = (
            "005930^70000^2^1000^1.45^"  # stck_shrn_iscd, stck_prpr, prdy_vrss_sign, prdy_vrss, prdy_ctrt
            "70010^70000^100^200^"  # askp1, bidp1, askp_rsqn1, bidp_rsqn1
            "70020^69990^150^250^"  # askp2, bidp2, askp_rsqn2, bidp_rsqn2
            "70030^69980^200^300^"  # askp3, bidp3, askp_rsqn3, bidp_rsqn3
            "70040^69970^250^350^"  # askp4, bidp4, askp_rsqn4, bidp_rsqn4
            "70050^69960^300^400^"  # askp5, bidp5, askp_rsqn5, bidp_rsqn5
            "0^0^0^0^" * 5
            + "1000^1500^1000000^70000000000^100"  # total_askp_rsqn, total_bidp_rsqn, ovrs_vol, ovrs_tr_pbmn, chgh_cnt
        )

        sample_header = {
            "ht_id": tr_id,
            "tr_id": tr_id,
            "tr_key": tr_key,
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다.",
        }
        sample_message = f"{json.dumps(sample_header)}|{sample_data_part}"

        header, response = self.ws_client._process_websocket_message(sample_message)

        assert isinstance(response, RealtimeQuoteResponse)
        assert response.tr_id == tr_id
        assert response.tr_key == tr_key
        assert response.output.stck_prpr == 70000
        assert response.output.askp1 == 70010
        assert response.output.total_bidp_rsqn == 1500
        assert header["tr_id"] == tr_id

    async def test_process_websocket_message_execution_parsing(self):
        """실시간 체결 통보 메시지 파싱 테스트"""
        tr_id = TR.TR_KS_ORDER_CHECK_V.value  # H0STCNI9 (Virtual Execution)
        account_num = "mock_account_num"  # Use the mocked account number

        sample_data_part = (
            "1^"  # trade_type (1: 매도)
            "0000000001^"  # odno
            "0000000000^"  # orgn_odno
            "005930^"  # iscd
            "70000^"  # ord_unpr
            "10^"  # ord_qty
            "090000^"  # ord_tmd
            "10^"  # ccld_qty
            "70000^"  # ccld_prc
            "090005^"  # ccld_tmd
            "0^"  # rmn_qty
            "삼성전자^"  # prdt_name
            "01^"  # sll_buy_dvsn_cd (01: 매도)
            "00"  # ord_dvsn_cd (00: 지정가)
        )

        sample_header = {
            "ht_id": tr_id,
            "tr_id": tr_id,
            "tr_key": account_num,
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다.",
        }
        sample_message = f"{json.dumps(sample_header)}|{sample_data_part}"

        header, response = self.ws_client._process_websocket_message(sample_message)

        assert isinstance(response, RealtimeExecutionResponse)
        assert response.tr_id == tr_id
        assert response.tr_key == account_num
        assert response.output.iscd == "005930"
        assert response.output.ccld_qty == 10
        assert header["tr_id"] == tr_id

    async def test_process_websocket_message_control(self):
        """제어 메시지 파싱 테스트"""
        sample_message = json.dumps({"header": {"rt_cd": "0", "msg_cd": "KISA0000", "msg1": "PING"}})
        header, response = self.ws_client._process_websocket_message(sample_message)
        assert header["msg1"] == "PING"
        assert response is None

    async def test_process_websocket_message_invalid_json(self):
        """유효하지 않은 JSON 메시지 파싱 테스트"""
        invalid_message = "this is not json"
        header, response = self.ws_client._process_websocket_message(invalid_message)
        assert header == {}
        assert response is None


if __name__ == "__main__":
    unittest.main()
