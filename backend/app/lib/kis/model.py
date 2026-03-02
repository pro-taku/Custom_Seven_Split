from datetime import datetime

from pydantic import BaseModel, Field


# --- Common Models ---
class KISBaseResponse(BaseModel):
    """Common fields for KIS API responses."""

    rt_cd: str = Field(description="성패 여부 (0: 성공, 1: 실패)")
    msg_cd: str = Field(description="응답 코드")
    msg1: str = Field(description="응답 메시지")


class KISRequestHeader(BaseModel):
    """Common headers for KIS API requests."""

    Content_Type: str = Field(
        default="application/json; charset=utf-8",
        alias="Content-Type",
    )
    Authorization: str | None = Field(None, description="Bearer + Access Token")
    AppKey: str = Field(description="발급받은 APP KEY", alias="appkey")
    AppSecret: str = Field(description="발급받은 APP SECRET", alias="appsecret")
    tr_id: str = Field(description="거래 ID", alias="tr_id")
    custtype: str = Field(
        default="P",
        description="고객 타입 (P: 개인, B: 법인)",
        alias="custtype",
    )
    hashkey: str | None = Field(
        None,
        description="HashKey (주식주문 시 필수)",
        alias="hashkey",
    )


class KISResponseHeader(BaseModel):
    """Common headers for KIS API responses."""

    Content_Type: str = Field(alias="Content-Type")
    tr_id: str = Field(description="거래 ID", alias="tr_id")
    tr_cont: str | None = Field(
        None,
        description="연속 거래 여부 (F: 연속, M: 마지막, D: 단건, E: 오류)",
        alias="tr_cont",
    )
    # For some responses, like WebSocket, there might be other fields, but this is for HTTP.


# --- 1. 접근 토큰 발급 (OAuth2 TokenP) ---
class OAuth2TokenPRequest(BaseModel):
    grant_type: str = Field(default="client_credentials", description="인증 타입")
    appkey: str = Field(description="발급받은 APP KEY")
    appsecret: str = Field(description="발급받은 APP SECRET")


class OAuth2TokenPResponse(BaseModel):
    access_token: str = Field(description="접근 토큰")
    access_token_token_expired: datetime = Field(
        description="접근 토큰 만료 시간 (YYYY-MM-DD HH:MM:SS)",
    )
    expires_in: int = Field(description="접근 토큰 유효 시간 (초)")
    token_type: str = Field(description="토큰 타입 (Bearer)")


# --- 2. 접근 토큰 폐기 (OAuth2 RevokeP) ---
class OAuth2RevokePRequest(BaseModel):
    appkey: str = Field(description="발급받은 APP KEY")
    appsecret: str = Field(description="발급받은 APP SECRET")
    token: str = Field(description="폐기할 접근 토큰")


class OAuth2RevokePResponse(KISBaseResponse):
    # KIS API Revoke response *does* include rt_cd, msg_cd, msg1
    pass


# --- 3. 웹소켓 접속키 발급 (OAuth2 Approval) ---
class OAuth2ApprovalRequest(BaseModel):
    grant_type: str = Field(default="client_credentials", description="인증 타입")
    appkey: str = Field(description="발급받은 APP KEY")
    secretkey: str = Field(description="발급받은 APP SECRET")


class OAuth2ApprovalResponse(BaseModel):
    approval_key: str = Field(description="웹소켓 접속 키")
    approval_key_token_expired: datetime = Field(
        description="웹소켓 접속 키 만료 시간 (YYYY-MM-DD HH:MM:SS)",
    )
    expires_in: int = Field(description="웹소켓 접속 키 유효 시간 (초)")


# --- 4. 주식주문 (현금) (Order Cash) ---
class OrderCashRequestHeader(KISRequestHeader):
    tr_id: str = Field(
        description="거래 ID (TTTC0012U: 매수, TTTC0011U: 매도, VTTC0012U: 모의매수, VTTC0011U: 모의매도)",
    )
    hashkey: str | None = Field(
        None,
        description="HashKey (주식주문 시 필수)",
        alias="hashkey",
    )


class OrderCashRequestBody(BaseModel):
    CANO: str = Field(description="종합계좌번호 (8자리)")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 (2자리)")
    PDNO: str = Field(description="종목코드 (6자리)")
    ORD_DVSN: str = Field(description="주문구분 (00: 지정가, 01: 시장가 등)")
    ORD_QTY: str = Field(description="주문수량")  # KIS API는 수량을 string으로 받음
    ORD_UNPR: str = Field(
        description="주문단가 (지정가 시 필수)",
    )


