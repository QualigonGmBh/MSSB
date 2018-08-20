
# -*- encoding: utf-8 -*-
import sys
import os
from time import sleep
import traceback			# traceback errors for debugging
import logging              # logging library
import serial               # library to connect to serial devices
import serial.tools.list_ports
import click

"""
	Reads serial data with fixed timeout and prints it out.
	Uses synchronous serial library
    Python packages needed: python -m pip install <package>
        -   pyserial
        -   click
"""

logger = logging.getLogger('MSSB Control')
logging.basicConfig(level=logging.INFO)
serial_read_timeout = 0.8

mssb_types = ['MSSB 4x1', 'MSSB 32x1', 'MSSB 16x2', 'MSSB 8x4']

settings_mssb_4x1 = {
    'baudrate': 2400,			                # Baudrate:		2400
    'bytesize': serial.EIGHTBITS,				# Bytesize:		8
    'parity': serial.PARITY_NONE,				# Parity: 		Odd for 8x4 to 32x1 and None for 4x1
    'stopbits': serial.STOPBITS_ONE,			# Stop Bits: 	1
    'xonxoff': False,			# Software Flow Control
    'dsrdtr': False,			# DSR/DTR Flow Control
    'rtscts': False,			# RTS/CTS Flow Control
    'timeout': serial_read_timeout,			    # Timeout for reading
    'write_timeout': None,		# Timeout for writing
    'inter_byte_timeout': None  # Inter-character timeout
}
settings_mssb_default = {
    'baudrate': 2400,			                # Baudrate:		2400
    'bytesize': serial.EIGHTBITS,				# Bytesize:		8
    'parity': serial.PARITY_ODD,				# Parity: 		Odd for 8x4 to 32x1 and None for 4x1
    'stopbits': serial.STOPBITS_ONE,			# Stop Bits: 	1
    'xonxoff': False,			# Software Flow Control
    'dsrdtr': False,			# DSR/DTR Flow Control
    'rtscts': False,			# RTS/CTS Flow Control
    'timeout': serial_read_timeout,			    # Timeout for reading
    'write_timeout': None,		# Timeout for writing
    'inter_byte_timeout': None  # Inter-character timeout
}


