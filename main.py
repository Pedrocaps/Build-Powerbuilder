import glob
import os
import subprocess
import time

import orca_util
import util


def get_pbt(pbt_path, config):
    try:
        util.get_from_tfs(pbt_path, config)
        _ = util.read_file(pbt_path)
    except FileNotFoundError:
        raise
    except EnvironmentError:
        raise


def get_pbr(config) -> str:
    base_path = f'{BASE_PATH}\\{SYSTEM_DIR}'
    pbr_path = '{}\\{}'.format(base_path, '*.pbr'.format(SYSTEM_NAME))

    util.get_from_tfs(pbr_path, config, False)

    pbr_list = []
    os.chdir(base_path)
    for file in glob.glob("*.pbr"):
        pbr_list.append(file)

    if len(pbr_list) == 0:
        raise FileNotFoundError
    else:
        return pbr_list[0]


def pbg_list_from_from_pbt(pbt_path: str, config, use_tfs=True) -> dict:
    pbt_content = util.read_file(pbt_path)

    lines = pbt_content.readlines()

    pbg_list = []
    pbd_list = []
    pbls = ''

    for line in lines:
        splits = line.split(' ')
        if splits[0] == 'LibList':
            pbls = splits[1].split(';')[:-1]

    util.change_cwd('{}\\{}'.format(BASE_PATH, SYSTEM_DIR))
    for pbl in pbls:
        pbl_rep = util.path_obj_from_line(pbl)
        if use_tfs:
            logger.info(f'\tGetting PBG {pbl_rep}')
            try:
                util.get_from_tfs(pbl_rep, config, True)
            except FileNotFoundError:
                raise

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
    MAX_THREADS = int(config['MAX_THREADS'])

    global BASE_PATH
    BASE_PATH = config['CHANGE_BASE_CWD']

    global SYSTEM_NAME
    SYSTEM_NAME = config['SYSTEM_NAME']

    global SYSTEM_DIR
    SYSTEM_DIR = config['BASE_DIR'] + config['SYSTEM_PATH'].replace('SYSTEM_NAME', SYSTEM_NAME)

    global BASE_SISTEMAS_PATH
    BASE_SISTEMAS_PATH = f"{BASE_PATH}\\{config['BASE_DIR']}"

    global DIST_FOLDER
    DIST_FOLDER = config['DIST_FOLDER']

    global PBT_PATH
    PBT_PATH = '{}\\{}\\{}'.format(BASE_PATH, SYSTEM_DIR, '{}.pbt'.format(SYSTEM_NAME))
    global PBW_PATH
    PBW_PATH = '{}\\{}\\{}'.format(BASE_PATH, SYSTEM_DIR, '{}.pbw'.format(SYSTEM_NAME))
    global SYSTEM_BIN_FILES
    SYSTEM_BIN_FILES = '{}\\{}'.format(BASE_PATH, SYSTEM_DIR)

    global VERSAO
    VERSAO = config['VERSAO']
    global FIGURAS_PATH
    FIGURAS_PATH = config['FIGURAS_PATH']


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


def run_bat(bat_path: str, log_path: str, bat_type: str, max_loop_config):
    i = 1
    max_loop = max_loop_config
    while i <= max_loop:
        util.print_and_log(logger.info, '\tRunning {} of {} bat executions'.format(i, max_loop))
        util.print_and_log(logger.info, '\t\t see {} for details '.format(log_path))
        cp = subprocess.run([bat_path], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True)
        i = i + 1

        if bat_type == 'EXE':
            with open(log_path, 'w+') as f:
                f.write(cp.stdout)

        if 'Result Code -22.' in cp.stdout:
            if i <= max_loop:
                continue
            try:
                errors_txt = util.get_error_from_orca_log(log_path)
                raise SyntaxError(f'Syntax Errors: {errors_txt}')
            except Exception as err:
                raise EnvironmentError('Reading log error: {}'.format(err))
        if 'Result Code -27' in cp.stdout:
            raise EnvironmentError('Target file not found:')
        if 'Result Code -6' in cp.stdout:
            raise EnvironmentError('Target file not found in path: set application')
        if 'Last Command Failed.' in cp.stdout:
            raise EnvironmentError('Error building exe')
        if 'End Session' in cp.stdout:
            return  # sucess

    raise EnvironmentError(f'Error running `{bat_type}` bat: i = {i}')


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

    util.set_read_only(file_path, '+')


