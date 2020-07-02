import glob
import json
import logging
import os
from io import TextIOWrapper
from os import path

CMD_BASE = 'cmd /c {}'
GET_TFS_DEFAULT = "get {} /force  /recursive"


def set_read_only(file_path):
    cmd = f'attrib -R {file_path}'
    run_cmd_default(cmd)


def get_config() -> dict:
    with open('C:\\MyProjects\\GetBuildSigod\\config.json') as json_data_file:
        data = json.load(json_data_file)
    return data


def read_file(base_path: str, encoding='') -> TextIOWrapper:
    if encoding:
        file = open(base_path, 'r', encoding=encoding)
    else:
        file = open(base_path, 'r')
    return file


def get_error_from_orca_log(log_path) -> str:
    try:
        content = read_file(log_path, 'utf-16')
        lines = content.readlines()
    except Exception as err:
        raise err

    errors_txt = ''
    is_error_lines = False

    for line in lines:
        strip_line = line.strip()
        if strip_line == 'PBORCA_SccRefreshTarget.':
            is_error_lines = True
            continue
        if line.strip() == 'PBORCA_SccClose':
            is_error_lines = False
        if is_error_lines:
            errors_txt = errors_txt + line

    return errors_txt


def run_cmd_default(cmd: str):
    cmd = CMD_BASE.format(cmd)
    os.system(cmd)


def get_from_tfs(obj_path: str, tfs_base_dir: str, validate=False) -> bool:
    get_path = GET_TFS_DEFAULT.format(obj_path)
    cmd = f'{tfs_base_dir} {get_path}'
    run_cmd_default(cmd)

    if path.exists(obj_path) or not validate:
        return True
    else:
        raise FileNotFoundError


def change_cwd(cwd: str):
    os.chdir(cwd)


def path_obj_from_line(base_path: str) -> str:
    return base_path.replace('\\\\', '\\').replace('"', '').replace('pbl', 'pbg')


def chunks(length, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(length), n):
        # Create an index range for l of n items:
        yield length[i:i + n]


def print_and_log(logger_level, line):
    print(line)
    logger_level(line)


def return_log_object(log_filename, log_name, when='MIDNIGHT', level=logging.INFO):
    """
        Fires a new process to create parallel dispatches.
        :param log_filename: the path of the file
        :param log_name: name of the logger
        :param when: to rotate the file
        :param level: log level
        :return: the logger object
        """
    # Set up a specific logger with our desired output level
    my_logger = logging.getLogger(log_name)
    my_logger.setLevel(level)

    # Add the log message handler to the logger
    if when is None:
        handler = logging.FileHandler(log_filename, mode='w+')
    else:
        handler = logging.handlers.TimedRotatingFileHandler(log_filename, when=when)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                  datefmt='%d/%m/%Y %H:%M:%S')
    handler.setFormatter(formatter)

    my_logger.addHandler(handler)

    return my_logger


def return_obj_path(base_path, base_filter) -> str:
    srj_list = []
    obj_path = f'{base_path}\\{base_filter}'
    for file in glob.glob(obj_path):
        srj_list.append(file)

    if len(srj_list) == 0:
        raise FileNotFoundError(f'File {obj_path} not found')
    else:
        return srj_list[0]


def return_pbd_from_srj(srj_path) -> dict:
    srj_file = return_obj_path(srj_path, '*.srj')

    lines = read_file(srj_file)
    pbd_dict = {}
    for line in lines:
        if 'PBD:' in line:
            splits = line.strip().split(',')
            abs_path = os.path.abspath(splits[0][4:])

            pbd = abs_path
            inout = splits[-1]

            pbd_dict[pbd] = inout

    return pbd_dict


def pbd_list_as_string(pbd_list: list) -> str:
    pbd_list = [f'"{i}"' for i in pbd_list]

    line = ' '.join(pbd_list)
    return line


def write_new_line(file: TextIOWrapper, text: str, qtd=1) -> str:
    new_line = '\n' * qtd
    line = f'{text}{new_line}'
    file.write(line)

    return line


def delete_files_filter(base_path):
    base_path = f'{base_path}\\**\\*.'
    path_full = f'{base_path}\\**\\*.*'
    files = set(glob.glob(path_full, recursive=True)) - set(glob.glob(base_path + 'pb*', recursive=True) +
                                                            glob.glob(base_path + 'sra', recursive=True) +
                                                            glob.glob(base_path + 'exe', recursive=True) +
                                                            glob.glob(base_path + 'log', recursive=True)
                                                            )

    for f in files:
        try:
            set_read_only(f)
            os.remove(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))
