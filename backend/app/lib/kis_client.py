import requests
import json
import time
from typing import Optional, Dict, Any
from enum import Enum

class TRID(Enum):
    # 주식 주문
    BUY_CASH = ("TTTC0802U", "VTTC0802U")
    SELL_CASH = ("TTTC0801U", "VTTC0801U")
    REVISE_CANCEL = ("TTTC0803U", "VTTC0803U")
    
    # 조회
    PSBL_REVISE_CANCEL = ("TTTC8036R", "VTTC8036R")
    BALANCE = ("TTTC8434R", "VTTC8434R")
    PSBL_ORDER = ("TTTC8908R", "VTTC8908R")
    HOLIDAY = ("CTCA0903R", "CTCA0903R")
    
    # 실시간 (웹소켓)
    WS_PRICE = ("H0STCNT0", "H0STCNT0")

    def get_id(self, is_virtual: bool) -> str:
        return self.value[1] if is_virtual else self.value[0]

class KISClient:
    def __init__(self, appkey: str, secret: str, cano: str, acnt_prdt_cd: str = "01", is_virtual: bool = True):
        self.appkey = appkey
        self.secret = secret
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd
        self.is_virtual = is_virtual
        
        if self.is_virtual:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
            
        self.access_token = None
        self.token_expiry = 0
        self.approval_key = None

    def _get_headers(self, tr_id: str, hashkey: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.appkey,
            "appsecret": self.secret,
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
            "appsecret": self.secret,
        }
        res = requests.post(url, headers=headers, data=json.dumps(data))
        return res.json().get("HASH")

    def get_access_token(self) -> str:
        """접근토큰발급(P)"""
        url = f"{self.base_url}/oauth2/tokenP"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.secret
        }
        res = requests.post(url, data=json.dumps(data))
        res_data = res.json()
        self.access_token = res_data.get("access_token")
        return self.access_token

    def get_approval_key(self) -> str:
        """실시간(웹소켓) 접속키 발급"""
        url = f"{self.base_url}/oauth2/Approval"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "secretkey": self.secret
        }
        res = requests.post(url, data=json.dumps(data))
        self.approval_key = res.json().get("approval_key")
        return self.approval_key

    def order_cash(self, symbol: str, qty: int, price: int, side: str = "BUY") -> Dict[str, Any]:
        """주식주문(현금) - side: BUY/SELL"""
        tr_id = TRID.BUY_CASH.get_id(self.is_virtual) if side == "BUY" else TRID.SELL_CASH.get_id(self.is_virtual)
            
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
        tr_id = TRID.REVISE_CANCEL.get_id(self.is_virtual)
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

    def inquire_psbl_rvsecncl(self, inqr_dvsn: str = "0") -> Dict[str, Any]:
        """주식정정취소가능주문조회 - inqr_dvsn: 0(전체), 1(매도), 2(매수)"""
        tr_id = TRID.PSBL_REVISE_CANCEL.get_id(self.is_virtual)
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
        tr_id = TRID.BALANCE.get_id(self.is_virtual)
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLG": "N",
            "OVR_FLG": "N",
            "PRCS_DVSN": "01",
            "UNPR_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        headers = self._get_headers(tr_id)
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def inquire_psbl_order(self, symbol: str, price: int, ord_dvsn: str = "00") -> Dict[str, Any]:
        """매수가능조회"""
        tr_id = TRID.PSBL_ORDER.get_id(self.is_virtual)
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

    def chk_holiday(self, base_dt: str) -> Dict[str, Any]:
        """국내휴장일조회 - base_dt: YYYYMMDD"""
        tr_id = TRID.HOLIDAY.get_id(self.is_virtual)
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
                    "tr_id": TRID.WS_PRICE.get_id(self.is_virtual),
                    "tr_key": symbol
                }
            }
        }
        return json.dumps(payload)