def change_pbr_relative_path():
    base_path = f'{BASE_PATH}\\{SYSTEM_DIR}'
    sra_path = f'{base_path}\\{SYSTEM_NAME}.pbr'
    file_path = f'{sra_path}'

    util.change_cwd(base_path)

    util.set_read_only(file_path)

    replace = '..\\'

    with open(file_path, 'r') as f:
        get_all = f.readlines()

    with open(file_path, 'w') as f:
        for i, line in enumerate(get_all, 0):
            if line.strip() == '':
                continue
            if replace in line:
                replace_str = os.path.abspath(line)
            elif '.pbl' in line:
                replace_str = line
            else:
                replace_str = f'{FIGURAS_PATH}{line}'

            f.writelines(replace_str)

    util.set_read_only(file_path, '+')


def get_project(config, use_tfs=True) -> dict:
    try:
        if not use_tfs:
            pbg_dict = pbg_list_from_from_pbt(PBT_PATH, config, use_tfs)
            return pbg_dict

        start = time.time()
        util.print_and_log(logger.info, '##### GET PBT ######')
        get_pbt(PBT_PATH, config)
        util.print_and_log(logger.info,
                           'Done getting {} ... ({})'.format(PBT_PATH, util.format_time_exec(time.time() - start)))

        start = time.time()
        util.print_and_log(logger.info, '##### CREATE PBW ######')
        create_pbw(PBW_PATH)
        util.print_and_log(logger.info,
                           'Done creating {} ... ({})'.format(PBW_PATH, util.format_time_exec(time.time() - start)))

        start = time.time()
        util.print_and_log(logger.info, '##### GET PBR ######')
        pbr_path = get_pbr(config)
        util.print_and_log(logger.info,
                           'Done getting pbr {}... ({})'.format(pbr_path, util.format_time_exec(time.time() - start)))

        start = time.time()
        util.print_and_log(logger.info, '##### CHANGE PBR BASE PATH ######')
        # change_pbr_relative_path()
        util.print_and_log(logger.info,
                           'Done changing PBR BASE PATH ({})'.format(util.format_time_exec(time.time() - start)))

        start = time.time()
        util.print_and_log(logger.info, '##### GET PBG ######')
        pbg_dict = pbg_list_from_from_pbt(PBT_PATH, config, use_tfs)
        pbg_list = pbg_dict['ALL']
        util.print_and_log(logger.info, 'Done getting PBG(D)s...'.format(util.format_time_exec(time.time() - start)))

        start = time.time()
        util.print_and_log(logger.info, '##### GET OBJ ######')
        util.prepare_get_obj_from_pbg_thread(pbg_list, MAX_THREADS)
        util.print_and_log(logger.info,
                           'Done getting all objects... ({})'.format(util.format_time_exec(time.time() - start)))

        start = time.time()
        util.print_and_log(logger.info, '##### GET HELP FILE ######')
        # TODO: Get help..file
        util.print_and_log(logger.info,
                           'Done get help file... ({})'.format((util.format_time_exec(time.time() - start))))

        start = time.time()
        util.print_and_log(logger.info, '##### GET COMPLEMENTOS ######')
        # TODO: Get complementos
        util.print_and_log(logger.info,
                           'Done get complementos... ({} min)'.format((util.format_time_exec(time.time() - start))))

        return pbg_dict

    except FileNotFoundError as ex:
        raise ex
    except EnvironmentError as ex:
        raise ex
    except ValueError as ex:
        raise ex

    finally:
        # TODO: undo tfs checkout
        pass


def create_logger():
    try:
        log_path = util.get_logger_path()
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
    start = time.time()
    util.print_and_log(logger.info, '##### DELETE TEMP FILES ######')
    if config['DELETE_TEMP_FILES'].upper() == 'S':
        util.prepare_delete_files_filter(BASE_SISTEMAS_PATH, MAX_THREADS)
        util.print_and_log(logger.info,
                           'Done delete temp files... ({})'.format(util.format_time_exec(time.time() - start)))
    else:
        util.print_and_log(logger.info, 'Delete flag off...')


