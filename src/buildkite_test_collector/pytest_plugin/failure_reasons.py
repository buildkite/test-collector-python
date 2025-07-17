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
    match longrepr:
        case None:
            return None, None

        case str() as s:
            lines = s.splitlines()
            failure_reason = lines[0] if lines else s
            return failure_reason, [{"expanded": lines[1:]}]

        case (path, line, msg)  if \
                isinstance(path, str) and isinstance(line, int) and isinstance(msg, str):
            failure_reason = msg
            return failure_reason, [{"expanded": [], "backtrace": [f"{path}:{line}"]}]

        case ExceptionInfo() as exc_info:
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

        case ExceptionRepr() as er if er.reprcrash is not None:
            failure_reason = er.reprcrash.message # e.g. "ZeroDivisionError: division by zero"
            failure_expanded = [{"expanded": str(er).splitlines()}]
            try:
                failure_expanded[0]["backtrace"] = [
                    str(getattr(entry, 'reprfileloc', entry))
                    for entry in er.reprtraceback.reprentries
                ]
            except AttributeError:
                pass
            return failure_reason, failure_expanded

        case _:
            lines = str(longrepr).splitlines()
            if len(lines) == 0:
                return None, None
            if len(lines) == 1:
                return lines[0], None
            return lines[0], [{"expanded": lines[1:]}]
