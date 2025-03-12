# V2.5

from __future__ import annotations
from os import path
import subprocess
from multiprocessing import Process, Queue
from sys import stderr, stdout
from threading import Thread, current_thread
from typing import IO, Any, Callable, Literal, Optional, overload

from utility import StreamAutoFlush

__g_thrads: list[Thread] = []

def convert_to_cmd(cmd: str) -> str:
    return f'cmd /c "{cmd}"'

def convert_to_start_program(file_path: str, args: tuple[str, ...] = tuple(), start_args: str = "") -> str:
    t_f_path, t_e_path = path.split(path.abspath(file_path))
    t_args = ""
    if len(args) != 0:
        t_format = '" "'
        t_args = f' "{t_format.join(args)}"'
    return convert_to_cmd(f'start {start_args} /D "{t_f_path}" "" "{t_e_path}"{t_args}')

@overload
def exec_programm(cmd: str, communicate: Literal[True] = True) -> tuple[str, str]:
    pass

@overload
def exec_programm(cmd: str, communicate: Literal[False]) -> None:
    pass

def exec_programm(cmd: str, communicate: bool = True) -> Optional[tuple[str, str]]:
    """if communicate=False -> non-blocking"""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    t = subprocess.Popen(cmd, startupinfo=startupinfo,
                         stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if communicate:
        t_out, t_err = t.communicate()
        t_out, t_err = t_out.decode("ansi"), t_err.decode("ansi")
        return t_out, t_err
    else:
        return None


def exec_programm_multiprocessed(cmd: str, callback_out: Callable[[str], Any] = lambda str: None, callback_err: Callable[[str], Any] = lambda str: None, callback_finished: Callable[[], Any] = lambda: None) -> None:
    t_t = Thread(target=__exec_programm_multiprocessed_inner1, args=(cmd, callback_out, callback_err, callback_finished))
    t_t.start()

def __exec_programm_multiprocessed_inner1(cmd: str, callback_out: Callable[[str], Any], callback_err: Callable[[str], Any], callback_finished: Callable[[], Any]) -> None:
    __g_thrads.append(current_thread())
    t_queue_out: Queue[str] = Queue()
    t_queue_err: Queue[str] = Queue()

    t_p = Process(target=__exec_programm_multiprocessed_inner2,
                  args=(cmd, (t_queue_out, t_queue_err)))
    t_p.start()

    while (t_p.is_alive()):
        while not t_queue_out.empty():
            callback_out(t_queue_out.get())
        while not t_queue_err.empty():
            callback_err(t_queue_err.get())

    t_p.join()
    callback_finished()
    __g_thrads.remove(current_thread())


def __exec_programm_multiprocessed_inner2(p_arg: str, p_queues: tuple[Queue[str], Queue[str]]) -> None:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    t = subprocess.Popen(p_arg, startupinfo=startupinfo,
                         stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    t_out = Thread(target=__get_output, args=(t.stdout, p_queues[0]))
    t_err = Thread(target=__get_output, args=(t.stderr, p_queues[1]))
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()


def __get_output(bytes: IO[bytes], queue: Queue[str]):
    while (t_line := bytes.read(1)):
        queue.put(t_line.decode("ansi").replace(u"\u0008", ""))


def join_threads() -> None:
    for t in __g_thrads:
        t.join()


if __name__ == "__main__":
    print(exec_programm(convert_to_cmd("echo TEST1")))
    
    exec_programm_multiprocessed(convert_to_start_program("cmd"))
    
    exec_programm_multiprocessed(convert_to_cmd("echo TEST2 && timeout /nobreak 3"), StreamAutoFlush(stdout.buffer).write, StreamAutoFlush(stderr.buffer).write, lambda: print("TEST2: FINISHED"))

    print("EOF")
    
    join_threads()
