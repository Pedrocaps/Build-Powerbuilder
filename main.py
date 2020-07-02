import concurrent.futures
import glob
import multiprocessing as mp
import os
import time
import subprocess
from io import TextIOWrapper

import obj_worker
import orca_util
import util


def get_pbt(pbt_path) -> TextIOWrapper:
    try:
        util.get_from_tfs(pbt_path, TFS_BASE_DIR)
        content = util.read_file(pbt_path)

        return content
    except FileNotFoundError:
        raise


def get_pbr() -> str:
    base_path = f'{BASE_PATH}\\{SYSTEM_DIR}'
    pbr_path = '{}\\{}'.format(base_path, '*.pbr'.format(SYSTEM_NAME))

    util.get_from_tfs(pbr_path, TFS_BASE_DIR, False)

    pbr_list = []
    os.chdir(base_path)
    for file in glob.glob("*.pbr"):
        pbr_list.append(file)

    if len(pbr_list) == 0:
        raise FileNotFoundError
    else:
        return pbr_list[0]


def pbg_list_from_from_pbt(pbt_content: TextIOWrapper) -> dict:
    lines = pbt_content.readlines()

    pbg_list = []
    pbd_list = []
    pbls = ''

    for line in lines:
        splits = line.split(' ')
        if splits[0] == 'LibList':
            pbls = splits[1].split(';')[:-1]

    util.change_cwd(SYSTEM_DIR.format(SYSTEM_NAME.upper()))
    for pbl in pbls:
        pbl_rep = util.path_obj_from_line(pbl)
        logger.info(f'\tGetting PBG {pbl_rep}')
        util.get_from_tfs(pbl_rep, TFS_BASE_DIR)

        abs_path = os.path.abspath(pbl_rep)

        if '.pbd' in pbl_rep:
            pbd_list.append(abs_path)

        pbg_list.append(pbl_rep)

    return {
        "PBD": pbd_list,
        "ALL": pbg_list
    }


def set_globals(config: dict):
    global MAX_THREADS
    MAX_THREADS = 5
    global TFS_BASE_DIR
    TFS_BASE_DIR = config['TFS_BASE_DIR']
    global SYSTEM_NAME
    SYSTEM_NAME = config['SYSTEM_NAME']
    global SYSTEM_DIR
    SYSTEM_DIR = config['BASE_DIR'] + '\\TECCOM\{}\\Fontes'.format(SYSTEM_NAME)
    global BASE_PATH
    BASE_PATH = config['CHANGE_BASE_CWD']
    global BASE_SISTEMAS_PATH
    BASE_SISTEMAS_PATH = f"{BASE_PATH}\\{config['BASE_DIR']}"

    global GET_TFS_DEFAULT
    GET_TFS_DEFAULT = config['GET_TFS_DEFAULT']
    global PBT_PATH
    PBT_PATH = '{}\\{}'.format(SYSTEM_DIR, '{}.pbt'.format(SYSTEM_NAME))
    global VERSAO
    VERSAO = config['VERSAO']
    global FIGURAS_PATH
    FIGURAS_PATH = config['FIGURAS_PATH']


def prepare_get_obj_from_pbg_process(pbgs: list):
    # Chunks of a list
    chunk_list = util.chunks(pbgs, 6)
    for chunk in chunk_list:
        process_list = []
        for pbg in chunk:
            p = mp.Process(target=obj_worker.obj_list_from_pbg, args=(pbg,))
            process_list.append(p)
            p.start()

        for p in process_list:
            p.join()


def chunker_list(seq, size):
    return (seq[i::size] for i in range(size))


def prepare_get_obj_from_pbg_thread(pbgs: list):
    max_threads = MAX_THREADS
    all_obj_list = []
    for pbg in pbgs:
        obj_list = obj_worker.obj_list_from_pbg(pbg)
        if obj_list:
            all_obj_list.extend(obj_list)

    obj_chunks = chunker_list(all_obj_list, max_threads)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(obj_worker.get_obj_from_list, obj_chunks)