class OrderCashResponseOutput(BaseModel):
    KRX_FWDG_ORD_ORGNO: str = Field(description="거래소전송주문조직번호")
    ODNO: str = Field(description="주문번호")
    ORD_TMD: str = Field(description="주문시각 (HHMMSS)")


class OrderCashResponse(KISBaseResponse):
    output: OrderCashResponseOutput | None = Field(None, description="응답 데이터")


# --- 5. 주식주문 (정정취소) (Order Rvsecncl) ---
class OrderRvsecnclRequestHeader(KISRequestHeader):
    tr_id: str = Field(
        description="거래 ID (TTTC0013U: 실전 정정/취소, VTTC0013U: 모의 정정/취소)",
    )
    hashkey: str | None = Field(
        None,
        description="HashKey (주식주문 시 필수)",
        alias="hashkey",
    )


class OrderRvsecnclRequestBody(BaseModel):
    CANO: str = Field(description="종합계좌번호 (8자리)")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 (2자리)")
    KRX_FWDG_ORD_ORGNO: str = Field(description="한국거래소전송주문조직번호")
    ORGN_ODNO: str = Field(description="원주문번호")
    PDNO: str = Field(description="종목코드 (6자리)")
    RVSE_CNCL_DVSN_CD: str = Field(description="정정/취소구분코드 (01: 정정, 02: 취소)")
    ORD_DVSN: str = Field(description="주문구분 (00: 지정가 등)")
    ORD_QTY: str = Field(description="주문수량")
    ORD_UNPR: str = Field(description="주문단가 (정정 시 필수)")
    QTY_ALL_ORD_YN: str = Field(description="잔량/전부 주문 여부 (Y: 전부, N: 잔량)")


class OrderRvsecnclResponseOutput(BaseModel):
    KRX_FWDG_ORD_ORGNO: str = Field(description="거래소전송주문조직번호")
    ODNO: str = Field(description="주문번호")
    ORD_TMD: str = Field(description="주문시각 (HHMMSS)")


class OrderRvsecnclResponse(KISBaseResponse):
    output: OrderRvsecnclResponseOutput | None = Field(
        None,
        description="응답 데이터",
    )


# --- 6. 주식정정취소가능주문조회 (Inquire Psbl Rvsecncl) ---
class InquirePsblRvsecnclRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (TTTC8031R: 실전, VTTC8031R: 모의)")
    tr_cont: str | None = Field(
        None,
        description="연속 거래 여부 (공백: 처음, N: 다음 페이지)",
    )


class InquirePsblRvsecnclRequestQuery(BaseModel):
    CANO: str = Field(description="계좌번호 앞 8자리")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 뒤 2자리")
    CTX_AREA_FK100: str | None = Field(
        "",
        description="연속 거래 시 이전 응답의 FK100",
    )
    CTX_AREA_NK100: str | None = Field(
        "",
        description="연속 거래 시 이전 응답의 NK100",
    )
    INQR_DVSN_1: str = Field(description="조회구분1 (0: 주문, 1: 종목)")
    INQR_DVSN_2: str = Field(description="조회구분2 (0: 전체, 1: 매도, 2: 매수)")


class InquirePsblRvsecnclResponseOutput(BaseModel):
    ord_gno_brno: str = Field(description="주문채번지점번호")
    odno: str = Field(description="주문번호")
    orgn_odno: str = Field(description="원주문번호")
    pdno: str = Field(description="종목번호")
    prdt_name: str = Field(description="종목이름")
    rvse_cncl_dvsn_name: str = Field(description="정정/취소 구분명")
    ord_qty: int = Field(description="주문수량", alias="ord_qty")
    ord_unpr: int = Field(description="주문단가", alias="ord_unpr")
    ord_tmd: str = Field(description="주문시각 (HHMMSS)")
    tot_ccld_qty: int = Field(description="총체결수량", alias="tot_ccld_qty")
    tot_ccld_amt: int = Field(description="총체결금액", alias="tot_ccld_amt")
    psbl_qty: int = Field(description="정정/취소 가능수량", alias="psbl_qty")
    sll_buy_dvsn_cd: str = Field(description="매도/매수 구분코드 (01: 매도, 02: 매수)")
    ord_dvsn_cd: str = Field(description="주문구분코드 (00: 지정가)")


