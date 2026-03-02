import json
import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from app.core.config import (
    CUSTOMER_TYPE,
    KIS_REAL_DOMAIN,
    KIS_REAL_WS_DOMAIN,
    KIS_VIRTUAL_DOMAIN,
    KIS_VIRTUAL_WS_DOMAIN,
    TR,
    read_data,
    save_data,
)
from app.core.http import get, post
from app.lib.kis.model import (
    InquireBalanceRequestHeader,
    InquireBalanceRequestQuery,
    InquireBalanceResponse,
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
    KISWebSocketHeader,
    KISWebSocketInput,
    OAuth2ApprovalRequest,
    OAuth2ApprovalResponse,
    OAuth2RevokePRequest,
    OAuth2RevokePResponse,
    OAuth2TokenPRequest,
    OAuth2TokenPResponse,
    OrderCashRequestBody,
    OrderCashRequestHeader,
    OrderCashResponse,
    OrderResvCcnlRequestHeader,
    OrderResvCcnlRequestQuery,
    OrderResvCcnlResponse,
    OrderResvRequestBody,
    OrderResvRequestHeader,
    OrderResvResponse,
    OrderResvRvsecnclRequestBody,
    OrderResvRvsecnclRequestHeader,
    OrderResvRvsecnclResponse,
    OrderRvsecnclRequestBody,
    OrderRvsecnclRequestHeader,
    OrderRvsecnclResponse,
    RealtimeExecutionParsedOutput,
    RealtimeExecutionResponse,
    RealtimeQuoteParsedOutput,
    RealtimeQuoteResponse,
    SearchStockInfoRequestHeader,
    SearchStockInfoRequestQuery,
    SearchStockInfoResponse,
)

