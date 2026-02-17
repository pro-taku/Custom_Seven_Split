from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.models import base
from app.schemas import schemas

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.StockStrategy)
def create_strategy(strategy: schemas.StockStrategyCreate, db: Session = Depends(get_db)):
    db_strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == strategy.stock_code).first()
    if db_strategy:
        raise HTTPException(status_code=400, detail="Strategy for this stock code already exists")
    
    new_strategy = base.StockStrategy(**strategy.dict())
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    return new_strategy

@router.get("/", response_model=List[schemas.StockStrategy])
def read_strategies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    strategies = db.query(base.StockStrategy).offset(skip).limit(limit).all()
    return strategies

@router.get("/{stock_code}", response_model=schemas.StockStrategy)
def read_strategy(stock_code: str, db: Session = Depends(get_db)):
    strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == stock_code).first()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@router.put("/{stock_code}", response_model=schemas.StockStrategy)
def update_strategy(stock_code: str, strategy_update: schemas.StockStrategyCreate, db: Session = Depends(get_db)):
    db_strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == stock_code).first()
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    for key, value in strategy_update.dict().items():
        setattr(db_strategy, key, value)
    
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@router.delete("/{stock_code}")
def delete_strategy(stock_code: str, db: Session = Depends(get_db)):
    db_strategy = db.query(base.StockStrategy).filter(base.StockStrategy.stock_code == stock_code).first()
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db.delete(db_strategy)
    db.commit()
    return {"message": "Strategy deleted successfully"}
