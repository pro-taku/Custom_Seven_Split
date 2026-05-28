from sqlalchemy.orm import Session
from app.table.user_table import User
from typing import Optional, List

class UserSession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_data: dict) -> User:
        db_user = User(**user_data)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_by_pk(self, appkey: str, appsecret: str) -> Optional[User]:
        return self.db.query(User).filter_by(appkey=appkey, appsecret=appsecret).first()

    def get_by_account_number(self, account_number: str) -> Optional[User]:
        return self.db.query(User).filter_by(account_number=account_number).first()

    def get_all(self) -> List[User]:
        return self.db.query(User).all()

    def update(self, appkey: str, appsecret: str, update_data: dict) -> Optional[User]:
        db_user = self.get_by_pk(appkey, appsecret)
        if db_user:
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def delete(self, appkey: str, appsecret: str) -> bool:
        db_user = self.get_by_pk(appkey, appsecret)
        if db_user:
            self.db.delete(db_user)
            self.db.commit()
            return True
        return False