logger = logging.getLogger(__name__)


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

        # Hashing functionality is currently disabled
        # if is_hash_needed and request_body_model:
        #     request_body_str = json.dumps(
        #         request_body_model.model_dump(by_alias=True, exclude_none=True),
        #     )
        #     headers["hashkey"] = self.hashing(request_body_str)

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
        pdno: str,
        ord_qty: int,
        ord_unpr: int,
        sll_buy_dvsn_cd: str,
        ord_dvsn: str = "00",
    ) -> OrderCashResponse:
        if not self.auth_token:
            await self.load_auth_token()

        tr_id = ""
        if sll_buy_dvsn_cd == "SELL":
            tr_id = (
                self.TR.TR_KS_SELL_V.value
                if self.env == "V"
                else self.TR.TR_KS_SELL_R.value
            )
        elif sll_buy_dvsn_cd == "BUY":
            tr_id = (
                self.TR.TR_KS_BUY_V.value
                if self.env == "V"
                else self.TR.TR_KS_BUY_R.value
            )
        else:
            raise ValueError(
                "Invalid sll_buy_dvsn_cd. Use 'SELL' for sell or 'BUY' for buy.",
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

        # Hashing functionality is currently disabled
        # request_body_json_str = request_body.model_dump_json(
        #     by_alias=True,
        #     exclude_none=True,
        # )
        # request_header.hashkey = self.hashing(request_body_json_str)

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
        pdno: str,
        rvse_cncl_dvsn_cd: str,
        ord_qty: int | None = None,
        ord_unpr: int | None = None,
        krx_fwdg_ord_orgno: str = "000000",
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
            PDNO=pdno,
            RVSE_CNCL_DVSN_CD=rvse_cncl_dvsn_cd,
            ORD_DVSN=ord_dvsn,
            ORD_QTY=str(ord_qty) if ord_qty is not None else "",
            ORD_UNPR=str(ord_unpr) if ord_unpr is not None else "",
            QTY_ALL_ORD_YN=qty_all_ord_yn,
        )

        # Hashing functionality is currently disabled
        # request_body_json_str = request_body.model_dump_json(
        #     by_alias=True,
        #     exclude_none=True,
        # )
        # request_header.hashkey = self.hashing(request_body_json_str)

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

    async def inquire_balance(
        self,
        afhr_flpr_yn: str = "N",
        inqr_dvsn: str = "01",
        unpr_dvsn: str = "01",
        fund_sttl_icld_yn: str = "N",
        fncg_amt_auto_rdpt_yn: str = "N",
        prcs_dvsn: str = "00",
        ctx_area_fk100: str = "",
        ctx_area_nk100: str = "",
    ) -> InquireBalanceResponse:
        if not self.auth_token:
            await self.load_auth_token()

        tr_id = (
            self.TR.TR_KS_ACCOUNT_V.value
            if self.env == "V"
            else self.TR.TR_KS_ACCOUNT_R.value
        )

        request_header = InquireBalanceRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=tr_id,
            tr_cont="N" if ctx_area_fk100 or ctx_area_nk100 else None,
        )
        request_query = InquireBalanceRequestQuery(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            AFHR_FLPR_YN=afhr_flpr_yn,
            INQR_DVSN=inqr_dvsn,
            UNPR_DVSN=unpr_dvsn,
            FUND_STTL_ICLD_YN=fund_sttl_icld_yn,
            FNCG_AMT_AUTO_RDPT_YN=fncg_amt_auto_rdpt_yn,
            PRCS_DVSN=prcs_dvsn,
            CTX_AREA_FK100=ctx_area_fk100,
            CTX_AREA_NK100=ctx_area_nk100,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/trading/inquire-balance",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=InquireBalanceResponse,
        )

    async def inquire_psbl_order(
        self,
        ord_unpr: int,
        ord_qty: int,
        pdno: str = "",
        ord_dvsn: str = "00",
        cash_prcs_dvsn_cd: str = "01",
        ivst_pdct_tp_cd: str = "01",
        loan_dt: str = "",
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
            ORD_QTY=str(ord_qty),
            ORD_DVSN=ord_dvsn,
            CASH_PRCS_DVSN_CD=cash_prcs_dvsn_cd,
            IVST_PDCT_TP_CD=ivst_pdct_tp_cd,
            LOAN_DT=loan_dt,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/trading/inquire-psbl-order",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=InquirePsblOrderResponse,
        )

    async def order_resv(
        self,
        pdno: str,
        sll_buy_dvsn_cd: str,
        ord_qty: int,
        ord_unpr: int,
        resv_qty_all_ord_yn: str,
        resv_ord_dvsn_cd: str,
        resv_ord_tp_cd: str,
        resv_ord_trgt_dt: str | None = None,
        resv_ord_tmd: str | None = None,
        resv_ord_lmt_tmd: str | None = None,
        mod_unpr_dvsn_cd: str = "00",
        lmt_unpr_type_cd: str = "00",
    ) -> OrderResvResponse:
        if self.env == "V":
            raise ValueError(
                "Reservation orders are not supported in virtual investment environment.",
            )
        if not self.auth_token:
            await self.load_auth_token()

        request_header = OrderResvRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=self.TR.TR_KS_RESV_ORDER_R.value,
        )
        request_body = OrderResvRequestBody(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            PDNO=pdno,
            SLL_BUY_DVSN_CD=sll_buy_dvsn_cd,
            ORD_QTY=str(ord_qty),
            ORD_UNPR=str(ord_unpr),
            RESV_QTY_ALL_ORD_YN=resv_qty_all_ord_yn,
            RESV_ORD_DVSN_CD=resv_ord_dvsn_cd,
            RESV_ORD_TP_CD=resv_ord_tp_cd,
            RESV_ORD_TRGT_DT=resv_ord_trgt_dt,
            RESV_ORD_TMD=resv_ord_tmd,
            RESV_ORD_LMT_TMD=resv_ord_lmt_tmd,
            MOD_UNPR_DVSN_CD=mod_unpr_dvsn_cd,
            LMT_UNPR_TYPE_CD=lmt_unpr_type_cd,
        )

        # Hashing functionality is currently disabled
        # request_body_json_str = request_body.model_dump_json(
        #     by_alias=True,
        #     exclude_none=True,
        # )
        # request_header.hashkey = self.hashing(request_body_json_str)

        return await self._send_request(
            method="post",
            api_path="/uapi/domestic-stock/v1/trading/order-resv",
            request_header_model=request_header,
            request_body_model=request_body,
            response_model=OrderResvResponse,
        )

    async def order_resv_rvsecncl(
        self,
        rsrv_odno: str,
        pdno: str,
        sll_buy_dvsn_cd: str,
        rvse_cncl_dvsn_cd: str,
        ord_qty: int | None = None,
        ord_unpr: int | None = None,
        qty_all_ord_yn: str = "N",
    ) -> OrderResvRvsecnclResponse:
        if self.env == "V":
            raise ValueError(
                "Reservation orders are not supported in virtual investment environment.",
            )
        if not self.auth_token:
            await self.load_auth_token()

        tr_id = ""
        if rvse_cncl_dvsn_cd == "01":
            tr_id = self.TR.TR_KS_RESV_FIX_R.value
        elif rvse_cncl_dvsn_cd == "02":
            tr_id = self.TR.TR_KS_RESV_CANCEL_R.value
        else:
            raise ValueError(
                "Invalid rvse_cncl_dvsn_cd. Use '01' for revise or '02' for cancel.",
            )

        request_header = OrderResvRvsecnclRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=tr_id,
        )
        request_body = OrderResvRvsecnclRequestBody(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            RSRV_ODNO=rsrv_odno,
            PDNO=pdno,
            SLL_BUY_DVSN_CD=sll_buy_dvsn_cd,
            RVSE_CNCL_DVSN_CD=rvse_cncl_dvsn_cd,
            ORD_QTY=str(ord_qty) if ord_qty is not None else "",
            ORD_UNPR=str(ord_unpr) if ord_unpr is not None else "",
            QTY_ALL_ORD_YN=qty_all_ord_yn,
        )

        # Hashing functionality is currently disabled
        # request_body_json_str = request_body.model_dump_json(
        #     by_alias=True,
        #     exclude_none=True,
        # )
        # request_header.hashkey = self.hashing(request_body_json_str)

        return await self._send_request(
            method="post",
            api_path="/uapi/domestic-stock/v1/trading/order-resv-rvsecncl",
            request_header_model=request_header,
            request_body_model=request_body,
            response_model=OrderResvRvsecnclResponse,
        )

    async def order_resv_cnnl(
        self,
        inqr_dvsn: str,
        inqr_bgn_dt: str | None = None,
        inqr_end_dt: str | None = None,
        ctx_area_fk100: str = "",
        ctx_area_nk100: str = "",
    ) -> OrderResvCcnlResponse:
        if self.env == "V":
            raise ValueError(
                "Reservation orders are not supported in virtual investment environment.",
            )
        if not self.auth_token:
            await self.load_auth_token()

        request_header = OrderResvCcnlRequestHeader(
            Authorization=f"Bearer {self.auth_token}",
            appkey=self.app_key,
            appsecret=self.app_secret,
            tr_id=self.TR.TR_KS_RESV_SELECT_R.value,
            tr_cont="N" if ctx_area_fk100 or ctx_area_nk100 else None,
        )
        request_query = OrderResvCcnlRequestQuery(
            CANO=self.account_prefix,
            ACNT_PRDT_CD=self.account_suffix,
            CTX_AREA_FK100=ctx_area_fk100,
            CTX_AREA_NK100=ctx_area_nk100,
            INQR_DVSN=inqr_dvsn,
            INQR_BGN_DT=inqr_bgn_dt,
            INQR_END_DT=inqr_end_dt,
        )
        return await self._send_request(
            method="get",
            api_path="/uapi/domestic-stock/v1/trading/order-resv-ccnl",
            request_header_model=request_header,
            request_query_model=request_query,
            response_model=OrderResvCcnlResponse,
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


class KISWsClient(_KISProperty):
    def __init__(self, env: str = "V", account_num: str | None = None):
        super().__init__(env, account_num)
        self.websocket_client: Any | None = None
        self.approval_key: str | None = self.ws_token

    async def load_websocket_approval_key(self) -> OAuth2ApprovalResponse:
        if self.approval_key:
            logger.info("WebSocket approval key is already available.")
            return OAuth2ApprovalResponse(
                rt_cd="0",
                msg_cd="KISA0000",
                msg1="Valid Approval Key",
                approval_key=self.approval_key,
                approval_key_token_expired=datetime.now(),
                expires_in=0,
            )

        api_url = "/oauth2/Approval"
        request_body = OAuth2ApprovalRequest(
            appkey=self.app_key,
            secretkey=self.app_secret,
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
            response = OAuth2ApprovalResponse.model_validate(response_json)

            if response.rt_cd == "0":
                self.approval_key = response.approval_key
                self.ws_token = response.approval_key
                save_data("ws_token", self.ws_token)
                # TODO: Save approval_key_token_expired and expires_in for proper management
                logger.info("WebSocket approval key issued and saved successfully.")
            else:
                logger.error(f"Failed to issue WebSocket approval key: {response.msg1}")
            return response
        except Exception as e:
            logger.error(f"Error getting WebSocket approval key: {e}")
            raise

    def _send_websocket_request(
        self,
        tr_id: str,
        tr_key: str,
        tr_type: str,
        req_type: str = "0",
    ) -> str:
        if not self.approval_key:
            logger.error(
                "WebSocket approval key is not available. Call load_websocket_approval_key first.",
            )
            raise ValueError("WebSocket approval key is required.")

        header = KISWebSocketHeader(
            approval_key=self.approval_key,
            custtype=CUSTOMER_TYPE,
            tr_type=tr_type,
        )
        body = {"input": KISWebSocketInput(tr_id=tr_id, tr_key=tr_key)}

        request_data = {
            "header": header.model_dump(by_alias=True),
            "body": body,
            "REQUSET_TYPE": req_type,
        }
        return json.dumps(request_data)

    def subscribe_realtime_quote(self, stock_code: str) -> str:
        return self._send_websocket_request(
            tr_id=self.TR.TR_KS_RT_PRICE_R.value,
            tr_key=stock_code,
            tr_type="2",
            req_type="0",
        )

    def subscribe_realtime_execution(self, account_num: str) -> str:
        return self._send_websocket_request(
            tr_id=self.TR.TR_KS_ORDER_CHECK_R.value,
            tr_key=account_num,
            tr_type="1",
            req_type="0",
        )

    def unsubscribe_realtime_data(self, tr_id: str, tr_key: str, tr_type: str) -> str:
        return self._send_websocket_request(
            tr_id=tr_id,
            tr_key=tr_key,
            tr_type=tr_type,
            req_type="1",
        )

    def _process_websocket_message(
        self,
        message: str,
    ) -> tuple[dict, RealtimeQuoteResponse | RealtimeExecutionResponse | None]:
        try:
            if "|" in message:
                json_part, data_part = message.split("|", 1)
                header_and_body = json.loads(json_part)

                tr_id = header_and_body.get("header", {}).get("tr_id")
                tr_key = header_and_body.get("body", {}).get("output", {}).get("tr_key")

                parsed_output = None
                if tr_id == self.TR.TR_KS_RT_PRICE_R.value:
                    data_fields = data_part.split("^")
                    try:
                        parsed_output = RealtimeQuoteParsedOutput(
                            stck_shrn_iscd=data_fields[0],
                            stck_prpr=int(data_fields[1]),
                            prdy_vrss_sign=data_fields[2],
                            prdy_vrss=int(data_fields[3]),
                            prdy_ctrt=float(data_fields[4]),
                            askp1=int(data_fields[5]),
                            bidp1=int(data_fields[6]),
                            askp_rsqn1=int(data_fields[7]),
                            bidp_rsqn1=int(data_fields[8]),
                            askp2=int(data_fields[9]) if len(data_fields) > 9 else 0,
                            bidp2=int(data_fields[10]) if len(data_fields) > 10 else 0,
                            askp_rsqn2=int(data_fields[11])
                            if len(data_fields) > 11
                            else 0,
                            bidp_rsqn2=int(data_fields[12])
                            if len(data_fields) > 12
                            else 0,
                            askp3=int(data_fields[13]) if len(data_fields) > 13 else 0,
                            bidp3=int(data_fields[14]) if len(data_fields) > 14 else 0,
                            askp_rsqn3=int(data_fields[15])
                            if len(data_fields) > 15
                            else 0,
                            bidp_rsqn3=int(data_fields[16])
                            if len(data_fields) > 16
                            else 0,
                            askp4=int(data_fields[17]) if len(data_fields) > 17 else 0,
                            bidp4=int(data_fields[18]) if len(data_fields) > 18 else 0,
                            askp_rsqn4=int(data_fields[19])
                            if len(data_fields) > 19
                            else 0,
                            bidp_rsqn4=int(data_fields[20])
                            if len(data_fields) > 20
                            else 0,
                            askp5=int(data_fields[21]) if len(data_fields) > 21 else 0,
                            bidp5=int(data_fields[22]) if len(data_fields) > 22 else 0,
                            askp_rsqn5=int(data_fields[23])
                            if len(data_fields) > 23
                            else 0,
                            bidp_rsqn5=int(data_fields[24])
                            if len(data_fields) > 24
                            else 0,
                            askp6=int(data_fields[25]) if len(data_fields) > 25 else 0,
                            bidp6=int(data_fields[26]) if len(data_fields) > 26 else 0,
                            askp_rsqn6=int(data_fields[27])
                            if len(data_fields) > 27
                            else 0,
                            bidp_rsqn6=int(data_fields[28])
                            if len(data_fields) > 28
                            else 0,
                            askp7=int(data_fields[29]) if len(data_fields) > 29 else 0,
                            bidp7=int(data_fields[30]) if len(data_fields) > 30 else 0,
                            askp_rsqn7=int(data_fields[31])
                            if len(data_fields) > 31
                            else 0,
                            bidp_rsqn7=int(data_fields[32])
                            if len(data_fields) > 32
                            else 0,
                            askp8=int(data_fields[33]) if len(data_fields) > 33 else 0,
                            bidp8=int(data_fields[34]) if len(data_fields) > 34 else 0,
                            askp_rsqn8=int(data_fields[35])
                            if len(data_fields) > 35
                            else 0,
                            bidp_rsqn8=int(data_fields[36])
                            if len(data_fields) > 36
                            else 0,
                            askp9=int(data_fields[37]) if len(data_fields) > 37 else 0,
                            bidp9=int(data_fields[38]) if len(data_fields) > 38 else 0,
                            askp_rsqn9=int(data_fields[39])
                            if len(data_fields) > 39
                            else 0,
                            bidp_rsqn9=int(data_fields[40])
                            if len(data_fields) > 40
                            else 0,
                            askp10=int(data_fields[41]) if len(data_fields) > 41 else 0,
                            bidp10=int(data_fields[42]) if len(data_fields) > 42 else 0,
                            askp_rsqn10=int(data_fields[43])
                            if len(data_fields) > 43
                            else 0,
                            bidp_rsqn10=int(data_fields[44])
                            if len(data_fields) > 44
                            else 0,
                            total_askp_rsqn=int(data_fields[45])
                            if len(data_fields) > 45
                            else 0,
                            total_bidp_rsqn=int(data_fields[46])
                            if len(data_fields) > 46
                            else 0,
                            ovrs_vol=int(data_fields[47])
                            if len(data_fields) > 47
                            else 0,
                            ovrs_tr_pbmn=int(data_fields[48])
                            if len(data_fields) > 48
                            else 0,
                            chgh_cnt=int(data_fields[49])
                            if len(data_fields) > 49
                            else 0,
                        )
                        response_model_instance = RealtimeQuoteResponse(
                            tr_id=tr_id,
                            tr_key=tr_key if tr_key else data_fields[0],
                            rt_cd=header_and_body.get("header", {}).get("rt_cd", "1"),
                            msg_cd=header_and_body.get("header", {}).get("msg_cd", ""),
                            msg1=header_and_body.get("header", {}).get("msg1", ""),
                            output=parsed_output,
                        )
                        return header_and_body.get(
                            "header",
                            {},
                        ), response_model_instance
                    except (IndexError, ValueError) as e:
                        logger.error(
                            f"Error parsing real-time quote data part: {e} in {data_part}",
                        )
                        return header_and_body.get("header", {}), None

                elif (
                    tr_id == self.TR.TR_KS_ORDER_CHECK_R.value
                    or tr_id == self.TR.TR_KS_ORDER_CHECK_V.value
                ):
                    data_fields = data_part.split("^")
                    try:
                        parsed_output = RealtimeExecutionParsedOutput(
                            trade_type=data_fields[0],
                            odno=data_fields[1],
                            orgn_odno=data_fields[2],
                            iscd=data_fields[3],
                            ord_unpr=int(data_fields[4]),
                            ord_qty=int(data_fields[5]),
                            ord_tmd=data_fields[6],
                            ccld_qty=int(data_fields[7]),
                            ccld_prc=int(data_fields[8]),
                            ccld_tmd=data_fields[9],
                            rmn_qty=int(data_fields[10]),
                            prdt_name=data_fields[11],
                            sll_buy_dvsn_cd=data_fields[12],
                            ord_dvsn_cd=data_fields[13],
                        )
                        response_model_instance = RealtimeExecutionResponse(
                            tr_id=tr_id,
                            tr_key=tr_key if tr_key else self.account_num,
                            rt_cd=header_and_body.get("header", {}).get("rt_cd", "1"),
                            msg_cd=header_and_body.get("header", {}).get("msg_cd", ""),
                            msg1=header_and_body.get("header", {}).get("msg1", ""),
                            output=parsed_output,
                        )
                        return header_and_body.get(
                            "header",
                            {},
                        ), response_model_instance
                    except (IndexError, ValueError) as e:
                        logger.error(
                            f"Error parsing real-time execution data part: {e} in {data_part}",
                        )
                        return header_and_body.get("header", {}), None

                else:
                    logger.warning(f"Unknown tr_id received: {tr_id}")
                    return header_and_body.get("header", {}), None

            else:
                control_message = json.loads(message)
                logger.debug(f"Received control message: {control_message}")
                return control_message.get("header", {}), None

        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decoding error in WebSocket message: {e} from {message}",
            )
            return {}, None
        except ValidationError as e:
            logger.error(
                f"Pydantic validation error for WebSocket message: {e.errors()} from {message}",
            )
            return {}, None
        except Exception as e:
            logger.error(
                f"Unexpected error processing WebSocket message: {e} from {message}",
            )
            return {}, None
