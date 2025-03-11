# V1.4

from __future__ import annotations
from io import TextIOBase, TextIOWrapper
import logging
from typing import Any, BinaryIO, Optional, cast
from sys import stderr
from os import devnull, getpid, path, remove
from enum import Enum
from glob import glob
from datetime import datetime
import warnings

# region code from snippets V2.0

# fmt: off
from io import TextIOWrapper
from os import path, fsync
class FileAutoSave(TextIOWrapper):
# fmt: on
    @property
    def path(self) -> str:
        return path.abspath(self._path)

    def __init__(self, path: str, *args: Any, **kwargs: Any):
        super().__init__(open(path, "a").detach(), *args, **kwargs)
        self._path: str = path

    def __del__(self):
        self.close()

    def write(self, text: str) -> int:
        t_return = super().write(text)
        self.flush()
        fsync(self.fileno())
        return t_return


# fmt: off
from typing import Any
from os import path, rename
class PathNotAFile(Exception):
# fmt: on
    def __init__(self, msg: str = 'given path is not a file', *args: Any, **kwargs: Any):
        super().__init__(msg, *args, **kwargs)


def check_file_already_open(file_path: str) -> bool:
    if not path.exists(file_path):
        return False
    if not path.isfile(file_path):
        raise PathNotAFile()
    try:
        rename(file_path, file_path)
        return False
    except OSError:
        return True


# fmt: off
from os import path
def convert_relpath_to_script_abspath(input_path: str) -> str:
# fmt: on
    from __main__ import __file__ as mainfile
    from sys import executable
    t_executable_name = path.split(executable)[1]
    if t_executable_name in ["python.exe", "pythonw.exe"]:
        t_mainfile = mainfile
    else:
        t_mainfile = executable
    return path.abspath(path.join(path.split(t_mainfile)[0], input_path))

# endregion


# region Enums

