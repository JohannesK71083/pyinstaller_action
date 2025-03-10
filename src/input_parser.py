from os import path
from sys import exc_info, stderr
from traceback import format_exc
from lib.github_storage_manager import GithubENVManager, GithubOutputManager


def print_to_err(x: str) -> None:
    return print(x, file=stderr)


class InputError(ValueError):
    pass


class ENVStorage(GithubENVManager):
    INPUT_PYTHON_REQUIREMENTS_FILE_PATH: str
    INPUT_INPUT_FILE_PATH: str
    INPUT_ONEFILE: str
    INPUT_NO_CONSOLE: str
    INPUT_OUTPUT_NAME: str
    INPUT_OUTPUT_PATH: str
    INPUT_ICON_PATH: str
    INPUT_ADDITIONAL_DATA: str
    INPUT_PATHS: str
    INPUT_HIDDEN_IMPORTS: str
    INPUT_EXCLUDE_MODULES: str


class OutputStorage(GithubOutputManager):
    python_requirements_file_path: str
    file_path: str
    onefile: str
    no_console: str
    output_name: str
    output_path: str
    icon: str
    additional_data: str
    paths: str
    hidden_imports: str
    exclude_modules: str


def validate_inputs():
    if (python_requirements_file := ENVStorage.INPUT_PYTHON_REQUIREMENTS_FILE_PATH) != "":
        if not path.exists(python_requirements_file):
            raise InputError(f"python-requirements-file-path {python_requirements_file} does not exist!")


    if (input_file := ENVStorage.INPUT_INPUT_FILE_PATH) == "":
        raise InputError("input-file-path is required!")
    input_file = path.abspath(input_file.replace('"', ""))
    if not path.exists(input_file) or not path.isfile(input_file):
        raise InputError(f"input-file-path {input_file} does not exist!")
    OutputStorage.file_path = input_file

    if (onefile := ENVStorage.INPUT_ONEFILE) not in ["true", "false"]:
        raise InputError(f"onefile must be either true or false, got {onefile}!")
    OutputStorage.onefile = "--onefile" if onefile == "true" else ""

    if (no_console := ENVStorage.INPUT_NO_CONSOLE) not in ["true", "false"]:
        raise InputError(f"no-console must be either true or false, got {no_console}!")
    OutputStorage.no_console = "--noconsole" if no_console == "true" else ""

    if (output_name := ENVStorage.INPUT_OUTPUT_NAME) == "":
        output_name = path.splitext(path.basename(input_file))[0]
    OutputStorage.output_name = output_name

    if (output_path := ENVStorage.INPUT_OUTPUT_PATH) == "":
        raise InputError("output-path is required!")
    output_path = path.abspath(output_path.replace('"', ""))
    OutputStorage.output_path = '--distpath "' + output_path + '"'

    if (icon_path := ENVStorage.INPUT_ICON_PATH) != "":
        icon_path = path.abspath(icon_path.replace('"', ""))
        if not path.exists(icon_path) or not path.isfile(icon_path):
            raise InputError(f"icon-path {icon_path} does not exist!")
        OutputStorage.icon = '--icon "' + icon_path + '"'
    else:
        OutputStorage.icon = ""

    if (additional_data := ENVStorage.INPUT_ADDITIONAL_DATA) != "":
        additional_datas_in = additional_data.replace('"', "").split("\n")
        additional_datas_out: list[tuple[str, str]] = []
        while "" in additional_datas_in:
            additional_datas_in.remove("")
        for p in additional_datas_in:
            ad_path, ad_target = p.split(";")
            ad_path = path.abspath(ad_path)
            if not path.exists(ad_path):
                raise InputError(f"additional-data path {ad_path} does not exist!")
            additional_datas_out.append((ad_path, ad_target))
        OutputStorage.additional_data = "--add-data " + " --add-data ".join([f'"{ad_path};{ad_target}"' for ad_path, ad_target in additional_datas_out])
    else:
        OutputStorage.additional_data = ""

    if (paths := ENVStorage.INPUT_PATHS) != "":
        paths_in = paths.replace('"', "").split("\n")
        paths_out: list[str] = []
        while "" in paths_in:
            paths_in.remove("")
        for p in paths_in:
            p = path.abspath(p)
            if not path.exists(p):
                raise InputError(f"path {p} does not exist!")
            paths_out.append(f'"{p}"')
        OutputStorage.paths = "--paths" + ";".join(paths_out)
    else:
        OutputStorage.paths = ""

    if (hidden_imports := ENVStorage.INPUT_HIDDEN_IMPORTS) != "":
        hidden_imports = hidden_imports.split("\n")
        while "" in hidden_imports:
            hidden_imports.remove("")
        OutputStorage.hidden_imports = "--hidden-import " + " --hidden-import ".join(hidden_imports)
    else:
        OutputStorage.hidden_imports = ""

    if (exclude_modules := ENVStorage.INPUT_EXCLUDE_MODULES) != "":
        exclude_modules = exclude_modules.split("\n")
        while "" in exclude_modules:
            exclude_modules.remove("")
        OutputStorage.exclude_modules = "--exclude-module " + " --exclude-module ".join(exclude_modules)
    else:
        OutputStorage.exclude_modules = ""


if __name__ == "__main__":
    try:
        validate_inputs()
    except BaseException as e:
        exc = format_exc()
        exc_type, exc_obj, exc_tb = exc_info()
        ln = exc_tb.tb_lineno if exc_tb is not None else -1
        fname = path.split(exc_tb.tb_frame.f_code.co_filename)[1] if exc_tb is not None else ""
        print_to_err(f"::error title={type(e).__name__}::{type(e).__name__}: {str(e)}\n{exc}")
        exit(1)