def create_pbw(pbw_path: str):
    with open(pbw_path, 'w+') as f:
        f.write("Save Format v3.0(19990112)\n")
        f.write("@begin Unchecked\n")
        f.write("@end;\n")
        f.write("@begin Targets\n")
        f.write(' 0 "{}.pbt";\n'.format(SYSTEM_NAME))
        f.write("@end;\n")
        f.write('DefaultTarget "{}.pbt";\n'.format(SYSTEM_NAME))
        f.write('DefaultRemoteTarget "{}.pbt";\n'.format(SYSTEM_NAME))


def run_bat(bat_path: str, log_path: str):
    i = 1
    max_loop = 2
    while i <= max_loop:
        util.print_and_log(logger.info, '\tRunning {} of {} bat executions'.format(i, max_loop))
        cp = subprocess.run([bat_path], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True)
        i = i + 1
        if 'Result Code -22.' in cp.stdout:
            try:
                errors_txt = util.get_error_from_orca_log(log_path)
                raise SyntaxError(f'Syntax Errors: {errors_txt}')
            except Exception as err:
                raise EnvironmentError('Reading log error: {}'.format(err))
            pass
        if 'Result Code -27' in cp.stdout:
            raise EnvironmentError('Target file not found:')
        if 'Result Code -6' in cp.stdout:
            raise EnvironmentError('Target file not found in path: set application')
        if 'Last Command Failed.' in cp.stdout:
            raise EnvironmentError('Error building exe')
        if 'End Session' in cp.stdout:
            return  # sucess

    raise EnvironmentError(f'Error running 3step bat: i = {i}')


def change_sra_version():
    base_path = f'{BASE_PATH}\\{SYSTEM_DIR}'
    sra_path = f'{base_path}\\{SYSTEM_NAME}.sra'
    file_path = f'{sra_path}'

    util.set_read_only(file_path)

    replace_str = f"string vgsVersao = '{VERSAO}'\n"
    with open(file_path, 'r') as f:
        get_all = f.readlines()

    with open(file_path, 'w') as f:
        for i, line in enumerate(get_all, 1):
            if 'string vgsVersao' in line:
                f.writelines(replace_str)
            else:
                f.writelines(line)

    util.set_read_only(file_path)


def change_pbr_relative_path():
    base_path = f'{BASE_PATH}\\{SYSTEM_DIR}'
    sra_path = f'{base_path}\\{SYSTEM_NAME}.pbr'
    file_path = f'{sra_path}'

    util.set_read_only(file_path)

    replace = '..\\..\\..'

    with open(file_path, 'r') as f:
        get_all = f.readlines()

    with open(file_path, 'w') as f:
        for i, line in enumerate(get_all, 0):
            if replace in line:
                replace_str = line.replace(replace, BASE_SISTEMAS_PATH)
                f.writelines(replace_str)
            else:
                replace_str = f'{FIGURAS_PATH}{line}'
                f.writelines(replace_str)

    util.set_read_only(file_path)


def get_project() -> dict:
    logger.info('Process starded....')
    print('####################')

    try:
        util.print_and_log(logger.info, '##### GET PBT ######')
        pbt_content = get_pbt(PBT_PATH)
        util.print_and_log(logger.info, 'Done getting {} ...'.format(PBT_PATH))

        util.print_and_log(logger.info, '##### CREATE PBW ######')
        pbw_path = SYSTEM_DIR.format(SYSTEM_NAME)
        pbw_path = "{}\\{}.pbw".format(pbw_path, SYSTEM_NAME)
        create_pbw(pbw_path)
        util.print_and_log(logger.info, 'Done creating {} ...'.format(pbw_path))

        util.print_and_log(logger.info, '##### GET PBG ######')
        pbg_dict = pbg_list_from_from_pbt(pbt_content)
        pbg_list = pbg_dict['ALL']
        util.print_and_log(logger.info, 'Done getting PBG(D)s...')

        util.print_and_log(logger.info, '##### GET PBR ######')
        pbr_path = get_pbr()
        util.print_and_log(logger.info, 'Done getting pbr {}...'.format(pbr_path))

        util.print_and_log(logger.info, '##### GET OBJ ######')
        prepare_get_obj_from_pbg_thread(pbg_list)
        util.print_and_log(logger.info, 'Done getting all objects...')

        util.print_and_log(logger.info, '##### CHANGE VGSVERSAO ######')
        change_sra_version()
        util.print_and_log(logger.info, 'Done changing vgsVersao')

        util.print_and_log(logger.info, '##### CHANGE PBR BASE PATH ######')
        change_pbr_relative_path()
        util.print_and_log(logger.info, 'Done changing PBR BASE PATH')

        util.print_and_log(logger.info, '##### GET HELP FILE ######')
        # TODO: Get help..file
        util.print_and_log(logger.info, 'Done get help file...')

        util.print_and_log(logger.info, '##### GET COMPLEMENTOS ######')
        # TODO: Get complementos
        util.print_and_log(logger.info, 'Done get complementos...')

        return pbg_dict

    except FileNotFoundError as ex:
        raise ex
    except EnvironmentError as ex:
        raise ex