def create_scripts(pbg_dict, config) -> dict:
    """
    Create the orca scripts to be used to build the project and create the exe
    :param pbg_dict: dict with the path of the pbgs
    :param config: config file
    :return:
    """
    start = time.time()
    orca_dict = {}
    util.print_and_log(logger.info, '##### CREATE ORCA SCRIPTS ######')
    orca_helper = orca_util.OrcaUtil(config, pbg_dict['PBD'], logger)
    orca_helper.create_pborca_scripts()
    util.print_and_log(logger.info,
                       'Done create orca scripts... ({})'.format(util.format_time_exec(time.time() - start)))

    orca_dict['BAT_PATH'] = orca_helper.BAT_PATH
    orca_dict['BAT_EXE'] = orca_helper.BAT_EXE
    orca_dict['ORCA_LOG'] = orca_helper.ORCA_LOG_PATH
    orca_dict['ORCA_EXE_LOG'] = orca_helper.ORCA_LOG_EXE_PATH

    return orca_dict


def prepare_run_bat(orca_dict, config):
    start = time.time()
    try:
        max_loop = config['MAX_LOOPS']
        run_bat(orca_dict['BAT_PATH'], orca_dict['ORCA_LOG'], '3STEP', max_loop)
    except EnvironmentError as err:
        err_txt = '\tError executing 3 step bat, open pbw and correct errors : \n\t\t{}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)
    except SyntaxError as err:
        err_txt = '\tError executing 3 step bat, correct errors - {}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)

    util.print_and_log(logger.info, 'Done running 3step bat... ({})'.format(util.format_time_exec(time.time() - start)))


def prepare_run_exe(orca_dict, config):
    max_loop = config['MAX_LOOPS']
    if config['CREATE_EXE'].upper() != 'S':
        util.print_and_log(logger.info, 'Exe flag off...')
        return

    start = time.time()
    util.print_and_log(logger.info, '##### RUN EXE BAT ######')
    try:
        run_bat(orca_dict['BAT_EXE'], orca_dict['ORCA_EXE_LOG'], 'EXE', max_loop)
    except EnvironmentError as err:
        err_txt = '\tError executing EXE bat, open pbw and correct errors - {}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)
    except SyntaxError as err:
        err_txt = '\tError executing EXE bat, correct errors - {}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)

    util.print_and_log(logger.info,
                       'Done running exe bat... ({})'.format(util.format_time_exec(time.time() - start)))


def prepare_move_dist(config):
    if config['CREATE_EXE'].upper() != 'S':
        util.print_and_log(logger.info, 'Exe flag off...')
        return

    start = time.time()
    util.print_and_log(logger.info, '##### MOVING PBDs ######')
    if DIST_FOLDER == "":
        dist_folder = util.get_dist_path()
    else:
        dist_folder = DIST_FOLDER

    try:
        util.move_bin_files(base_path=SYSTEM_BIN_FILES, new_dst=dist_folder)

        util.print_and_log(logger.info,
                           'Done moving pbds... ({})'.format(util.format_time_exec(time.time() - start)))
    except Exception as err:
        err_txt = '\tError moving files, correct errors - {}'.format(err)
        util.print_and_log(logger.info, err_txt)
        raise EnvironmentError(err_txt)


def main():
    """
    Main function, it will start the timer, instantiate de logger
        and inititate de build/get process
    :return:
    """

    try:
        start = time.time()

        config = util.get_config()
        set_globals(config)
        util.change_cwd(BASE_PATH)
    except Exception as err:
        print(err)

    try:
        create_logger()
    except Exception as err:
        print(err)
        return

    logger.info('Process starded....')
    print('####################')

    is_proc_ok = start_process(config)

    minutes = (time.time() - start) / 60
    if is_proc_ok:
        util.print_and_log(logger.info, 'Complete process took {} minutes'.format(minutes))
    else:
        util.print_and_log(logger.info, 'Complete process took {} minutes, with ERRORS. Check log.'.format(minutes))


def start_process(config) -> bool:
    """
    Initiate each process of the get and build
    :param config: Config object
    :return:
    """

    try:
        pbg_dict = get_project(config, use_tfs=True)

        orca_dict = create_scripts(pbg_dict, config)

        prepare_run_bat(orca_dict, config)

        prepare_run_exe(orca_dict, config)

        prepare_move_dist(config)

        delete_temp_files(config)
    except (FileNotFoundError, EnvironmentError, SyntaxError, ValueError) as ex:
        util.print_and_log(logger.error, ex)
        return False

    return True


if __name__ == '__main__':
    main()
