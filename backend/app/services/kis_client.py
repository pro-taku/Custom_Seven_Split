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
- 주식 잔고 조회
- 매수 가능 조회
- 주식 예약 주문
- 주식 예약 주문 정정/취소
- 주식 예약 주문 조회
- 자산 조회

### [국내주식] 기본시세

- 주식현재가 시세

### [국내주식] 실시간시세

- 국내주식 실시간 호가 (KRX)
- 국내주식 실시간 체결 통보
"""

from enum import Enum
import httpx
from typing import Optional, Dict, Any, AsyncGenerator
import datetime
import hashlib
import hmac
import json

from backend.app.core.config import KIS_VIRTUAL_INVESTMENT_BASE_URL, KIS_REAL_INVESTMENT_BASE_URL

class KISClient:
    # KIS 관련 상수
    KIS_REAL_INVESTMENT_BASE_URL = "https://openapi.koreainvestment.com:9443"
    KIS_VIRTUAL_INVESTMENT_BASE_URL = "https://openapivts.koreainvestment.com:29443"

    KIS_REAL_ENV = 'real'
    KIS_VIRTUAL_ENV = 'demo'

    ORDER_TYPE_BUY = 'buy'
    ORDER_TYPE_SELL = 'sell'

    """
    TR ID 모음
    - KS : Korea Stock (국내주식)
    - R : Real (실전투자)
    - V : Virtual (모의투자)
    """
    class TR(Enum):
        TR_KS_SELL_R = 'TTTC0011U'              # 실전 매도
        TR_KS_SELL_V = 'VTTC0011U'              # 모의 매도
        TR_KS_BUY_R = 'TTTC0012U'               # 실전 매수
        TR_KS_BUY_V = 'VTTC0012U'               # 모의 매수
        TR_KS_BUY_POSSIBLE_R = 'TTTC8908R'      # 실전 매수 가능 여부
        TR_KS_BUY_POSSIBLE_V = 'VTTC8908R'      # 모의 매수 가능 여부
        TR_KS_FIX_CANCEL_R = 'TTTC0013U'        # 실전 정정/취소
        TR_KS_FIX_CANCEL_V = 'VTTC0013U'        # 모의 정정/취소
        TR_KS_RESV_ORDER_R = 'CTSC0008U'        # 실전 예약 매매 (모의 지원 X)
        TR_KS_RESV_CANCEL_R = 'CTSC0009U'       # 실전 예약 취소 (모의 지원 X)
        TR_KS_RESV_FIX_R = 'CTSC0013U'          # 실전 예약 정정 (모의 지원 X)
        TR_KS_RESV_SELECT_R = 'CTSC0004R'       # 실전 예약 조회 (모의 지원 X)
        TR_KS_ACCOUNT_R = 'TTTC8434R'           # 실전 주식잔고조회
        TR_KS_ACCOUNT_V = 'VTTC8434R'           # 모의 주식잔고조회
        TR_KS_ORDER_CHECK_R = 'H0STCNI0'        # 실전 실시간 체결통보
        TR_KS_ORDER_CHECK_V = 'H0STCNI9'        # 모의 실시간 체결통보
        TR_KS_PRICE_R = 'FHKST01010100'         # 실전 주식 현재가
        TR_KS_PRICE_V = 'FHKST01010100'         # 모의 주식 현재가
        TR_KS_RT_PRICE_R = 'H0STASP0'           # 실전 실시간 주식 호가
        TR_KS_RT_PRICE_V = 'H0STASP0'           # 모의 실시간 주식 호가
    
    def __init__(self, app_key: str, app_secret: str, account_num: str, is_virtual: bool = True):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_num = account_num
        self.is_virtual = is_virtual
        self.base_url = KIS_VIRTUAL_INVESTMENT_BASE_URL if is_virtual else KIS_REAL_INVESTMENT_BASE_URL
        self.ws_url = self.KIS_VIRTUAL_WS_URL if is_virtual else self.KIS_REAL_WS_URL
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime.datetime] = None
        self.approval_key: Optional[str] = None # Added for websocket
        self.http_client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)
    
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

        """
        웹소켓 접속키 발급 (Approval Key)
        """
        url = "/oauth2/Approval"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                if response.status_code == 200 and data.get("approval_key"):
                    self.approval_key = data["approval_key"] # Store the approval key
                    return self.approval_key
                else:
                    raise Exception(f"Failed to get websocket approval key: {data.get('msg1', 'Unknown error')}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error during websocket token issuance: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"Network error during websocket token issuance: {e}") from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred during websocket token issuance: {e}") from e

    async def _connect_websocket(self):
        """
        Establish a WebSocket connection.
        """
        if self.websocket_client and not self.websocket_client.closed:
            return # Already connected
        
        if not self.approval_key:
            await self.get_ws_token()
            if not self.approval_key:
                raise ValueError("Failed to obtain WebSocket approval key.")

        try:
            self.websocket_client = await websockets.connect(
                self.ws_url,
                extra_headers={
                    "appkey": self.app_key,
                    "appsecret": self.app_secret
                }
            )
            print(f"WebSocket connected to {self.ws_url}")
        except Exception as e:
            raise Exception(f"Failed to connect to WebSocket: {e}") from e

    async def _disconnect_websocket(self):
        """
        Close the WebSocket connection.
        """
        if self.websocket_client and not self.websocket_client.closed:
            await self.websocket_client.close()
            self.websocket_client = None
            print("WebSocket disconnected.")
    
    # OAuth 토큰 발급
    async def get_auth_token(self) -> str:
        """
        Issuance of Access Token.
        """
        # 이미 유효한 토큰을 가지고 있다면
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

    # OAuth 토큰 폐기
    async def revoke_auth_token(self) -> Dict[str, Any]:
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

    # 웹소켓 토큰 발급
    async def get_ws_token(self) -> str:
        pass

    async def _subscribe_websocket(self, tr_id: str, stock_code: str, tr_type: str = "1"):
        """
        Send a subscription request to the WebSocket.
        tr_type: 1 (체결), 2 (호가)
        """
        if not self.websocket_client or self.websocket_client.closed:
            await self._connect_websocket()

        header = {"approval_key": self.approval_key, "custtype": "P", "tr_type": tr_type, "content-type": "text/plain"}
        body = {"input": {"tr_id": tr_id, "tr_key": stock_code}}
        request_message = ["[HEADER]", json.dumps(header), "[BODY]", json.dumps(body)]
        
        try:
            await self.websocket_client.send("|".join(request_message))
            print(f"Subscribed to {stock_code} with TR_ID {tr_id}")
        except Exception as e:
            raise Exception(f"Failed to send WebSocket subscription message: {e}") from e

    # 현재가 조회
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

    # 실시간 현재가 조회
    async def get_rt_current_price(self, stock_code: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get real-time current price of a stock via WebSocket.
        [국내주식] 실시간시세 - 국내주식 실시간 호가 (KRX)
        TR_ID: H0STASP0
        """
        if not self.websocket_client or self.websocket_client.closed:
            await self._connect_websocket()

        # Subscribe to real-time quotes (tr_type="2" for 호가, "1" for 체결)
        await self._subscribe_websocket(tr_id=self.TR.TR_KS_RT_PRICE_R.value if not self.is_virtual else self.TR.TR_KS_RT_PRICE_V.value, 
                                        stock_code=stock_code, 
                                        tr_type="2") # Assuming tr_type "2" for 호가 as per documentation

        try:
            async for message in self.websocket_client:
                # KIS WebSocket messages often come in two parts: header and body
                if message.startswith("0|") or message.startswith("1|"):
                    header_str, body_str = message.split("|", 1)
                    header = json.loads(header_str)
                    body = json.loads(body_str)
                    yield {"header": header, "body": body}
                else:
                    # Handle other types of messages or keep raw
                    yield {"raw_message": message}
        except websockets.exceptions.ConnectionClosedOK:
            print("WebSocket connection closed normally.")
        except Exception as e:
            print(f"Error receiving WebSocket messages: {e}")
        finally:
            await self._disconnect_websocket()

    # 주식 주문 (현금)
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

    # 주식 주문 정정/취소 가능 여부
    async def check_if_order_corret_cancel_possible(self, order_date: str, product_code: str = "") -> Dict[str, Any]:
        """
        Check for correctable/cancelable stock orders.
        [국내주식] 주문/계좌 - 주식 정정/취소 가능 주문 조회
        TR_ID: TTTC0013U (실전), VTTC0013U (모의)
        """
        path = "/uapi/domestic-stock/v1/trading/inquire-daily-ccnl" # Assuming path based on common API patterns
        tr_id = self.TR.TR_KS_FIX_CANCEL_R.value if not self.is_virtual else self.TR.TR_KS_FIX_CANCEL_V.value

        params = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "ORD_DT": order_date, # YYYYMMDD
            "PDNO": product_code, # Optional, if empty, retrieves all orders
            "ORD_DVSN": "00", # All order divisions
            "SLL_BUY_DVSN": "00", # All sell/buy divisions
            "CCLD_DVSN": "00", # All correction/cancellation divisions
        }

        return await self._send_request("GET", path, tr_id, params=params)

    # 주식 주문 정정
    async def correct_order(self, original_order_no: str, stock_code: str, new_quantity: int, new_price: int, order_division: str = "00") -> Dict[str, Any]:
        """
        Correct an existing stock order.
        [국내주식] 주문/계좌 - 주식주문 (정정/취소)
        TR_ID: TTTC0013U (실전), VTTC0013U (모의)
        """
        path = "/uapi/domestic-stock/v1/trading/order-rvsecncl" # Assuming path for revision/cancellation
        tr_id = self.TR.TR_KS_FIX_CANCEL_R.value if not self.is_virtual else self.TR.TR_KS_FIX_CANCEL_V.value

        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "KRX_FWDG_ORD_ORGNO": "00000", # Not used for KIS, placeholder
            "ORGN_ORD_NO": original_order_no,
            "ORD_DVSN": order_division,
            "RVCN_CNCL_DVSN_CD": "01", # 01: 정정
            "ORD_QTY": str(new_quantity),
            "ORD_UNPR": str(new_price),
            "PDNO": stock_code,
        }

        return await self._send_request("POST", path, tr_id, json_data=payload, is_hashkey_required=True)
        
    # 주식 주문 취소
    async def cancel_order(self, original_order_no: str, order_division: str = "00") -> Dict[str, Any]:
        """
        Cancel an existing stock order.
        [국내주식] 주문/계좌 - 주식주문 (정정/취소)
        TR_ID: TTTC0013U (실전), VTTC0013U (모의)
        """
        path = "/uapi/domestic-stock/v1/trading/order-rvsecncl" # Assuming path for revision/cancellation
        tr_id = self.TR.TR_KS_FIX_CANCEL_R.value if not self.is_virtual else self.TR.TR_KS_FIX_CANCEL_V.value

        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "KRX_FWDG_ORD_ORGNO": "00000", # Not used for KIS, placeholder
            "ORGN_ORD_NO": original_order_no,
            "ORD_DVSN": order_division,
            "RVCN_CNCL_DVSN_CD": "02", # 02: 취소
            "ORD_QTY": "0", # Not applicable for cancellation, but required by API spec
            "ORD_UNPR": "0", # Not applicable for cancellation, but required by API spec
            "PDNO": "", # Not applicable for cancellation, but required by API spec
        }

        return await self._send_request("POST", path, tr_id, json_data=payload, is_hashkey_required=True)

    # 주식 예약 주문
    async def resvere_order(self, stock_code: str, quantity: int, price: int, order_division: str = "00", reserve_type: str = "00") -> Dict[str, Any]:
        """
        Place a reserved stock order.
        [국내주식] 주문/계좌 - 주식 예약 주문
        TR_ID: CTSC0008U (실전) - Note: KIS API documentation indicates no virtual support for reservation orders.
        """
        path = "/uapi/domestic-stock/v1/trading/exec-reserve" # Assuming path for executing reserve orders
        tr_id = self.TR.TR_KS_RESV_ORDER_R.value

        if self.is_virtual:
            raise ValueError("Reservation orders are not supported in virtual environment for KIS API.")

        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "PDNO": stock_code,
            "ORD_DVSN": order_division, # 00: 지정가, 01: 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price) if order_division == "00" else "0",
            "KRX_FWDG_ORD_ORGNO": "00000", # Not used for KIS, placeholder
            "TR_REG_GB": reserve_type, # 00: 일반예약, 01: 조건부예약
            "ORD_RVD_QTY": "", # Not directly used for initial order, but can be for revisions
            "TR_EXEC_YN": "N", # N: 예약 등록, Y: 예약 즉시 실행 (if conditions met)
        }

        return await self._send_request("POST", path, tr_id, json_data=payload, is_hashkey_required=True)

    # 주식 예약 주문 정정
    async def correct_resvered_order(self, original_reserve_no: str, stock_code: str, new_quantity: int, new_price: int, order_division: str = "00") -> Dict[str, Any]:
        """
        Correct an existing reserved stock order.
        [국내주식] 주문/계좌 - 주식 예약 주문 정정
        TR_ID: CTSC0013U (실전)
        """
        path = "/uapi/domestic-stock/v1/trading/modify-reserve" # Assuming path for modifying reserve orders
        tr_id = self.TR.TR_KS_RESV_FIX_R.value

        if self.is_virtual:
            raise ValueError("Reservation order corrections are not supported in virtual environment for KIS API.")

        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "PDNO": stock_code,
            "ORD_DVSN": order_division,
            "RSRV_ORD_NO": original_reserve_no,
            "ORD_QTY": str(new_quantity),
            "ORD_UNPR": str(new_price),
            "TR_REG_GB": "00", # Default to general reservation type for correction
        }

        return await self._send_request("POST", path, tr_id, json_data=payload, is_hashkey_required=True)

    # 주식 예약 주문 취소
    async def cancel_reserved_order(self, original_reserve_no: str) -> Dict[str, Any]:
        """
        Cancel an existing reserved stock order.
        [국내주식] 주문/계좌 - 주식 예약 주문 취소
        TR_ID: CTSC0009U (실전)
        """
        path = "/uapi/domestic-stock/v1/trading/cancel-reserve" # Assuming path for cancelling reserve orders
        tr_id = self.TR.TR_KS_RESV_CANCEL_R.value

        if self.is_virtual:
            raise ValueError("Reservation order cancellations are not supported in virtual environment for KIS API.")

        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:],
            "RSRV_ORD_NO": original_reserve_no,
            "KRX_FWDG_ORD_ORGNO": "00000", # Not used for KIS, placeholder
        }

        return await self._send_request("POST", path, tr_id, json_data=payload, is_hashkey_required=True)

    # 주식 잔고 조회
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

