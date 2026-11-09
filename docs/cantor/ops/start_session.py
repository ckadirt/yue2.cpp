"""Start a new explicitly authorized, bounded YuE2 validation session."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import modal

APP, NAME = "cantor-node", "cantor-node-session"


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", choices=["L4", "A10G"], default="A10G")
    args = parser.parse_args()
    try:
        active = await modal.Sandbox.from_name.aio(APP, NAME)
    except modal.exception.NotFoundError:
        pass
    else:
        raise RuntimeError(f"Refusing duplicate volume mount: {active.object_id}")
    started = datetime.now(timezone.utc)
    sb = await modal.Sandbox.create.aio(
        "sleep", "infinity", app=await modal.App.lookup.aio(APP), name=NAME,
        image=modal.Image.from_id("im-eLYz27DDL7hHhAw53e4YMj"),
        gpu=args.gpu, cpu=4, memory=65536, timeout=10800,
        volumes={"/cantor": modal.Volume.from_name("cantor-node")},
        env={"HF_HOME": "/cantor/cache/huggingface", "CMAKE_BUILD_PARALLEL_LEVEL": "2"},
    )
    receipt_path = Path(__file__).with_name("session.json")
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text())
        receipt_path.with_name(f"session-{old['sandbox_id']}.json").write_text(json.dumps(old, indent=2) + "\n")
    receipt = {"sandbox_id": sb.object_id, "gpu": args.gpu, "host_memory_mib": 65536,
               "timeout_seconds": 10800, "created_by_client_utc": started.isoformat(),
               "shutdown_no_later_than_utc": (started + timedelta(hours=3)).isoformat(),
               "authorization": "User explicitly requested restarting the expired instance on 2026-11-09",
               "volume": "cantor-node", "mount": "/cantor"}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
