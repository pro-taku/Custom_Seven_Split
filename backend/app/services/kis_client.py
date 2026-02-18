import httpx
from typing import Optional, Dict, Any
import datetime

"""
지금 얘가 제일 중요한데, 사용법을 아직 못 익혔음
"""
class KISClient:
    def __init__(self, app_key: str, app_secret: str, account_num: str, is_virtual: bool = True):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_num = account_num
        self.is_virtual = is_virtual
        self.base_url = "https://openapivts.koreainvestment.com:29443" if is_virtual else "https://openapi.koreainvestment.com:9443"
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime.datetime] = None

    # API를 쓰기 위해 token 가져오기
    async def get_access_token(self) -> str:
        """
        Issuance of Access Token.
        """
        if self.access_token and self.token_expiry and self.token_expiry > datetime.datetime.now():
            return self.access_token

        # 여기 나중에 수정할 것
        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
            
            if response.status_code == 200:
                self.access_token = data["access_token"]
                # Token is valid for 24 hours, but let's refresh a bit earlier.
                expires_in = data.get("expires_in", 86400)
                self.token_expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 3600)
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {data}")

    # 현재가 불러오기
    async def get_current_price(self, stock_code: str) -> int:
        """
        Get current price of a stock.
        """
        token = await self.get_access_token()
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            data = response.json()
            
            if response.status_code == 200 and data.get("rt_cd") == "0":
                return int(data["output"]["stck_prpr"])
            else:
                raise Exception(f"Failed to get current price for {stock_code}: {data}")

    # 주문 요청
    async def place_order(self, stock_code: str, quantity: int, price: int, side: str = "BUY") -> Dict[str, Any]:
        """
        Place a buy or sell order.
        side: "BUY" (VTTC0802U) or "SELL" (VTTC0801U) for virtual.
        Real: "TTTC0802U" (BUY), "TTTC0801U" (SELL).
        """
        token = await self.get_access_token()
        
        # Determine tr_id based on side and environment
        if self.is_virtual:
            tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side == "BUY" else "TTTC0801U"
            
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
        
        # Account number formatting: first 8 digits and last 2 digits
        payload = {
            "CANO": self.account_num[:8],
            "ACNT_PRDT_CD": self.account_num[8:] if len(self.account_num) > 8 else "01",
            "PDNO": stock_code,
            "ORD_DVSN": "00", # Market price: 01, Limit price: 00
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price) if side == "SELL" or tr_id.endswith("U") else "0", # For market price BUY, use "0"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            return data
