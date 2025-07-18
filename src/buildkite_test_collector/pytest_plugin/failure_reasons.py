"""Buildkite Test Engine PyTest failure reason mapping"""

from typing import Iterable, Mapping

# importing these privates isn't ideal, but we're only using them for type checking
from _pytest._code.code import ExceptionInfo, ExceptionRepr, TerminalRepr

# pylint: disable=too-many-locals
# pylint: disable=too-many-return-statements
def failure_reasons(
    longrepr: None | ExceptionInfo[BaseException] | tuple[str, int, str] | str | TerminalRepr
) -> tuple[str | None, Iterable[Mapping[str, Iterable[str]]] | None]:
    """
    Derives Buildkite's failure_reason & failure_expanded from PyTest's longrepr.

    Args:
        longrepr: The PyTest longrepr object containing failure information

    Returns:
        A tuple containing:
        - A string with the failure reason or None if not available
        - A list of mappings with additional failure details or None if not available
    """
    if longrepr is None:
        return None, None

    if isinstance(longrepr, str):
        return _handle_string_longrepr(longrepr)

    if (isinstance(longrepr, tuple) and len(longrepr) == 3 and
          isinstance(longrepr[0], str) and
          isinstance(longrepr[1], int) and
          isinstance(longrepr[2], str)):
        path, line, msg = longrepr
        return _handle_tuple_longrepr(path, line, msg)

    if isinstance(longrepr, ExceptionInfo):
        return _handle_exception_info_longrepr(longrepr)

    if isinstance(longrepr, ExceptionRepr) and longrepr.reprcrash is not None:
        return _handle_exception_repr_longrepr(longrepr)

    return _handle_default_longrepr(longrepr)


def _handle_string_longrepr(
    s: str
) -> tuple[str | None, Iterable[Mapping[str, Iterable[str]]] | None]:
    """Handle string longrepr case"""
    lines = s.splitlines()
    failure_reason = lines[0] if lines else s
    return failure_reason, [{"expanded": lines[1:]}]


def _handle_tuple_longrepr(
    path: str,
    line: int,
    msg: str
) -> tuple[str | None, Iterable[Mapping[str, Iterable[str]]] | None]:
    """Handle tuple longrepr case (path, line, msg)"""
    failure_reason = msg
    return failure_reason, [{"expanded": [], "backtrace": [f"{path}:{line}"]}]


def _handle_exception_info_longrepr(
    exc_info: ExceptionInfo[BaseException]
) -> tuple[str | None, Iterable[Mapping[str, Iterable[str]]] | None]:
    """Handle ExceptionInfo longrepr case"""
    failure_reason = exc_info.exconly()
    expanded = []
    backtrace = []

    if hasattr(exc_info, "traceback") and exc_info.traceback:
        for entry in exc_info.traceback:
            backtrace.append(f"{entry.path}:{entry.lineno}: {entry.name}")
            source = entry.getsource() if hasattr(entry, "getsource") else None
            if source:
                expanded.extend(str(line) for line in source)

    failure_expanded = {}
    if len(expanded) > 0:
        failure_expanded["expanded"] = expanded
    if len(backtrace) > 0:
        failure_expanded["backtrace"] = backtrace

    return failure_reason, [failure_expanded]


def _handle_exception_repr_longrepr(
    er: ExceptionRepr
) -> tuple[str | None, Iterable[Mapping[str, Iterable[str]]] | None]:
    """Handle ExceptionRepr longrepr case"""
    failure_reason = er.reprcrash.message  # e.g. "ZeroDivisionError: division by zero"
    failure_expanded = [{"expanded": str(er).splitlines()}]
    try:
        failure_expanded[0]["backtrace"] = [
            str(getattr(entry, 'reprfileloc', entry))
            for entry in er.reprtraceback.reprentries
        ]
    except AttributeError:
        pass
    return failure_reason, failure_expanded


def _handle_default_longrepr(
    longrepr: None | ExceptionInfo[BaseException] | tuple[str, int, str] | str | TerminalRepr
) -> tuple[str | None, Iterable[Mapping[str, Iterable[str]]] | None]:
    """Handle default longrepr case"""
    lines = str(longrepr).splitlines()
    if len(lines) == 0:
        return None, None
    if len(lines) == 1:
        return lines[0], None
    return lines[0], [{"expanded": lines[1:]}]