class InquirePsblRvsecnclResponse(KISBaseResponse):
    ctx_area_fk100: str | None = Field(None, description="연속 거래를 위한 FK100")
    ctx_area_nk100: str | None = Field(None, description="연속 거래를 위한 NK100")
    output: list[InquirePsblRvsecnclResponseOutput] = Field(description="주문 목록")


# --- 7. 주식잔고조회 (Inquire Balance) ---
class InquireBalanceRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (TTTC8434R: 실전, VTTC8434R: 모의)")
    tr_cont: str | None = Field(
        None,
        description="연속 거래 여부 (공백: 처음, N: 다음 페이지)",
    )


class InquireBalanceRequestQuery(BaseModel):
    CANO: str = Field(description="계좌번호 앞 8자리")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 뒤 2자리")
    AFHR_FLPR_YN: str | None = Field(
        "N",
        description="시간외단일가, 거래소여부 (Y/N)",
    )
    INQR_DVSN: str | None = Field("01", description="조회구분 (01: 대출일별)")
    UNPR_DVSN: str | None = Field("01", description="단가구분 (01: 매입평균단가)")
    FUND_STTL_ICLD_YN: str | None = Field(
        "N",
        description="펀드결제분포함여부 (Y/N)",
    )
    FNCG_AMT_AUTO_RDPT_YN: str | None = Field(
        "N",
        description="융자금액자동상환여부 (Y/N)",
    )
    PRCS_DVSN: str | None = Field(
        "00",
        description="처리구분 (00: 전일매매포함, 01: 전일매매미포함)",
    )
    CTX_AREA_FK100: str | None = Field(
        "",
        description="연속 거래 시 이전 응답의 FK100",
    )
    CTX_AREA_NK100: str | None = Field(
        "",
        description="연속 거래 시 이전 응답의 NK100",
    )


class InquireBalanceResponseOutput1(BaseModel):  # stock balance info
    pdno: str = Field(description="종목 코드")
    prdt_name: str = Field(description="종목명")
    trad_dvsn_name: str = Field(description="매매구분명")
    bfdy_buy_qty: int = Field(description="전일매수수량", alias="bfdy_buy_qty")
    bfdy_sll_qty: int = Field(description="전일매도수량", alias="bfdy_sll_qty")
    thdt_buyqty: int = Field(description="금일매수수량", alias="thdt_buyqty")
    thdt_sll_qty: int = Field(description="금일매도수량", alias="thdt_sll_qty")
    hldg_qty: int = Field(description="보유수량", alias="hldg_qty")
    ord_psbl_qty: int = Field(description="주문가능수량", alias="ord_psbl_qty")
    pchs_avg_pric: int = Field(description="매입평균가격", alias="pchs_avg_pric")
    pchs_amt: int = Field(description="매입금액", alias="pchs_amt")
    prpr: int = Field(description="현재가", alias="prpr")
    eval_prvs_amt: int = Field(description="평가금액", alias="eval_prvs_amt")
    evlu_amt: int = Field(description="평가금액 (PRPR * HLDG_QTY)", alias="evlu_amt")
    evlu_pfls_amt: int = Field(description="평가손익금액", alias="evlu_pfls_amt")
    evlu_pfls_rt: float = Field(description="평가손익률", alias="evlu_pfls_rt")
    ccl_cnld_amt: int = Field(description="결제예정금액", alias="ccl_cnld_amt")
    rmn_qty: int = Field(description="잔고수량", alias="rmn_qty")
    loan_dt: str | None = Field(None, description="대출일자")
    loan_item_amt: int | None = Field(None, description="대출금액")
    mgna_rt: float | None = Field(None, description="위탁증거금률")
    item_chgrc_amt: int | None = Field(None, description="종목변경차액금액")
    loan_exp_dt: str | None = Field(None, description="대출만기일")


