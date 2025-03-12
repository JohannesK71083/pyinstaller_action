# V1.7

from __future__ import annotations
from io import TextIOWrapper
from os import fsync, listdir, mkdir, path, rename
from shutil import move
from typing import IO, Any, Callable, Optional, Type
from warnings import warn
from send2trash import send2trash as s2t
import ctypes
from sys import stderr

from psutil import process_iter
from pyautogui import hotkey


class StreamAutoFlush(TextIOWrapper):
    def __init__(self, buffer: IO[bytes]):
        super().__init__(buffer, encoding="utf-8")

    def write(self, str: str) -> int:
        t_return = super().write(str)
        super().flush()
        return t_return


class FileAutoSave(TextIOWrapper):
    @property
    def path(self) -> str:
        return path.abspath(self._path)

    def __init__(self, path: str):
        super().__init__(open(path, "a").detach())
        self._path: str = path

    def __del__(self):
        self.close()

    def write(self, text: str) -> int:
        t_return = super().write(text)
        self.flush()
        fsync(self.fileno())
        return t_return


class PathNotAFile(Exception):
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


def check_if_program_is_opened(exe_name: str) -> bool:
    return exe_name in (p.name() for p in process_iter())


def convert_relpath_to_script_abspath(input_path: str) -> str:
    from __main__ import __file__ as mainfile
    from sys import executable
    t_executable_name = path.split(executable)[1]
    if t_executable_name in ["python.exe", "pythonw.exe"]:
        t_mainfile = mainfile
    else:
        t_mainfile = executable
    return path.abspath(path.join(path.split(t_mainfile)[0], input_path))


def ignore_exceptions(func: Callable[..., Any]) -> Callable[..., Any | str]:
    def inner(*args: Any, **kwargs: Any):
        try:
            func(*args, **kwargs)
        except BaseException as err:
            t_err_type = str(type(err))
            t_first = t_err_type.find("'") + 1
            t_second = t_err_type.find("'", t_first)
            return f'{t_err_type[t_first:t_second]}: {err}'
    return inner


def find_nth_occurrence(string: str, find_str: str, n: int, *, start_index: int = 0, forwards: bool = True) -> int:
    if not forwards:
        return len(string) - find_nth_occurrence(string[::-1], find_str[::-1], n) - len(find_str)
    if n == 0:
        return string.find(find_str, start_index)
    elif n > 0:
        return find_nth_occurrence(string, find_str, n-1, start_index=string.find(find_str))
    else:
        raise ValueError


def send_hotkey(*args: str):
    hotkey(*args)


def send_folder_contents_to_trash(folder_path: str, temp_del_path: str, ignored_files: tuple[str, ...] = tuple()):
    if path.exists(temp_del_path):
        s2t(temp_del_path)
    try:
        mkdir(temp_del_path)
    except:
        pass
    if not path.exists(folder_path):
        print(f'Failed to move {folder_path}. Reason: FileNotFoundError')
        s2t(temp_del_path)
        return
    for filename in listdir(folder_path):
        if filename in ignored_files:
            continue
        file_path = path.join(folder_path, filename)
        try:
            move(file_path, temp_del_path)
        except Exception as e:
            print('Failed to move %s. Reason: %s' % (file_path, e))
    s2t(temp_del_path)


def close_program(name: str, force_close: bool = True):
    try:
        stderr.write(exec.exec_programm(exec.convert_to_cmd(f'for /f "delims=" %a in (\'tasklist /FI "IMAGENAME eq "{name}""\') do ( taskkill /IM {name} )'))[1])
    except:
        pass
    if force_close:
        force_close_program(name)


def force_close_program(p_name: str):
    try:
        stderr.write(exec.exec_programm(exec.convert_to_cmd(f'taskkill /F /IM "{p_name}"'))[1])
    except:
        pass


def check_if_admin() -> bool:
    return ctypes.windll.shell32.IsUserAnAdmin() != 0


def find_next(st: str, searches: tuple[str, ...], start: int = 0, end: Optional[int] = None):
    if end == None:
        end = len(st)
    erg: dict[str, int] = {}
    for s in searches:
        erg[s] = st.find(s, start, end)
    erg = {k: v for k, v in erg.items() if v != -1}
    return min(erg.items(), key=lambda v: v[1])


class _SubclassableEnumType(type):
    _members: dict[str, Any]
    _in_construction: bool

    def __new__(metacls, name: str, bases: tuple[Type[Any]], classdict: dict[str, Any], **kwds: Any) -> _SubclassableEnumType:
        t_member_keys = classdict.get("_values", {})
        cls = type.__new__(metacls, name, bases, classdict)
        cls._in_construction = True

        _members = {e: cls(e, classdict["_values"][e]) for e in t_member_keys}
        for k, v in _members.items():
            setattr(cls, k, v)
            if k not in classdict.get("__annotations__", {}).keys():
                warn(f"missing annotation for {v} in {type(v)}")

        for a in classdict.get("__annotations__", {}).keys():
            if a not in _members.keys() and a not in ["_values"]:
                warn(f"missing value for {name}.{a}")

        cls._members = {}
        for b in bases:
            cls._members.update(getattr(b, "_members", {}))
        cls._members.update(_members)

        cls._in_construction = False
        return cls

    def __setattr__(cls, name: str, value: Any):
        if name != "_in_construction" and not cls._in_construction:
            raise AttributeError(f"cannot alter class {cls.__name__} after creation")
        super().__setattr__(name, value)

    def __iter__(cls):
        return iter(cls._members.values())

    def __len__(cls):
        return len(cls._members.keys())

    def __contains__(cls, value: object) -> bool:
        return value in cls._members.values()

    def __repr__(cls) -> str:
        return f"{type(cls).__name__}({', '.join(repr(m) for m in cls._members.values())})"

    def __str__(cls) -> str:
        return f"{type(cls).__name__}({', '.join(str(m) for m in cls._members.values())})"


class SubclassableEnum(metaclass=_SubclassableEnumType):
    _values: dict[str, Any] = {}

    def __init__(self, name: str = "", value: Any = None) -> None:
        if not self._in_construction:  # type:ignore
            raise RuntimeError(f"class {type(self).__name__} is static")
        self._name = name
        self._value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> Any:
        return self._value

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self._name}: {self._value}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self._name}"


# have to be at the bottom, otherwise circular import problems
# fmt: off
import msgbox # type:ignore
import exec # type:ignore
from keylistener import KeyListener # type:ignore
import keylistener # type:ignore
# fmt: on