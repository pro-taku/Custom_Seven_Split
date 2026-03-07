from datetime import datetime
from typing import Optional

from fastapi.logger import logger
from pydantic import BaseModel, ValidationError

from app.core.config import (
    KIS_REAL_DOMAIN,
    KIS_REAL_WS_DOMAIN,
    KIS_VIRTUAL_DOMAIN,
    KIS_VIRTUAL_WS_DOMAIN,
    TR,
    TradeType,
    read_data,
    save_data,
)
from app.core.http import get, post
from app.core.websocket import CSSWebSocket
from app.lib.kis.model import (
    InquireHolidayRequestHeader,
    InquireHolidayRequestQuery,
    InquireHolidayResponse,
    InquirePriceRequestHeader,
    InquirePriceRequestQuery,
    InquirePriceResponse,
    InquirePsblOrderRequestHeader,
    InquirePsblOrderRequestQuery,
    InquirePsblOrderResponse,
    InquirePsblRvsecnclRequestHeader,
    InquirePsblRvsecnclRequestQuery,
    InquirePsblRvsecnclResponse,
    KISBaseResponse,
    KISRequestHeader,
    OAuth2ApprovalRequest,
    OAuth2ApprovalResponse,
    OAuth2RevokePRequest,
    OAuth2RevokePResponse,
    OAuth2TokenPRequest,
    OAuth2TokenPResponse,
    OrderCashRequestBody,
    OrderCashRequestHeader,
    OrderCashResponse,
    OrderRvsecnclRequestBody,
    OrderRvsecnclRequestHeader,
    OrderRvsecnclResponse,
    SearchStockInfoRequestHeader,
    SearchStockInfoRequestQuery,
    SearchStockInfoResponse,
)


class _KISProperty:
    def __init__(self, env: str, account_num: Optional[str] = None):
        self.env = env
        if env == "V":
            self.app_key = read_data("virtual_app_key")
            self.app_secret = read_data("virtual_app_secret")
            self.account_num = (
                read_data("virtual_account") + "-" + read_data("virtual_prod")
                if account_num is None
                else account_num
            )
            self.http_domain = KIS_VIRTUAL_DOMAIN
            self.ws_domain = KIS_VIRTUAL_WS_DOMAIN
        elif env == "R":
            self.app_key = read_data("real_app_key")
            self.app_secret = read_data("real_app_secret")
            self.account_num = (
                read_data("real_account") + "-" + read_data("real_prod")
                if account_num is None
                else account_num
            )
            self.http_domain = KIS_REAL_DOMAIN
            self.ws_domain = KIS_REAL_WS_DOMAIN
        else:
            raise ValueError(
                "Invalid environment specified. Use 'V' for virtual or 'R' for real.",
            )

        self.auth_token = read_data("auth_token")
        self.token_type = read_data("token_type")
        self.expired_time_str = read_data("expired_time")
        self.expired_time = (
            datetime.strptime(self.expired_time_str, "%Y-%m-%d %H:%M:%S")
            if self.expired_time_str
            else None
        )
        self.ws_token = read_data("ws_token")
        self.account_prefix = self.account_num[:8]
        self.account_suffix = self.account_num[9:]
        self.TR = TR

    def __str__(self):
        return f"""
        < KISClient Properties >
        Environment: {"Virtual" if self.env == "V" else "Real"}
        Account Number: {self.account_num}
        HTTP Domain: {self.http_domain}
        WebSocket Domain: {self.ws_domain}
        App Key: {self.app_key}
        App Secret: {"*" * len(self.app_secret) if self.app_secret else None}
        Auth Token: {"*" * len(self.auth_token) if self.auth_token else None}
        Expired Time: {self.expired_time}
        """