class MSSBController:
    def __init__(self, serial_port, module=None, mode='legacy', log=None):
        self.log = log if log is not None else logging.getLogger(
            'MSSB Control')
        self.type = module
        self.mode = mode
        self.serial_settings = None
        self.serial_port = serial_port
        self.serial = serial.Serial(self.serial_port)
        self.select_module_settings(module)
        self.serial.apply_settings(self.serial_settings)

    def select_module_settings(self, module):
        self.type = 'default' if module is None else module
        if self.type == 'MSSB 4x1':
            self.serial_settings = settings_mssb_4x1
        elif self.type == 'MSSB 8x4':
            self.serial_settings = settings_mssb_default
        elif self.type == 'MSSB 16x2':
            self.serial_settings = settings_mssb_default
        elif self.type == 'MSSB 32x1':
            self.serial_settings = settings_mssb_default
        else:
            self.serial_settings = settings_mssb_default

    def get_hardware_version(self):
        if self.mode == 'legacy':
            self.write_hex(66)
        if self.mode == 'text':
            self.write_char('Hardware?')
        sleep(serial_read_timeout)
        line = self.serial.readline()
        line = line.decode('utf-8').strip()
        self.log.debug(f'Reading: {line}')
        return line.replace('Hardware: ', '')

    def get_software_version(self):
        if self.mode == 'legacy':
            self.write_hex(67)
        if self.mode == 'text':
            self.write_char('Software?')
        sleep(serial_read_timeout)
        line = self.serial.readline()
        line = line.decode('utf-8').strip()
        self.log.debug(f'Reading: {line}')
        return line.replace('Software-Version: ', '')

    def get_connections(self):
        if self.mode == 'legacy':
            self.write_hex(65)
        if self.mode == 'text':
            self.write_char('Connections?')
        self.readlines()

    def set_legacy_mode(self):
        self.write_hex(91)
        if self.readline_char() == 'Leaving Textmode':
            self.mode = 'legacy'
            logger.info("Changed to legacy mode")
        else:
            logger.warning("Error: changing to legacy mode failed")

    def set_text_mode(self):
        self.write_hex(93)
        if self.readline_char() == 'Entering Textmode':
            self.mode = 'text'
            logger.info("Changed to text mode")
        else:
            logger.warning("Error: changing to text mode failed")

    def connect_sim_legacy(self, sim, terminal=None):
        value = return_value = 0
        if self.type == 'MSSB 4x1':
            value = (160 + (sim - 1))

        elif self.type == 'MSSB 8x4':
            value = (160 + (sim - 1) * 4 + (terminal - 1))
        elif self.type == 'MSSB 16x2':
            value = (160 + (sim - 1) * 2 + (terminal - 1))

        elif self.type == 'MSSB 32x1':
            value = (160 + (sim - 1))
        else:
            value = (160 + (sim - 1))
        self.write_hex(value)
        return_value = self.readline_hex()

        logger.debug(
            f'Connect: Sending {hex(value)}  Receiving 0x{return_value}')
        if f'{hex(value)}' == f'0x{return_value}':
            return True
        else:
            logger.warning(
                f'Connecting error on SIM {sim} Terminal {terminal}')
            return False

    def connect_sim_text(self, sim, terminal=None):
        value = return_value = 0
        if self.type == 'MSSB 4x1':
            value = f'0:{sim-1}'
        elif self.type == 'MSSB 8x4':
            value = f'{terminal-1}:{sim-1}'
        elif self.type == 'MSSB 16x2':
            value = f'{terminal-1}:{sim-1}'
        elif self.type == 'MSSB 32x1':
            value = f'0:{sim-1}'
        else:
            value = f'0:{sim-1}'

        self.write_char(value)
        return_value = self.readline_char()

        logger.debug(
            f'Connect: Sending {value} OK Receiving {return_value}')
        if f'{value} OK' == f'{return_value}':
            return True
        else:
            logger.warning(
                f'Connecting error on SIM {sim} Terminal {terminal}')
            return False

    def connect_sim(self, sim, terminal=None):
        if self.mode == 'legacy':
            return self.connect_sim_legacy(sim, terminal)
        elif self.mode == 'text':
            return self.connect_sim_text(sim, terminal)

    def disconnect_sim_legacy(self, sim, terminal=None):
        value = return_value = 0
        if self.type == 'MSSB 4x1':
            if self.mode == 'legacy':
                value = (128 + (sim - 1))
            if self.mode == 'text':
                value = f'0:{sim-1}'
        elif self.type == 'MSSB 8x4':
            if self.mode == 'legacy':
                value = (128 + (sim - 1) * 4 + (terminal - 1))
            if self.mode == 'text':
                value = f'{terminal-1}:{sim-1}'
        elif self.type == 'MSSB 16x2':
            if self.mode == 'legacy':
                value = (128 + (sim - 1) * 2 + (terminal - 1))
            if self.mode == 'text':
                value = f'{terminal-1}:{sim-1}'
        elif self.type == 'MSSB 32x1':
            if self.mode == 'legacy':
                value = (128 + (sim - 1))
            if self.mode == 'text':
                value = f'0:{sim-1}'
        else:
            if self.mode == 'legacy':
                value = (128 + (sim - 1))
            if self.mode == 'text':
                value = f'0:{sim-1}'
        self.write_hex(value)
        return_value = self.readline_hex()
        logger.debug(
            f'Disconnect: Sending {hex(value)}  Receiving 0x{return_value}')
        if f'{hex(value)}' == f'0x{return_value}':
            return True
        else:
            logger.warning(
                f'Disconnecting error on SIM {sim} Terminal {terminal}')
            return False

    def disconnect_sim_text(self, sim, terminal=None):
        value = return_value = 0
        if self.type == 'MSSB 4x1':
            value = f'0:'
        elif self.type == 'MSSB 8x4':
            value = f'{terminal-1}:'
        elif self.type == 'MSSB 16x2':
            value = f'{terminal-1}:'
        elif self.type == 'MSSB 32x1':
            value = f'0:'
        else:
            value = f'0:'

        self.write_char(value)
        return_value = self.readline_char()

        logger.debug(
            f'Connect: Sending {value} OK Receiving {return_value}')
        if f'{value} OK' == f'{return_value}':
            return True
        else:
            logger.warning(
                f'Connecting error on SIM {sim} Terminal {terminal}')
            return False

    def disconnect_sim(self, sim, terminal=None):
        if self.mode == 'legacy':
            return self.disconnect_sim_legacy(sim, terminal)
        elif self.mode == 'text':
            return self.disconnect_sim_text(sim, terminal)

    def readlines(self):
        try:
            sleep(serial_read_timeout)
            lines = self.serial.readlines()
            for line in lines:
                text = line.decode('utf-8').strip()
                self.log.info(f'Reading: {text}')
        except:
            traceback.print_exc()

    def readline_char(self):
        try:
            sleep(serial_read_timeout)
            line = self.serial.readline()
            line = line.decode('utf-8').strip()
            self.log.debug(f'Reading: {line}')
            return line
        except:
            traceback.print_exc()

    def readline_hex(self):
        try:
            sleep(serial_read_timeout)
            line = self.serial.readline()
            line = str(line.hex()).replace('0d0a', '')
            self.log.debug(f'Reading: {line}')
            return line
        except:
            traceback.print_exc()

    def write_char(self, message):
        try:
            self.log.debug(f'Writing: {message}')
            self.serial.write(message.encode('utf-8'))
        except:
            traceback.print_exc()

    def write_hex(self, message):
        try:
            self.log.debug(f'Writing: {message}')
            self.serial.write(message.to_bytes(1, byteorder='big'))
        except:
            traceback.print_exc()

    def test_internal(self):
        if self.mode == 'legacy':
            self.write_hex(69)
            self.readlines()
        if self.mode == 'text':
            self.write_char('Selftest?')
            self.readlines()
        sleep(3)

    def test_mssb(self):
        if self.type == 'MSSB 4x1':
            self.test_mssb_4x1()
        elif self.type == 'MSSB 8x4':
            self.test_mssb_8x4()
        elif self.type == 'MSSB 16x2':
            self.test_mssb_16x2()
        elif self.type == 'MSSB 32x1':
            self.test_mssb_32x1()
        else:
            self.log.error('No matching MSSB Type found for test')

    def test_mssb_4x1(self):
        self.get_connections()
        self.log.info('Software: ' + self.get_software_version())
        self.log.info('Hardware: ' + self.get_hardware_version())
        for sim in range(1, 5):
            self.connect_sim(sim)

    def test_mssb_32x1(self):
        self.get_connections()
        self.log.info('Software: ' + self.get_software_version())
        self.log.info('Hardware: ' + self.get_hardware_version())
        for sim in range(1, 33):
            self.connect_sim(sim)

    def test_mssb_16x2(self):
        self.get_connections()
        self.log.info('Software: ' + self.get_software_version())
        self.log.info('Hardware: ' + self.get_hardware_version())
        for sim in range(1, 17):
            for terminal in range(1, 3):
                self.connect_sim(sim, terminal)
                self.disconnect_sim(sim, terminal)

    def test_mssb_8x4(self):
        self.get_connections()
        self.log.info('Software: ' + self.get_software_version())
        self.log.info('Hardware: ' + self.get_hardware_version())
        for sim in range(1, 9):
            for terminal in range(1, 5):
                self.connect_sim(sim, terminal)
                self.disconnect_sim(sim, terminal)


