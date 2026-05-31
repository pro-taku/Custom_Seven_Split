import requests
import json
import time
from typing import Optional, Dict, Any
from enum import Enum

class TRID(Enum):
    # 주식 주문
    BUY_CASH = ("TTTC0802U")
    SELL_CASH = ("TTTC0801U")
    REVISE_CANCEL = ("TTTC0803U")
    
    # 조회
    PSBL_REVISE_CANCEL = ("TTTC8036R")
    BALANCE = ("TTTC8434R")
    PSBL_ORDER = ("TTTC8908R")
    PRICE = ("FHKST01010100")
    HOLIDAY = ("CTCA0903R")
    
    # 실시간 (웹소켓)
    WS_PRICE = ("H0STCNT0")

    def get_id(self) -> str:
        return self.value

class KISClient:
    def __init__(
            self,
            appkey: str, 
            appsecret: str,
            cano: str,
            acnt_prdt_cd: str = "01",
            access_token: Optional[str] = None,
            token_expiry: Optional[str] = None,
            approval_key: Optional[str] = None
        ):
        self.appkey = appkey
        self.appsecret = appsecret
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd
        self.base_url = "https://openapivts.koreainvestment.com:29443"
            
        self.access_token = access_token
        self.token_expiry = token_expiry
        self.approval_key = approval_key

    def _get_headers(self, tr_id: str, hashkey: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": tr_id,
            "custtype": "P",  # Personal
        }
        if hashkey:
            headers["hashkey"] = hashkey
        return headers

    def get_hashkey(self, data: Dict[str, Any]) -> str:
        """보안을 위한 hashkey 생성"""
        url = f"{self.base_url}/uapi/hashkey"
        headers = {
            "Content-Type": "application/json",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
        }
        res = requests.post(url, headers=headers, data=json.dumps(data))
        return res.json().get("HASH")

    def get_access_token(self) -> Dict[str, Any]:
        """접근토큰발급(P)"""
        url = f"{self.base_url}/oauth2/tokenP"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret
        }
        res = requests.post(url, data=json.dumps(data))
        res_data = res.json()
        self.access_token = res_data.get("access_token")
        return res_data

    def get_approval_key(self) -> str:
        """실시간(웹소켓) 접속키 발급"""
        url = f"{self.base_url}/oauth2/Approval"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "secretkey": self.appsecret
        }
        res = requests.post(url, data=json.dumps(data))
        self.approval_key = res.json().get("approval_key")
        return self.approval_key

    def order_cash(self, symbol: str, qty: int, price: int, side: str = "BUY") -> Dict[str, Any]:
        """주식주문(현금) - side: BUY/SELL"""
        tr_id = TRID.BUY_CASH.get_id() if side == "BUY" else TRID.SELL_CASH.get_id()

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_DVSN": "00" if price > 0 else "01", # 00:지정가, 01:시장가
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price)
        }
        headers = self._get_headers(tr_id, self.get_hashkey(data))
        res = requests.post(url, headers=headers, data=json.dumps(data))
        return res.json()

    def order_rvsecncl(self, orgn_odno: str, rvse_cncl_dv: str, qty: int, price: int, ord_dvsn: str = "00") -> Dict[str, Any]:
        """주식주문(정정취소) - rvse_cncl_dv: 01(정정), 02(취소)"""
        tr_id = TRID.REVISE_CANCEL.get_id()
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-rvsecncl"
        data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "ORGN_ODNO": orgn_odno,
            "RVSE_CNCL_DV_CODE": rvse_cncl_dv,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
            "ORD_DVSN": ord_dvsn
        }
        headers = self._get_headers(tr_id, self.get_hashkey(data))
        res = requests.post(url, headers=headers, data=json.dumps(data))
        return res.json()

    def cancel_order(self, orgn_odno: str, qty: int = 0, price: int = 0) -> Dict[str, Any]:
        """주식주문 취소"""
        return self.order_rvsecncl(orgn_odno, "02", qty, price)

    def inquire_psbl_rvsecncl(self, inqr_dvsn: str = "0") -> Dict[str, Any]:
        """주식정정취소가능주문조회 - inqr_dvsn: 0(전체), 1(매도), 2(매수)"""
        tr_id = TRID.PSBL_REVISE_CANCEL.get_id()
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "INQR_DVSN": inqr_dvsn,
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        headers = self._get_headers(tr_id)
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def inquire_balance(self) -> Dict[str, Any]:
        """주식잔고조회"""
        tr_id = TRID.BALANCE.get_id()
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLG": "N",
            "OVR_FLG": "N",
            "PRCS_DVSN": "00",
            "UNPR_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        headers = self._get_headers(tr_id)
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def inquire_psbl_order(self, symbol: str, price: int, ord_dvsn: str = "00") -> Dict[str, Any]:
        """매수가능조회"""
        tr_id = TRID.PSBL_ORDER.get_id()
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_UNPR": str(price),
            "ORD_DVSN": ord_dvsn,
            "CMA_EVAL_AMT_ICLD_YN": "N"
        }
        headers = self._get_headers(tr_id)
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def inquire_price(self, symbol: str) -> Dict[str, Any]:
        """주식현재가조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # KRX
            "FID_INPUT_ISCD": symbol,
        }
        headers = self._get_headers(TRID.PRICE.get_id())
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def chk_holiday(self, base_dt: str) -> Dict[str, Any]:
        """국내휴장일조회 - base_dt: YYYYMMDD"""
        tr_id = TRID.HOLIDAY.get_id()
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/chk-holiday"
        params = {
            "BASS_DT": base_dt,
            "CTX_AREA_NK": "",
            "CTX_AREA_FK": ""
        }
        headers = self._get_headers(tr_id)
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def get_ws_subscribe_payload(self, symbol: str, tr_type: str = "1") -> str:
        """국내주식 실시간체결가 (KRX) 구독용 페이로드 생성 - tr_type: 1(등록), 2(해제)"""
        if not self.approval_key:
            self.get_approval_key()
            
        payload = {
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": tr_type,
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": TRID.WS_PRICE.get_id(),
                    "tr_key": symbol
                }
            }
        }
        return json.dumps(payload)
