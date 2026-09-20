"""Stream broker with asynchronous queue backpressure, exponential retry, and Dead-Letter Queue (DLQ)."""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.core.providers import BaseStreamProvider, get_stream_provider

logger = get_logger("data_engineering.stream")


class StreamMessage(BaseModel):
    """Event envelope for streaming ingestion and action egress."""
    message_id: str
    topic: str
    payload: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    error_trace: Optional[str] = None


class StreamBroker:
    """Enterprise event streaming broker with DLQ and backpressure control."""

    def __init__(self, provider: Optional[BaseStreamProvider] = None, max_buffer_size: int = 1000):
        self.provider = provider or get_stream_provider()
        self.max_buffer_size = max_buffer_size
        # asyncio.Queue must be created lazily inside a running event loop (Python 3.10+)
        self._in_flight_buffer: Optional[asyncio.Queue] = None
        self.dead_letter_queue: List[StreamMessage] = []
        self.processed_count: int = 0
        self.failed_count: int = 0

    def _get_buffer(self) -> asyncio.Queue:
        """Lazily initialise the asyncio.Queue inside the running event loop."""
        if self._in_flight_buffer is None:
            self._in_flight_buffer = asyncio.Queue(maxsize=self.max_buffer_size)
        return self._in_flight_buffer

    async def publish_event(self, topic: str, payload: Dict[str, Any]) -> str:
        """Publishes an event to the stream with buffer backpressure."""
        buf = self._get_buffer()
        msg = StreamMessage(
            message_id=f"msg_{int(time.time() * 1000)}_{self.processed_count + 1}",
            topic=topic,
            payload=payload,
        )

        if buf.full():
            logger.warning("Stream buffer full; applying backpressure", topic=topic)
            try:
                # Wait up to 2 seconds rather than sleeping blindly
                await asyncio.wait_for(buf.join(), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Backpressure timeout; dropping to DLQ", topic=topic)
                self.dead_letter_queue.append(msg)
                return msg.message_id

        await buf.put(msg)
        published_id = await self.provider.publish(topic, msg.model_dump())
        return published_id

    async def process_with_retry(
        self, message: StreamMessage, handler: Callable[[Dict[str, Any]], Any]
    ) -> bool:
        """Executes handler with exponential backoff; pushes to DLQ on repeated failure."""
        for attempt in range(message.max_retries):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message.payload)
                else:
                    handler(message.payload)
                self.processed_count += 1
                return True
            except Exception as ex:
                message.retry_count = attempt + 1
                message.error_trace = str(ex)
                backoff_delay = 0.05 * (2 ** attempt)
                logger.warning(
                    "Stream handler attempt failed; backing off",
                    msg_id=message.message_id,
                    attempt=attempt + 1,
                    delay_sec=backoff_delay,
                    err=str(ex),
                )
                await asyncio.sleep(backoff_delay)

        # Route to Dead-Letter Queue
        self.failed_count += 1
        self.dead_letter_queue.append(message)
        logger.error(
            "Message routed to Dead-Letter Queue (DLQ)",
            msg_id=message.message_id,
            topic=message.topic,
        )
        return False

    def get_dlq_stats(self) -> Dict[str, Any]:
        """Returns DLQ inspection telemetry."""
        buf = self._in_flight_buffer
        return {
            "dlq_size": len(self.dead_letter_queue),
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "buffer_depth": buf.qsize() if buf else 0,
        }
