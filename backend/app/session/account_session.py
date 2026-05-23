from sqlalchemy.orm import Session
from app.table.account_table import Account
from typing import Optional, List

class AccountSession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, account_data: dict) -> Account:
        db_account = Account(**account_data)
        self.db.add(db_account)
        self.db.commit()
        self.db.refresh(db_account)
        return db_account

    def get_by_number(self, account_number: str) -> Optional[Account]:
        return self.db.query(Account).filter(Account.account_number == account_number).first()

    def get_all(self) -> List[Account]:
        return self.db.query(Account).all()

    def update(self, account_number: str, update_data: dict) -> Optional[Account]:
        db_account = self.get_by_number(account_number)
        if db_account:
            for key, value in update_data.items():
                setattr(db_account, key, value)
            self.db.commit()
            self.db.refresh(db_account)
        return db_account

    def delete(self, account_number: str) -> bool:
        db_account = self.get_by_number(account_number)
        if db_account:
            self.db.delete(db_account)
            self.db.commit()
            return True
        return False
