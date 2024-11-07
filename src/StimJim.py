import logging
import serial.tools.list_ports
from enum import IntEnum
from typing import List

# noinspection PyUnresolvedReferences
from PyQt5 import uic
from PyQt5.QtWidgets import QInputDialog
from serial.tools.list_ports_common import ListPortInfo


STIMJIM_SERIAL_BAUDRATE = 115200
STIMJIM_SERIAL_INFO = "VID:PID=16C0:0483"  # this is for a Teensy 4.1
SERIAL_READ_INTERVAL_MS = 250
STIMJIM_N_OUTPUTS = 2
STIMJIM_N_TRIGGERS = 2
STIMJIM_MAX_PULSETRAINS = 100

logger = logging.getLogger("StimJimGUI")


class StimJimOutputModes(IntEnum):
    VOLTAGE = 0
    CURRENT = 1
    DISCONNECTED = 2
    GROUNDED = 3


class StimJimTrigDirection(IntEnum):
    RISING = 0
    FALLING = 1


STIMJIM_DEFAULT_MODE = StimJimOutputModes.GROUNDED

STIMJIM_MODE_NAMES = {
    StimJimOutputModes.VOLTAGE: "Voltage",
    StimJimOutputModes.CURRENT: "Current",
    StimJimOutputModes.DISCONNECTED: "Disconnected",
    StimJimOutputModes.GROUNDED: "Grounded (OFF)",
}

STIMJIM_MAX_VALS = {
    StimJimOutputModes.VOLTAGE: 14.9,  # integer overflow if we try to go all the way to 15V
    StimJimOutputModes.CURRENT: 3.330e-3,
    StimJimOutputModes.DISCONNECTED: 0,
    StimJimOutputModes.GROUNDED: 0,
}
STIMJIM_UNITS = {
    StimJimOutputModes.VOLTAGE: "V",
    StimJimOutputModes.CURRENT: "A",
    StimJimOutputModes.DISCONNECTED: "",
    StimJimOutputModes.GROUNDED: "",
}
STIMJIM_SCALING_FACTORS = {
    StimJimOutputModes.VOLTAGE: 1e3,  # Voltages are expressed in mV
    StimJimOutputModes.CURRENT: 1e6,  # Current is expressed un μA
    StimJimOutputModes.DISCONNECTED: 1,
    StimJimOutputModes.GROUNDED: 1,
}
STIMJIM_INCREMENT_STEPS = {
    StimJimOutputModes.VOLTAGE: 1e-3,  # Voltages are expressed in mV
    StimJimOutputModes.CURRENT: 1e-6,  # Current is expressed un μA
    StimJimOutputModes.DISCONNECTED: 0,
    StimJimOutputModes.GROUNDED: 0,
}
STIMJIM_DURATION_SCALING_FACTOR = 1e6  # durations are expressed in μs
STIMJIM_TRIGGER_COMMANDS = ["T", "U"]


def discover_ports(pattern=STIMJIM_SERIAL_INFO):
    logger.debug(f"Discovering ports containing pattern '{pattern}'")
    ports = list(serial.tools.list_ports.grep(pattern))
    logger.debug(f"Found: {ports}")
    return ports


class StimJimTooManyStagesException(Exception):
    pass


class Trigger(object):
    def __init__(
        self, trig_id=0, trig_direction=StimJimTrigDirection.RISING, train_target=-1
    ):
        self.trig_id = trig_id
        self.trig_direction = StimJimTrigDirection(int(trig_direction))
        self.train_target = train_target

    def __repr__(self):
        return f"Tigger [{'OFF' if self.trig_id<0 else self.trig_id}][{self.trig_direction.name}] -> Train {self.train_target}"

    def get_stimjim_string(self):
        return f"R{self.trig_id},{self.train_target},{self.trig_direction}"

    def to_json(self):
        return self.__dict__

    @staticmethod
    def from_json(json_dct):
        return Trigger(**json_dct)