class InquireBalanceResponseOutput2(BaseModel):  # total balance info
    dnca_tot_amt: int = Field(description="예수금총금액", alias="dnca_tot_amt")
    nxdy_excc_amt: int = Field(
        description="다음 영업일 출금가능금액",
        alias="nxdy_excc_amt",
    )
    prvs_rcdl_excc_amt: int = Field(
        description="전일 체결잔고 금액",
        alias="prvs_rcdl_excc_amt",
    )
    cma_evlu_amt: int = Field(description="CMA평가금액", alias="cma_evlu_amt")
    bfdy_buy_amt: int = Field(description="전일 매수금액", alias="bfdy_buy_amt")
    thdt_buy_amt: int = Field(description="금일 매수금액", alias="thdt_buy_amt")
    nxdy_buy_amt: int = Field(description="다음 영업일 매수금액", alias="nxdy_buy_amt")
    bfdy_sll_amt: int = Field(description="전일 매도금액", alias="bfdy_sll_amt")
    thdt_sll_amt: int = Field(description="금일 매도금액", alias="thdt_sll_amt")
    nxdy_sll_amt: int = Field(description="다음 영업일 매도금액", alias="nxdy_sll_amt")
    tot_sll_amt: int = Field(description="총 매도금액", alias="tot_sll_amt")
    tot_buy_amt: int = Field(description="총 매수금액", alias="tot_buy_amt")
    sttl_dt: str = Field(description="결제일 (YYYYMMDD)")
    thdt_sttl_dpst: int = Field(description="금일 결제예수금", alias="thdt_sttl_dpst")
    ottr_cash_rsv_amt: int = Field(
        description="타사 출고 현금 예약금액",
        alias="ottr_cash_rsv_amt",
    )
    ottr_crdt_rsv_amt: int = Field(
        description="타사 출고 신용 예약금액",
        alias="ottr_crdt_rsv_amt",
    )


class InquireBalanceResponse(KISBaseResponse):
    ctx_area_fk100: str | None = Field(None, description="연속 거래를 위한 FK100")
    ctx_area_nk100: str | None = Field(None, description="연속 거래를 위한 NK100")
    output1: list[InquireBalanceResponseOutput1] = Field(description="주식 잔고 목록")
    output2: InquireBalanceResponseOutput2 | None = Field(
        None,
        description="총 잔고 정보",
    )


# --- 8. 매수가능조회 (Inquire Psbl Order) ---
class InquirePsblOrderRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (TTTC8908R: 실전, VTTC8908R: 모의)")


class InquirePsblOrderRequestQuery(BaseModel):
    CANO: str = Field(description="계좌번호 앞 8자리")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 뒤 2자리")
    PDNO: str | None = Field(
        "",
        description="종목번호 (6자리, 빈 값: 전체 계좌 매수 가능금액)",
    )
    ORD_UNPR: str = Field(description="주문단가 (매수 가능 금액 조회 시 필수)")
    ORD_QTY: str = Field(description="주문수량 (매수 가능 금액 조회 시 필수)")
    ORD_DVSN: str = Field(description="주문구분 (00: 지정가, 01: 시장가 등)")
    CASH_PRCS_DVSN_CD: str = Field(
        description="현금 처리 구분 코드 (01: 현금, 02: 위탁증거금)",
    )
    IVST_PDCT_TP_CD: str | None = Field(
        "01",
        description="투자상품유형코드 (01: 주식)",
    )
    LOAN_DT: str | None = Field("", description="대출일자 (신용거래 시)")


class InquirePsblOrderResponseOutput(BaseModel):
    ord_psbl_cash: int = Field(description="주문가능현금", alias="ord_psbl_cash")
    ord_psbl_qty: int = Field(description="주문가능수량", alias="ord_psbl_qty")
    ord_psbl_loan_rt_qty: int = Field(
        description="주문가능융자비율수량",
        alias="ord_psbl_loan_rt_qty",
    )
    ord_psbl_crdt_qty: int = Field(
        description="주문가능신용수량",
        alias="ord_psbl_crdt_qty",
    )
    ord_psbl_min_qty: int = Field(
        description="주문가능최소수량",
        alias="ord_psbl_min_qty",
    )
    max_prc: int = Field(description="최대주문가능금액", alias="max_prc")
    min_prc: int = Field(description="최소주문가능금액", alias="min_prc")


class InquirePsblOrderResponse(KISBaseResponse):
    output: InquirePsblOrderResponseOutput | None = Field(
        None,
        description="응답 데이터",
    )


# --- 9. 주식예약주문 (Order Resv) ---
class OrderResvRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (CTSC0008U: 실전)")  # 모의투자 지원 X
    hashkey: str | None = Field(
        None,
        description="HashKey (주식주문 시 필수)",
        alias="hashkey",
    )


