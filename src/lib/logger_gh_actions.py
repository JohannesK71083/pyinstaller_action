# V1.3


from sys import stderr, stdout
from .logger import LOG_LEVEL, LogStreamBase, StreamHandler


class GithubErrorStream(LogStreamBase):
    def __init__(self):
        super().__init__(init_message=False)

    def write(self, message: str) -> int:
        print(f"::error::{message}", file=stderr, flush=True, end="")
        return len(message)


class GithubWarningStream(LogStreamBase):
    def __init__(self):
        super().__init__(init_message=False)

    def write(self, message: str) -> int:
        print(f"::warning::{message}", file=stderr, flush=True, end="")
        return len(message)


class GithubInfoStream(LogStreamBase):
    def __init__(self):
        super().__init__(init_message=False)

    def write(self, message: str) -> int:
        print(f"::notice::{message}", file=stdout, flush=True, end="")
        return len(message)


class GithubDebugStream(LogStreamBase):
    def __init__(self, *, init_message: bool = True, app_name: str = ""):
        super().__init__(init_message=init_message, app_name=app_name)

    def write(self, message: str) -> int:
        print(f"{message}", file=stdout, flush=True, end="")
        return len(message)


def use_std_config(app_name: str = "") -> tuple[StreamHandler, StreamHandler, StreamHandler, StreamHandler]:
    error_log_stream = GithubErrorStream()
    warning_log_stream = GithubWarningStream()
    info_log_stream = GithubInfoStream()
    debug_log_stream = GithubDebugStream(init_message=True, app_name=app_name)

    error_handler = StreamHandler(error_log_stream, LOG_LEVEL.ERROR)
    warning_handler = StreamHandler(warning_log_stream, LOG_LEVEL.WARNING, max_log_level=LOG_LEVEL.WARNING)
    info_handler = StreamHandler(info_log_stream, LOG_LEVEL.INFO, max_log_level=LOG_LEVEL.INFO)
    debug_handler = StreamHandler(debug_log_stream, LOG_LEVEL.DEBUG, max_log_level=LOG_LEVEL.DEBUG)

    return (error_handler, warning_handler, info_handler, debug_handler)


def start_log_group(name: str):
    print(f"::group::{name}", flush=True)


def end_log_group():
    print("::endgroup::")
