import asyncio
from typing import Any, Callable, Dict, List, Optional

import websockets
from fastapi.logger import logger


class CSSWebSocket:
    def __init__(self, ws_url: str, max_retries: int = 5, retry_delay: int = 5):
        self.ws_url = ws_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.is_running = False
        self.current_retry_count = 0
        self.subscriptions: Dict[
            str,
            List[asyncio.Queue],
        ] = {}  # {topic: [queue1, queue2, ...]}
        self.message_list: List = []  # WebSocket으로 보낼 메시지 큐
        self._task: Optional[asyncio.Task] = None  # 새로 추가: start() 태스크를 저장

    async def _connect(self) -> Optional[websockets.WebSocketClientProtocol]:
        """단일 WebSocket 연결 시도를 관리합니다."""
        try:
            websocket = await websockets.connect(self.ws_url, ping_interval=60)
            logger.info(f"Connected to WebSocket: {self.ws_url}")
            self.current_retry_count = 0  # Successful connection resets retry count
            return websocket
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return None

    async def _disconnect(self):
        """WebSocket 연결을 종료합니다."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("WebSocket connection closed.")

    async def _send_to_websocket(self, message: str):
        """WebSocket 서버로 메시지를 전송합니다."""
        if self.websocket and self.is_running:
            try:
                await self.websocket.send(message)
                logger.debug(f"Sent message to WebSocket: {message}")
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")

    async def _receive_from_websocket(self, message_handler: Callable[[str], Any]):
        """WebSocket으로부터 메시지를 지속적으로 수신하고 처리합니다."""
        while self.is_running and self.websocket:
            try:
                message = await self.websocket.recv()
                logger.debug(f"Received message from WebSocket: {message}")
                await message_handler(message)  # Pass raw message to handler
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket Connection Closed during receive: {e}")
                raise  # Re-raise to trigger reconnection logic
            except Exception as e:
                logger.error(f"Error receiving from WebSocket: {e}", exc_info=True)
                raise  # Re-raise to trigger reconnection logic

    async def _run_logic(self, message_handler: Callable[[str], Any]):
        """start() 메서드에서 백그라운드 태스크로 실행될 실제 로직"""
        logger.info("Starting WebSocket client logic...")
        self.is_running = True  # 여기서 is_running을 True로 설정

        while self.is_running and self.current_retry_count < self.max_retries:
            self.websocket = await self._connect()
            if self.websocket:
                try:
                    await self._receive_from_websocket(message_handler)
                except asyncio.CancelledError:  # 태스크 취소 예외 처리
                    logger.info("WebSocket client task cancelled.")
                    break  # 루프 종료
                except Exception:
                    # _receive_from_websocket re-raises exceptions to trigger reconnection
                    pass
                finally:
                    await self._disconnect()

            if self.is_running:  # Only retry if still running
                self.current_retry_count += 1
                logger.warning(
                    f"Reconnecting in {self.retry_delay} seconds... "
                    f"(Attempt {self.current_retry_count}/{self.max_retries})",
                )
                try:
                    await asyncio.sleep(self.retry_delay)
                except asyncio.CancelledError:  # sleep 중 취소될 수 있음
                    logger.info("WebSocket client sleep cancelled.")
                    break  # 루프 종료

        if self.is_running:  # If loop exited due to max_retries
            logger.error(
                f"Max retries ({self.max_retries}) reached. Stopping WebSocket client.",
            )
        self.is_running = False  # 루프 종료 후 is_running False로 설정
        logger.info("WebSocket client logic stopped.")

    async def start(self, message_handler: Callable[[str], Any]):
        """
        WebSocket 통신을 비동기 태스크로 시작하고 연결을 유지합니다.
        message_handler는 수신된 raw 메시지를 처리하는 콜백 함수입니다.
        """
        if self._task and not self._task.done():
            logger.info("WebSocket client is already running.")
            return

        self._task = asyncio.create_task(self._run_logic(message_handler))
        logger.info("WebSocket client start task initiated.")

    async def stop(self):
        """WebSocket 통신을 종료하고 연결을 해제합니다."""
        if self._task:
            self.is_running = False  # 로직 루프 종료 플래그 설정
            self._task.cancel()  # 태스크 취소
            try:
                await self._task  # 태스크가 완료될 때까지 기다림 (취소될 때까지)
            except asyncio.CancelledError:
                logger.info("WebSocket client task successfully cancelled.")
            finally:
                self._task = None

        await self._disconnect()  # 최종적으로 연결 해제 (태스크 취소 후 안전하게)
        logger.info("WebSocket client gracefully stopped.")

    async def subscribe_client(self, topic: str, client_queue: asyncio.Queue):
        """
        주어진 topic에 대한 클라이언트 큐를 구독 목록에 추가합니다.
        클라이언트 큐는 해당 topic에 대한 메시지를 받을 것입니다.
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(client_queue)
        logger.info(f"Client subscribed to topic: {topic}")

    async def unsubscribe_client(self, topic: str, client_queue: asyncio.Queue):
        """
        주어진 topic에서 클라이언트 큐를 구독 목록에서 제거합니다.
        """
        if topic in self.subscriptions and client_queue in self.subscriptions[topic]:
            self.subscriptions[topic].remove(client_queue)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]  # Remove topic if no more subscribers
            logger.info(f"Client unsubscribed from topic: {topic}")

    async def publish_to_subscribers(self, topic: str, data: Any):
        """
        주어진 topic을 구독하는 모든 클라이언트 큐에 데이터를 게시합니다.
        """
        if topic in self.subscriptions:
            for queue in self.subscriptions[topic]:
                await queue.put(data)
            logger.debug(
                f"Published data to {len(self.subscriptions[topic])} subscribers for topic: {topic}",
            )

    def add_message(self, message: str):
        """WebSocket으로 보낼 메시지를 큐에 추가합니다."""
        self.message_list.append(message)
        logger.debug(f"Message added to send queue: {message}")

    def remove_message(self, message: str):
        """WebSocket으로 보낼 메시지를 큐에서 제거합니다."""
        if message in self.message_list:
            self.message_list.remove(message)
            logger.debug(f"Message removed from send queue: {message}")

    def clear_messages(self):
        """WebSocket으로 보낼 메시지 큐를 비웁니다."""
        self.message_list.clear()
        logger.debug("Send message queue cleared.")

    def get_pending_messages(self) -> List[str]:
        """WebSocket으로 보낼 메시지 큐에 있는 모든 메시지를 반환합니다."""
        return self.message_list.copy()

    def send_message(self):
        """WebSocket으로 메시지를 즉시 전송합니다."""
        while len(self.message_list) > 0:
            message_to_send = self.message_list.pop(0)
            asyncio.create_task(self._send_to_websocket(message_to_send))