class OrderResvRequestBody(BaseModel):
    CANO: str = Field(description="종합계좌번호 (8자리)")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 (2자리)")
    PDNO: str = Field(description="종목코드 (6자리)")
    SLL_BUY_DVSN_CD: str = Field(description="매도/매수 구분코드 (01: 매도, 02: 매수)")
    ORD_QTY: str = Field(description="주문수량")
    ORD_UNPR: str = Field(description="주문단가")
    RESV_QTY_ALL_ORD_YN: str = Field(
        description="예약잔량/전부 주문 여부 (Y: 전부, N: 잔량)",
    )
    RESV_ORD_DVSN_CD: str = Field(
        description="예약주문구분코드 (01: 지정가, 02: 시장가 등)",
    )
    RESV_ORD_TP_CD: str = Field(
        description="예약주문유형코드 (01: 당일, 02: 익일, 03: 지정일)",
    )
    RESV_ORD_TRGT_DT: str | None = Field(
        None,
        description="예약주문대상일자 (YYYYMMDD, 지정일 시 필수)",
    )
    RESV_ORD_TMD: str | None = Field(
        None,
        description="예약주문시간 (HHMMSS, 지정일 시 필수)",
    )
    RESV_ORD_LMT_TMD: str | None = Field(
        None,
        description="예약주문제한시간 (HHMMSS, 지정일 시 필수)",
    )
    MOD_UNPR_DVSN_CD: str | None = Field(
        "00",
        description="수정단가구분코드 (00: 지정가)",
    )
    LMT_UNPR_TYPE_CD: str | None = Field(
        "00",
        description="한도단가유형코드 (00: 지정가)",
    )


class OrderResvResponseOutput(BaseModel):
    RSRV_ODNO: str = Field(description="예약주문번호")
    RESV_ORD_TMD: str = Field(description="예약주문시각")


class OrderResvResponse(KISBaseResponse):
    output: OrderResvResponseOutput | None = Field(None, description="응답 데이터")


# --- 10. 주식예약주문 정정취소 (Order Resv Rvsecncl) ---
class OrderResvRvsecnclRequestHeader(KISRequestHeader):
    tr_id: str = Field(
        description="거래 ID (CTSC0013U: 정정, CTSC0009U: 취소)",
    )  # 모의투자 지원 X
    hashkey: str | None = Field(
        None,
        description="HashKey (주식주문 시 필수)",
        alias="hashkey",
    )


class OrderResvRvsecnclRequestBody(BaseModel):
    CANO: str = Field(description="종합계좌번호 (8자리)")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 (2자리)")
    RSRV_ODNO: str = Field(description="예약주문번호")
    SLL_BUY_DVSN_CD: str = Field(description="매도/매수 구분코드 (01: 매도, 02: 매수)")
    PDNO: str = Field(description="종목코드 (6자리)")
    RVSE_CNCL_DVSN_CD: str = Field(
        description="정정/취소 구분코드 (01: 정정, 02: 취소)",
    )
    ORD_QTY: str = Field(description="주문수량")
    ORD_UNPR: str = Field(description="주문단가 (정정 시 필수)")
    QTY_ALL_ORD_YN: str = Field(description="잔량/전부 주문 여부 (Y: 전부, N: 잔량)")


class OrderResvRvsecnclResponseOutput(BaseModel):
    RSRV_ODNO: str = Field(description="예약주문번호")
    RESV_ORD_TMD: str = Field(description="예약주문시각")


class OrderResvRvsecnclResponse(KISBaseResponse):
    output: OrderResvRvsecnclResponseOutput | None = Field(
        None,
        description="응답 데이터",
    )


# --- 11. 주식예약주문조회 (Order Resv Ccnl) ---
class OrderResvCcnlRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (CTSC0004R: 실전)")  # 모의투자 지원 X
    tr_cont: str | None = Field(
        None,
        description="연속 거래 여부 (공백: 처음, N: 다음 페이지)",
    )


