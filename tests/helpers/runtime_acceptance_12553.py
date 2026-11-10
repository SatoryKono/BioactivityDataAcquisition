"""Opt-in observation of real file handles and directory iterators for #12553.

This plugin does not replace resource implementations with successful mocks.
Only allocations through actual Python I/O APIs at inventory call sites count.
Events are observations, not a blanket lifecycle acceptance or scenario label.
"""

from __future__ import annotations

import asyncio
import builtins
from concurrent.futures import ThreadPoolExecutor
import functools
import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SITES: dict[tuple[str, int], set[tuple[str, str]]] = {}
EVENTS: list[dict] = []
HANDLES: list[tuple[dict, object]] = []
TASKS: list[tuple[dict, asyncio.Task]] = []
EXECUTORS: list[tuple[dict, ThreadPoolExecutor]] = []
OUTCOMES: dict[str, dict[str, str]] = {}
ACTIVE = ""
PATCH = pytest.MonkeyPatch()


def _identities(kinds: set[str]) -> tuple[list[str], list[str]]:
    frame = sys._getframe(2)
    identities: set[str] = set()
    sites: set[str] = set()
    while frame:
        filename = frame.f_code.co_filename.replace("\\", "/")
        prefix = ROOT.as_posix() + "/"
        if not filename.casefold().startswith(prefix.casefold()):
            frame = frame.f_back
            continue
        relative = filename[len(prefix) :]
        key = (relative, frame.f_lineno)
        matches = {identity for identity, kind in SITES.get(key, ()) if kind in kinds}
        if matches:
            identities.update(matches)
            sites.add(f"{relative}:{frame.f_lineno}")
            break
        frame = frame.f_back
    return sorted(identities), sorted(sites)


def _observe_open(original):
    @functools.wraps(original)
    def observed(*args, **kwargs):
        identities, sites = _identities({"file"}) if ACTIVE else ([], [])
        try:
            handle = original(*args, **kwargs)
        except BaseException as exc:
            if identities:
                EVENTS.append(
                    {
                        "node": ACTIVE,
                        "identities": identities,
                        "sites": sites,
                        "event": "allocation-error",
                        "error": type(exc).__name__,
                    }
                )
            raise
        if identities and isinstance(handle, io.IOBase):
            event = {
                "node": ACTIVE,
                "identities": identities,
                "sites": sites,
                "event": "opened",
                "handle_id": f"file-{len(EVENTS)}",
                "initially_closed": handle.closed,
            }
            EVENTS.append(event)
            HANDLES.append((event, handle))
        return handle

    return observed


def _observe_iterator(original):
    @functools.wraps(original)
    def observed(*args, **kwargs):
        identities, sites = (
            _identities({"directory-enumeration", "directory-walk", "directory-glob"})
            if ACTIVE
            else ([], [])
        )
        iterator = original(*args, **kwargs)
        if not identities:
            return iterator
        event = {
            "node": ACTIVE,
            "identities": identities,
            "sites": sites,
            "event": "iterator-created",
            "handle_id": f"iterator-{len(EVENTS)}",
            "exhausted": False,
            "closed": False,
        }
        EVENTS.append(event)

        def consume():
            try:
                yield from iterator
                event["exhausted"] = True
            except BaseException as exc:
                event["error"] = type(exc).__name__
                raise
            finally:
                close = getattr(iterator, "close", None)
                if close:
                    close()
                event["closed"] = True

        return consume()

    return observed


def _observe_task(original):
    @functools.wraps(original)
    def observed(*args, **kwargs):
        identities, sites = _identities({"task"}) if ACTIVE else ([], [])
        task = original(*args, **kwargs)
        if identities and isinstance(task, asyncio.Task):
            event = {
                "node": ACTIVE,
                "identities": identities,
                "sites": sites,
                "event": "task-created",
                "handle_id": f"task-{len(EVENTS)}",
            }
            EVENTS.append(event)
            TASKS.append((event, task))
        return task

    return observed


def _observe_executor(original):
    @functools.wraps(original)
    def observed(executor, *args, **kwargs):
        identities, sites = _identities({"executor"}) if ACTIVE else ([], [])
        original(executor, *args, **kwargs)
        if identities:
            event = {
                "node": ACTIVE,
                "identities": identities,
                "sites": sites,
                "event": "executor-created",
                "handle_id": f"executor-{len(EVENTS)}",
            }
            EVENTS.append(event)
            EXECUTORS.append((event, executor))

    return observed


def pytest_configure():
    inventory = json.loads(
        (ROOT / "configs/quality/external_resource_inventory.json").read_text()
    )
    for part in inventory["resource_parts"]:
        for resource in json.loads((ROOT / part["file"]).read_text())["resources"]:
            if resource["type"] not in {
                "file",
                "directory-enumeration",
                "directory-walk",
                "directory-glob",
                "task",
                "executor",
            }:
                continue
            for site in resource["creation_sites"]:
                SITES.setdefault((site["file"], site["line"]), set()).add(
                    (resource["identity"], resource["type"])
                )
    PATCH.setattr(builtins, "open", _observe_open(builtins.open))
    PATCH.setattr(io, "open", _observe_open(io.open))
    for name in ("glob", "rglob"):
        PATCH.setattr(Path, name, _observe_iterator(getattr(Path, name)))
    PATCH.setattr(os, "walk", _observe_iterator(os.walk))
    PATCH.setattr(asyncio, "create_task", _observe_task(asyncio.create_task))
    PATCH.setattr(
        ThreadPoolExecutor, "__init__", _observe_executor(ThreadPoolExecutor.__init__)
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item):
    global ACTIVE
    ACTIVE = item.nodeid
    yield
    for event, handle in HANDLES:
        if event["node"] == ACTIVE:
            event["closed_after_teardown"] = handle.closed
    for event, task in TASKS:
        if event["node"] == ACTIVE:
            event["done_after_teardown"] = task.done()
            event["cancelled_after_teardown"] = task.cancelled()
    for event, executor in EXECUTORS:
        if event["node"] == ACTIVE:
            event["shutdown_after_teardown"] = executor._shutdown
            event["remaining_threads"] = sum(t.is_alive() for t in executor._threads)
    ACTIVE = ""


def pytest_runtest_logreport(report):
    OUTCOMES.setdefault(report.nodeid, {})[report.when] = report.outcome


def pytest_sessionfinish(exitstatus):
    PATCH.undo()
    output = Path(os.environ["BIOETL_12553_EVENTS"])
    output.write_text(
        json.dumps(
            {
                "pytest_exit_code": int(exitstatus),
                "events": EVENTS,
                "outcomes": OUTCOMES,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
