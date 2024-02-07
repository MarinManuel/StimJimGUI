import json
import logging
from pathlib import Path

import serial

# noinspection PyUnresolvedReferences
from PyQt5 import uic
from PyQt5.QtCore import QTimer, QAbstractTableModel, Qt, QSignalBlocker
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QInputDialog,
    QWidget,
    QGroupBox,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QToolButton,
    QPlainTextEdit,
    QHBoxLayout,
    QTableView,
    QStyledItemDelegate,
    QFileDialog,
)

from src.StimJim import (
    SERIAL_READ_INTERVAL_MS,
    StimJim,
    StimJimOutputModes,
    STIMJIM_N_OUTPUTS,
    STIMJIM_SCALING_FACTORS,
    STIMJIM_MODE_NAMES,
    STIMJIM_DEFAULT_MODE,
    STIMJIM_UNITS,
    STIMJIM_INCREMENT_STEPS,
    STIMJIM_MAX_VALS,
    STIMJIM_DURATION_SCALING_FACTOR,
    STIMJIM_TRIGGER_COMMANDS,
    PulseStage,
    PulseTrain,
    StimJimTooManyStagesException,
    StimJimTrigDirection,
    STIMJIM_N_TRIGGERS,
)
from src.scientific_spinbox import ScienDSpinBox

logger = logging.getLogger("StimJimGUI")


class PulseStageTableDelegate(QStyledItemDelegate):
    def __init__(self):
        super().__init__()

    def createEditor(self, parent, option, index):
        spinbox = ScienDSpinBox(parent)
        stage: PulseStage = index.model().list_of_stages[index.row()]

        if (
            index.column() in range(len(stage.channel_amps))
            and stage.pulse_train is not None
        ):
            spinbox.setSuffix(STIMJIM_UNITS[stage.pulse_train.get_mode(index.column())])
            spinbox.setMaximum(
                STIMJIM_MAX_VALS[stage.pulse_train.get_mode(index.column())]
            )
            spinbox.setMinimum(
                -1 * STIMJIM_MAX_VALS[stage.pulse_train.get_mode(index.column())]
            )
            spinbox.setSingleStep(
                STIMJIM_INCREMENT_STEPS[stage.pulse_train.get_mode(index.column())]
            )
        else:
            spinbox.setSuffix("s")
            spinbox.setMinimum(0)
            spinbox.setMaximum(1e6)

        return spinbox

    def setEditorData(self, editor: ScienDSpinBox, index):
        stage: PulseStage = index.model().list_of_stages[index.row()]
        value = (stage.channel_amps + [stage.duration_us])[index.column()]
        if index.column() in range(len(stage.channel_amps)):
            value = (
                value
                / STIMJIM_SCALING_FACTORS[stage.pulse_train.get_mode(index.column())]
            )
        else:
            value = value / STIMJIM_DURATION_SCALING_FACTOR
        editor.setValue(value)

    def setModelData(self, editor: ScienDSpinBox, model, index):
        value = editor.value()
        stage: PulseStage = index.model().list_of_stages[index.row()]
        if index.column() in range(len(stage.channel_amps)):
            scale = STIMJIM_SCALING_FACTORS[stage.pulse_train.get_mode(index.column())]
            value = value * scale
            stage.channel_amps[index.column()] = value
        else:
            value = value * STIMJIM_DURATION_SCALING_FACTOR
            stage.duration_us = value
        index.model().dataChanged.emit(index, index, [Qt.EditRole])