@click.command()
@click.option("--port", "-p", default='COM14', help="COM Port // ttyUSB for the connection")
@click.option("--mssbtype", "-t", default='MSSB 32x1', help="Defines MSSB Type.")
@click.option("--verbose", "-v", is_flag=True, help="More verbose output")
@click.option("--autodetect", "-auto", is_flag=True, help="Looks for MSSB via TTY/COM")
def test(port=None, mssbtype=None, verbose=False, autodetect=False):
    if verbose:
        logger.setLevel(logging.DEBUG)

    if autodetect:
        logger.info('Autodetect MSSB')
        if os.name == 'nt':
            serial_list = serial.tools.list_ports.grep('[COM]')
        elif os.name == 'posix':
            serial_list = serial.tools.list_ports.grep('/dev/tty[USB]')
        mssb = check_serial_devices(serial_list)
    else:
        mssb = MSSBController(port, mssbtype, logger)  # 'COM14'

    if mssb is None:
        logger.error('No matching MSSB detected')
        sys.exit()

    logger.info(
        f'MSSB Module type: {mssb.type} connected on Port: {mssb.serial.port}')

    logger.info('Testing')
    logger.info(mssb.get_software_version())
    mssb.test_internal()
    mssb.set_text_mode()
    mssb.test_internal()
    mssb.set_legacy_mode()
    logger.info('Testing finished')
    sys.exit()


@click.command()
@click.option("--port", "-p", default='COM14', help="COM Port // ttyUSB for the connection")
@click.option("--mssbtype", "-t", default='MSSB 32x1', help="Defines MSSB Type.")
@click.option("--verbose", "-v", is_flag=True, help="More verbose output")
@click.option("--autodetect", "-auto", is_flag=True, help="Looks for MSSB via TTY/COM")
def get_mssb(port, mssbtype, verbose, autodetect):
    if verbose:
        logger.setLevel(logging.DEBUG)
    if autodetect:
        logger.info('Autodetect MSSB')
        if os.name == 'nt':
            serial_list = serial.tools.list_ports.grep('[COM]')
        elif os.name == 'posix':
            serial_list = serial.tools.list_ports.grep('/dev/tty[USB]')
        mssb = check_serial_devices(serial_list)
    else:
        mssb = MSSBController(port, mssbtype, logger)  # 'COMx'

    if mssb is None:
        logger.error('No matching MSSB detected')
        sys.exit()
    return mssb


def check_serial_devices(serial_list):
    for comPort in sorted(serial_list):
        try:
            logger.info('Checking ports: ' + comPort.device)
            mssb = MSSBController(comPort.device, 'default')
            mssb_type = mssb.get_hardware_version()
            logger.debug('Hardware type read: ' + mssb_type)
            if mssb_type in mssb_types:
                logger.info(
                    f'On Port {comPort.device} matching type found: {mssb_type}')
                mssb.type = mssb_type
                return mssb
        except serial.serialutil.SerialException:
            logger.error(
                f"Can't connect to Serial Device {comPort.device}. It's already in use!")
        except:
            traceback.print_exc()
    return None


if __name__ == '__main__':
    test()
