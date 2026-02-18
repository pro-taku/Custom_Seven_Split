from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date # Added for DailySummary

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

# db에 cashflow 테이블 추가
@router.post("/cashflow", response_model=schemas.CashFlow)
def create_cash_flow(cash_flow: schemas.CashFlowBase, db: Session = Depends(get_db)):
    new_flow = base.CashFlow(**cash_flow.model_dump())
    db.add(new_flow)
    db.commit()
    db.refresh(new_flow)
    return new_flow

# db에서 cashflow 리스트 조회
# 생성일자에 따라 정렬하고, 'skip'번째부터 'limit'까지 Row를 반환
@router.get("/cashflow", response_model=List[schemas.CashFlow])
def read_cash_flows(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    flows = db.query(base.CashFlow).order_by(base.CashFlow.created_at.desc()).offset(skip).limit(limit).all()
    return flows

# cashflow 테이블에서 제일 최신 Row 불러오기
@router.get("/summary", response_model=schemas.DailySummary)
def get_latest_summary(db: Session = Depends(get_db)):
    summary = db.query(base.DailySummary).order_by(base.DailySummary.date.desc()).first()
    if summary is None:
        # Return a dummy summary if none exists
        return schemas.DailySummary(date="2026-01-01", total_asset=0, total_invested=0, daily_profit=0)
    return summary

# 누적 순입금액 조회 (투자 원금)
@router.get("/cumulative-cashflow", response_model=schemas.CumulativeCashFlow)
def get_cumulative_cash_flow(db: Session = Depends(get_db)):
    deposits = db.query(base.CashFlow).filter(base.CashFlow.flow_type == "DEPOSIT").sum(base.CashFlow.amount) or 0
    withdrawals = db.query(base.CashFlow).filter(base.CashFlow.flow_type == "WITHDRAW").sum(base.CashFlow.amount) or 0
    
    return schemas.CumulativeCashFlow(
        cumulative_deposit=deposits,
        cumulative_withdraw=withdrawals,
        net_deposit=deposits - withdrawals
    )

# 총 확정 수익 조회
@router.get("/total-realized-profit", response_model=schemas.TotalRealizedProfit)
def get_total_realized_profit(db: Session = Depends(get_db)):
    total_profit = db.query(base.TradeHistory).filter(base.TradeHistory.realized_profit != None).sum(base.TradeHistory.realized_profit) or 0
    return schemas.TotalRealizedProfit(total_realized_profit=total_profit)

# 투자 수익률 (ROI) 조회
@router.get("/roi", response_model=schemas.ROIReport)
def get_roi(db: Session = Depends(get_db)):
    # 1. 누적 순입금액 계산
    deposits = db.query(base.CashFlow).filter(base.CashFlow.flow_type == "DEPOSIT").sum(base.CashFlow.amount) or 0
    withdrawals = db.query(base.CashFlow).filter(base.CashFlow.flow_type == "WITHDRAW").sum(base.CashFlow.amount) or 0
    net_deposit = deposits - withdrawals

    # 2. 현재 총 자산 조회 (최신 DailySummary 사용)
    latest_summary = db.query(base.DailySummary).order_by(base.DailySummary.date.desc()).first()
    current_total_asset = latest_summary.total_asset if latest_summary else 0

    # 3. ROI 계산
    roi = 0.0
    if net_deposit > 0:
        roi = ((current_total_asset - net_deposit) / net_deposit) * 100

    return schemas.ROIReport(
        current_total_asset=current_total_asset,
        net_deposit=net_deposit,
        roi=roi
    )

