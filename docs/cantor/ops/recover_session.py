"""Recover the interrupted GPU task without extending its original deadline."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

import modal

APP, NAME = "cantor-node", "cantor-node-session"
DEADLINE = datetime.fromisoformat("2026-11-09T17:22:28+00:00")


async def main():
    try:
        active = await modal.Sandbox.from_name.aio(APP, NAME)
    except modal.exception.NotFoundError:
        pass
    else:
        raise RuntimeError(f"Refusing a second volume mount; session exists: {active.object_id}")
    timeout = int((DEADLINE - datetime.now(timezone.utc)).total_seconds()) - 300
    if timeout < 60:
        raise RuntimeError("Original task deadline is too close; refusing a new allocation")
    image = modal.Image.from_id("im-eLYz27DDL7hHhAw53e4YMj")
    try:
        sb = await asyncio.wait_for(modal.Sandbox.create.aio(
            "sleep", "infinity", app=await modal.App.lookup.aio(APP), name=NAME,
            image=image, gpu="A10G", cpu=4, memory=65536, timeout=timeout,
            volumes={"/cantor": modal.Volume.from_name("cantor-node")},
            env={"HF_HOME": "/cantor/cache/huggingface", "CMAKE_BUILD_PARALLEL_LEVEL": "2"},
        ), timeout=240)
    except asyncio.TimeoutError:
        pending = await modal.Sandbox.from_name.aio(APP, NAME)
        await pending.terminate.aio(wait=True)
        raise RuntimeError("A10G allocation exceeded four minutes and was terminated")
    now = datetime.now(timezone.utc)
    receipt = {"sandbox_id": sb.object_id, "gpu": "A10G", "host_memory_mib": 65536,
               "timeout_seconds": timeout, "client_ready_utc": now.isoformat(),
               "original_task_deadline_utc": DEADLINE.isoformat(),
               "volume": "cantor-node", "mount": "/cantor", "replaces": "sb-KAOORLiKNJml5mm4SnCh8D"}
    Path(__file__).with_name("session.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    asyncio.run(main())