# noinspection PyMethodOverriding
class PulseStageTableModel(QAbstractTableModel):
    HEADER = ["Ch0 amp", "Ch1 amp", "Stage duration"]

    def __init__(self, pulse_stages):
        super().__init__()
        self.list_of_stages = pulse_stages

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADER[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return f"Stage {section + 1}"
        return None

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsEditable

    def data(self, index, role):
        if role in (Qt.DisplayRole, Qt.EditRole):
            stage: PulseStage = self.list_of_stages[index.row()]
            if index.column() in range(len(stage.channel_amps)):
                return stage.channel_amps[index.column()]
            else:
                return stage.duration_us

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            stage: PulseStage = self.list_of_stages[index.row()]
            if index.column() in range(len(stage.channel_amps)):
                stage.channel_amps[index.column()] = value
            else:
                stage.duration_us = value
            self.dataChanged.emit(index, index, [Qt.EditRole])
            return True
        return False

    def rowCount(self, index=None):
        return len(self.list_of_stages)

    def columnCount(self, index=None):
        return 3


class FullModeWidget(QWidget):
    trig0SpinBox: QSpinBox
    trig0DirGroupBox: QGroupBox
    trig0RisingEdgeButton: QToolButton
    trig0FallingEdgeButton: QToolButton
    trig0ManualTriggerButton: QToolButton
    trig0CancelTrainButton: QToolButton
    trig1SpinBox: QSpinBox
    trig1DirGroupBox: QGroupBox
    trig1RisingEdgeButton: QToolButton
    trig1FallingEdgeButton: QToolButton
    trig1ManualTriggerButton: QToolButton
    trig1CancelTrainButton: QToolButton
    trainDurationSpinBox: ScienDSpinBox
    ch1ModeSpinBox: QComboBox
    pulseTrainIDSpinBox: QSpinBox
    ch0ModeSpinBox: QComboBox
    pulseStagesTable: QTableView
    trainPeriodSpinBox: ScienDSpinBox
    addStageButton: QToolButton
    removeStageButton: QToolButton

    def __init__(self, stimjim: StimJim):
        super().__init__()
        self.stimjim = stimjim
        #
        # UI
        #
        uic.loadUi("./src/FullModeWidget.ui", self)
        self.ch0ModeSpinBox.addItems(STIMJIM_MODE_NAMES.values())
        self.ch1ModeSpinBox.addItems(STIMJIM_MODE_NAMES.values())
        self.pulseStagesTable.setItemDelegate(PulseStageTableDelegate())

        #
        # SIGNALS
        #
        self.trig0SpinBox.valueChanged.connect(self._on_trig0SpinBox_changed)
        self.trig1SpinBox.valueChanged.connect(self._on_trig1SpinBox_changed)
        self.trig0RisingEdgeButton.clicked.connect(self._on_trig0SpinBox_changed)
        self.trig0FallingEdgeButton.clicked.connect(self._on_trig0SpinBox_changed)
        self.trig1RisingEdgeButton.clicked.connect(self._on_trig1SpinBox_changed)
        self.trig1FallingEdgeButton.clicked.connect(self._on_trig1SpinBox_changed)
        self.trig0ManualTriggerButton.clicked.connect(self._on_trig0_manual_trigger)
        self.trig1ManualTriggerButton.clicked.connect(self._on_trig1_manual_trigger)
        self.trig0CancelTrainButton.clicked.connect(self._on_trig0_cancel)
        self.trig1CancelTrainButton.clicked.connect(self._on_trig1_cancel)
        self.pulseTrainIDSpinBox.valueChanged.connect(self._on_pulseTrainID_changed)
        self.ch0ModeSpinBox.currentIndexChanged.connect(self._on_ch0mode_changed)
        self.ch1ModeSpinBox.currentIndexChanged.connect(self._on_ch1mode_changed)
        self.trainDurationSpinBox.valueChanged.connect(self._on_train_duration_changed)
        self.trainPeriodSpinBox.valueChanged.connect(self._on_train_period_changed)
        self.addStageButton.clicked.connect(self._on_add_stage)
        self.removeStageButton.clicked.connect(self._on_remove_stage)

        self.trig0SpinBox.valueChanged.connect(self.update_stimjim)
        self.trig1SpinBox.valueChanged.connect(self.update_stimjim)
        self.trig0RisingEdgeButton.clicked.connect(self.update_stimjim)
        self.trig0FallingEdgeButton.clicked.connect(self.update_stimjim)
        self.trig1RisingEdgeButton.clicked.connect(self.update_stimjim)
        self.trig1FallingEdgeButton.clicked.connect(self.update_stimjim)
        self.pulseTrainIDSpinBox.valueChanged.connect(self.update_stimjim)
        self.ch0ModeSpinBox.currentIndexChanged.connect(self.update_stimjim)
        self.ch1ModeSpinBox.currentIndexChanged.connect(self.update_stimjim)
        self.trainDurationSpinBox.valueChanged.connect(self.update_stimjim)
        self.trainPeriodSpinBox.valueChanged.connect(self.update_stimjim)
        self.addStageButton.clicked.connect(self.update_stimjim)
        self.removeStageButton.clicked.connect(self.update_stimjim)

        #
        # UPDATE
        #
        self.populate_pulseTrain(0)

    def _on_trig0SpinBox_changed(self, _):
        # this function can be called either from the spinbox or the buttons, so we don't use the argument
        direction = "0" if self.trig0RisingEdgeButton.isChecked() else "1"
        command = f"R0,{self.trig0SpinBox.value()},{direction}"
        self.stimjim.send_command(command)

    def _on_trig1SpinBox_changed(self, _):
        direction = "0" if self.trig1RisingEdgeButton.isChecked() else "1"
        command = f"R1,{self.trig0SpinBox.value()},{direction}"
        self.stimjim.send_command(command)

    def _on_trig0_manual_trigger(self, _):
        self.stimjim.send_command(f"T{self.trig0SpinBox.value()}")

    def _on_trig1_manual_trigger(self, _):
        self.stimjim.send_command(f"U{self.trig1SpinBox.value()}")

    def _on_trig0_cancel(self, _):
        self.stimjim.send_command("T-1")

    def _on_trig1_cancel(self, _):
        self.stimjim.send_command("U-1")

    def _on_pulseTrainID_changed(self, index: int):
        self.populate_pulseTrain(index)

    def _on_ch0mode_changed(self, index: int):
        pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        pulsetrain.set_mode(channel_index=0, mode=StimJimOutputModes(index))
        self.show_all_delegates()

    def _on_ch1mode_changed(self, index: int):
        pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        pulsetrain.set_mode(channel_index=1, mode=StimJimOutputModes(index))
        self.show_all_delegates()

    def _on_train_duration_changed(self, value: float):
        pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        pulsetrain.train_duration_s = value

    def _on_train_period_changed(self, value: float):
        pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        pulsetrain.train_period_s = value

    def _on_add_stage(self, _):
        pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        try:
            pulsetrain.add_stage()
            # noinspection PyUnresolvedReferences
            self.pulseStagesTable.model().layoutChanged.emit()
            self.show_all_delegates()
        except StimJimTooManyStagesException:
            pass  # TODO: could add a sound effect here?

    def _on_remove_stage(self, _):
        pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        try:
            pulsetrain.remove_stage()
            # noinspection PyUnresolvedReferences
            self.pulseStagesTable.model().layoutChanged.emit()
            self.show_all_delegates()
        except IndexError:
            pass  # TODO: could add a sound effect?

    def show_all_delegates(self):
        # FIXME: This works but is very hacky
        if self.pulseStagesTable.model() is not None:
            for i in range(self.pulseStagesTable.model().rowCount()):
                for j in range(self.pulseStagesTable.model().columnCount()):
                    self.pulseStagesTable.closePersistentEditor(
                        self.pulseStagesTable.model().index(i, j)
                    )
                    self.pulseStagesTable.openPersistentEditor(
                        self.pulseStagesTable.model().index(i, j)
                    )

    def populate_pulseTrain(self, pulsetrain_id: int):
        pulsetrain: PulseTrain = self.stimjim.pulse_trains[pulsetrain_id]
        self.ch0ModeSpinBox.setCurrentIndex(pulsetrain.get_mode(0))
        self.ch1ModeSpinBox.setCurrentIndex(pulsetrain.get_mode(1))
        self.trainDurationSpinBox.setValue(pulsetrain.train_duration_s)
        self.trainPeriodSpinBox.setValue(pulsetrain.train_period_s)
        self.pulseStagesTable.setModel(PulseStageTableModel(pulsetrain.stages))
        self.show_all_delegates()
        self.pulseStagesTable.model().dataChanged.connect(self.update_stimjim)

    # noinspection PyUnusedLocal
    def update_stimjim(self, *args):
        current_pulsetrain = self.stimjim.pulse_trains[self.pulseTrainIDSpinBox.value()]
        self.stimjim.send_command(current_pulsetrain.get_stimjim_string())

        self.stimjim.triggers[0].train_target = self.trig0SpinBox.value()
        self.stimjim.triggers[0].trig_direction = (
            0 if self.trig0RisingEdgeButton.isChecked() else 1
        )
        self.stimjim.triggers[1].train_target = self.trig1SpinBox.value()
        self.stimjim.triggers[1].trig_direction = (
            0 if self.trig1RisingEdgeButton.isChecked() else 1
        )

        command = "\n".join(
            [
                self.stimjim.triggers[i].get_stimjim_string()
                for i in range(STIMJIM_N_TRIGGERS)
            ]
        )
        self.stimjim.send_command(command)

    # noinspection PyUnusedLocal
    def update_widgets(self, *args):
        self.trig0SpinBox.setValue(self.stimjim.triggers[0].train_target)
        self.trig0RisingEdgeButton.setChecked(
            self.stimjim.triggers[0].trig_direction == StimJimTrigDirection.RISING
        )
        self.trig1SpinBox.setValue(self.stimjim.triggers[1].train_target)
        self.trig1RisingEdgeButton.setChecked(
            self.stimjim.triggers[1].trig_direction == StimJimTrigDirection.RISING
        )
        self.populate_pulseTrain(self.pulseTrainIDSpinBox.value())


class SimpleModeWidget(QWidget):
    channelGroupBox: QGroupBox
    stimModeComboBox: QComboBox
    stimAmplitudeSpinBox: ScienDSpinBox
    stimDurationSpinBox: ScienDSpinBox
    isBipolarCheckBox: QCheckBox
    stimNPulsesSpinBox: QSpinBox
    stimTrainFreqSpinBox: ScienDSpinBox
    stimTrainDurationSpinBox: ScienDSpinBox
    trigStimPushButton: QPushButton
    thresholdButton: QPushButton
    thresholdValueSpinBox: ScienDSpinBox

    def __init__(self, channel_id, stimjim: StimJim):
        super().__init__()
        uic.loadUi("./src/SimpleModeWidget.ui", self)

        self.channel_id = channel_id
        self.stimjim = stimjim

        self.channelGroupBox.setTitle(
            f"CH {self.channel_id} ( Trig {self.channel_id} )"
        )

        self.stimModeComboBox.addItems(STIMJIM_MODE_NAMES.values())
        self.stimModeComboBox.setCurrentIndex(STIMJIM_DEFAULT_MODE)

        self.stimDurationSpinBox.setValue(1 / STIMJIM_DURATION_SCALING_FACTOR)
        self.stimDurationSpinBox.setSingleStep(
            1 / STIMJIM_DURATION_SCALING_FACTOR, dynamic_stepping=False
        )

        self.stimModeComboBox.currentIndexChanged.connect(self._on_mode_changed)
        self.stimNPulsesSpinBox.valueChanged.connect(self._update_train_duration)
        self.stimTrainFreqSpinBox.valueChanged.connect(self._update_train_duration)
        self.stimDurationSpinBox.valueChanged.connect(self._update_train_duration)

        self.stimModeComboBox.currentIndexChanged.connect(self.update_stimjim)
        self.stimAmplitudeSpinBox.valueChanged.connect(self.update_stimjim)
        self.stimDurationSpinBox.valueChanged.connect(self.update_stimjim)
        self.isBipolarCheckBox.stateChanged.connect(self.update_stimjim)
        self.stimNPulsesSpinBox.valueChanged.connect(self.update_stimjim)
        self.stimTrainFreqSpinBox.valueChanged.connect(self.update_stimjim)
        self.thresholdValueSpinBox.valueChanged.connect(self.update_stimjim)
        self.thresholdButton.clicked.connect(self.update_stimjim)

        self.trigStimPushButton.clicked.connect(self._on_trigger_button)
        self.thresholdButton.clicked.connect(self._on_threshold_button)

        self._update_train_duration(None)
        self._on_mode_changed(StimJimOutputModes.GROUNDED)
        self.update_stimjim()

    def _on_mode_changed(self, current_id: int):
        self.thresholdButton.setChecked(False)
        for box in [self.thresholdValueSpinBox, self.stimAmplitudeSpinBox]:
            box.setValue(0.0)
            box.setSuffix(STIMJIM_UNITS[current_id])
            box.setMaximum(STIMJIM_MAX_VALS[current_id])
            box.setMinimum(-1 * STIMJIM_MAX_VALS[current_id])
            box.setSingleStep(
                STIMJIM_INCREMENT_STEPS[current_id], dynamic_stepping=False
            )

    def _update_train_duration(self, _):
        self.stimTrainDurationSpinBox.setValue(
            (self.stimNPulsesSpinBox.value() - 1) / self.stimTrainFreqSpinBox.value()
            + self.stimDurationSpinBox.value()
        )

    # noinspection PyUnusedLocal
    def _on_trigger_button(self, *args):
        command = f"{STIMJIM_TRIGGER_COMMANDS[self.channel_id]}{self.channel_id}"
        self.stimjim.send_command(command)

    def _on_threshold_button(self, checked: bool):
        if checked:  # Enable threshold mode
            self.thresholdValueSpinBox.setValue(self.stimAmplitudeSpinBox.value())
            self.stimAmplitudeSpinBox.setSuffix(" x T")
            self.stimAmplitudeSpinBox.setSingleStep(0.1, dynamic_stepping=False)
            self.stimAmplitudeSpinBox.setMinimum(0)
            self.stimAmplitudeSpinBox.setMaximum(100)
            self.stimAmplitudeSpinBox.setValue(1.0)
        else:  # Disable threshold mode
            value = (
                self.thresholdValueSpinBox.value() * self.stimAmplitudeSpinBox.value()
            )
            self._on_mode_changed(self.stimModeComboBox.currentIndex())
            self.stimAmplitudeSpinBox.setValue(value)

    # noinspection PyUnusedLocal
    def update_stimjim(self, *args):
        # trigger
        self.stimjim.triggers[self.channel_id].train_target = self.channel_id
        self.stimjim.triggers[
            self.channel_id
        ].trig_direction = StimJimTrigDirection.RISING
        # Pulse Train
        pulse_train = self.stimjim.pulse_trains[self.channel_id]
        pulse_train.set_mode(self.channel_id, self.stimModeComboBox.currentIndex())
        other_channel = (
            range(STIMJIM_N_OUTPUTS).index(self.channel_id) + 1
        ) % STIMJIM_N_OUTPUTS
        pulse_train.set_mode(other_channel, StimJimOutputModes.GROUNDED)

        period_us = int(
            STIMJIM_DURATION_SCALING_FACTOR / self.stimTrainFreqSpinBox.value()
        )
        train_duration_us = (
            STIMJIM_DURATION_SCALING_FACTOR * self.stimTrainDurationSpinBox.value()
        )
        pulse_train.train_duration_us = train_duration_us
        pulse_train.train_period_us = period_us

        # Pulse Stage(s)
        amps = [0, 0]
        if self.thresholdButton.isChecked():
            amp = int(
                self.stimAmplitudeSpinBox.value()
                * self.thresholdValueSpinBox.value()
                * STIMJIM_SCALING_FACTORS[self.stimModeComboBox.currentIndex()]
            )
        else:
            amp = int(
                self.stimAmplitudeSpinBox.value()
                * STIMJIM_SCALING_FACTORS[self.stimModeComboBox.currentIndex()]
            )
        amps[self.channel_id] = amp

        stage_duration_us = (
            STIMJIM_DURATION_SCALING_FACTOR * self.stimDurationSpinBox.value()
        )
        if self.isBipolarCheckBox.isChecked():
            stage_duration_us /= 2
        stage_duration_us = int(stage_duration_us)

        while len(pulse_train.stages) > 0:
            pulse_train.remove_stage(-1)
        pulse_train.add_stage(
            PulseStage(ch0_amp=amps[0], ch1_amp=amps[1], duration=stage_duration_us)
        )
        if self.isBipolarCheckBox.isChecked():
            pulse_train.add_stage(
                PulseStage(
                    ch0_amp=-1 * amps[0],
                    ch1_amp=-1 * amps[1],
                    duration=stage_duration_us,
                )
            )

        command = self.stimjim.get_stimjim_string(self.channel_id)
        command += "\n"
        command += self.stimjim.triggers[self.channel_id].get_stimjim_string()
        command += "\n"
        self.stimjim.send_command(command)

    def update_widgets(self):
        pulse_train = self.stimjim.pulse_trains[self.channel_id]
        stage0: PulseStage = pulse_train.stages[0]
        is_bipolar = len(pulse_train.stages) > 1
        with QSignalBlocker(self.stimModeComboBox):
            self.stimModeComboBox.setCurrentIndex(pulse_train.get_mode(self.channel_id))
            self._on_mode_changed(self.stimModeComboBox.currentIndex())
        with QSignalBlocker(self.stimAmplitudeSpinBox):
            self.stimAmplitudeSpinBox.setValue(
                stage0.channel_amps[self.channel_id]
                / STIMJIM_SCALING_FACTORS[pulse_train.get_mode(self.channel_id)]
            )
        stim_duration_us = (
            stage0.duration_us if not is_bipolar else stage0.duration_us * 2
        )
        stim_duration_s = stim_duration_us / STIMJIM_DURATION_SCALING_FACTOR
        with QSignalBlocker(self.stimDurationSpinBox):
            self.stimDurationSpinBox.setValue(stim_duration_s)
        with QSignalBlocker(self.isBipolarCheckBox):
            self.isBipolarCheckBox.setChecked(is_bipolar)
        n_stim = int(
            (pulse_train.train_duration_s - stim_duration_s)
            / (pulse_train.train_period_us * 1e-6)
            + 1
        )  # this in the inverse of the calculation in _update_train_duration
        with QSignalBlocker(self.stimNPulsesSpinBox):
            self.stimNPulsesSpinBox.setValue(n_stim)
        with QSignalBlocker(self.stimTrainFreqSpinBox):
            self.stimTrainFreqSpinBox.setValue(1 / pulse_train.train_period_s)
        with QSignalBlocker(self.stimTrainDurationSpinBox):
            self.stimTrainDurationSpinBox.setValue(pulse_train.train_duration_s)
        self.update_stimjim()


class StimJimGUI(QMainWindow):
    def __init__(self, serial_port: serial.Serial, log_filename=None):
        super().__init__()
        self.serial = serial_port
        self.simple_stimjim = StimJim(serial_port)
        self.full_stimjim = StimJim(serial_port)
        self.log_filename = log_filename

        self.splitter = QSplitter(self)
        self.tabWidget = QTabWidget(self.splitter)
        self.serialOutputTextEdit = QPlainTextEdit(self.splitter)

        self.splitter.addWidget(self.tabWidget)
        self.splitter.addWidget(self.serialOutputTextEdit)
        self.setCentralWidget(self.splitter)

        self.tabWidget.currentChanged.connect(self._on_tab_changed)

        #
        # Simple Mode tab
        #
        self.simpleModeTab = QWidget()
        self.simpleModeTab.setLayout(QHBoxLayout())
        self.simpleModeWidgets = []
        for ch in range(STIMJIM_N_OUTPUTS):
            w = SimpleModeWidget(channel_id=ch, stimjim=self.simple_stimjim)
            self.simpleModeTab.layout().addWidget(w)
            self.simpleModeWidgets.append(w)
        self.tabWidget.addTab(self.simpleModeTab, "Simple Mode")

        #
        # Full Mode tab
        #
        self.fullModeTab = QWidget()
        self.fullModeTab.setLayout(QHBoxLayout())
        self.fullModeWidget = FullModeWidget(stimjim=self.full_stimjim)
        self.fullModeTab.layout().addWidget(self.fullModeWidget)
        self.tabWidget.addTab(self.fullModeTab, "Full Mode")

        #
        # Menu Items
        #
        file_menu = self.menuBar().addMenu("&File")
        action_open_file = file_menu.addAction("&Open configuration file...")
        action_open_file.setIcon(QIcon(":/icons/Open"))
        action_open_file.triggered.connect(self._on_action_open_config)
        action_load_file = file_menu.addAction("&Save current configuration...")
        action_load_file.setIcon(QIcon(":/icons/Save"))
        action_load_file.triggered.connect(self._on_action_save_config)
        action_save_log = file_menu.addAction("Save &log to disk...")
        action_save_log.setIcon(QIcon(":/icons/Stream"))
        action_save_log.triggered.connect(self._on_action_save_log)
        file_menu.addSeparator()
        action_quit = file_menu.addAction("&Quit")
        action_quit.setIcon(QIcon(":/icons/Quit"))
        action_quit.triggered.connect(self.close)

        window_menu = self.menuBar().addMenu("&Window")
        action_keep_on_top = window_menu.addAction("Keep on &top")
        action_keep_on_top.setCheckable(True)
        action_keep_on_top.triggered.connect(self._on_action_keep_on_top)

        help_menu = self.menuBar().addMenu("&Help")
        # noinspection SpellCheckingInspection
        action_send_command = help_menu.addAction("Send serial co&mmand...")
        action_send_command.setIcon(QIcon(":/icons/Serial"))
        action_send_command.triggered.connect(self._on_action_send_command)
        self.previous_custom_commands = []

        #
        # Serial Timer
        #
        self.serial_output_timer = QTimer()
        self.serial_output_timer.timeout.connect(self._on_serial_output_timer)
        self.serial_output_timer.start(SERIAL_READ_INTERVAL_MS)

    def to_json(self):
        json_dict = {
            "CurrentTab": self.tabWidget.currentIndex(),
            "SimpleMode": self.simple_stimjim.to_json(),
            "FullMode": self.full_stimjim.to_json(),
        }
        return json_dict

    def _on_serial_output_timer(self):
        recv = self.full_stimjim.read_serial()
        if len(recv.strip()) > 0:
            # only keep actual content, StimJim sometimes sends a bunch of CR for no reason
            self.serialOutputTextEdit.appendPlainText(recv)
            self.serialOutputTextEdit.ensureCursorVisible()  # scroll to bottom
            if self.log_filename is not None:
                with open(self.log_filename, "a") as f:
                    f.write(recv)

    def _on_action_send_command(self):
        command, ok = QInputDialog().getItem(
            self,
            "Custom Command",
            "Send a custom command to StimJim:",
            self.previous_custom_commands,
            0,
            True,
        )
        if ok and command:
            if command not in self.previous_custom_commands:
                self.previous_custom_commands.insert(0, command)
            self.full_stimjim.send_command(command)

    def _on_action_keep_on_top(self, checked: bool):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()

    def _on_tab_changed(self, index: int):
        pass

    def _on_action_save_config(self):
        filename, ok = QFileDialog.getSaveFileName(
            self, "Save current configuration", str(Path.home()), "Json files (*.json)"
        )
        if ok:
            with open(filename, "w") as f:
                json.dump(self.to_json(), f, indent=4)

    def _on_action_save_log(self):
        filename, ok = QFileDialog.getSaveFileName(
            self, "Save current configuration", str(Path.home()), "Text file (*.txt)"
        )
        if ok:
            self.log_filename = filename
            with open(filename, "a") as f:
                f.write(self.serialOutputTextEdit.toPlainText())

    def _on_action_open_config(self):
        filename, ok = QFileDialog.getOpenFileName(
            self, "Open configuration file", str(Path.home()), "Json files (*.json)"
        )
        if ok and Path(filename).is_file():
            with open(filename, "r") as f:
                json_dict = json.load(f)

            if "CurrentTab" in json_dict:
                self.tabWidget.setCurrentIndex(json_dict["CurrentTab"])

            if self.tabWidget.currentIndex() == 0:
                self.update_full_mode_widget(json_dict=json_dict["FullMode"])
                self.update_simple_mode_widget(json_dict=json_dict["SimpleMode"])
            else:
                self.update_simple_mode_widget(json_dict=json_dict["SimpleMode"])
                self.update_full_mode_widget(json_dict=json_dict["FullMode"])

    def update_full_mode_widget(self, json_dict):
        try:
            temp_stimjim = StimJim(self.serial)
            temp_stimjim.from_json(json_dict=json_dict)
            self.full_stimjim = temp_stimjim
            self.fullModeWidget.stimjim = temp_stimjim
            self.fullModeWidget.update_widgets()
        except Exception as e:
            self.serialOutputTextEdit.appendPlainText("Error loading config file")
            logger.debug(f"Error while loading config file in Full Mode: {str(e)}")

    def update_simple_mode_widget(self, json_dict):
        try:
            temp_stimjim = StimJim(self.serial)
            temp_stimjim.from_json(json_dict=json_dict)
            self.simple_stimjim = temp_stimjim
            for w in self.simpleModeWidgets:
                w.stimjim = temp_stimjim
                w.update_widgets()
        except Exception as e:
            self.serialOutputTextEdit.appendPlainText("Error loading config file")
            logger.debug(f"Error while loading config file in Simple Mode: {str(e)}")
