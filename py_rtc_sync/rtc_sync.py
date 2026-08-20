#!/usr/bin/env python3
"""Check and optionally synchronize STM32 RTC through the USB CDC CLI."""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime

try:
    import serial
except ImportError:  # pragma: no cover - helpful message for host setup
    serial = None


RTC_RE = re.compile(r"^OK RTC (?P<dt>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$")


class CliError(RuntimeError):
    pass


def read_response(port: "serial.Serial", timeout_s: float) -> list[str]:
    deadline = time.monotonic() + timeout_s
    lines: list[str] = []

    while time.monotonic() < deadline:
        raw = port.readline()
        if not raw:
            continue

        line = raw.decode("ascii", errors="replace").strip()
        if not line:
            continue

        lines.append(line)
        if line == "READY":
            return lines

    raise CliError(f"Timeout waiting for READY. Received: {lines!r}")


def send_command(port: "serial.Serial", command: str, timeout_s: float) -> list[str]:
    port.reset_input_buffer()
    port.write((command + "\r\n").encode("ascii"))
    port.flush()
    return read_response(port, timeout_s)


def get_rtc(port: "serial.Serial", timeout_s: float) -> datetime:
    lines = send_command(port, "RTC GET", timeout_s)

    for line in lines:
        match = RTC_RE.match(line)
        if match:
            return datetime.strptime(match.group("dt"), "%Y-%m-%d %H:%M:%S")

    raise CliError(f"RTC GET did not return an RTC timestamp. Response: {lines!r}")


def set_rtc(port: "serial.Serial", value: datetime, timeout_s: float) -> list[str]:
    command = value.strftime("RTC SET %Y-%m-%d %H:%M:%S")
    lines = send_command(port, command, timeout_s)

    if "OK" not in lines:
        raise CliError(f"RTC SET failed. Response: {lines!r}")

    return lines


def format_delta(delta_s: float) -> str:
    sign = "+" if delta_s >= 0 else "-"
    delta_s = abs(delta_s)
    return f"{sign}{delta_s:.3f} s"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare STM32 RTC with local PC time over the USB CDC CLI and "
            "set RTC when the difference is above threshold."
        )
    )
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port path.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=2.0,
        help="Maximum accepted absolute difference in seconds.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Timeout for one CLI command in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the difference; do not set the STM32 RTC.",
    )
    parser.add_argument(
        "--no-initial-drain",
        action="store_true",
        help="Do not read pending READY/banner lines after opening the port.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if serial is None:
        print("ERROR: missing pyserial. Install it with: python3 -m pip install pyserial", file=sys.stderr)
        return 2

    try:
        with serial.Serial(args.port, args.baud, timeout=0.2, write_timeout=args.timeout) as port:
            if not args.no_initial_drain:
                time.sleep(0.3)
                port.reset_input_buffer()

            pc_before = datetime.now().replace(microsecond=0)
            rtc_before = get_rtc(port, args.timeout)
            pc_after = datetime.now().replace(microsecond=0)
            pc_reference = pc_before + (pc_after - pc_before) / 2
            delta_s = (rtc_before - pc_reference).total_seconds()

            print(f"PC time:          {pc_reference:%Y-%m-%d %H:%M:%S}")
            print(f"STM32 RTC:        {rtc_before:%Y-%m-%d %H:%M:%S}")
            print(f"Difference RTC-PC:{format_delta(delta_s)}")

            if abs(delta_s) <= args.threshold:
                print(f"OK: difference is within threshold ({args.threshold:.3f} s).")
                return 0

            if args.dry_run:
                print("DRY RUN: RTC would be updated.")
                return 1

            target = datetime.now().replace(microsecond=0)
            print(f"Setting STM32 RTC to: {target:%Y-%m-%d %H:%M:%S}")
            set_rtc(port, target, args.timeout)

            rtc_after = get_rtc(port, args.timeout)
            pc_verify = datetime.now().replace(microsecond=0)
            verify_delta_s = (rtc_after - pc_verify).total_seconds()

            print(f"STM32 RTC after:  {rtc_after:%Y-%m-%d %H:%M:%S}")
            print(f"PC time after:    {pc_verify:%Y-%m-%d %H:%M:%S}")
            print(f"Difference after: {format_delta(verify_delta_s)}")

            return 0 if abs(verify_delta_s) <= args.threshold else 1

    except (OSError, serial.SerialException, CliError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