def create_logger():
    try:
        log_path = f'{BASE_SISTEMAS_PATH}\\{SYSTEM_NAME}_LOG'
        os.makedirs(log_path)
    except Exception as ex:
        print(ex)
    finally:
        log_path = '{}\\GERAL.log'.format(log_path)

    try:
        global logger
        logger = util.return_log_object(log_filename=log_path,
                                        log_name='LOG_GERAL', when=None)
    except Exception as err:
        raise err


def delete_temp_files(config):
    util.print_and_log(logger.info, '##### DELETE TEMP FILES ######')
    if config['DELETE_TEMP_FILES'].upper() == 'S':
        util.delete_files_filter(BASE_SISTEMAS_PATH)
        util.print_and_log(logger.info, 'Done delete temp files...')
    else:
        util.print_and_log(logger.info, 'Delete flag off...')


def create_scripts(pbg_dict, config) -> dict:
    orca_dict = {}
    util.print_and_log(logger.info, '##### CREATE ORCA SCRIPTS ######')
    orca_helper = orca_util.OrcaUtil(config, pbg_dict['PBD'], logger)
    orca_helper.create_pborca_scripts()
    util.print_and_log(logger.info, 'Done create orca scripts...')

    orca_dict['BAT_PATH'] = orca_helper.BAT_PATH
    orca_dict['BAT_EXE'] = orca_helper.BAT_EXE
    orca_dict['ORCA_LOG'] = orca_helper.ORCA_LOG_PATH

    return orca_dict


def prepare_run_bat(orca_dict, config):
    try:
        run_bat(orca_dict['BAT_PATH'], orca_dict['ORCA_LOG'])
    except EnvironmentError as err:
        err_txt = '\tError executing 3 step bat, open pbw and correct errors - \n{}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)
    except SyntaxError as err:
        err_txt = '\tError executing 3 step bat, correct errors - {}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)

    util.print_and_log(logger.info, 'Done running 3step bat')

    if config['CREATE_EXE'].upper() == 'S':
        util.print_and_log(logger.info, '##### RUN EXE BAT ######')
        try:
            run_bat(orca_dict['BAT_EXE'], orca_dict['ORCA_LOG'])
        except EnvironmentError as err:
            err_txt = '\tError executing EXE bat, open pbw and correct errors - {}'.format(err)
            util.print_and_log(logger.info, err_txt)
            raise EnvironmentError(err_txt)
        except SyntaxError as err:
            err_txt = '\tError executing EXE bat, correct errors - {}'.format(err)
            util.print_and_log(logger.info, err_txt)
            raise EnvironmentError(err_txt)

        util.print_and_log(logger.info, 'Done running exe bat')


def main():
    start = time.time()

    config = util.get_config()
    set_globals(config)
    util.change_cwd(BASE_PATH)

    try:
        create_logger()
    except Exception as err:
        print(err)
        return

    try:
        pbg_dict = get_project()
    except FileNotFoundError as ex:
        util.print_and_log(logger.error, ex)
        return
    except EnvironmentError as ex:
        util.print_and_log(logger.error, ex)
        return

    orca_dict = create_scripts(pbg_dict, config)

    try:
        prepare_run_bat(orca_dict, config)
    except (EnvironmentError, SyntaxError) as err:
        return

    delete_temp_files(config)

    minutes = (time.time() - start) / 60
    util.print_and_log(logger.info, 'Complete process took {} minutes'.format(minutes))


if __name__ == '__main__':
    main()