class OrderResvCcnlRequestQuery(BaseModel):
    CANO: str = Field(description="계좌번호 앞 8자리")
    ACNT_PRDT_CD: str = Field(description="계좌상품코드 뒤 2자리")
    CTX_AREA_FK100: str | None = Field(
        "",
        description="연속 거래 시 이전 응답의 FK100",
    )
    CTX_AREA_NK100: str | None = Field(
        "",
        description="연속 거래 시 이전 응답의 NK100",
    )
    INQR_DVSN: str = Field(
        description="조회구분 (00: 전체, 01: 매도, 02: 매수, 03: 정정, 04: 취소)",
    )
    INQR_BGN_DT: str | None = Field(None, description="조회시작일자 (YYYYMMDD)")
    INQR_END_DT: str | None = Field(None, description="조회종료일자 (YYYYMMDD)")


class OrderResvCcnlResponseOutput(BaseModel):
    rsrv_odno: str = Field(description="예약주문번호")
    resv_ord_dvs_cd_name: str = Field(description="예약주문구분코드명")
    sll_buy_dvsn_cd_name: str = Field(description="매도매수구분코드명")
    ord_tp_cd_name: str = Field(description="주문유형코드명")
    pdno: str = Field(description="종목번호")
    prdt_name: str = Field(description="상품명")
    ord_qty: int = Field(description="주문수량", alias="ord_qty")
    ord_unpr: int = Field(description="주문단가", alias="ord_unpr")
    ord_tmd: str = Field(description="주문시간 (HHMMSS)")
    resv_trgt_dt: str = Field(description="예약처리대상일자 (YYYYMMDD)")
    resv_tmd: str = Field(description="예약처리시간 (HHMMSS)")
    resv_stts_cd_name: str = Field(description="예약상태코드명")


class OrderResvCcnlResponse(KISBaseResponse):
    ctx_area_fk100: str | None = Field(None, description="연속 거래를 위한 FK100")
    ctx_area_nk100: str | None = Field(None, description="연속 거래를 위한 NK100")
    output: list[OrderResvCcnlResponseOutput] = Field(description="예약주문 목록")


# --- 12. 주식현재가 시세 (Inquire Price) ---
class InquirePriceRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (FHKST01010100)")


class InquirePriceRequestQuery(BaseModel):
    fid_cond_mrkt_div_code: str = Field(
        default="J",
        description="시장 조건 구분 코드 (J: 주식)",
    )
    fid_input_iscd: str = Field(description="종목코드 (6자리)")


class InquirePriceResponseOutput(BaseModel):
    iscd_entp_name: str | None = Field(None, description="기업명")
    iscd_cd: str | None = Field(None, description="종목코드")
    stck_prpr: int = Field(description="현재가", alias="stck_prpr")
    prdy_vrss_sign: str = Field(
        description="전일대비부호 (1: 상한, 2: 상승, 3: 보합, 4: 하한, 5: 하락)",
    )
    prdy_vrss: int = Field(description="전일대비", alias="prdy_vrss")
    prdy_ctrt: float = Field(description="전일대비율", alias="prdy_ctrt")
    acml_vol: int = Field(description="누적거래량", alias="acml_vol")
    acml_tr_pbmn: int = Field(description="누적거래대금", alias="acml_tr_pbmn")
    prdy_vol: int | None = Field(None, description="전일거래량", alias="prdy_vol")
    # ... many more fields can be added from the documentation
    stck_oprc: int | None = Field(None, description="시가", alias="stck_oprc")
    stck_hgpr: int | None = Field(None, description="고가", alias="stck_hgpr")
    stck_lwpr: int | None = Field(None, description="저가", alias="stck_lwpr")
    stck_mxpr: int | None = Field(None, description="상한가", alias="stck_mxpr")
    stck_llpr: int | None = Field(None, description="하한가", alias="stck_llpr")
    askp: int | None = Field(None, description="매도호가", alias="askp")
    bidp: int | None = Field(None, description="매수호가", alias="bidp")
    prdy_vol_vrss_vol_rate: float | None = Field(
        None,
        description="전일거래량대비",
        alias="prdy_vol_vrss_vol_rate",
    )
    vol_tnrt: float | None = Field(None, description="거래량회전율", alias="vol_tnrt")
    per: float | None = Field(None, description="PER", alias="per")
    eps: int | None = Field(None, description="EPS", alias="eps")
    pbr: float | None = Field(None, description="PBR", alias="pbr")
    bps: int | None = Field(None, description="BPS", alias="bps")
    dvsd_rrt: float | None = Field(None, description="배당수익률", alias="dvsd_rrt")
    dvsd_amt: int | None = Field(None, description="배당락", alias="dvsd_amt")
    stck_fcam: int | None = Field(None, description="액면가", alias="stck_fcam")
    stck_parpr: int | None = Field(None, description="현재가", alias="stck_parpr")


