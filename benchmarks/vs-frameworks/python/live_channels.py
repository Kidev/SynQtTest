# SPDX-FileCopyrightText: 2026 Alexandre 'kidev' Poumaroux
# SPDX-License-Identifier: Apache-2.0

"""Python's other answer: Django Channels, which is what a team with an existing Django
application would actually reach for.

Two Python columns rather than one, because they are not the same stack wearing different
names. ``live_fastapi.py`` is a bare async endpoint; this one is Django's ASGI application
with the Channels consumer stack and its group layer in front of the same sockets, and the
gap between the two rows is the cost of that machinery.

The same shape as ``node/live-bare.mjs``, and everything that is not the server lives in
``measure.py``, shared with the FastAPI column, so the difference between the two files is
only the framework.

The channel layer is the in-memory one on purpose. Channels' documentation is clear that
``InMemoryChannelLayer`` is not for production and that a deployment uses Redis, and a Redis
column here would be measuring Redis: every other column in this table publishes from the
same process that holds the sockets, so this one does too. The README says so where the
number is reported.
"""

from __future__ import annotations

import asyncio
from typing import Any, List

import django
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.urls import path as url_path

import measure

# Django refuses to do anything before it is configured, and this column has no project on
# disk to configure it from: one endpoint and no models, views, templates, database or
# middleware. Everything below the ASGI application is what Channels itself brings.
if not settings.configured:
    settings.configure(
        DEBUG=False,
        ALLOWED_HOSTS=["*"],
        SECRET_KEY="benchmark-only-never-a-deployment",
        INSTALLED_APPS=["channels"],
        DATABASES={},
        USE_TZ=True,
    )
    django.setup()


class LiveConsumer(AsyncWebsocketConsumer):
    """One subscriber's consumer. It never receives, only sends, so the only thing it does
    is join and leave the set the publisher writes to."""

    clients: List["LiveConsumer"] = []

    async def connect(self) -> None:
        await self.accept()
        LiveConsumer.clients.append(self)

    async def disconnect(self, code: int) -> None:
        if self in LiveConsumer.clients:
            LiveConsumer.clients.remove(self)


class Server:
    """Django's ASGI application on this process's event loop."""

    def __init__(self) -> None:
        self.url = ""
        self.endpoint: Any = None
        self.task: Any = None
        self.application = ProtocolTypeRouter({
            "websocket": URLRouter([url_path("live", LiveConsumer.as_asgi())]),
        })

    async def start(self) -> "Server":
        # Served by uvicorn rather than by daphne, and that is a stated difference from a
        # Channels deployment rather than an accident. Daphne runs on twisted with a reactor
        # of its own, which cannot share this process's asyncio loop with the subscribers,
        # and the contract puts the publisher and every subscriber in one process on one
        # clock. What is measured either way is Django Channels' consumer stack, which is
        # the framework this column is about; the ASGI server underneath it is the same
        # class of thing in both cases. The README says so where the number is reported.
        from uvicorn import Config, Server as Uvicorn

        config = Config(self.application, host="127.0.0.1", port=0,
                        log_level="critical", access_log=False)
        self.endpoint = Uvicorn(config)
        self.task = asyncio.create_task(self.endpoint.serve())
        while not self.endpoint.started:
            await asyncio.sleep(0.01)
        port = self.endpoint.servers[0].sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/live"
        return self

    def connected(self) -> int:
        return len(LiveConsumer.clients)

    async def broadcast(self, frame: bytes) -> None:
        # Build the frame once, then hand the same bytes to every consumer, as every other
        # column does. Writing per subscriber would measure the framing N times over.
        for client in list(LiveConsumer.clients):
            try:
                await client.send(bytes_data=frame)
            except Exception:
                pass

    async def close(self) -> None:
        for client in list(LiveConsumer.clients):
            try:
                await client.close()
            except Exception:
                pass
        LiveConsumer.clients.clear()
        self.endpoint.should_exit = True
        try:
            await asyncio.wait_for(self.task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self.task.cancel()


async def connect(url: str) -> Any:
    import websockets

    return await websockets.connect(url, max_size=None, ping_interval=None)


async def main() -> None:
    args = measure.parse_args(measure.DEFAULTS)
    await measure.drive(
        start_server=lambda: Server().start(),
        connect=connect,
        stack="python-channels",
        path="Django Channels consumers, ASGI WebSockets on uvicorn",
        args=args,
    )


if __name__ == "__main__":
    asyncio.run(main())