class PulseTrain(object):
    MAX_N_PHASES = 10

    def __init__(
        self,
        train_id=0,
        train_period_us=2000,
        train_duration_us=1000000,
        channel_modes=None,
        stages=None,
    ):
        self.train_id = train_id
        self._channel_modes = (
            [StimJimOutputModes.GROUNDED] * STIMJIM_N_OUTPUTS
            if channel_modes is None
            else channel_modes
        )
        self._train_period_us = train_period_us
        self._train_duration_us = train_duration_us
        self._stages = [] if stages is None else stages

    def add_stage(self, stage=None):
        if len(self._stages) >= self.MAX_N_PHASES:
            raise StimJimTooManyStagesException(
                f"Cannot add more that {self.MAX_N_PHASES} to a PulseTrain"
            )
        else:
            if stage is None:
                stage = PulseStage()
            stage.pulse_train = self
            self._stages.append(stage)

    def remove_stage(self, index: int = -1):
        self._stages.pop(index)

    @property
    def stages(self):
        return self._stages

    def set_mode(self, channel_index: int, mode: StimJimOutputModes):
        self._channel_modes[channel_index] = mode

    def get_mode(self, channel_index: int):
        return self._channel_modes[channel_index]

    @property
    def train_period_us(self) -> int:
        return int(self._train_period_us)

    @train_period_us.setter
    def train_period_us(self, value: int):
        self._train_period_us = int(value)

    @property
    def train_period_s(self) -> float:
        return self._train_period_us / STIMJIM_DURATION_SCALING_FACTOR

    @train_period_s.setter
    def train_period_s(self, value: float):
        self._train_period_us = int(value * STIMJIM_DURATION_SCALING_FACTOR)

    @property
    def train_duration_us(self) -> int:
        return int(self._train_duration_us)

    @train_duration_us.setter
    def train_duration_us(self, value: int):
        self._train_duration_us = int(value)

    @property
    def train_duration_s(self) -> float:
        return self._train_duration_us / STIMJIM_DURATION_SCALING_FACTOR

    @train_duration_s.setter
    def train_duration_s(self, value: int):
        self._train_duration_us = int(value * STIMJIM_DURATION_SCALING_FACTOR)

    def get_stimjim_string(self):
        command = f"S{self.train_id:d},{self.get_mode(0):d},{self.get_mode(1):d},{self.train_period_us:d},{self.train_duration_us:d}"
        for stage in self.stages:
            command += ";" + stage.get_stimjim_string()
        command += "\n"
        return command

    def to_json(self):
        return dict(
            train_id=self.train_id,
            train_period_us=self.train_period_us,
            train_duration_us=self.train_duration_us,
            channel_modes=[int(mode) for mode in self._channel_modes],
            stages=[stage.to_json() for stage in self.stages],
        )

    @staticmethod
    def from_json(json_dict):
        pt = PulseTrain(
            json_dict["train_id"],
            train_period_us=json_dict["train_period_us"],
            train_duration_us=json_dict["train_duration_us"],
            channel_modes=json_dict["channel_modes"],
        )
        for stage_dict in json_dict["stages"]:
            pp = PulseStage(**stage_dict)
            pp.pulse_train = pt
            pt.add_stage(pp)
        return pt


class PulseStage(object):
    def __init__(self, ch0_amp=0, ch1_amp=0, duration=100):
        self.channel_amps = [ch0_amp, ch1_amp]
        self.duration_us = duration
        self._pulse_train = None

    @property
    def pulse_train(self):
        return self._pulse_train

    @pulse_train.setter
    def pulse_train(self, value: PulseTrain):
        self._pulse_train = value

    def get_stimjim_string(self):
        return f"{int(self.channel_amps[0]):d},{int(self.channel_amps[1]):d},{int(self.duration_us):d}"

    def to_json(self):
        return dict(
            ch0_amp=self.channel_amps[0],
            ch1_amp=self.channel_amps[1],
            duration=self.duration_us,
        )

    @staticmethod
    def from_json(json_dict):
        raise NotImplementedError  # TODO


class StimJim(object):
    def __init__(self, serial_port: serial.Serial):
        self._serial = serial_port
        self.triggers = [Trigger(trig_id=x) for x in range(STIMJIM_N_TRIGGERS)]
        self.pulse_trains = [PulseTrain(x) for x in range(STIMJIM_MAX_PULSETRAINS)]

    def get_stimjim_string(self, pulse_train_id):
        return self.pulse_trains[pulse_train_id].get_stimjim_string()

    def send_command(self, command: str):
        temp = command.replace("\n", "\\n")
        logger.debug(f"Sending command [{temp}] to StimJim")
        if not command.endswith("\n"):
            command += "\n"
        self._serial.write(command.encode())

    def read_serial(self):
        return self._serial.read(self._serial.in_waiting).decode()

    def to_json(self):
        return dict(
            triggers=[trigger.to_json() for trigger in self.triggers],
            pulse_trains=[pulsetrain.to_json() for pulsetrain in self.pulse_trains],
        )

    def from_json(self, json_dict):
        triggers = [Trigger.from_json(d) for d in json_dict["triggers"]]
        self.triggers[: len(triggers)] = triggers
        pulse_trains = [PulseTrain.from_json(d) for d in json_dict["pulse_trains"]]
        self.pulse_trains[: len(pulse_trains)] = pulse_trains


def choose_port_dialog(ports: List[ListPortInfo]):
    ret_val = None
    items = [f"{p.name} ({p.description})" for p in ports]
    item, ok = QInputDialog().getItem(
        None, "Choose the correct serial port", "Serial ports:", items, 0, False
    )
    if ok:
        item_id = items.index(item)
        ret_val = ports[item_id].device
    return ret_val
