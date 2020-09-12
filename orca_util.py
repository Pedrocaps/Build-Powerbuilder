from util import pbd_list_as_string, write_new_line, return_obj_path, return_pbd_from_srj, print_and_log,\
    return_properties_srj, get_logger_path, get_orca_path
import os
import re


class OrcaUtil:
    def __init__(self, config: dict, pbd_list: list, logger):
        self.SYSTEM_NAME = config['SYSTEM_NAME']
        self.BASE_PATH = config['CHANGE_BASE_CWD']
        self.BASE_DIR = config['BASE_DIR']
        self.SYSTEM_DIR = config['BASE_DIR'] + config['SYSTEM_PATH'].replace('SYSTEM_NAME', self.SYSTEM_NAME)
        self.SYSTEM_DIR = '{}\\{}'.format(self.BASE_PATH, self.SYSTEM_DIR)

        self.ICO_PATH = config['ICO_PATH']

        self.PBT_PATH = '{}\\{}'.format(self.SYSTEM_DIR, '{}.pbt'.format(self.SYSTEM_NAME))
        self.PBR_PATH = '{}\\{}'.format(self.SYSTEM_DIR, '{}.pbr'.format(self.SYSTEM_NAME))
        self.PBL_PATH = '{}\\{}'.format(self.SYSTEM_DIR, '{}.pbl'.format(self.SYSTEM_NAME))
        self.EXE_PATH = '{}\\{}'.format(self.SYSTEM_DIR, '{}.exe'.format(self.SYSTEM_NAME))

        self.BASE_SISTEMAS_PATH = f"{self.BASE_PATH}\\{config['BASE_DIR']}"
        self.CONFIG_ORCA = config['PBORCA']
        self.VERSAO = config['VERSAO']
        self.PBD_LIST = pbd_list
        self.LOGGER = logger
        self.SYSTEM_DESC = config['SYSTEM_DESC']
        self.USE_SRJ = str(config['USE_SRJ']).upper() == 'S'

        build_path = get_orca_path()
        orca_log_path = get_logger_path()

        bat_3step = self.CONFIG_ORCA['BAT_3STEP'].format(self.SYSTEM_NAME)
        dat_3step = self.CONFIG_ORCA['ORCA_3STEP_DAT'].format(self.SYSTEM_NAME)

        self.BAT_PATH = f"{build_path}\\{bat_3step}"
        self.DAT_PATH = f"{build_path}\\{dat_3step}"

        bat_exe = self.CONFIG_ORCA['BAT_BUILD_EXE'].format(self.SYSTEM_NAME)
        dat_exe = self.CONFIG_ORCA['ORCA_EXE_DAT'].format(self.SYSTEM_NAME)

        self.BAT_EXE = f"{build_path}\\{bat_exe}"
        self.DAT_EXE = f"{build_path}\\{dat_exe}"

        self.ORCA_LOG_PATH = '{}\\3step.log'.format(orca_log_path)
        self.ORCA_LOG_EXE_PATH = '{}\\exe_orca_log.log'.format(orca_log_path)

    def create_pborca_scripts(self):
        print_and_log(self.LOGGER.info, '\tCREATE 3STEP SCRIPT')
        self.create_3step_script()
        print_and_log(self.LOGGER.info, '\tDone create 3step scripts...')

        print_and_log(self.LOGGER.info, '\tCREATE EXE SCRIPT')
        self.create_pborca_exe_script()
        print_and_log(self.LOGGER.info, '\tDone create exe scripts...')

    def create_3step_script(self):
        orca_exe_path = self.CONFIG_ORCA['ORCA_EXE']
        orca_exe = f'"{orca_exe_path}"'

        cmd_bat = f'echo %time%\n' \
                  f'{orca_exe} {self.DAT_PATH}\n' \
                  f'echo %time%'

        orca_3step_base_scrpt = self.CONFIG_ORCA['BASE_3STEP_SCRIPT']
        orca_script_lines = dict(orca_3step_base_scrpt)

        self.write_pborca_script_3step(self.DAT_PATH, orca_script_lines, self.PBD_LIST)
        self.write_bat(cmd_bat, self.BAT_PATH)

    def create_pborca_exe_script(self):
        orca_exe_path = self.CONFIG_ORCA['ORCA_EXE']
        orca_exe = f'"{orca_exe_path}"'

        cmd_bat = f'echo %time%\n' \
                  f'{orca_exe} {self.DAT_EXE}\n' \
                  f'echo %time%'

        self.write_bat(cmd_bat, self.BAT_EXE)

        orca_exe_base_scrpt = self.CONFIG_ORCA['BASE_EXE_SCRIPT']
        orca_script_lines = dict(orca_exe_base_scrpt)

        self.write_pborca_script_exe(self.DAT_EXE, orca_script_lines)

        pass

    def write_pborca_script_3step(self, orca_file: str, orca_script_lines: dict, pbd_list: list):
        try:
            with open(orca_file, 'w+') as f:
                for k, v in orca_script_lines.items():
                    if k == 'LOG_FILE':
                        v = v.format('\"{}\"'.format(self.ORCA_LOG_PATH))
                    elif k == 'PROJ_PATH':
                        v = v.format(f'\"{self.SYSTEM_DIR}\"')
                    elif k == 'SET_TARGET':
                        v = v.format(f'\"{self.PBT_PATH}\"')
                    elif k == 'EXCLUDE_PBD':
                        pbds = pbd_list_as_string(pbd_list)
                        v = v.format('{}'.format(pbds))

                    write_new_line(f, v, qtd=2)
        except Exception as err:
            print(err)

    def write_pborca_script_exe(self, orca_file: str, orca_script_lines: dict):
        try:
            pbd_dict = return_pbd_from_srj(self.SYSTEM_DIR)
            prp_dict = return_properties_srj(self.SYSTEM_DIR)
        except FileNotFoundError:
            raise

        with open(orca_file, 'w+') as f:
            for k, v in orca_script_lines.items():
                if k == 'SET_LIB_LIST':
                    lib_list = ';'.join([pbl for pbl in pbd_dict])
                    v = v.format(f'"{lib_list}"')
                elif k == 'SET_APPLICATION':
                    v = v.format(f'"{self.PBL_PATH}" "{self.SYSTEM_NAME}"')
                elif k == 'FILE_VERSION_NUM':
                    if self.USE_SRJ:
                        version = prp_dict['FVN'].strip()
                    else:
                        version = f'{self.VERSAO[0:2]},{self.VERSAO[2:5]},{self.VERSAO[5:]},{0}'
                    v = v.format(f'"{version}"')
                elif k == 'FILE_VERSION':
                    if self.USE_SRJ:
                        version = prp_dict['FVS'].strip()
                    else:
                        version = f'{self.VERSAO[0:2]}.{self.VERSAO[2:5]}.{self.VERSAO[5:]}'
                    v = v.format(f'"{version}"')
                elif k == 'COMPANY_NAME':
                    if self.USE_SRJ:
                        company = self.decode_pb_line(prp_dict['COM'].strip())
                    else:
                        company = 'S.A.'
                    v = v.format(f'"{company}"')
                elif k == 'DESCRIPTION':
                    if self.USE_SRJ:
                        desc = self.decode_pb_line(prp_dict['DES'])
                    else:
                        desc = 'Sistema de Controle de Cálculo de Indenizações'
                    v = v.format(f'"{desc}"')
                elif k == 'COPYRIGHT':
                    if self.USE_SRJ:
                        copy_right = self.decode_pb_line(prp_dict['CPY'].strip())
                    else:
                        copy_right = 'SA'
                    v = v.format(f'"{copy_right}"')
                elif k == 'PRODUCT_NAME':
                    if self.USE_SRJ:
                        prd = prp_dict['PRD']
                        v = v.format(f'"{prd}"')
                    else:
                        v = v.format(f'"{self.SYSTEM_NAME}"')
                elif k == 'PRODUCT_VERSION_NUM':
                    if self.USE_SRJ:
                        version = prp_dict['PVN'].strip()
                    else:
                        version = f'{self.VERSAO[0:2]},{self.VERSAO[2:5]},{self.VERSAO[5:]}'
                    v = v.format(f'"{version}"')
                elif k == 'PRODUCT_VERSION':
                    if self.USE_SRJ:
                        version = prp_dict['PVS'].strip()
                    else:
                        version = f'{self.VERSAO[0:2]}.{self.VERSAO[2:5]}.{self.VERSAO[5:]}'
                    v = v.format(f'"{version}"')
                elif k == 'BUILD_LIBRARY':
                    pbds = ''.join([f'build library "{k}" "" pbd\n'
                                    if v == '1' and '.pbd' not in k else '' for k, v in pbd_dict.items()])
                    v = v.format(pbds)
                elif k == 'BUILD_EXE':
                    exe_name = self.EXE_PATH
                    ico_path = self.ICO_PATH
                    pbr_path = return_obj_path(self.SYSTEM_DIR, f'{self.SYSTEM_NAME}.pbr')
                    build_pbd = ''.join(['n' if v == '0' else 'y' for k, v in pbd_dict.items()])
                    exe_line = f'"{exe_name}" "{ico_path}" "{pbr_path}" "{build_pbd}"'
                    v = v.format(exe_line)

                write_new_line(f, v, qtd=2)

    def write_bat(self, cmd: str, bat_name):
        with open(bat_name, 'w+') as f:
            write_new_line(file=f, text=cmd)

    def decode_pb_line(self, line):
        split_arr = line.split('$$')
        hex_str = ''
        str_ret = ''
        find = False

        for s in split_arr:
            if find:
                hex_str = hex_str + s
                some_bytes = bytes.fromhex(hex_str)
                decoded = some_bytes.decode('utf-16le')

                par_str = decoded
                find = False
                hex_str = ''
            elif re.match(r'HEX[0-9]', s):
                find = True
                par_str = ''
            elif s == 'ENDHEX':
                par_str = ''
            else:
                par_str = s

            str_ret = str_ret + par_str

        return str_ret
