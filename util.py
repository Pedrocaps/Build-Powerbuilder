import concurrent.futures
import glob
import shutil
import re
import datetime
import json
import logging
import multiprocessing as mp
import os
import sys
from io import TextIOWrapper
from os import path

import obj_worker


def delete_build_folder():
    build_path = get_build_path()
    shutil.rmtree(build_path, ignore_errors=True)


def get_build_path():
    config = get_config()

    base_path = f"{config['CHANGE_BASE_CWD']}\\{config['BASE_DIR']}"
    system_name = config['SYSTEM_NAME']

    build_path = f'{base_path}\\BUILD_{system_name}'

    return build_path


def get_logger_path():
    build_path = get_build_path()

    log_path = os.path.join(build_path, 'LOGS')

    return log_path


def get_orca_path():
    build_path = get_build_path()

    dir = os.path.join(build_path, 'ORCA')
    if not os.path.exists(dir):
        os.mkdir(dir)

    return dir


def get_dist_path():
    build_path = get_build_path()

    dir = os.path.join(build_path, 'DIST')
    if not os.path.exists(dir):
        os.mkdir(dir)

    return dir


def get_dist_path():
    build_path = get_build_path()

    dir = os.path.join(build_path, 'DIST')
    if not os.path.exists(dir):
        os.mkdir(dir)

    return dir


def set_read_only(file_path, set='-'):
    cmd1 = 'attrib'
    cmd2 = f'{set}R'  # - remove read only + add readonly
    cmd3 = file_path

    run_cmd_default([cmd1, cmd2, cmd3])


def get_config() -> dict:
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)

    application_path = os.path.join(application_path, 'config.json')

    with open(application_path) as json_data_file:
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


def run_cmd_default(cmd: list):
    import subprocess

    i = 1
    while i <= 4:
        error_msg = ''
        try:
            cp = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                check=True, timeout=10 * i)
            if cp.returncode == 0:
                break
        except subprocess.TimeoutExpired as err:
            error_msg = f'Timeout after {i} tries. {err}'
            continue
        except subprocess.CalledProcessError as err:
            raise EnvironmentError(err.stderr)

    if error_msg != '':
        raise TimeoutError(error_msg)

    return cp.stdout.strip().replace('\n', '-')


def get_from_tfs(obj_path: str, config, validate=False) -> bool:
    par0 = config['TFS_BASE_DIR']
    par1 = 'get'
    par2 = obj_path
    par3 = '/force'
    par4 = '/recursive'

    try:
        ret = run_cmd_default([par0, par1, par2, par3, par4])
    except TimeoutError as err:
        raise err
    except EnvironmentError as err:
        raise err

    if path.exists(obj_path) or not validate:
        return ret
    else:
        raise FileNotFoundError(f'File {obj_path} do not exists. {ret}')


def change_cwd(cwd: str):
    os.chdir(cwd)


def path_obj_from_line(base_path: str) -> str:
    return base_path.replace('\\\\', '\\').replace('"', '').replace('.pbl', '.pbg')


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


def return_properties_srj(srj_path) -> dict:
    srj_file = return_obj_path(srj_path, '*.srj')
    lines = read_file(srj_file)
    ret_dict = {}

    for line in lines:
        if re.match(r'\b[A-Z]{3}:', line):
            splits = line.split(':')

            ret_dict[splits[0]] = splits[1].strip()

    return ret_dict


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

            pass

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


def prepare_delete_files_filter(base_path, max_threads):
    path_full = f'{base_path}\\**\\*.*'
    log_path = f'{get_build_path()}\\**\\*.*'

    all_obj_list = list(set(glob.glob(path_full, recursive=True)) -
                        set(glob.glob(path_full + 'pb*', recursive=True)) -
                        set(glob.glob(log_path, recursive=True)))

    obj_chunks = chunker_list(all_obj_list, max_threads)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(obj_worker.delete_files_filter, obj_chunks)


def chunker_list(seq, size):
    return (seq[i::size] for i in range(size))


def prepare_get_obj_from_pbg_process(pbgs: list):
    # Chunks of a list
    chunk_list = chunks(pbgs, 6)
    for chunk in chunk_list:
        process_list = []
        for pbg in chunk:
            p = mp.Process(target=obj_worker.obj_list_from_pbg, args=(pbg,))
            process_list.append(p)
            p.start()

        for p in process_list:
            p.join()


def prepare_get_obj_from_pbg_thread(pbgs: list, max_threads):
    all_obj_list = []
    for pbg in pbgs:
        obj_list = obj_worker.obj_list_from_pbg(pbg)
        if obj_list:
            all_obj_list.extend(obj_list)

    obj_chunks = chunker_list(all_obj_list, max_threads)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        result = executor.map(obj_worker.get_obj_from_list, obj_chunks)

        for ret in result:
            if not ret:
                raise ValueError('There was an error downloading a object.. see object log for more info...')


def format_time_exec(total_time) -> str:
    return '{:.2f} min'.format(total_time / 60) if total_time > 60 else '{:.2f} sec'.format(total_time)


def move_bin_files(base_path, new_dst):
    path_full = f'{base_path}\\**\\*.*'
    all_obj_list = list(set(glob.glob(path_full + 'pbd', recursive=True) +
                            glob.glob(path_full + 'exe', recursive=True)))

    try:
        for file in all_obj_list:
            shutil.move(file, new_dst)
    except Exception as err:
        raise err
