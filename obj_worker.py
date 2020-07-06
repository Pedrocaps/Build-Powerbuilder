import util
import uuid
import os


def obj_list_from_pbg(pbg):
    get_objects_list = []

    if pbg[-4:] == '.pbd':
        return
    content = util.read_file(pbg)
    lines = content.readlines()

    is_pbl = False
    pbl = ''
    is_obj = False

    for line in lines:
        if not line.strip():
            continue
        if '@begin Libraries' in line:
            is_pbl = True
            continue
        if is_pbl:
            splits = line.strip().split(' ')
            try:
                ini = 1 if splits[0].rfind('\\\\') == -1 else splits[0].rfind('\\\\') + 2
                fim = -1
                pbl = splits[0].strip()[ini:fim]
                # logger.info('\tPBL: {}'.format(pbl))
            except IndexError as err:
                pass  # logger.error('\tsplits: {}'.format(splits))
            is_pbl = False
            continue
        if '@begin Objects' in line:
            is_obj = True
            continue
        if is_obj:
            if '@end;' in line.strip():
                continue
            if line.strip() == '':
                continue
            line = line.strip()
            if line[0] != ' ':
                line = ' ' + line
            splits = line.split(' ')
            ini = 1 if splits[-1].rfind('\\\\') == -1 else splits[-1].rfind('\\\\') + 2
            fim = -2
            pbl_obj = splits[-1].strip()[ini:fim]
            if pbl_obj == pbl:
                try:
                    path = splits[1]

                    path_dwl = util.path_obj_from_line(path)
                    get_objects_list.append(path_dwl)
                except IndexError:
                    raise
                except FileNotFoundError:
                    raise

    return get_objects_list


def get_obj_from_list(obj_list: list):
    config = util.get_config()

    tfs_base = config['TFS_BASE_DIR']
    base_path = f"{config['CHANGE_BASE_CWD']}\\{config['BASE_DIR']}"
    system_name = config['SYSTEM_NAME']

    log_path = f'{base_path}\\{system_name}_LOG'
    thread_name = uuid.uuid1().hex
    log_path = '{}\\{}.log'.format(log_path, thread_name)
    logger = util.return_log_object(log_filename=log_path, log_name=thread_name, when=None)

    logger.info(f'Start getting {len(obj_list)} objects...')

    for i, obj in enumerate(obj_list):
        logger.info(f'\tgetting {i + 1} of {len(obj_list)} : {obj} ...')

        try:
            ret = util.get_from_tfs(obj, True)
            logger.info(f'\t\t{ret} ...')
        except FileNotFoundError as err:
            logger.info(f'\t\tError getting obj : {err}')
            return
        except TimeoutError as err:
            logger.info(f'\t\tTimeout getting obj : {err}')
            return

    logger.info(f'End getting objects...')


def delete_files_filter(files_path_list):
    config = util.get_config()

    base_path = f"{config['CHANGE_BASE_CWD']}\\{config['BASE_DIR']}"
    system_name = config['SYSTEM_NAME']

    log_path = f'{base_path}\\{system_name}_LOG'
    thread_name = uuid.uuid1().hex
    log_path = '{}\\delete_{}.log'.format(log_path, thread_name)
    logger = util.return_log_object(log_filename=log_path, log_name=thread_name, when=None)

    logger.info(f'Start deleting {len(files_path_list)} objects...')

    for i, f in enumerate(files_path_list):
        try:
            logger.info(f'\tgetting {i + 1} of {len(files_path_list)} :{f} ...')
            util.set_read_only(f)
            os.remove(f)
        except OSError as e:
            logger.info("\t\tError: %s : %s" % (f, e.strerror))
