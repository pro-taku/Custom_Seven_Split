from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

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

@router.post("/cashflow", response_model=schemas.CashFlow)
def create_cash_flow(cash_flow: schemas.CashFlowBase, db: Session = Depends(get_db)):
    new_flow = base.CashFlow(**cash_flow.dict())
    db.add(new_flow)
    db.commit()
    db.refresh(new_flow)
    return new_flow

@router.get("/cashflow", response_model=List[schemas.CashFlow])
def read_cash_flows(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    flows = db.query(base.CashFlow).order_by(base.CashFlow.created_at.desc()).offset(skip).limit(limit).all()
    return flows

@router.get("/summary", response_model=schemas.DailySummary)
def get_latest_summary(db: Session = Depends(get_db)):
    summary = db.query(base.DailySummary).order_by(base.DailySummary.date.desc()).first()
    if summary is None:
        # Return a dummy summary if none exists
        return schemas.DailySummary(date="2026-01-01", total_asset=0, total_invested=0, daily_profit=0)
    return summary
