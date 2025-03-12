# V1.0

from __future__ import annotations
from datetime import datetime
from glob import glob
from sys import stderr
from typing import Any, Literal, Optional, TextIO, overload

import logging
from os import devnull, getpid, path
from enum import Enum
import warnings

from utility import FileAutoSave, check_file_already_open, convert_relpath_to_script_abspath


# Enums:

class LOG_LEVEL(Enum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# Exceptions:

class InternalError(Exception):
    pass


class FileBusy(Exception):
    def __init__(self, msg: str = 'logfile is already busy', *args: Any, **kwargs: Any):
        super().__init__(msg, *args, **kwargs)


class HandlerDetached(Exception):
    def __init__(self, msg: str = 'handler is detached', *args: Any, **kwargs: Any):
        super().__init__(msg, *args, **kwargs)


class _StreamBase():
    def __init__(self, stream: TextIO | _StreamBase | None, *, init_message: bool = True, app_name: Optional[str] = None, init_message_suffix: str = ""):
        self._stream: TextIO | _StreamBase | None = stream
        self._app_name = app_name
        self._init_message_suffix = init_message_suffix
        if init_message:
            self._write_init_message()

    def __del__(self):
        if self._stream != None:
            self._stream.close()

    @staticmethod
    def _convert_time_to_string(time: datetime) -> str:
        return f"{time.strftime('%Y-%m-%d %H:%M:%S,')}{time.strftime('%f')[0:3]}"

    def _write_init_message(self) -> None:
        t_appname = ""
        if self._app_name != None:
            t_appname = f"{self._app_name} - "
        self.write(f"{t_appname}PID: {getpid()} - program start time: [{self._convert_time_to_string(_start_time)}] - log start time: \
[{self._convert_time_to_string(datetime.now())}] {self._init_message_suffix}\n")

    def write(self, text: str) -> int:
        if self._stream == None:
            raise InternalError()
        return self._stream.write(text)

    def flush(self) -> None:
        if self._stream == None:
            raise InternalError()
        self._stream.flush()

    def close(self) -> None:
        if self._stream == None:
            raise InternalError()
        return self._stream.close()

    def fileno(self) -> int:
        if self._stream == None:
            raise InternalError()
        return self._stream.fileno()

    @property
    def closed(self) -> bool:
        if self._stream == None:
            raise InternalError()
        return self._stream.closed


class LogStream(_StreamBase):
    def __init__(self, stream: TextIO, *, init_message: bool = True, app_name: Optional[str] = None, init_message_suffix: str = ""):
        super().__init__(stream, init_message=init_message, app_name=app_name, init_message_suffix=init_message_suffix)


class LogFile(_StreamBase):
    def __init__(self, file_path: str, *, blank_lines: int = 3, init_message: bool = True, app_name: Optional[str] = None, init_message_suffix: str = "", clear_logfile: bool = False):
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

        super().__init__(FileAutoSave(file_path),
                         init_message=False, app_name=app_name, init_message_suffix=init_message_suffix)

        if t_newlines:
            self.write("\n"*blank_lines)

        if init_message:
            self._write_init_message()

    @property
    def path(self) -> str:
        return self._path


class LogFileOnDemand(_StreamBase):
    def __init__(self, file_path: str, *, blank_lines: int = 3, init_message: bool = True, app_name: Optional[str] = None, init_message_suffix: str = "", clear_logfile: bool = False):
        super().__init__(None, init_message=False, app_name=app_name, init_message_suffix=init_message_suffix)
        file_path = convert_relpath_to_script_abspath(file_path)
        self.__path = file_path
        self.__blank_lines = blank_lines
        self.__init_message = init_message
        self.__clear_logfile = clear_logfile

    def write(self, text: str) -> int:
        if self._stream == None:
            self._stream = LogFile(self.__path, blank_lines=self.__blank_lines,
                                   init_message=self.__init_message, app_name=self._app_name, init_message_suffix=self._init_message_suffix, clear_logfile=self.__clear_logfile)

        return super().write(text)

    def flush(self) -> None:
        if self._stream == None:
            return
        super().flush()

    @property
    def path(self) -> str:
        return self.__path


class CrashLogFile(_StreamBase):
    def __init__(self, file_path_praefix: str, file_path_suffix: str, *, file_number_digits: int = 3, init_message: bool = True, app_name: str | None = None, init_message_suffix: str = ""):
        super().__init__(None, init_message=False, app_name=app_name, init_message_suffix=init_message_suffix)
        file_path_praefix = convert_relpath_to_script_abspath(file_path_praefix)
        self.__file_path_praefix = file_path_praefix
        self.__file_path_suffix = file_path_suffix
        self.__init_message = init_message
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
                t_path, init_message=self.__init_message, app_name=self._app_name, init_message_suffix=self._init_message_suffix)

        return super().write(text)

    def flush(self) -> None:
        if self._stream == None:
            return
        super().flush()

    @property
    def path(self) -> tuple[str, str]:
        return self.__file_path_praefix, self.__file_path_suffix


