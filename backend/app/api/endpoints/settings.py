from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import base
from app.schemas import schemas

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=schemas.SystemSetting)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(base.SystemSetting).first()
    if not settings:
        # Create default if not exists
        settings = base.SystemSetting(
            account_num="00000000",
            app_key="YOUR_APP_KEY",
            app_secret="YOUR_APP_SECRET",
            is_virtual=True
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/", response_model=schemas.SystemSetting)
def update_settings(settings_update: schemas.SystemSettingBase, db: Session = Depends(get_db)):
    settings = db.query(base.SystemSetting).first()
    if not settings:
        settings = base.SystemSetting(**settings_update.dict())
        db.add(settings)
    else:
        for key, value in settings_update.dict().items():
            setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return settings