class KISClient(_KISProperty):
    def __init__(self, env: str = "V", account_num: str | None = None):
        super().__init__(env, account_num)

    async def _send_request(
        self,
        method: str,
        api_path: str,
        request_header_model: KISRequestHeader,
        response_model: type[KISBaseResponse],
        request_body_model: BaseModel | None = None,
        request_query_model: BaseModel | None = None,
    ) -> KISBaseResponse:
        url = self.http_domain + api_path
        headers = request_header_model.model_dump(by_alias=True, exclude_none=True)

        request_data = {}
        if request_body_model:
            request_data["json"] = request_body_model.model_dump(
                by_alias=True,
                exclude_none=True,
            )
        if request_query_model:
            request_data["params"] = request_query_model.model_dump(
                by_alias=True,
                exclude_none=True,
            )

        try:
            if method.lower() == "get":
                response_json = await get(url, headers=headers, **request_data)
            elif method.lower() == "post":
                response_json = await post(url, headers=headers, **request_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            return response_model.model_validate(response_json)
        except ValidationError as e:
            logger.error(f"Pydantic validation error for {api_path}: {e.errors()}")
            raise
        except Exception as e:
            logger.error(f"Error sending request to {api_path}: {e}")
            raise

    async def load_auth_token(self) -> OAuth2TokenPResponse:
        logger.info(
            f"Current auth_token: {'[REDACTED]' if self.auth_token else 'None'}. Expired time: {self.expired_time}. Current time: {datetime.now()}",
        )
        if self.auth_token and self.expired_time and self.expired_time > datetime.now():
            logger.info("Access token is still valid. No new token request needed.")
            return OAuth2TokenPResponse(
                rt_cd="0",
                msg_cd="KISA0000",
                msg1="Valid Token",
                access_token=self.auth_token,
                access_token_token_expired=self.expired_time,
                expires_in=(self.expired_time - datetime.now()).seconds,
                token_type=self.token_type,
            )

        logger.info("Access token is expired or not available. Requesting a new one...")
        api_url = "/oauth2/tokenP"
        request_body = OAuth2TokenPRequest(
            appkey=self.app_key,
            appsecret=self.app_secret,
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        try:
            logger.debug(f"Requesting new auth token to {self.http_domain + api_url}")
            logger.debug(f"Request headers: {headers}")
            logger.debug(
                f"Request body: {request_body.model_dump_json(by_alias=True, exclude_none=True)}",
            )

            response_json = await post(
                url=self.http_domain + api_url,
                headers=headers,
                json=request_body.model_dump(by_alias=True, exclude_none=True),
            )
            logger.debug(f"Auth token response: {response_json}")
            response = OAuth2TokenPResponse.model_validate(response_json)

            self.auth_token = response.access_token
            self.token_type = response.token_type
            self.expired_time = response.access_token_token_expired
            save_data("auth_token", self.auth_token)
            save_data("token_type", self.token_type)
            save_data(
                "expired_time",
                self.expired_time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            logger.info("Access token issued and saved successfully.")
            return response
        except Exception as e:
            logger.error(f"Error loading auth token: {e}")
            raise

    async def dispose_auth_token(self) -> OAuth2RevokePResponse:
        if not self.auth_token:
            logger.info("No access token to dispose.")
            return OAuth2RevokePResponse(
                rt_cd="0",
                msg_cd="KISA0000",
                msg1="No Token to Revoke",
            )

        api_url = "/oauth2/revokeP"
        request_body = OAuth2RevokePRequest(
            appkey=self.app_key,
            appsecret=self.app_secret,
            token=self.auth_token,
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        try:
            response_json = await post(
                url=self.http_domain + api_url,
                headers=headers,
                json=request_body.model_dump(by_alias=True, exclude_none=True),
            )
            response = OAuth2RevokePResponse.model_validate(response_json)

            if response.rt_cd == "0":
                self.auth_token = ""
                self.token_type = ""
                self.expired_time = None
                save_data("auth_token", "")
                save_data("token_type", "")
                save_data("expired_time", "")
                logger.info("Access token disposed successfully.")
            else:
                logger.error(f"Failed to dispose access token: {response.msg1}")
            return response
        except Exception as e:
            logger.error(f"Error disposing auth token: {e}")
            raise

    async def order_cash(
        self,
        trade_type: TradeType,
        pdno: str,
        ord_qty: int,
        ord_unpr: int,
        ord_dvsn: str = "00",
    ) -> OrderCashResponse:
        if not self.auth_token:
            await self.load_auth_token()

        tr_id = ""
        if trade_type == TradeType.SELL:
            tr_id = (
                self.TR.TR_KS_SELL_V.value
                if self.env == "V"
                else self.TR.TR_KS_SELL_R.value
            )
        elif trade_type == TradeType.BUY:
            tr_id = (
                self.TR.TR_KS_BUY_V.value
                if self.env == "V"
                else self.TR.TR_KS_BUY_R.value
            )
        else:
            raise ValueError(
                "Invalid trade_type. Use 'SELL' for sell or 'BUY' for buy.",
            )

        request_header = OrderCashRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=tr_id,
        )
        request_body = OrderCashRequestBody(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            PDNO=pdno,
            ORD_DVSN=ord_dvsn,
            ORD_QTY=str(ord_qty),
            ORD_UNPR=str(ord_unpr),
        )

        return await self._send_request(
            method="post",
            api_path="/uapi/domestic-stock/v1/trading/order-cash",
            request_header_model=request_header,
            request_body_model=request_body,
            response_model=OrderCashResponse,
        )

    async def order_rvsecncl(
        self,
        orgn_odno: str,
        rvse_cncl_dvsn_cd: str,
        ord_qty: int | None = None,
        ord_unpr: int | None = None,
        krx_fwdg_ord_orgno: str = "000000",  # TODO: 수정 필요
        ord_dvsn: str = "00",
        qty_all_ord_yn: str = "N",
    ) -> OrderRvsecnclResponse:
        if not self.auth_token:
            await self.load_auth_token()

        tr_id = ""
        if rvse_cncl_dvsn_cd == "01" or rvse_cncl_dvsn_cd == "02":
            tr_id = (
                self.TR.TR_KS_FIX_CANCEL_V.value
                if self.env == "V"
                else self.TR.TR_KS_FIX_CANCEL_R.value
            )
        else:
            raise ValueError(
                "Invalid rvse_cncl_dvsn_cd. Use '01' for revise or '02' for cancel.",
            )

        request_header = OrderRvsecnclRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=tr_id,
        )

        request_body = OrderRvsecnclRequestBody(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            KRX_FWDG_ORD_ORGNO=krx_fwdg_ord_orgno,
            ORGN_ODNO=orgn_odno,
            RVSE_CNCL_DVSN_CD=rvse_cncl_dvsn_cd,
            ORD_DVSN=ord_dvsn,
            ORD_QTY=str(ord_qty) if ord_qty is not None else "",
            ORD_UNPR=str(ord_unpr) if ord_unpr is not None else "",
            QTY_ALL_ORD_YN=qty_all_ord_yn,
        )

        return await self._send_request(
            method="post",
            api_path="/uapi/domestic-stock/v1/trading/order-rvsecncl",
            request_header_model=request_header,
            request_body_model=request_body,
            response_model=OrderRvsecnclResponse,
        )

    async def inquire_psbl_rvsecncl(
        self,
        inqr_dvsn_1: str,
        inqr_dvsn_2: str,
        ctx_area_fk100: str = "",
        ctx_area_nk100: str = "",
    ) -> InquirePsblRvsecnclResponse:
        if self.env == "V":
            raise ValueError(
                "Inquire possible revise/cancel is not supported in virtual investment environment.",
            )

        if not self.auth_token:
            await self.load_auth_token()

        tr_id = (
            self.TR.TR_KS_FIX_CANCEL_V.value
            if self.env == "V"
            else self.TR.TR_KS_FIX_CANCEL_R.value
        )

        request_header = InquirePsblRvsecnclRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=tr_id,
            tr_cont="N" if ctx_area_fk100 or ctx_area_nk100 else None,
        )
        request_query = InquirePsblRvsecnclRequestQuery(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            CTX_AREA_FK100=ctx_area_fk100,
            CTX_AREA_NK100=ctx_area_nk100,
            INQR_DVSN_1=inqr_dvsn_1,
            INQR_DVSN_2=inqr_dvsn_2,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=InquirePsblRvsecnclResponse,
        )

    async def inquire_psbl_order(
        self,
        pdno: str,
        ord_unpr: int,
        ord_dvsn: str = "00",
    ) -> InquirePsblOrderResponse:
        if not self.auth_token:
            await self.load_auth_token()

        tr_id = (
            self.TR.TR_KS_BUY_POSSIBLE_V.value
            if self.env == "V"
            else self.TR.TR_KS_BUY_POSSIBLE_R.value
        )

        request_header = InquirePsblOrderRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=tr_id,
        )
        request_query = InquirePsblOrderRequestQuery(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            PDNO=pdno,
            ORD_UNPR=str(ord_unpr),
            ORD_DVSN=ord_dvsn,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/trading/inquire-psbl-order",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=InquirePsblOrderResponse,
        )

    async def inquire_price(
        self,
        fid_input_iscd: str,
        fid_cond_mrkt_div_code: str = "J",
    ) -> InquirePriceResponse:
        if not self.auth_token:
            await self.load_auth_token()

        request_header = InquirePriceRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=self.TR.TR_KS_PRICE_R.value,
        )
        request_query = InquirePriceRequestQuery(
            fid_cond_mrkt_div_code=fid_cond_mrkt_div_code,
            fid_input_iscd=fid_input_iscd,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/quotations/inquire-price",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=InquirePriceResponse,
        )

    async def search_stock_info(
        self,
        fid_input_iscd: str,
        fid_cond_mrkt_div_code: str = "J",
    ) -> SearchStockInfoResponse:
        if self.env == "V":
            raise ValueError(
                "Stock information search is not supported in virtual investment environment.",
            )

        if not self.auth_token:
            await self.load_auth_token()

        request_header = SearchStockInfoRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id="FHKST01020000",
        )
        request_query = SearchStockInfoRequestQuery(
            fid_cond_mrkt_div_code=fid_cond_mrkt_div_code,
            fid_input_iscd=fid_input_iscd,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/quotations/search-stock-info",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=SearchStockInfoResponse,
        )

    async def chk_holiday(self, date: str) -> bool:
        """
        국내 휴장일 여부 조회
        :param date: 기준일자 (YYYYMMDD)
        :return: 휴장일이면 True, 영업일이면 False
        """
        if self.env == "V":
            raise ValueError(
                "Stock information search is not supported in virtual investment environment.",
            )

        if not self.auth_token:
            await self.load_auth_token()

        request_header = InquireHolidayRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=self.TR.TR_KS_HOLIDAY.value,
        )
        request_query = InquireHolidayRequestQuery(
            BASS_DT=date,
        )

        response = await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/quotations/chk-holiday",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=InquireHolidayResponse,
        )

        if response.rt_cd == "0" and response.output:
            for item in response.output:
                if item.bass_dt == date:
                    # opnd_yn: 개장일여부 (Y: 개장, N: 휴장)
                    return item.opnd_yn == "N"

        logger.warning(
            f"Could not determine holiday status for {date}. Assuming it's a holiday.",
        )
        return True


