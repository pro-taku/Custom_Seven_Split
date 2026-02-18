from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import base
from app.schemas import schemas

########################################################

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

########################################################

# 시스템 설정값 조회
@router.get("/", response_model=schemas.SystemSetting)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(base.SystemSetting).first()
    if not settings:
        # 만약 처음 실행했다면, DB에 SystemSetting 추가
        # (* 값 변경 필요)
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

# 시스템 설정값 업데이트
@router.put("/", response_model=schemas.SystemSetting)
def update_settings(settings_update: schemas.SystemSettingBase, db: Session = Depends(get_db)):
    settings = db.query(base.SystemSetting).first()
    if not settings:
        settings = base.SystemSetting(**settings_update.model_dump())
        db.add(settings)
    else:
        for key, value in settings_update.model_dump().items():
            setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return settings