class LOG_LEVEL(Enum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

# endregion


# region Exceptions

class InternalError(Exception):
    pass


class FileBusy(Exception):
    def __init__(self, msg: str = 'logfile is already busy', *args: Any, **kwargs: Any):
        super().__init__(msg, *args, **kwargs)


class HandlerDetached(Exception):
    def __init__(self, msg: str = 'handler is detached', *args: Any, **kwargs: Any):
        super().__init__(msg, *args, **kwargs)

# endregion


# region Streams

class LogStreamBase(TextIOBase):
    def __init__(self, *, init_message: bool = True, app_name: str = "", init_message_suffix: str = ""):
        super().__init__()
        if init_message:
            self._write_init_message(app_name, init_message_suffix)

    def __del__(self):
        self.close()

    @staticmethod
    def _convert_time_to_string(time: datetime) -> str:
        return f"{time.strftime('%Y-%m-%d %H:%M:%S,')}{time.strftime('%f')[0:3]}"

    def _write_init_message(self, app_name: str, init_message_suffix: str, log_start_time: Optional[datetime] = None) -> None:
        if log_start_time is None:
            log_start_time = datetime.now()
        app_name = f"{app_name} - " if app_name != "" else ""
        self.write(f"{app_name}PID: {getpid()} - program start time: [{self._convert_time_to_string(_start_time)}] - log start time: \
[{self._convert_time_to_string(log_start_time)}] {init_message_suffix}\n")


class LogStreamWrapper(TextIOWrapper, LogStreamBase):  # type: ignore
    def __init__(self, stream: BinaryIO, *, init_message: bool = True, app_name: str = "", init_message_suffix: str = ""):
        super().__init__(stream)
        LogStreamBase.__init__(self, init_message=init_message, app_name=app_name, init_message_suffix=init_message_suffix)


class LogFile(FileAutoSave, LogStreamWrapper):
    def __init__(self, file_path: str, *, blank_lines: int = 3, init_message: bool = True, app_name: str = "", init_message_suffix: str = "", clear_logfile: bool = False):
        self._path = file_path = convert_relpath_to_script_abspath(file_path)

        if check_file_already_open(file_path):
            raise FileBusy()

        if clear_logfile:
            if path.exists(file_path):
                remove(file_path)

        t_newlines = False
        if path.exists(file_path):
            with open(file_path, "r") as f:
                if f.read() != "":
                    t_newlines = True

        super().__init__(file_path,
                         init_message=False)

        if t_newlines:
            self.write("\n"*blank_lines)

        if init_message:
            self._write_init_message(app_name, init_message_suffix)

    @property
    def path(self) -> str:
        return self._path


class LogFileOnDemand(LogStreamBase):
    def __init__(self, file_path: str, *, blank_lines: int = 3, init_message: bool = True, app_name: str = "", init_message_suffix: str = "", clear_logfile: bool = False):
        super().__init__(init_message=False)
        file_path = convert_relpath_to_script_abspath(file_path)
        self._stream: LogFile | None = None
        self._path = file_path
        self._blank_lines = blank_lines
        self._init_message = init_message
        self._app_name = app_name
        self._init_message_suffix = init_message_suffix
        self._clear_logfile = clear_logfile

    def close(self):
        if self._stream != None:
            self._stream.close()
            self._stream = None

    def write(self, text: str) -> int:
        if self._stream == None:
            self._stream = LogFile(self._path, blank_lines=self._blank_lines,
                                   init_message=self._init_message, app_name=self._app_name, init_message_suffix=self._init_message_suffix, clear_logfile=self._clear_logfile)
        return self._stream.write(text)

    def flush(self) -> None:
        if self._stream == None:
            return
        super().flush()

    @property
    def path(self) -> str:
        return self._path


class CrashLogFile(LogFileOnDemand):
    def __init__(self, file_path_praefix: str, file_path_suffix: str, *, file_number_digits: int = 3, init_message: bool = True, app_name: str = "", init_message_suffix: str = ""):
        super().__init__("", init_message=init_message, app_name=app_name, init_message_suffix=init_message_suffix)
        file_path_praefix = convert_relpath_to_script_abspath(file_path_praefix)
        self.__file_path_praefix = file_path_praefix
        self.__file_path_suffix = file_path_suffix
        self.__file_number_digits = file_number_digits

    def write(self, text: str) -> int:
        if self._stream == None:
            t_crash_logs = glob(
                f"{self.__file_path_praefix}[0-9]*{self.__file_path_suffix}")

            t_num = 1
            if len(t_crash_logs) > 0:
                t_crash_logs.sort(reverse=True)
                t_num = t_crash_logs[0].removeprefix(
                    self.__file_path_praefix).removesuffix(self.__file_path_suffix)
                t_num = int(t_num) + 1

            t_path = f"{self.__file_path_praefix}\
{str(t_num).zfill(self.__file_number_digits)}{self.__file_path_suffix}"

            self._stream = LogFile(
                t_path, init_message=self._init_message, app_name=self._app_name, init_message_suffix=self._init_message_suffix)

        return super().write(text)

    @property
    def path(self) -> tuple[str, str]:  # type: ignore
        return self.__file_path_praefix, self.__file_path_suffix

# endregion


# MARK: Filter
class _MaxLogLevelFilter(logging.Filter):
    def __init__(self, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL):
        self.max_log_level = max_log_level

    def filter(self, record: logging.LogRecord) -> bool:
        return True if record.levelno <= self.max_log_level.value else False


# region Handler

class Handler:
    def __init__(self, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        self._handler: logging.Handler = getattr(self, "_handler", logging.Handler())
        self.__max_loglevel_filter = _MaxLogLevelFilter()
        self._handler.addFilter(self.__max_loglevel_filter)
        _handler.append(self)
        self.__attached = True
        self.__handle_exec_info = True
        self.handle_exec_info = handle_exec_info
        self.enabled = True
        self.log_level = log_level
        self.max_log_level = max_log_level
        self.format = format

    @property
    def attached(self) -> bool:
        return self.__attached

    def detach(self) -> Any:
        self.enabled = False
        _handler.remove(self)
        self.__attached = False

    def __check_attached(self):
        if not self.__attached:
            raise HandlerDetached()

    @property
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.__check_attached()
        self.__enabled = value
        if value:
            logging.getLogger().addHandler(self._handler)
        else:
            logging.getLogger().removeHandler(self._handler)

    @property
    def log_level(self) -> LOG_LEVEL:
        return self.__log_level

    @log_level.setter
    def log_level(self, level: LOG_LEVEL) -> None:
        self.__log_level = level
        self._handler.setLevel(level.value)

    @property
    def max_log_level(self) -> LOG_LEVEL:
        return self.__max_log_level

    @max_log_level.setter
    def max_log_level(self, level: LOG_LEVEL) -> None:
        self.__max_log_level = level
        self.__max_loglevel_filter.max_log_level = level

    @property
    def format(self) -> str:
        return self.__format

    @format.setter
    def format(self, format: str) -> None:
        self.__format = format
        self._handler.setFormatter(logging.Formatter(self.__format))

    @property
    def handle_exec_info(self) -> bool:
        return self.__handle_exec_info

    def __handler_emit_without_exec_info(self, record: logging.LogRecord):
        record.exc_info = None
        record.exc_text = None
        self.__handler_emit(record)

    @handle_exec_info.setter
    def handle_exec_info(self, value: bool):
        if self.__handle_exec_info == value:
            return
        self.__handle_exec_info = value
        if not value:
            self.__handler_emit = self._handler.emit
            self._handler.emit = self.__handler_emit_without_exec_info
        else:
            self._handler.emit = self.__handler_emit
            del self.__handler_emit


class StreamHandlerBase(Handler):
    def __init__(self, stream: LogStreamBase, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        self._handler = logging.StreamHandler(stream)
        super().__init__(log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)

    def detach(self) -> LogStreamBase:
        super().detach()
        return cast(logging.StreamHandler[LogStreamBase], self._handler).stream


class StreamHandler(StreamHandlerBase):
    def __init__(self, stream: LogStreamBase, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        super().__init__(stream, log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)

    def detach(self) -> LogStreamBase:
        return super().detach()


class StdErrHandler(StreamHandler):
    def __init__(self, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True, init_message: bool = True, app_name: str = "", init_message_suffix: str = ""):
        super().__init__(LogStreamWrapper(stderr.buffer, init_message=init_message,
                                          app_name=app_name, init_message_suffix=init_message_suffix), log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)


class FileHandler(StreamHandlerBase):
    def __init__(self, file: LogFile | LogFileOnDemand | CrashLogFile, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        super().__init__(file, log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)

# endregion


# MARK: class Logger
class Logger:
    def __init__(self, name: str):
        self.__logger = logging.getLogger(name)

    def debug(self, *log_objs: object) -> None:
        _check_has_handler()
        self.__logger.debug(*log_objs)

    def info(self, *log_objs: object) -> None:
        _check_has_handler()
        self.__logger.info(*log_objs)

    def warning(self, *log_objs: object) -> None:
        _check_has_handler()
        self.__logger.warning(*log_objs)

    def error(self, *log_objs: object) -> None:
        _check_has_handler()
        self.__logger.error(*log_objs)

    def critical(self, *log_objs: object) -> None:
        _check_has_handler()
        self.__logger.critical(*log_objs)

    def exception(self, *log_objs: object) -> None:
        _check_has_handler()
        self.__logger.critical(*log_objs, exc_info=True)

    def print(self, *log_objs: object, simulated_loglevel: LOG_LEVEL = LOG_LEVEL.CRITICAL) -> None:
        """Send log_objs to all handlers without formatting."""
        _check_has_handler()

        handlers: dict[logging.Handler, logging.Formatter | None] = {}

        for handler in logging.getLogger().handlers:
            formatter = handler.formatter
            handler.setFormatter(logging.Formatter("%(message)s"))
            handlers[handler] = formatter

        self.__logger.log(simulated_loglevel.value, *log_objs)

        for handler, formatter in handlers.items():
            handler.setFormatter(formatter)

    @property
    def disabled(self) -> bool:
        return self.__logger.disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self.__logger.disabled = value


# region module methods

def _check_has_handler() -> None:
    global _no_handlers_warning_issued
    t_handler: list[Handler] = _handler

    for h in t_handler:
        if h.enabled:
            _no_handlers_warning_issued = False
            return

    if not _no_handlers_warning_issued:
        warnings.warn("Logger hat keine Handler!")
        _no_handlers_warning_issued = True

# endregion


# MARK: module init
_handler: list[Handler] = []
_no_handlers_warning_issued = False
logging.lastResort = logging.StreamHandler(open(devnull, "w"))
logging.basicConfig(handlers=(), level=LOG_LEVEL.NOTSET.value)
warnings.filterwarnings("always", ".*", category=UserWarning)
_start_time = datetime.now()
