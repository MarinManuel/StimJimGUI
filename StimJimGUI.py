import argparse
import logging

import serial

# noinspection PyUnresolvedReferences
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
)

# noinspection PyUnresolvedReferences
import resources.resources
from src.StimJim import discover_ports, choose_port_dialog, STIMJIM_SERIAL_BAUDRATE
from src.GUI import StimJimGUI

logger = logging.getLogger("StimJimGUI")
handler = logging.StreamHandler()
# noinspection SpellCheckingInspection
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
LOGGING_LEVELS = [logging.NOTSET, logging.WARNING, logging.INFO, logging.DEBUG]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="StimJimGUI",
        description="This software provides a graphical user interface for controlling a StimJim, an open source "
        "electrophysiology stimulator for physiology and behavior",
    )
    parser.add_argument(
        "-p",
        "--port",
        help="the serial port used to communicate with the StimJim. If not provided, "
        "then the software will try to find the port automatically, and/or offer "
        "a choice of possible ports",
    )
    parser.add_argument(
        "-l", "--log", help="save the log file to file FILENAME", default=None
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase verbosity of output (can be "
        "repeated to increase verbosity further)",
    )
    args = parser.parse_args()

    level = LOGGING_LEVELS[
        min(args.verbose, len(LOGGING_LEVELS) - 1)
    ]  # cap to last level index
    logger.setLevel(level=level)

    if args.port is None:
        logger.info("Starting serial port auto-discovery...")
        possible_ports = discover_ports()
        if len(possible_ports) > 1:
            # there are more than 1 valid port.
            logger.info(
                f"Found serial ports {','.join([p.device for p in possible_ports])}. Asking user to choose one"
            )
            args.port = choose_port_dialog(possible_ports)
        elif len(possible_ports) == 1:
            args.port = possible_ports[0].device
            logger.info(f"Found serial port [{args.port}]")
        else:
            args.port = None

    if args.port is None:
        raise IOError(
            "Could not find a suitable serial port. Please provide the serial port using the "
            "--port argument"
        )

    serial_port = serial.Serial(args.port, baudrate=STIMJIM_SERIAL_BAUDRATE)

    app = QApplication([])
    mw = StimJimGUI(serial_port=serial_port, log_filename=args.log)
    mw.show()
    # Start the event loop.
    app.exec()
