import json
import asyncio
import websockets
from typing import Dict, Optional, Callable, List, Any
from app.lib.kis_client import KISClient, TRID

class KISWebSocketManager:
    """KIS 웹소켓 연결 및 구독을 총괄 관리하는 매니저 (AppKey별 독립 연결)"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.connections = {}  # {app_key: websockets.connect}
            cls._instance.handlers = {}     # {app_key: {tr_id: {tr_key: [callbacks]}}}
            cls._instance.tasks = {}        # {app_key: listen_task}
        return cls._instance

    async def get_connection(self, client: KISClient) -> websockets.WebSocketClientProtocol:
        """AppKey에 해당하는 웹소켓 연결을 가져오거나 새로 생성"""
        app_key = client.appkey
        if app_key not in self.connections or self.connections[app_key].closed:
            uri = "ws://ops.koreainvestment.com:31000"
            if client.base_url.find("vts") != -1:
                uri = "ws://ops.koreainvestment.com:31000" # 모의투자도 동일한 경우 많음 (체크 필요)
            
            ws = await websockets.connect(uri)
            self.connections[app_key] = ws
            
            # 수신 루프 시작
            if app_key in self.tasks:
                self.tasks[app_key].cancel()
            self.tasks[app_key] = asyncio.create_task(self._listen_loop(app_key))
            print(f"New KIS WS Connection established for AppKey: {app_key}")
            
        return self.connections[app_key]

    async def subscribe(self, client: KISClient, tr_id: str, tr_key: str, callback: Callable):
        """특정 TR ID와 Key에 대해 구독 및 콜백 등록 (중복 방지를 위해 딕셔너리 사용)"""
        app_key = client.appkey
        ws = await self.get_connection(client)
        
        # 콜백 등록
        if app_key not in self.handlers:
            self.handlers[app_key] = {}
        if tr_id not in self.handlers[app_key]:
            self.handlers[app_key][tr_id] = {}
        if tr_key not in self.handlers[app_key][tr_id]:
            self.handlers[app_key][tr_id][tr_key] = {}
            # 신규 구독인 경우 KIS 서버에 요청 전송
            payload = client.get_ws_subscribe_payload(tr_id, tr_key, tr_type="1")
            await ws.send(payload)
            print(f"KIS WS Subscribed: {tr_id} - {tr_key}")
            
        cb_name = callback.__name__ if hasattr(callback, '__name__') else str(id(callback))
        self.handlers[app_key][tr_id][tr_key][cb_name] = callback

    async def unsubscribe(self, client: KISClient, tr_id: str, tr_key: str):
        """특정 TR ID와 Key에 대해 구독 해제 요청"""
        app_key = client.appkey
        if app_key in self.connections and not self.connections[app_key].closed:
            ws = self.connections[app_key]
            payload = client.get_ws_subscribe_payload(tr_id, tr_key, tr_type="2")
            await ws.send(payload)
            
            if app_key in self.handlers and tr_id in self.handlers[app_key] and tr_key in self.handlers[app_key][tr_id]:
                del self.handlers[app_key][tr_id][tr_key]
                print(f"KIS WS Unsubscribed: {tr_id} - {tr_key}")

    async def _listen_loop(self, app_key: str):
        """AppKey별 독립적인 수신 루프"""
        ws = self.connections[app_key]
        try:
            async for message in ws:
                # KIS 데이터 포맷: 0|tr_id|... (실시간) 또는 JSON (응답)
                if isinstance(message, str):
                    if message.startswith('0') or message.startswith('1'):
                        parts = message.split('|')
                        if len(parts) > 2:
                            tr_id = parts[1]
                            # 실시간 체결통보(H0STCNI0)와 현재가(H0STCNT0)는 파싱 방식이 다름
                            # 여기서는 tr_id와 tr_key(종목코드 또는 HTS ID)를 추출하여 라우팅
                            # 예: 체결통보의 경우 tr_key가 암호화되어 있을 수 있으나 라우팅 로직 필요
                            
                            # 단순화를 위해 전체 tr_id 채널에 콜백 실행
                            # 실제로는 parts[3] 등에서 종목코드/HTS ID 추출 필요
                            await self._dispatch(app_key, tr_id, message)
                    else:
                        try:
                            data = json.loads(message)
                            print(f"KIS WS Control Message [{app_key}]: {data}")
                        except:
                            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"KIS WS Error in loop [{app_key}]: {e}")
        finally:
            print(f"KIS WS Connection closed for AppKey: {app_key}")

    async def _dispatch(self, app_key: str, tr_id: str, message: str):
        """등록된 콜백들에게 데이터 분배 (비동기 스레드 실행)"""
        if app_key in self.handlers and tr_id in self.handlers[app_key]:
            for tr_key in self.handlers[app_key][tr_id]:
                # 해당 채널의 모든 콜백 실행
                for cb_name, callback in self.handlers[app_key][tr_id][tr_key].items():
                    # 💡 핵심: 무거운 DB 로직 등을 위해 스레드 풀에서 실행
                    asyncio.create_task(asyncio.to_thread(callback, message))

    async def stop_all(self):
        for ws in self.connections.values():
            await ws.close()
        for task in self.tasks.values():
            task.cancel()