class KISWsClient(_KISProperty):
    def __init__(self, env: str = "V", account_num: str | None = None):
        super().__init__(env, account_num)
        self.websocket = CSSWebSocket(ws_url=self.ws_domain)
        self.approval_key: str | None = self.ws_token

    async def load_websocket_approval_key(self) -> OAuth2ApprovalResponse:
        """Load the WebSocket approval key."""
        if self.approval_key:
            logger.info("WebSocket approval key is already available.")
            return OAuth2ApprovalResponse(
                approval_key=self.approval_key,
            )

        api_url = "/oauth2/Approval"
        request_body = OAuth2ApprovalRequest(
            appkey=self.app_key,
            secretkey=self.app_secret,
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

        try:
            response_json = await post(
                url=self.http_domain + api_url,
                headers=headers,
                json=request_body.model_dump(by_alias=True, exclude_none=True),
            )
            response = OAuth2ApprovalResponse.model_validate(response_json)

            self.approval_key = response.approval_key
            self.ws_token = response.approval_key
            save_data("ws_token", self.ws_token)
            logger.info("WebSocket approval key issued and saved successfully.")
            return response
        except Exception as e:
            logger.error(f"Error getting WebSocket approval key: {e}")
            raise

    def register_check_execution_realtime(self):
        """Register for real-time execution notifications."""
        message = self._send_websocket_request(
            tr_id=self.TR.TR_KS_ORDER_CHECK_R.value,
            tr_key=self.account_num,
            tr_type="1",
            req_type="0",
        )
        self.websocket.add_message(message)
        self.websocket.send_message()

    def unregister_check_execution_realtime(self):
        """Unregister from real-time execution notifications."""
        message = self._send_websocket_request(
            tr_id=self.TR.TR_KS_ORDER_CHECK_R.value,
            tr_key=self.account_num,
            tr_type="1",
            req_type="1",
        )
        self.websocket.add_message(message)
        self.websocket.send_message()
