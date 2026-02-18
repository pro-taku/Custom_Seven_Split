"""
## 한국투자증권(KIS) API에서 필요한 기능

### OAuth

- 접근 토큰 발급
- 접근 토큰 폐기
- HashKey
- 실시간 웹소켓 접속키 발급

### [국내주식] 주문/계좌

- 주식주문 (현금)
- 주식주문 (정정/취소)
- 주식 정정/취소 가능 주문 조회
- 주식 일별 주문 체결 조회
- 주식 잔고 조회
- 매수 가능 조회
- 매도 가능 수량 조회
- 주식 예약 주문
- 주식 예약 주문 정정/취소
- 주식 예약 주문 조회
- 주식 예약 주문
- 투자 계좌 자산 현황 조회

### [국내주식] 기본시세

- 주식현재가 시세

### [국내주식] 종목정보

- 주식기본조회

### [국내주식] 실시간시세

- 국내주식 실시간 호가 (KRX)
"""

import httpx
from typing import Optional, Dict, Any
import datetime
import hashlib
import hmac # Import hmac
import json # Import json

class KISClient:
    def __init__(self, app_key: str, app_secret: str, account_num: str, is_virtual: bool = True):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_num = account_num
        self.is_virtual = is_virtual
        self.base_url = "https://openapivts.koreainvestment.com:29443" if is_virtual else "https://openapi.koreainvestment.com:9443"
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime.datetime] = None
        # It's better to manage httpx.AsyncClient as a single instance for connection pooling.
        self.http_client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0) # Add a timeout

    async def _send_request(self, method: str, path: str, tr_id: str,
                             headers: Optional[Dict] = None, params: Optional[Dict] = None,
                             json_data: Optional[Dict] = None, is_hashkey_required: bool = False) -> Dict[str, Any]:
        """
        Helper method to send requests to the KIS API.
        Handles access token, common headers, and response parsing.
        """
        if not self.access_token or (self.token_expiry and self.token_expiry <= datetime.datetime.now()):
            await self.get_access_token()

        default_headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P", # Personal customer
            "gt_id": tr_id, # Guidance TR_ID, often same as tr_id for non-realtime
        }
        
        # Override tr_id for specific scenarios if needed, e.g., for hashkey calculation
        if tr_id.startswith("V") and not self.is_virtual:
             raise ValueError(f"Virtual TR_ID {tr_id} used in real environment.")
        if not tr_id.startswith("V") and self.is_virtual:
             raise ValueError(f"Real TR_ID {tr_id} used in virtual environment.")

        if headers:
            default_headers.update(headers)

        if is_hashkey_required and json_data:
            default_headers["hashkey"] = self._get_hashkey(json_data)
        elif is_hashkey_required and not json_data:
            raise ValueError("Hashkey required but no JSON data provided for hashing.")


        try:
            if method.upper() == "GET":
                response = await self.http_client.get(path, headers=default_headers, params=params)
            elif method.upper() == "POST":
                response = await self.http_client.post(path, headers=default_headers, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            # KIS API often returns 'rt_cd' as '0' for success.
            # However, for some error cases, it might return 200 OK with an error code in body.
            if data.get("rt_cd") != "0":
                raise Exception(f"KIS API Error ({data.get('rt_cd')}): {data.get('msg1', 'Unknown error')}")

            return data

        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error occurred: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"An error occurred while requesting {e.request.url!r}: {e}") from e
        except Exception as e:
            # Catching generic Exception for KIS API specific errors like rt_cd != "0"
            raise Exception(f"An unexpected error occurred: {e}") from e

    def _get_hashkey(self, payload: Dict[str, Any]) -> str:
        """
        Generate HashKey for signing request bodies using HMAC-SHA256.
        """
        if not self.app_secret:
            raise ValueError("App secret must be set to generate hash key.")
        
        payload_str = json.dumps(payload, ensure_ascii=False)
        
        # KIS API hashkey generation: HMAC-SHA256 with appsecret as key, and request body as message.
        hashed = hmac.new(
            self.app_secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        )
        return hashed.hexdigest()

    async def get_access_token(self) -> str:
        """
        Issuance of Access Token.
        """
        if self.access_token and self.token_expiry and self.token_expiry > datetime.datetime.now():
            return self.access_token

        url = "/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        try:
            # For token issuance, we use a fresh AsyncClient to avoid potential issues
            # if the main client is somehow in a bad state or for specific token endpoint requirements.
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if response.status_code == 200 and data.get("access_token"):
                    self.access_token = data["access_token"]
                    # Token is valid for 24 hours, refresh 1 hour early to be safe.
                    expires_in = data.get("expires_in", 86400) # Default to 24 hours if not provided
                    self.token_expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 3600)
                    return self.access_token
                else:
                    raise Exception(f"Failed to get access token: {data.get('msg1', 'Unknown error')}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error during token issuance: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"Network error during token issuance: {e}") from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred during token issuance: {e}") from e

    async def revoke_access_token(self) -> Dict[str, Any]:
        """
        Revocation of Access Token.
        """
        url = "/oauth2/revokeP"
        payload = {
            "appkey": self.app_key,
            "secretkey": self.app_secret,
            "token": self.access_token if self.access_token else "" # Send empty string if token is None
        }
        
        try:
            # Similar to get_access_token, use a fresh client for revocation
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if response.status_code == 200 and data.get("rt_cd") == "0":
                    self.access_token = None
                    self.token_expiry = None
                    return data
                else:
                    raise Exception(f"Failed to revoke access token: {data.get('msg1', 'Unknown error')}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error during token revocation: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"Network error during token revocation: {e}") from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred during token revocation: {e}") from e

    async def get_current_price(self, stock_code: str) -> int:
        """
        Get current price of a stock.
        [국내주식] 기본시세 - 주식현재가 시세
        TR_ID: FHKST01010100
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        tr_id = "FHKST01010100"
        params = {
            "fid_cond_mrkt_div_code": "J", # J: 주식
            "fid_input_iscd": stock_code
        }
        
        data = await self._send_request("GET", path, tr_id, params=params)
        return int(data["output"]["stck_prpr"])

    async def place_order(self, stock_code: str, quantity: int, price: int, side: str = "BUY", order_division: str = "00") -> Dict[str, Any]:
        """
        Place a buy or sell order.
        [국내주식] 주문/계좌 - 주식주문 (현금)
        Virtual Buy: VTTC0802U, Virtual Sell: VTTC0801U
        Real Buy: TTTC0802U, Real Sell: TTTC0801U
        order_division: "00" (지정가), "01" (시장가)
        """
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        
        if self.is_virtual:
            tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side == "BUY" else "TTTC0801U"
            
        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "PDNO": stock_code,
            "ORD_DVSN": order_division, # 00: 지정가, 01: 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price) if order_division == "00" else "0", # 지정가일 경우 가격, 시장가 매수일 경우 "0"
        }
        
        return await self._send_request("POST", path, tr_id, json_data=payload, is_hashkey_required=True)

    async def get_stock_balance(self) -> Dict[str, Any]:
        """
        Get stock balance.
        [국내주식] 주문/계좌 - 주식 잔고 조회
        TR_ID: TTTC8434R (실전), VTTC8434R (모의)
        """
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        tr_id = "VTTC8434R" if self.is_virtual else "TTTC8434R"
        
        params = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "FID_COND_MRKT_DIV_CODE": "J", # J: 주식
            "FID_ETC_CLS_CODE": "0" # 0: 전체
        }
        
        return await self._send_request("GET", path, tr_id, params=params)

    async def get_daily_order_conclusion(self, start_date: str, end_date: str, sll_buy_dvsn_code: str = "00", inqr_dvsn: str = "01", pdno: str = "", ccld_dvsn: str = "00") -> Dict[str, Any]:
        """
        Get daily order conclusion.
        [국내주식] 주문/계좌 - 주식 일별 주문 체결 조회
        TR_ID: TTTC8001R (실전), VTTC8001R (모의)
        start_date, end_date format: YYYYMMDD
        sll_buy_dvsn_code: "00" (전체), "01" (매도), "02" (매수)
        inqr_dvsn: "01" (잔고수량), "02" (주문수량)
        pdno: 종목번호, 전부 조회 시 공백
        ccld_dvsn: "00" (전체), "01" (체결), "02" (미체결)
        """
        path = "/uapi/domestic-stock/v1/trading/inquire-daily-concluded"
        tr_id = "VTTC8001R" if self.is_virtual else "TTTC8001R"
        
        params = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "INQR_STRT_DT": start_date,
            "INQR_END_DT": end_date,
            "SLL_BUY_DVSN_CODE": sll_buy_dvsn_code,
            "INQR_DVSN": inqr_dvsn,
            "PDNO": pdno,
            "CCLD_DVSN": ccld_dvsn,
            "CTX_AREA_FK100": "", # 연속조회용
            "CTX_AREA_NK100": ""  # 연속조회용
        }
        
        return await self._send_request("GET", path, tr_id, params=params)

    async def get_invest_account_asset_status(self) -> Dict[str, Any]:
        """
        Get investor account asset status.
        [국내주식] 주문/계좌 - 투자 계좌 자산 현황 조회
        TR_ID: TTTC8436R (실전), VTTC8436R (모의)
        """
        path = "/uapi/domestic-stock/v1/trading/inquire-ccnl"
        tr_id = "VTTC8436R" if self.is_virtual else "TTTC8436R"

        params = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "FID_BCNT_NO": "", # 명칭별 일련번호
            "FID_DIV_CLS_CODE": "0", # 0: 전체, 1: 주식, 2: 펀드, ...
            "FID_COND_MRKT_DIV_CODE": "J", # J: 주식
            "FID_INPUT_ISCD": "" # 종목번호, 전체 조회 시 공백
        }
        
        return await self._send_request("GET", path, tr_id, params=params)

    async def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        Get basic stock information.
        [국내주식] 종목정보 - 주식기본조회
        TR_ID: FHKST01010100 (This TR_ID is also used for current price, and its output
                                 contains basic stock information as well.
                                 If a more specific "basic info only" TR_ID/endpoint exists, it should be used.)
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        tr_id = "FHKST01010100"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code
        }

        data = await self._send_request("GET", path, tr_id, params=params)
        return data["output"] # Return the whole output as it contains basic info
