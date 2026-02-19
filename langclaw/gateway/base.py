"""
BaseChannel — abstract interface for all message channels.

Adding a new channel = one file implementing BaseChannel + one field in ChannelsConfig.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langclaw.bus.base import BaseMessageBus, OutboundMessage


class BaseChannel(ABC):
    """
    Abstract base for all langclaw gateway channels.

    Lifecycle managed by :class:`~langclaw.gateway.manager.GatewayManager`.
    Each channel runs as an independent async task inside an ``asyncio.TaskGroup``.
    """

    name: str
    """Unique channel identifier (e.g. ``"telegram"``, ``"discord"``)."""

    @abstractmethod
    async def start(self, bus: BaseMessageBus) -> None:
        """
        Connect to the channel and start consuming incoming messages.

        Must publish each incoming message to *bus* via
        ``await bus.publish(InboundMessage(...))``.

        This coroutine runs indefinitely until cancelled.
        """
        ...

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """
        Deliver *msg* back to the user on this channel.

        Implementations should handle streaming chunks gracefully
        (e.g. editing/appending to a previous message on Telegram).
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully disconnect and release resources."""
        ...

    def is_enabled(self) -> bool:
        """Return True if this channel should be started by the gateway."""
        return True