class InquirePriceResponse(KISBaseResponse):
    output: InquirePriceResponseOutput | None = Field(
        None,
        description="응답 데이터",
    )


# --- 13. 주식기본조회 (Search Stock Info) ---
class SearchStockInfoRequestHeader(KISRequestHeader):
    tr_id: str = Field(description="거래 ID (FHKST01020000)")


class SearchStockInfoRequestQuery(BaseModel):
    fid_cond_mrkt_div_code: str = Field(
        default="J",
        description="시장 조건 구분 코드 (J: 주식)",
    )
    fid_input_iscd: str = Field(description="종목코드 (6자리)")


class SearchStockInfoResponseOutput(BaseModel):
    prdt_type_code: str = Field(description="상품유형코드")
    prdt_type_name: str = Field(description="상품유형명")
    prdt_name: str = Field(description="종목명")
    prdt_name1: str = Field(description="종목명1")
    std_pdno: str = Field(description="표준종목코드")
    scty_kacd_name: str = Field(description="증권 종류 명")
    stck_prpr: int = Field(description="현재가", alias="stck_prpr")
    # ... many more fields from documentation
    prdy_vrss_sign: str = Field(description="전일대비부호")
    prdy_vrss: int = Field(description="전일대비")
    prdy_ctrt: float = Field(description="전일대비율")
    acml_vol: int = Field(description="누적거래량")
    acml_tr_pbmn: int = Field(description="누적거래대금")
    stck_fcam: int = Field(description="액면가")
    stck_parpr: int = Field(description="호가단위")
    list_prc: int = Field(description="상장가격")
    list_dt: str = Field(description="상장일")
    mrkt_name: str = Field(description="시장명")
    spsb_eot_ratio: float = Field(description="신용증거금률")


class SearchStockInfoResponse(KISBaseResponse):
    output: SearchStockInfoResponseOutput | None = Field(
        None,
        description="응답 데이터",
    )


# --- WebSocket Models ---
class KISWebSocketHeader(BaseModel):
    approval_key: str = Field(description="웹소켓 접속 키")
    custtype: str = Field(default="P", description="고객 타입 (P: 개인, B: 법인)")
    tr_type: str = Field(description="거래 타입 (1: 체결, 2: 호가)")
    Content_Type: str = Field(default="text/plain", alias="content-type")


class KISWebSocketInput(BaseModel):
    tr_id: str = Field(description="거래 ID")
    tr_key: str = Field(description="종목코드 또는 계좌번호")


class KISWebSocketRequest(BaseModel):
    header: KISWebSocketHeader
    body: dict[str, KISWebSocketInput]  # body: {"input": KISWebSocketInput}


# For WebSocket responses, the raw message is split. We model the parsed parts.


