
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
serial_timeout = 0.5

mssb_types = ["MSSB 4x1", "MSSB 32x1", "MSSB 16x2", "MSSB 8x4"]

settings_mssb_4x1 = {
    'baudrate': 2400,			                # Baudrate:		2400
    'bytesize': serial.EIGHTBITS,				# Bytesize:		8
    'parity': serial.PARITY_NONE,				# Parity: 		Odd for 8x4 to 32x1 and None for 4x1
    'stopbits': serial.STOPBITS_ONE,			# Stop Bits: 	1
    'xonxoff': False,			# Software Flow Control
    'dsrdtr': False,			# DSR/DTR Flow Control
    'rtscts': False,			# RTS/CTS Flow Control
    'timeout': serial_timeout,			    # Timeout for reading
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
    'timeout': serial_timeout,			    # Timeout for reading
    'write_timeout': None,		# Timeout for writing
    'inter_byte_timeout': None  # Inter-character timeout
}


class MSSBController:
    def __init__(self, serial_port, module=None, log=None):
        self.log = log if log is not None else logging.getLogger(
            'MSSB Control')
        self.module = module
        self.serial_settings = None
        self.serial_port = serial_port
        self.serial = serial.Serial(self.serial_port)
        self.select_module_settings(module)
        self.serial.apply_settings(self.serial_settings)

    def select_module_settings(self, module):
        self.module = 'default' if module is None else module
        if self.module == 'MSSB 4x1':
            self.serial_settings = settings_mssb_4x1
        elif self.module == 'MSSB 8x4':
            self.serial_settings = settings_mssb_default
        elif self.module == 'MSSB 16x2':
            self.serial_settings = settings_mssb_default
        elif self.module == 'MSSB 32x1':
            self.serial_settings = settings_mssb_default
        else:
            self.serial_settings = settings_mssb_default

    def get_hardware_version(self):
        self.serial_write(66)
        sleep(0.25)
        line = self.serial.readline()
        line = line.decode('utf-8').strip()
        return line.replace('Hardware: ', '')

    def get_software_version(self):
        self.serial_write(67)
        sleep(0.25)
        line = self.serial.readline()
        line = line.decode('utf-8').strip()
        return line.replace('Software-Version: ', '')

    def get_connections(self):
        self.serial_write(65)
        self.serial_read()

    def connect_sim(self, sim, terminal=None):
        if self.module == 'MSSB 4x1':
            self.serial_write(160 + (sim - 1))
        elif self.module == 'MSSB 8x4':
            self.serial_write(160 + (sim - 1) * 4 + (terminal - 1))
        elif self.module == 'MSSB 16x2':
            self.serial_write(160 + (sim - 1) * 2 + (terminal - 1))
        elif self.module == 'MSSB 32x1':
            self.serial_write(160 + (sim - 1))
        else:
            self.serial_write(160 + (sim - 1))
        sleep(serial_timeout)
        self.serial_read_hex()

    def disconnect_sim(self, sim, terminal=None):
        if self.module == 'MSSB 4x1':
            self.serial_write(128 + (sim - 1))
        elif self.module == 'MSSB 8x4':
            self.serial_write(128 + (sim - 1) * 4 + (terminal - 1))
        elif self.module == 'MSSB 16x2':
            self.serial_write(128 + (sim - 1) * 2 + (terminal - 1))
        elif self.module == 'MSSB 32x1':
            self.serial_write(128 + (sim - 1))
        else:
            self.serial_write(128 + (sim - 1))
        sleep(serial_timeout)
        self.serial_read_hex()

    def serial_read(self):
        try:
            sleep(serial_timeout)
            lines = self.serial.readlines()
            for line in lines:
                text = line.decode('utf-8').strip()
                self.log.info("MSSB: {0}".format(text))
        except:
            traceback.print_exc()

    def serial_read_hex(self):
        try:
            line = self.serial.readline()
            line = str(line.hex()).replace('0d0a', '')
            self.log.debug("Reading MSSB: {0}".format(line))
        except:
            traceback.print_exc()

    def serial_write(self, message):
        try:
            self.log.debug("Writing: {0}".format(message))
            self.serial.write(message.to_bytes(1, byteorder='big'))
        except:
            traceback.print_exc()

    def test_mssb(self):
        if self.module == 'MSSB 4x1':
            self.test_mssb_4x1()
        elif self.module == 'MSSB 8x4':
            self.test_mssb_8x4()
        elif self.module == 'MSSB 16x2':
            self.test_mssb_16x2()
        elif self.module == 'MSSB 32x1':
            self.test_mssb_32x1()
        else:
            self.log.errors("No matching MSSB Type found for test")

    def test_mssb_4x1(self):
        self.get_connections()
        self.log.info("Software: " + self.get_software_version())
        self.log.info("Hardware: " + self.get_hardware_version())
        for sim in range(1, 5):
            self.connect_sim(sim)

    def test_mssb_32x1(self):
        self.get_connections()
        self.log.info("Software: " + self.get_software_version())
        self.log.info("Hardware: " + self.get_hardware_version())
        for sim in range(1, 33):
            self.connect_sim(sim)

    def test_mssb_16x2(self):
        self.get_connections()
        self.log.info("Software: " + self.get_software_version())
        self.log.info("Hardware: " + self.get_hardware_version())
        for sim in range(1, 17):
            for terminal in range(1, 3):
                self.connect_sim(sim, terminal)
                self.disconnect_sim(sim, terminal)

    def test_mssb_8x4(self):
        self.get_connections()
        self.log.info("Software: " + self.get_software_version())
        self.log.info("Hardware: " + self.get_hardware_version())
        for sim in range(1, 9):
            for terminal in range(1, 5):
                self.connect_sim(sim, terminal)
                self.disconnect_sim(sim, terminal)


@click.command()
@click.option("--port", "-p", default='COM14', help="COM Port // ttyUSB for the connection")
@click.option("--mssbtype", "-t", default='MSSB 32x1', help="Defines MSSB Type.")
@click.option("--verbose", "-v", is_flag=True, help="More verbose output")
@click.option("--autodetect", "-auto", is_flag=True, help="Looks for MSSB via TTY/COM")
def test(port, mssbtype, verbose, autodetect):
    if verbose:
        logger.setLevel(logging.DEBUG)

    if autodetect:
        logger.info("Autodetect MSSB")
        if os.name == 'nt':
            serial_list = serial.tools.list_ports.grep('[COM]')
        elif os.name == 'posix':
            serial_list = serial.tools.list_ports.grep('/dev/tty[USB]')
        mssb = check_serial_devices(serial_list)
    else:
        mssb = MSSBController(port, mssbtype, logger)  # 'COM14'
        if mssb is None:
            logger.errors("No matching MSSB detected")
            sys.exit()

    logger.info('MSSB Module type: ' + mssb.module +
                ' connected on Port:' + mssb.serial.port)

    logger.info("Testing")
    mssb.test_mssb()

    sys.exit()


def check_serial_devices(serial_list):
    for comPort in sorted(serial_list):
        try:
            logger.info("Checking ports: " + comPort.device)
            mssb = MSSBController(comPort.device, 'default')
            mssb_type = mssb.get_hardware_version()
            if mssb_type in mssb_types:
                logger.info("On Port:{0} matching type found: {1}".format(
                    comPort.device, mssb_type))
                mssb.module = mssb_type
                return mssb
        except:
            traceback.print_exc()
    return None


if __name__ == "__main__":
    test()
