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

    def get_by_appkey(self, appkey: str) -> Optional[User]:
        return self.db.query(User).filter(User.appkey == appkey).first()

    def get_all(self) -> List[User]:
        return self.db.query(User).all()

    def update(self, appkey: str, update_data: dict) -> Optional[User]:
        db_user = self.get_by_appkey(appkey)
        if db_user:
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def delete(self, appkey: str) -> bool:
        db_user = self.get_by_appkey(appkey)
        if db_user:
            self.db.delete(db_user)
            self.db.commit()
            return True
        return False
