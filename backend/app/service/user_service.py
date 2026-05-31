from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.session.user_session import UserSession
from app.lib.kis_client import KISClient

class UserService():
    def __init__(self, db: Session):
        self.user_session = UserSession(db)

    def create_user(self, appkey: str, appsecret: str, account_number: str):
        """
        UserSession.create() 메서드를 호출하여 새로운 유저를 데이터베이스에 추가한다.

        appkey, appsecret, account_number를 이 함수의 입력값으로 받고,
        appkey, appsecret을 사용하여 KIS API로 접근토큰과 웹소켓 토큰을 발급받는다.
        그리고, DB에 appkey, appsecret, token, websocket, expiration, account_number 정보를 저장한다.
        """
        client = KISClient(appkey, appsecret, account_number)
        token_data = client.get_access_token()
        ws_token = client.get_approval_key()
        
        user_data = {
            "appkey": appkey,
            "appsecret": appsecret,
            "token": token_data.get("access_token"),
            "websocket": ws_token,
            "expiration": token_data.get("access_token_token_expired"),
            "account_number": account_number
        }
        
        return self.user_session.create(user_data)

    def update_user(self, appkey: str, appsecret: str, update_data: dict):
        """
        UserSession.update() 메서드를 호출하여 기존 유저의 정보를 업데이트한다.
        주로 접근토큰 또는 웹소켓 토큰이 만료되었을 때, 새로운 토큰으로 업데이트하는 용도로 사용된다.

        함수 입력값으로 appkey, appsecret, update_data를 받는다.
        update_data는 업데이트할 필드와 값을 포함하는 딕셔너리 형태로 전달된다.
        PK인 appkey와 appsecret을 사용하여 해당 유저를 조회한 후, update_data에 포함된 필드들을 업데이트한다.
        """
        return self.user_session.update(appkey, appsecret, update_data)

    def delete_user(self, appkey: str, appsecret: str):
        """
        UserSession.delete() 메서드를 호출하여 기존 유저를 데이터베이스에서 삭제한다.

        함수 입력값으로 appkey와 appsecret을 받는다.
        PK인 appkey와 appsecret을 사용하여 해당 유저를 조회한 후, 유저를 삭제한다.
        """
        return self.user_session.delete(appkey, appsecret)

    def login(self, appkey: str, appsecret: str):
        """
        appkey와 appsecret을 사용하여 db에서 유저를 조회한다
        조회했을 때 토큰이 만료됐거나 없다면, KIS API로 접근토큰과 웹소켓 토큰을 발급받는다.
        그리고, user_update() 메서드를 호출하여 DB에 토큰과 만료시간을 업데이트한다.
        """
        user = self.user_session.get_by_pk(appkey, appsecret)

        if not user or not user.token or not user.websocket or not user.expiration:
            return self.create_user(appkey, appsecret, account_number=None)
        
        try:
            exp_time = datetime.strptime(user.expiration, "%Y-%m-%d %H:%M:%S")
            if exp_time <= datetime.now():
                return self.update_user(appkey, appsecret, account_number=user.account_number)
        except ValueError:
            return self.create_user(appkey, appsecret, account_number=user.account_number)

        return user

    def logout(self, appkey: str, appsecret: str):
        """
        appkey와 appsecret을 사용하여 db에서 유저를 조회한다
        조회된 user의 토큰과 웹소켓 토큰을 삭제한다.
        """
        update_data = {
            "token": None,
            "websocket": None
        }
        return self.update_user(appkey, appsecret, update_data)

    def get_token(self, appkey: str, appsecret: str) -> Optional[Dict[str, Any]]:
        """DB에서 유저 정보를 조회하여 KIS API로 접근토큰과 웹소켓 토큰을 발급받는다."""
        user = self.user_session.get_by_pk(appkey, appsecret)
        if not user:
            return None
        
        client = KISClient(appkey, appsecret, user.account_number)
        token_data = client.get_access_token()
        ws_token = client.get_approval_key()
        
        return {
            "token": token_data.get("access_token"),
            "websocket": ws_token,
            "expiration": token_data.get("access_token_token_expired")
        }

    def validate_token(self, appkey: str, appsecret: str) -> bool:
        """
        appkey와 appsecret을 사용하여 db에서 유저를 조회한다
        조회된 user의 토큰의 만료기간을 확인한다
        만료기간이 지났다면 False, 만료기간이 지나지 않았다면 True를 반환한다.
        """
        user = self.user_session.get_by_pk(appkey, appsecret)
        if not user or not user.expiration:
            return False
            
        try:
            exp_time = datetime.strptime(user.expiration, "%Y-%m-%d %H:%M:%S")
            return exp_time > datetime.now()
        except ValueError:
            return False
