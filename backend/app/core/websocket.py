import json
import asyncio
import websockets
from typing import List, Dict, Optional, Callable
from fastapi import WebSocket
from app.lib.kis_client import KISClient

class ConnectionManager:
    """프론트엔드 클라이언트 웹소켓 연결 관리자"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # 연결이 끊긴 경우 등 예외 처리
                continue

class KISWebSocketClient:
    """한국투자증권(KIS) 실시간 웹소켓 클라이언트"""
    def __init__(self, kis_client: KISClient):
        self.kis_client = kis_client
        self.uri = "ws://ops.koreainvestment.com:21000" if not kis_client.is_virtual else "ws://ops.koreainvestment.com:31000"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.subscriptions = set()

    async def connect(self):
        """KIS 웹소켓 서버 접속"""
        try:
            self.ws = await websockets.connect(self.uri)
            self.is_running = True
            print(f"Connected to KIS WebSocket: {self.uri}")
        except Exception as e:
            print(f"Failed to connect KIS WebSocket: {e}")
            self.is_running = False

    async def subscribe(self, symbol: str):
        """종목 실시간 체결가 구독 요청"""
        if not self.ws:
            await self.connect()
        
        if symbol not in self.subscriptions:
            payload = self.kis_client.get_ws_subscribe_payload(symbol, tr_type="1")
            await self.ws.send(payload)
            self.subscriptions.add(symbol)
            print(f"Subscribed to {symbol}")

    async def unsubscribe(self, symbol: str):
        """종목 구독 해제"""
        if self.ws and symbol in self.subscriptions:
            payload = self.kis_client.get_ws_subscribe_payload(symbol, tr_type="2")
            await self.ws.send(payload)
            self.subscriptions.remove(symbol)
            print(f"Unsubscribed from {symbol}")

    async def listen(self, handler: Callable[[dict], None]):
        """메시지 수신 루프 및 핸들러 호출"""
        while self.is_running:
            try:
                data = await self.ws.recv()
                # KIS 데이터 포맷 처리 (주로 '|' 구분자로 전송됨)
                if data.startswith('0') or data.startswith('1'):
                    # 실시간 데이터인 경우 파싱 로직 필요
                    # 여기서는 원본 데이터를 핸들러로 전달
                    await handler(data)
                else:
                    # 응답 메시지(JSON) 처리
                    res = json.loads(data)
                    print(f"KIS WS Message: {res}")
            except Exception as e:
                print(f"KIS WS Error: {e}")
                self.is_running = False
                break

    async def stop(self):
        """연결 종료"""
        self.is_running = False
        if self.ws:
            await self.ws.close()

# 싱글톤 인스턴스 생성 (필요시 사용)
manager = ConnectionManager()