class MSGBoxStream(_StreamBase):
    def __init__(self, app_name: Optional[str] = None):
        super().__init__(None, init_message=False, app_name=app_name)

    def write(self, text: str) -> int:
        from utility import msgbox
        t_app_name_str = ""
        if self._app_name != None:
            t_app_name_str = f"{self._app_name} - "
        msgbox.create_async_msg_box(
            f"{t_app_name_str}FEHLER", text, msgbox.BUTTON_STYLES.OK)
        return len(text)

    def flush(self) -> None:
        return


class _MaxLogLevelFilter(logging.Filter):
    def __init__(self, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL):
        self.max_log_level = max_log_level

    def filter(self, record: logging.LogRecord) -> bool:
        return True if record.levelno <= self.max_log_level.value else False


class Handler:
    def __init__(self, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        self._handler = getattr(self, "_handler", logging.Handler())
        self.__max_loglevel_filter = _MaxLogLevelFilter()
        self._handler.addFilter(self.__max_loglevel_filter)
        _handler.append(self)
        self.__attached = True
        self.__handle_exec_info = True
        self.handle_exec_info = handle_exec_info
        self.enabled = True
        self.log_level = log_level
        self.max_log_level = max_log_level
        self.formatter = format

    @property
    def attached(self) -> bool:
        return self.__attached

    def detach(self):
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
    def formatter(self) -> str:
        return self.__format

    @formatter.setter
    def formatter(self, format: str) -> None:
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


class _StreamHandlerBase(Handler):
    def __init__(self, stream: _StreamBase, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        self._handler = logging.StreamHandler(stream)
        super().__init__(log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)


class StreamHandler(_StreamHandlerBase):
    def __init__(self, stream: LogStream, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        super().__init__(stream, log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)


class StdErrHandler(StreamHandler):
    def __init__(self, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True, init_message: bool = True, app_name: str | None = None, init_message_suffix: str = ""):
        super().__init__(LogStream(stderr, init_message=init_message,
                                   app_name=app_name, init_message_suffix=init_message_suffix), log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)


class FileHandler(_StreamHandlerBase):
    def __init__(self, file: LogFile | LogFileOnDemand | CrashLogFile, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        super().__init__(file, log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)


class MSGBoxHandler(_StreamHandlerBase):
    def __init__(self, stream: MSGBoxStream, log_level: LOG_LEVEL, *, max_log_level: LOG_LEVEL = LOG_LEVEL.CRITICAL, format: str = "%(name)s - %(levelname)s: %(message)s", handle_exec_info: bool = True):
        super().__init__(stream, log_level, max_log_level=max_log_level, format=format, handle_exec_info=handle_exec_info)

    def join_threads(self):
        from utility import msgbox
        msgbox.join_threads()


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


# Modulemethods:

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


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, MSGBoxHandler, FileHandler, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, MSGBoxHandler, FileHandler, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, MSGBoxHandler, None, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, MSGBoxHandler, None, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, None, FileHandler, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, None, FileHandler, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, None, None, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[True] = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[StdErrHandler, None, None, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, MSGBoxHandler, FileHandler, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, MSGBoxHandler, FileHandler, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, MSGBoxHandler, None, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[True] = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, MSGBoxHandler, None, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, None, FileHandler, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[True] = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, None, FileHandler, None]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[True] = True, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, None, None, FileHandler]:
    pass


@overload
def use_std_config(*, app_name: str = "APP", use_stderr: Literal[False], stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: Literal[False], msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: Literal[False], logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: Literal[False], logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[None, None, None, None]:
    pass


def use_std_config(*, app_name: str = "APP", use_stderr: bool = True, stderr_loglevel: LOG_LEVEL = LOG_LEVEL.INFO, use_msgbox: bool = True, msgbox_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_error: bool = True, logfile_error_loglevel: LOG_LEVEL = LOG_LEVEL.WARNING, use_logfile_verbose: bool = False, logfile_verbose_loglevel: LOG_LEVEL = LOG_LEVEL.INFO) -> tuple[Optional[StdErrHandler], Optional[MSGBoxHandler], Optional[FileHandler], Optional[FileHandler]]:
    """returnValue: (stderr_handler: Optional[StdErrHandler], msgbox_handler: Optional[MSGBoxHandler], logfile_error_handler: Optional[FileHandler], logfile_verbose_handler: Optional[FileHandler])
    used file modes: logfile_error_file: LogFileOnDemand, logfile_verbose_file: LogFile"""

    t_stderr_handler, t_logfile_error_handler, t_logfile_verbose_handler, t_msgbox_handler = None, None, None, None

    if use_stderr:
        t_stderr_handler = StdErrHandler(stderr_loglevel, app_name=app_name)
    if use_msgbox:
        t_msgbox_handler = MSGBoxHandler(
            MSGBoxStream(app_name), msgbox_loglevel)
    if use_logfile_error:
        t_logfile_error_handler = FileHandler(LogFileOnDemand(
            f"{app_name}_error.log", app_name=app_name), logfile_error_loglevel)
    if use_logfile_verbose:
        t_logfile_verbose_handler = FileHandler(
            LogFile(f"{app_name}_verbose.log", app_name=app_name), logfile_verbose_loglevel)

    return t_stderr_handler, t_msgbox_handler, t_logfile_error_handler, t_logfile_verbose_handler


# Init:
_handler: list[Handler] = []
_no_handlers_warning_issued = False
logging.lastResort = logging.StreamHandler(open(devnull, "w"))
logging.basicConfig(handlers=(), level=LOG_LEVEL.NOTSET.value)
warnings.filterwarnings("always", ".*", category=UserWarning)
_start_time = datetime.now()


# Test:

if __name__ == "__main__":
    import logger as lg
    from os import remove

    t_logfile_path = "test_logfile.log"
    t_logfileondemand_path = "test_logfileondemand.log"
    t_crashlogfile_praefix = "test_crashlogfile_"
    t_crashlogfile_suffix = ".log"

    try:
        remove(convert_relpath_to_script_abspath(t_logfile_path))
        remove(convert_relpath_to_script_abspath(t_logfileondemand_path))
        for f in glob(f"{convert_relpath_to_script_abspath(t_crashlogfile_praefix)}[0-9]*{t_crashlogfile_suffix}"):
            remove(f)
            pass
        pass
    except:
        pass

    # exit()

    logger = lg.Logger("")

    logger.debug("Test")

    t_handler_stderr = lg.StdErrHandler(lg.LOG_LEVEL.DEBUG)

    t_logfile = LogFile(t_logfile_path, app_name="LOG")
    t_handler_logfile = lg.FileHandler(t_logfile, lg.LOG_LEVEL.DEBUG, max_log_level=LOG_LEVEL.WARNING)

    t_logfileondemand = LogFileOnDemand(t_logfileondemand_path, app_name="LOG")
    t_handler_logfileondemand = lg.FileHandler(
        t_logfileondemand, lg.LOG_LEVEL.DEBUG)

    t_crashlogfile = CrashLogFile(
        t_crashlogfile_praefix, t_crashlogfile_suffix)
    t_handler_crashlogfile = lg.FileHandler(
        t_crashlogfile, lg.LOG_LEVEL.WARNING)

    t_msgbox = lg.MSGBoxStream("LOG")
    t_msgbox_handler = lg.MSGBoxHandler(t_msgbox, lg.LOG_LEVEL.WARNING)

    logger.debug("ALL")

    t_handler_stderr.enabled = False

    logger.debug("NO STDERR")

    t_handler_stderr.enabled = True
    t_handler_logfile.enabled = False

    logger.debug("NO LOGFILE")

    t_handler_logfile.enabled = True
    t_handler_logfileondemand.enabled = False

    logger.debug("NO LOGFILEONDEMAND")

    t_handler_logfileondemand.enabled = True

    logger.debug("ALL")

    t_handler_logfileondemand.log_level = lg.LOG_LEVEL.WARNING

    logger.debug("DEBUG")
    logger.info("INFO")
    logger.warning("WARNING")
    logger.error("ERROR")
    try:
        raise Exception()
    except Exception as e:
        logger.exception("EXCEPTION")
        # raise e

    t_handler_stderr.formatter = "-> %(message)s"

    logger.debug("DEBUG")

    t_handler_stderr.enabled = False
    t_handler_logfile.enabled = False
    t_handler_logfileondemand.enabled = False

    logger.debug("DEBUG")

    t_msgbox_handler.handle_exec_info = False
    try:
        raise Exception()
    except Exception as e:
        logger.exception("EXCEPTION")

    t_msgbox_handler.join_threads()
