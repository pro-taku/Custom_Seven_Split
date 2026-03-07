import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.lib.kis.client import KISClient


class TestKISClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock config read_data to return some default values
        self.patcher_read_data = patch("app.lib.kis.client.read_data")
        self.mock_read_data = self.patcher_read_data.start()
        self.mock_read_data.side_effect = self._mock_read_data

        # Mock config save_data
        self.patcher_save_data = patch("app.lib.kis.client.save_data")
        self.mock_save_data = self.patcher_save_data.start()

        # Mock http get and post
        self.patcher_get = patch("app.lib.kis.client.get", new_callable=AsyncMock)
        self.mock_get = self.patcher_get.start()
        self.patcher_post = patch("app.lib.kis.client.post", new_callable=AsyncMock)
        self.mock_post = self.patcher_post.start()

        self.client = KISClient(env="R")

    def tearDown(self):
        self.patcher_read_data.stop()
        self.patcher_save_data.stop()
        self.patcher_get.stop()
        self.patcher_post.stop()

    def _mock_read_data(self, key):
        data = {
            "real_app_key": "r_app_key",
            "real_app_secret": "r_app_secret",
            "real_account": "87654321",
            "real_prod": "01",
            "auth_token": "old_token",
            "token_type": "Bearer",
            "expired_time": (datetime.now() + timedelta(hours=1)).strftime(
                "%Y-%m-%d %H:%M:%S",
            ),
            "ws_token": "ws_token",
        }
        return data.get(key)

    # async def test_load_auth_token_valid(self):
    #     # Token is still valid, should not call API
    #     response = await self.client.load_auth_token()
    #     self.assertEqual(response.access_token, "old_token")
    #     self.mock_post.assert_not_called()

    # async def test_load_auth_token_expired(self):
    #     # Force token expired
    #     self.client.expired_time = datetime.now() - timedelta(seconds=1)

    #     mock_resp = {
    #         "access_token": "new_token",
    #         "access_token_token_expired": (
    #             datetime.now() + timedelta(hours=2)
    #         ).strftime("%Y-%m-%d %H:%M:%S"),
    #         "expires_in": 7200,
    #         "token_type": "Bearer",
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.load_auth_token()
    #     self.assertEqual(response.access_token, "new_token")
    #     self.mock_post.assert_called_once()
    #     self.mock_save_data.assert_any_call("auth_token", "new_token")

    # async def test_dispose_auth_token(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "KISA0000",
    #         "msg1": "Success",
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.dispose_auth_token()
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(self.client.auth_token, "")
    #     self.mock_save_data.assert_any_call("auth_token", "")

    async def test_order_cash(self):
        mock_resp = {
            "rt_cd": "0",
            "msg_cd": "0000",
            "msg1": "Order Placed",
            "output": {
                "KRX_FWDG_ORD_ORGNO": "12345",
                "ODNO": "ORD123",
                "ORD_TMD": "100000",
            },
        }
        self.mock_post.return_value = mock_resp

        response = await self.client.order(
            pdno="005930",
            ord_qty=10,
            ord_unpr=70000,
            sll_buy_dvsn_cd="BUY",
        )
        print(response)
        self.assertEqual(response.rt_cd, "0")
        self.assertEqual(response.output.ODNO, "ORD123")

    # async def test_inquire_psbl_rvsecncl(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Success",
    #         "output": {
    #             "psbl_rvsecncl_yn": "Y",
    #         },
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.inquire_psbl_rvsecncl(
    #         odno="ORD123",
    #     )
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.psbl_rvsecncl_yn, "Y")

    # async def test_order_modify(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Order Modified",
    #         "output": {
    #             "KRX_FWDG_ORD_ORGNO": "12345",
    #             "ODNO": "ORD123",
    #             "ORD_TMD": "100000",
    #         },
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.order_modify(
    #         odno="ORD123",
    #         ord_qty=20,
    #         ord_unpr=69000,
    #     )
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.ODNO, "ORD123")

    # async def test_order_cancel(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Order Cancelled",
    #         "output": {
    #             "KRX_FWDG_ORD_ORGNO": "12345",
    #             "ODNO": "ORD123",
    #             "ORD_TMD": "100000",
    #         },
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.order_cancel(
    #         odno="ORD123",
    #     )
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.ODNO, "ORD123")

    # async def test_order_resve(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Reservation Placed",
    #         "output": {
    #             "KRX_FWDG_ORD_ORGNO": "12345",
    #             "ODNO": "ORD123",
    #             "ORD_TMD": "100000",
    #         },
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.order_resve(
    #         pdno="005930",
    #         ord_qty=10,
    #         ord_unpr=70000,
    #         sll_buy_dvsn_cd="BUY",
    #         ord_sve_dvsn_cd="DAY",
    #     )
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.ODNO, "ORD123")

    # async def test_order_resv_rvsecncl(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Success",
    #         "output": {
    #             "psbl_rvsecncl_yn": "Y",
    #         },
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.order_resv_rvsecncl(
    #         odno="ORD123",
    #     )
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.psbl_rvsecncl_yn, "Y")

    # async def test_order_resv_cnnl(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Reservation Cancelled",
    #         "output": {
    #             "KRX_FWDG_ORD_ORGNO": "12345",
    #             "ODNO": "ORD123",
    #             "ORD_TMD": "100000",
    #         },
    #     }
    #     self.mock_post.return_value = mock_resp

    #     response = await self.client.order_resv_cnnl(
    #         odno="ORD123",
    #     )
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.ODNO, "ORD123")

    # async def test_inquire_balance(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Success",
    #         "output1": [],
    #         "output2": {
    #             "dnca_tot_amt": "1000000",
    #             "nxdy_excc_amt": "1000000",
    #             "prvs_rcdl_excc_amt": "1000000",
    #             "cma_evlu_amt": "0",
    #             "bfdy_buy_amt": "0",
    #             "thdt_buy_amt": "0",
    #             "nxdy_buy_amt": "0",
    #             "bfdy_sll_amt": "0",
    #             "thdt_sll_amt": "0",
    #             "nxdy_sll_amt": "0",
    #             "tot_sll_amt": "0",
    #             "tot_buy_amt": "0",
    #             "sttl_dt": "20231027",
    #             "thdt_sttl_dpst": "1000000",
    #             "ottr_cash_rsv_amt": "0",
    #             "ottr_crdt_rsv_amt": "0",
    #         },
    #     }
    #     self.mock_get.return_value = mock_resp

    #     response = await self.client.inquire_balance()
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output2.dnca_tot_amt, 1000000)

    # async def test_inquire_price(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Success",
    #         "output": {
    #             "stck_prpr": "70000",
    #             "prdy_vrss": "500",
    #             "prdy_vrss_sign": "2",
    #             "prdy_ctrt": "0.72",
    #             "acml_vol": "1000000",
    #             "acml_tr_pbmn": "70000000000",
    #         },
    #     }
    #     self.mock_get.return_value = mock_resp

    #     response = await self.client.inquire_price(fid_input_iscd="005930")
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.stck_prpr, 70000)

    # async def test_search_stock_info(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Success",
    #         "output": {
    #             "prdt_type_code": "300",
    #             "prdt_type_name": "주식",
    #             "prdt_name": "삼성전자",
    #             "prdt_name1": "삼성전자",
    #             "std_pdno": "KR7005930003",
    #             "scty_kacd_name": "보통주",
    #             "stck_prpr": "70000",
    #             "prdy_vrss_sign": "2",
    #             "prdy_vrss": "500",
    #             "prdy_ctrt": "0.72",
    #             "acml_vol": "1000000",
    #             "acml_tr_pbmn": "70000000000",
    #             "stck_fcam": "100",
    #             "stck_parpr": "100",
    #             "list_prc": "100",
    #             "list_dt": "19750611",
    #             "mrkt_name": "KOSPI",
    #             "spsb_eot_ratio": "0.0",
    #         },
    #     }
    #     self.mock_get.return_value = mock_resp

    #     response = await self.client.search_stock_info(fid_input_iscd="005930")
    #     self.assertEqual(response.rt_cd, "0")
    #     self.assertEqual(response.output.prdt_name, "삼성전자")

    # async def test_chk_holiday(self):
    #     mock_resp = {
    #         "rt_cd": "0",
    #         "msg_cd": "0000",
    #         "msg1": "Success",
    #         "output": [
    #             {
    #                 "bass_dt": "20231027",
    #                 "wday_cd": "06",
    #                 "bzdy_yn": "Y",
    #                 "tr_dy_yn": "Y",
    #                 "opnd_yn": "Y",
    #                 "sttl_dy_yn": "Y",
    #             },
    #         ],
    #     }
    #     self.mock_get.return_value = mock_resp

    #     is_holiday = await self.client.chk_holiday(date="20231027")
    #     self.assertFalse(is_holiday)


if __name__ == "__main__":
    unittest.main()
