from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

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

# 새 감시전략 생성
@router.post("/", response_model=schemas.StockStrategy)
def create_strategy(strategy: schemas.StockStrategyBase, db: Session = Depends(get_db)):
    # 해당 종목의 전략이 존재한다면, HTTP 예외처리
    db_strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == strategy.stock_code).first()
    if db_strategy:
        raise HTTPException(status_code=400, detail="Strategy for this stock code already exists")
    
    new_strategy = base.StockStrategy(**strategy.model_dump())
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    return new_strategy

# 감시전략 리스트 조회
@router.get("/", response_model=List[schemas.StockStrategy])
def read_strategies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    strategies = db.query(base.StockStrategy).offset(skip).limit(limit).all()
    return strategies

# 특정 종목의 감시전략 조회
@router.get("/{stock_code}", response_model=schemas.StockStrategy)
def read_strategy(stock_code: str, db: Session = Depends(get_db)):
    # 이 종목의 감시전략이 없다면, HTTP 예외처리
    strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == stock_code).first()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

# 특정 종목의 감시전략 수정
@router.put("/{stock_code}", response_model=schemas.StockStrategy)
def update_strategy(stock_code: str, strategy_update: schemas.StockStrategyBase, db: Session = Depends(get_db)):
    # 이 종목의 감시전략이 없다면, HTTP 예외처리
    db_strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == stock_code).first()
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # 속성값 변경
    for key, value in strategy_update.model_dump().items():
        setattr(db_strategy, key, value)
    
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

# 특정 종목 감시전략 삭제
@router.delete("/{stock_code}")
def delete_strategy(stock_code: str, db: Session = Depends(get_db)):
    # 이 종목의 감시전략이 없다면, HTTP 예외처리
    db_strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == stock_code).first()
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db.delete(db_strategy)
    db.commit()
    return {"message": "Strategy deleted successfully"}
