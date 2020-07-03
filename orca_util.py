from util import pbd_list_as_string, write_new_line, return_obj_path, return_properties_from_srj, print_and_log


class OrcaUtil:
    def __init__(self, config: dict, pbd_list: list, logger):
        self.SYSTEM_NAME = config['SYSTEM_NAME']
        self.BASE_PATH = config['CHANGE_BASE_CWD']
        self.BASE_DIR = config['BASE_DIR']
        self.SYSTEM_DIR = f'{self.BASE_PATH}\\{self.BASE_DIR}\\TECCOM\{self.SYSTEM_NAME}\\Fontes'
        self.PBT_PATH = '{}\\{}'.format(self.SYSTEM_DIR, '{}.pbt'.format(self.SYSTEM_NAME))
        self.BASE_SISTEMAS_PATH = f"{self.BASE_PATH}\\{config['BASE_DIR']}"
        self.CONFIG_ORCA = config['PBORCA']
        self.VERSAO = config['VERSAO']
        self.PBD_LIST = pbd_list
        self.LOGGER = logger
        self.SYSTEM_DESC = config['SYSTEM_DESC']

        bat_3step = self.CONFIG_ORCA['BAT_3STEP'].format(self.SYSTEM_NAME)
        self.BAT_PATH = f"{self.BASE_SISTEMAS_PATH}\\{bat_3step}"

        bat_exe = self.CONFIG_ORCA['BAT_BUILD_EXE'].format(self.SYSTEM_NAME)
        self.BAT_EXE = f"{self.BASE_SISTEMAS_PATH}\\{bat_exe}"

        orca_log_path = f'{self.BASE_SISTEMAS_PATH}\\{self.SYSTEM_NAME}_LOG'
        self.ORCA_LOG_PATH = '{}\\3step.log'.format(orca_log_path)

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

        orca_3step_dat = self.CONFIG_ORCA['ORCA_3STEP_DAT'].format(self.SYSTEM_NAME)
        orca_3_step_file = f"{self.BASE_SISTEMAS_PATH}\\{orca_3step_dat}"
        cmd_bat = f'echo %time%\n' \
                  f'{orca_exe} {orca_3_step_file}\n' \
                  f'echo %time%'

        orca_3step_base_scrpt = self.CONFIG_ORCA['BASE_3STEP_SCRIPT']
        orca_script_lines = dict(orca_3step_base_scrpt)

        self.write_pborca_script_3step(orca_3_step_file, orca_script_lines, self.PBD_LIST)
        self.write_bat(cmd_bat, self.BAT_PATH)

    def create_pborca_exe_script(self):
        orca_exe_path = self.CONFIG_ORCA['ORCA_EXE']
        orca_exe = f'"{orca_exe_path}"'

        orca_exe_dat = self.CONFIG_ORCA['ORCA_EXE_DAT'].format(self.SYSTEM_NAME)
        orca_exe_file = f"{self.BASE_SISTEMAS_PATH}\\{orca_exe_dat}"
        cmd_bat = f'echo %time%\n' \
                  f'{orca_exe} {orca_exe_file}\n' \
                  f'echo %time%'

        self.write_bat(cmd_bat, self.BAT_EXE)

        orca_exe_base_scrpt = self.CONFIG_ORCA['BASE_EXE_SCRIPT']
        orca_script_lines = dict(orca_exe_base_scrpt)

        self.write_pborca_script_exe(orca_exe_file, orca_script_lines)

        pass

    def write_pborca_script_3step(self, orca_file: str, orca_script_lines: dict, pbd_list: list):
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

    def write_pborca_script_exe(self, orca_file: str, orca_script_lines: dict):
        try:
            pbd_dict = return_properties_from_srj(self.SYSTEM_DIR)
        except FileNotFoundError:
            raise

        with open(orca_file, 'w+') as f:
            for k, v in orca_script_lines.items():
                if k == 'SET_LIB_LIST':
                    lib_list = ';'.join([pbl for pbl in pbd_dict])
                    v = v.format(f'"{lib_list}"')
                elif k == 'SET_APPLICATION':
                    sra_path = f'{self.SYSTEM_DIR}\\{self.SYSTEM_NAME}.pbl'
                    sra_path = f'"{sra_path}" "{self.SYSTEM_NAME}"'
                    v = v.format(sra_path)
                elif k == 'FILE_VERSION_NUM':
                    version = f'{self.VERSAO[0:2]},{self.VERSAO[2:5]},{self.VERSAO[5:]},{0}'
                    v = v.format(f'"{version}"')
                elif k == 'FILE_VERSION':
                    version = f'{self.VERSAO[0:2]}.{self.VERSAO[2:5]}.{self.VERSAO[5:]}'
                    v = v.format(f'"{version}"')
                elif k == 'COMPANY_NAME':
                    company = 'ENERGISA S.A.'
                    v = v.format(f'"{company}"')
                elif k == 'DESCRIPTION':
                    desc = 'Sistema de Controle de Cálculo de Indenizações'
                    v = v.format(f'"{desc}"')
                elif k == 'COPYRIGHT':
                    copy_right = 'ENERGISA S.A.'
                    v = v.format(f'"{copy_right}"')
                elif k == 'PRODUCT_NAME':
                    v = v.format(f'"{self.SYSTEM_NAME}"')
                elif k == 'PRODUCT_VERSION_NUM':
                    version = f'{self.VERSAO[0:2]},{self.VERSAO[2:5]},{self.VERSAO[5:]}'
                    v = v.format(f'"{version}"')
                elif k == 'PRODUCT_VERSION':
                    version = f'{self.VERSAO[0:2]}.{self.VERSAO[2:5]}.{self.VERSAO[5:]}'
                    v = v.format(f'"{version}"')
                elif k == 'BUILD_LIBRARY':
                    pbds = ''.join([f'build library "{k}" "" pbd\n' if v == '1' else '' for k, v in pbd_dict.items()])
                    v = v.format(pbds)
                elif k == 'BUILD_EXE':
                    exe_name = f'{self.SYSTEM_DIR}\\{self.SYSTEM_NAME}.exe'
                    ico_path = ''
                    pbr_path = return_obj_path(self.SYSTEM_DIR, f'{self.SYSTEM_NAME}.pbr')
                    build_pbd = ''.join(['n' if v == '0' else 'y' for k, v in pbd_dict.items()])
                    exe_line = f'"{exe_name}" "{ico_path}" "{pbr_path}" "{build_pbd}"'
                    v = v.format(exe_line)

                write_new_line(f, v, qtd=2)

    def write_bat(self, cmd: str, bat_name):
        with open(bat_name, 'w+') as f:
            write_new_line(file=f, text=cmd)