# --- 14. 국내주식 실시간호가(KRX) (Real-time Quote) ---
class RealtimeQuoteParsedOutput(BaseModel):
    # KIS returns almost everything as string, convert to appropriate types
    ovrs_excg_cd: str | None = Field(None, description="해외거래소코드")
    ovrs_item_type_cd: str | None = Field(None, description="해외상품유형코드")
    ovrs_iscd: str | None = Field(None, description="해외종목코드")
    stck_prpr: int = Field(description="현재가")
    prdy_vrss_sign: str = Field(
        description="전일대비부호 (1: 상한, 2: 상승, 3: 보합, 4: 하한, 5: 하락)",
    )
    prdy_vrss: int = Field(description="전일대비")
    prdy_ctrt: float = Field(description="전일대비율")
    # 10호가
    askp1: int = Field(description="매도1호가")
    bidp1: int = Field(description="매수1호가")
    askp_rsqn1: int = Field(description="매도1호가 잔량")
    bidp_rsqn1: int = Field(description="매수1호가 잔량")
    askp2: int = Field(description="매도2호가")
    bidp2: int = Field(description="매수2호가")
    askp_rsqn2: int = Field(description="매도2호가 잔량")
    bidp_rsqn2: int = Field(description="매수2호가 잔량")
    askp3: int = Field(description="매도3호가")
    bidp3: int = Field(description="매수3호가")
    askp_rsqn3: int = Field(description="매도3호가 잔량")
    bidp_rsqn3: int = Field(description="매수3호가 잔량")
    askp4: int = Field(description="매도4호가")
    bidp4: int = Field(description="매수4호가")
    askp_rsqn4: int = Field(description="매도4호가 잔량")
    bidp_rsqn4: int = Field(description="매수4호가 잔량")
    askp5: int = Field(description="매도5호가")
    bidp5: int = Field(description="매수5호가")
    askp_rsqn5: int = Field(description="매도5호가 잔량")
    bidp_rsqn5: int = Field(description="매수5호가 잔량")
    askp6: int = Field(description="매도6호가")
    bidp6: int = Field(description="매수6호가")
    askp_rsqn6: int = Field(description="매도6호가 잔량")
    bidp_rsqn6: int = Field(description="매수6호가 잔량")
    askp7: int = Field(description="매도7호가")
    bidp7: int = Field(description="매수7호가")
    askp_rsqn7: int = Field(description="매도7호가 잔량")
    bidp_rsqn7: int = Field(description="매수7호가 잔량")
    askp8: int = Field(description="매도8호가")
    bidp8: int = Field(description="매수8호가")
    askp_rsqn8: int = Field(description="매도8호가 잔량")
    bidp_rsqn8: int = Field(description="매수8호가 잔량")
    askp9: int = Field(description="매도9호가")
    bidp9: int = Field(description="매수9호가")
    askp_rsqn9: int = Field(description="매도9호가 잔량")
    bidp_rsqn9: int = Field(description="매수9호가 잔량")
    askp10: int = Field(description="매도10호가")
    bidp10: int = Field(description="매수10호가")
    askp_rsqn10: int = Field(description="매도10호가 잔량")
    bidp_rsqn10: int = Field(description="매수10호가 잔량")

    total_askp_rsqn: int = Field(description="총매도호가 잔량")
    total_bidp_rsqn: int = Field(description="총매수호가 잔량")
    ovrs_vol: int = Field(description="누적거래량")
    ovrs_tr_pbmn: int = Field(description="누적거래대금")
    stck_shrn_iscd: str = Field(description="단축종목코드")
    chgh_cnt: int = Field(description="체결강도")
    # ... more fields from documentation if needed


class RealtimeQuoteResponse(BaseModel):
    # For WebSocket, rt_cd, msg_cd, msg1 are often in the first part of the message string
    tr_id: str = Field(description="거래 ID (H0STASP0)")
    tr_key: str = Field(description="종목코드")
    rt_cd: str = Field(description="성패 여부 (0: 성공, 1: 실패)")
    msg_cd: str = Field(description="응답 코드")
    msg1: str = Field(description="응답 메시지")
    output: RealtimeQuoteParsedOutput = Field(description="실시간 호가 데이터")


# --- 15. 국내주식 실시간체결통보 (Real-time Execution Notification) ---
class RealtimeExecutionParsedOutput(BaseModel):
    trade_type: str = Field(description="체결유형 (1: 매도, 2: 매수, 3: 정정, 4: 취소)")
    odno: str = Field(description="주문번호")
    orgn_odno: str = Field(description="원주문번호")
    iscd: str = Field(description="종목코드")
    ord_unpr: int = Field(description="주문단가")
    ord_qty: int = Field(description="주문수량")
    ord_tmd: str = Field(description="주문시각 (HHMMSS)")
    ccld_qty: int = Field(description="체결수량")
    ccld_prc: int = Field(description="체결단가")
    ccld_tmd: str = Field(description="체결시각 (HHMMSS)")
    rmn_qty: int = Field(description="잔여수량")
    prdt_name: str = Field(description="종목명")
    sll_buy_dvsn_cd: str = Field(description="매매구분코드 (01: 매도, 02: 매수)")
    ord_dvsn_cd: str = Field(description="주문구분코드 (00: 지정가)")
    # ... more fields from documentation if needed


class RealtimeExecutionResponse(BaseModel):
    tr_id: str = Field(description="거래 ID (H0STCNI0)")
    tr_key: str = Field(description="계좌번호")
    rt_cd: str = Field(description="성패 여부 (0: 성공, 1: 실패)")
    msg_cd: str = Field(description="응답 코드")
    msg1: str = Field(description="응답 메시지")
    output: RealtimeExecutionParsedOutput = Field(description="실시간 체결 통보 데이터")
