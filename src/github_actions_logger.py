# V1.0


from sys import stderr, stdout
from typing import TextIO
from .lib_python.logger import LOG_LEVEL, LogStream, StreamHandler


class GithubErrorStream(TextIO):
    def write(self, message: str) -> int:
        print(f"::error::{message}", file=stderr, flush=True)
        return len(message)


class GithubWarningStream(TextIO):
    def write(self, message: str) -> int:
        print(f"::warning::{message}", file=stderr, flush=True)
        return len(message)


class GithubInfoStream(TextIO):
    def write(self, message: str) -> int:
        print(f"::info::{message}", file=stdout, flush=True)
        return len(message)


class GithubDebugStream(TextIO):
    def write(self, message: str) -> int:
        print(f"{message}", file=stdout, flush=True)
        return len(message)


def use_std_config() -> tuple[StreamHandler, StreamHandler, StreamHandler, StreamHandler]:
    error_stream = GithubErrorStream()
    warning_stream = GithubWarningStream()
    info_stream = GithubInfoStream()
    debug_stream = GithubDebugStream()

    error_log_stream = LogStream(error_stream, init_message=False)
    warning_log_stream = LogStream(warning_stream, init_message=False)
    info_log_stream = LogStream(info_stream, init_message=False)
    debug_log_stream = LogStream(debug_stream, init_message=True)

    error_handler = StreamHandler(error_log_stream, LOG_LEVEL.ERROR)
    warning_handler = StreamHandler(warning_log_stream, LOG_LEVEL.WARNING, max_log_level=LOG_LEVEL.WARNING)
    info_handler = StreamHandler(info_log_stream, LOG_LEVEL.INFO, max_log_level=LOG_LEVEL.INFO)
    debug_handler = StreamHandler(debug_log_stream, LOG_LEVEL.DEBUG, max_log_level=LOG_LEVEL.DEBUG)

    return (error_handler, warning_handler, info_handler, debug_handler)
