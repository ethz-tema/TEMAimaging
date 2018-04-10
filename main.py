import time

import schedule
import serial
import urwid
import signal

from hardware.arduino_trigger import ArduTrigger
from hardware.laser_compex import OpMode, TriggerModes, CompexLaserProtocol
from scheduler import MyScheduler
from hardware.mcs_stage import MCSStage, MCSAxis
from scans import MeasurementController, rectangle, engraver
from hardware.shutter import Shutter, AIODevice
from PIL import Image


class MyOverlay(urwid.Overlay):
    def __init__(
            self, top_w, bottom_w,
            align, width, valign, height,
            min_width=None, min_height=None,
            left=0, right=0,
            top=0, bottom=0, parent=None):
        super(MyOverlay, self).__init__(
            top_w, bottom_w,
            align, width, valign, height,
            min_width, min_height,
            left, right,
            top, bottom)
        self.parent = parent

    def keypress(self, size, key):
        super(MyOverlay, self).keypress(size, key)
        if key == "tab":
            pass
        elif key == "esc":
            self.parent.button_press(None, "back")
        return True


class MyRadioButton(urwid.CheckBox):
    states = {
        True: urwid.SelectableIcon("(X)"),
        False: urwid.SelectableIcon("( )"),
        'mixed': urwid.SelectableIcon("(#)")}
    reserve_columns = 4

    def __init__(self, group, label, state="first True",
                 on_state_change=None, user_data=None):

        if state == "first True":
            state = not group

        self.group = group
        super().__init__(label, state, False, on_state_change,
                         user_data)
        group.append(self)

    def set_state(self, state, do_callback=True, from_toggle=False):
        if self._state == state:
            return

        self.__super.set_state(state, do_callback)

        # if we're clearing the state we don't have to worry about
        # other buttons in the button group
        if state is not True:
            return

        # clear the state of each other radio button
        for cb in self.group:
            if cb is self:
                continue
            if cb._state:
                cb.set_state(False, do_callback and not from_toggle)

    def toggle_state(self):
        self.set_state(True, from_toggle=True)


class Loop(urwid.MainLoop):
    """Controller class for MainLoop instance of the program."""

    palette = [
        ('body', 'black', 'light gray', 'standout'),
        ('header', 'white', 'dark red', 'bold'),
        ('button normal', 'light gray', 'dark blue', 'standout'),
        ('button select', 'white', 'dark green'),
        ('button disabled', 'dark gray', 'dark blue'),
        ('edit', 'light gray', 'dark blue'),
        ('ok', 'light green', 'default'),
        ('warn', 'yellow', 'default'),
        ('error', 'dark red', 'default'),
        ('exit', 'white', 'dark blue'),
        ('default', 'default', 'default')
    ]

    def __init__(self, top_widget, input_handler):
        """Initialize parent class, get terminal size and set up stack.
        The stack holds all widgets that were displayed in order that
        they've appeared. This way going "back" is easily achieved
        just by popping the stack and setting `widget` property to point
        at the current topmost widget.
        Note: it should not be used directly, just use the setters and
        deleters below.
        """
        super(Loop, self).__init__(
            top_widget,
            self.palette,
            unhandled_input=input_handler)
        self.dimensions = self.screen.get_cols_rows()
        self._widget_stack = []

    # Properties to ease manipulation of top-level widgets.
    @property
    def baseWidget(self):
        """Read-only property returns the very lowest widget."""
        return self.widget.base_widget

    @property
    def origWidget(self):
        """Return widget one lower than the topmost one."""
        return self.widget.original_widget

    @property
    def Widget(self):
        """Returns the full topmost widget, with all wrappers etc."""
        return self.widget

    @Widget.setter
    def Widget(self, widget):
        """Setter for topmost widget, used to switch view modes.
        @widget - widget instance, most probably ur.Frame
        Assigns a new topmost widget to be displayed, essentially
        allowing us to switch between modes, like board view,
        main menu, etc.
        """
        self._widget_stack.append(widget)
        self.widget = widget

    @Widget.deleter
    def Widget(self):
        """Delete the topmost widget and draw new topmost one.
        Usage:
            `del self.loop.Widget` will remove current widget from view and
                draw the earlier one.
        """
        self._widget_stack.pop()
        self.widget = self._widget_stack[-1]

    @property
    def stack_len(self):
        return len(self._widget_stack)

    @property
    def frameBody(self):
        """Returns body (a list of widgets in the form of
        Simple[Focus]ListWalker) of top-level Frame widget to manipulate."""
        return self.widget.original_widget.contents["body"][0]. \
            original_widget.body


class LaserDisplay:
    def __init__(self):
        self.view = None
        self.loop = Loop(None, self.unhandled_input)
        self.status_text = urwid.AttrMap(urwid.BigText('', urwid.HalfBlock7x7Font()), 'default')
        self.detail_text = urwid.Text('')
        self.stats_text = urwid.Text('')
        self.search_result = urwid.SimpleFocusListWalker([])
        self.ldap = None
        self.data_manager = None
        self.opmode_group = []
        self.shutter_group = []
        self.trigger_group = []
        self.energy_mode_group = []
        self.curr_op_mode = urwid.Text('Operation mode: OFF')
        self.laser_ver_text = urwid.Text('Not connected')
        self.curr_opmode = OpMode.OFF
        self.curr_trigger_mode = TriggerModes.INT
        self.reprate_edit = urwid.Edit(('edit', 'Rate (Hz):'))
        self.counts_edit = urwid.Edit(('edit', 'Counts:'))
        self.curr_reprate = 0
        self.curr_counts = 0
        self.curr_hv_volatge = 0
        self.curr_energy = 0
        self.hv_voltage_edit = urwid.Edit(('edit', 'HV voltage:'))
        self.energy_edit = urwid.Edit(('edit', 'Energy:'))
        self.curr_hv_voltage_text = urwid.Text('HV: 0 V')
        self.curr_enegry_text = urwid.Text('Energy: 0 mJ')
        self.curr_reprate_text = urwid.Text('Rate: 0 Hz')
        self.curr_counts_text = urwid.Text('Count: 0')
        self.shoot_freq_edit = urwid.Edit(('edit', "Shot freq. (Hz): "), edit_text='100')
        self.shoot_count_edit = urwid.Edit(('edit', "Shot count: "), edit_text='10')
        self.shoot_rep_edit = urwid.Edit(('edit', 'Shot repetitions count: '), edit_text='10')
        self.shoot_rep_pause_edit = urwid.Edit(('edit', "Pause between reps. (ms): "), edit_text='100')
        self.shoot_count_text = urwid.Text("Curr. shots count: 0")
        ser_laser = serial.serial_for_url('/dev/ttyUSB1', timeout=1)
        self.laser_thread = serial.threaded.ReaderThread(ser_laser, CompexLaserProtocol)
        self.laser_thread.start()
        transport, self.laser_conn = self.laser_thread.connect()

        #self.shutter_con = Shutter(AIODevice(), 24)

        ser_trigger = serial.serial_for_url('/dev/ttyACM0', timeout=1, baudrate=19200)
        self.trigger_thread = serial.threaded.ReaderThread(ser_trigger, ArduTrigger)
        self.trigger_thread.start()
        transport, self.trigger_conn = self.trigger_thread.connect()

        self.stage = MCSStage('usb:ix:0')
        self.stage.open_mcs()
        self.stage.find_references()
        self.stage.set_position_limit(MCSAxis.X, -25000000, 25000000)
        self.stage.set_position_limit(MCSAxis.Y, -34000000, 35400000)
        self.stage.set_position_limit(MCSAxis.Z, -750000, 2700000)
        self.stage.move(MCSAxis.Z, 888000)

        self.meas_ctrl = MeasurementController(self.laser_conn, self.trigger_conn, self.stage)
        self.stop_scan_event = None

    def main(self):
        self.view = self.setup_view()
        self.loop.Widget = self.view

        self.update_status(True)
        self.laser_ver_text.set_text(
            'Connected - Laser: {}, Version: {}'.format(self.laser_conn.laser_type, self.laser_conn.version))

        schedule.default_scheduler = MyScheduler()
        schedule.every(1).second.do(self.update_status)

        self.loop.set_alarm_in(1, schedule.default_scheduler.run_urwid)

        self.loop.run()

    def setup_view(self):
        op_mode_panel = urwid.Columns([
            urwid.Pile([
                urwid.Text("Operation mode"),
                MyRadioButton(self.opmode_group, 'Off', on_state_change=self.op_mode_changed, user_data=OpMode.OFF),
                MyRadioButton(self.opmode_group, 'On', on_state_change=self.op_mode_changed, user_data=OpMode.ON)
            ]),
            urwid.Pile([
                urwid.Text("Shutter"),
                MyRadioButton(self.shutter_group, 'Closed', on_state_change=self.shutter_changed, user_data=False),
                MyRadioButton(self.shutter_group, 'Open', on_state_change=self.shutter_changed, user_data=True)
            ])
        ])
        op_mode_box = urwid.LineBox(op_mode_panel)

        fire_mode_panel = urwid.Columns([
            urwid.Pile([
                urwid.Columns([
                    urwid.Text("TriggerModes:"),
                    urwid.Pile([
                        MyRadioButton(self.trigger_group, "Internal", on_state_change=self.trigger_changed,
                                      user_data=TriggerModes.INT),
                        MyRadioButton(self.trigger_group, "External", on_state_change=self.trigger_changed,
                                      user_data=TriggerModes.EXT)
                    ])
                ]),
                self.reprate_edit,
                self.counts_edit,
                urwid.Button('Set', self.button_press, 'fire_set')
            ]),
            urwid.Pile([
                urwid.Columns([
                    urwid.Text("Energy mode:"),
                    urwid.Pile([
                        urwid.RadioButton(self.energy_mode_group, "const. HV"),
                        urwid.RadioButton(self.energy_mode_group, "const. E")
                    ])
                ]),
                self.hv_voltage_edit,
                self.energy_edit
            ])
        ], dividechars=1)
        fire_mode_box = urwid.LineBox(fire_mode_panel)

        status_panel = urwid.Pile([
            urwid.Text(('header', 'Current values'), 'center'),
            urwid.Divider(),
            urwid.Columns([
                urwid.Pile([
                    self.curr_op_mode,
                    urwid.Divider(),
                    urwid.Text('Energy mode: const. HV'),
                    self.curr_hv_voltage_text,
                    self.curr_enegry_text
                ]),
                urwid.Pile([
                    self.curr_reprate_text,
                    self.curr_counts_text
                ])
            ])
        ])
        status_box = urwid.LineBox(status_panel)

        shoot_panel = urwid.Pile([
            urwid.Text(('header', 'Shooting settings'), 'center'),
            urwid.Divider(),
            urwid.Columns([
                urwid.Pile([
                    self.shoot_freq_edit,
                    self.shoot_count_edit,
                    self.shoot_rep_edit,
                    self.shoot_rep_pause_edit
                ]),
                urwid.Pile([
                    self.shoot_count_text
                ])
            ]),
            urwid.Button('Set & Start', self.button_press, 'shoot_set_start'),
            urwid.Button('Stop', self.button_press, 'shoot_stop')
        ])
        shoot_box = urwid.LineBox(shoot_panel)

        scan_panel = urwid.Pile([
            urwid.Text(('header', 'Scan settings'), 'center'),
            urwid.Divider(),
            urwid.Button('Set & Start', self.button_press, 'scan_set_start'),
            urwid.Button('Stop', self.button_press, 'scan_stop'),
        ])
        scan_box = urwid.LineBox(scan_panel)

        cols = urwid.Filler(urwid.Pile([op_mode_box, fire_mode_box, shoot_box, status_box, scan_box]))

        box = urwid.LineBox(cols)
        footer = urwid.Columns([urwid.Button('F12 - Close', self.button_press, 'quit'), self.laser_ver_text])
        frame = urwid.Frame(body=box, footer=footer)

        return frame

    def op_mode_changed(self, radio, new_state, data):
        self.laser_conn.opmode = data

    def shutter_changed(self, radio, new_state, data):
        pass
        #self.shutter_con.set(data)

    def trigger_changed(self, radio, new_state, data):
        self.laser_conn.trigger = data

    def update_status(self, init=False):
        self.curr_opmode = self.laser_conn.opmode
        if self.curr_opmode[0] in (OpMode.ON, OpMode.OFF_WAIT):
            self.opmode_group[1].set_state(True, do_callback=False)
        else:
            self.opmode_group[0].set_state(True, do_callback=False)

        self.curr_trigger_mode = self.laser_conn.trigger
        if self.curr_trigger_mode == TriggerModes.INT:
            self.trigger_group[0].set_state(True, do_callback=False)
        else:
            self.trigger_group[1].set_state(True, do_callback=False)

        self.curr_op_mode.set_text('Operation mode: {}'.format(self.curr_opmode))
        self.curr_reprate_text.set_text('Rate: {} Hz'.format(self.laser_conn.reprate))
        self.curr_counts_text.set_text('Counts: {}'.format(self.laser_conn.counts))

        if init:
            self.reprate_edit.set_edit_text(str(self.laser_conn.reprate))
            self.counts_edit.set_edit_text(str(self.laser_conn.counts))

    def button_press(self, button, data):
        """Generic callback method for buttons (not key-presses!).
        @button - button object instance that called the method,
        @data - (string) additional data provided by calling button
            instance, used to define what action should be taken.
        """
        if data == 'back':
            # Go back, restore saved widgets from previous screen.
            del self.loop.Widget
        elif data == 'quit':
            self.quit_prompt()
        elif data == 'really_quit':
            self.laser_conn.stop()
            self.trigger_conn.stop()
            self.stage.close_mcs()
            raise urwid.ExitMainLoop()
        elif data == 'fire_set':
            self.laser_conn.reprate = int(self.reprate_edit.edit_text)
            self.laser_conn.counts = self.counts_edit.edit_text
        elif data == 'shoot_set_start':
            self.trigger_conn.rep_sleep_time = float(self.shoot_rep_pause_edit.edit_text)
            self.trigger_conn.rep_count = int(self.shoot_rep_edit.edit_text)
            time.sleep(0.1)
            self.trigger_conn.set_freq(self.shoot_freq_edit.edit_text)
            time.sleep(0.1)
            self.trigger_conn.set_count(self.shoot_count_edit.edit_text)
            time.sleep(0.1)
            self.trigger_conn.start_trigger()
        elif data == 'shoot_stop':
            self.trigger_conn.stop_trigger()
        elif data == 'scan_set_start':
            self.trigger_conn.set_freq(self.shoot_freq_edit.edit_text)
            time.sleep(0.1)
            self.trigger_conn.set_count(self.shoot_count_edit.edit_text)
            self.trigger_conn.rep_sleep_time = 0
            time.sleep(0.1)
            #scan = measurement_controller.LineScan(44 * 1e-6, 10, 45, 10)
            image = Image.open('eth_logo.jpg').convert(mode='1').resize((400, 65))
            scan = engraver.Engraver(60 * 1e-6, 7, image)
            #scan = rectangle.RectangleScan(60 * 1e-5, 120 * 1e-6, 60 * 1e-6, 60, 10, False)
            #rectangle.MCSAxis()
            self.stop_scan_event = self.meas_ctrl.start_scan(scan)
        elif data == 'scan_stop':
            if self.stop_scan_event:
                self.stop_scan_event.set()
                self.stop_scan_event = None

    def quit_prompt(self):
        """Pop-up window that appears when you try to quit."""
        # Nothing fancy here.
        question = urwid.Text(("bold", "Really quit?"), "center")
        yes_btn = urwid.AttrMap(urwid.Button(
            "Yes", self.button_press, "really_quit"), "error", None)
        no_btn = urwid.AttrMap(urwid.Button(
            "No", self.button_press, "back"), "ok", None)

        prompt = urwid.LineBox(urwid.ListBox(urwid.SimpleFocusListWalker(
            [question, urwid.Divider(), urwid.Divider(), no_btn, yes_btn])))

        # The only interesting thing in this method is this Overlay widget.
        overlay = MyOverlay(
            prompt, self.loop.baseWidget,
            "center", 20, "middle", 8,
            16, 8,
            parent=self)
        self.loop.Widget = overlay

    def unhandled_input(self, key):
        if key == 'f12':
            self.quit_prompt()
            return True
        elif key == 'q':
            self.quit_prompt()
            return True

        return True

    def handle_signal(self, signum, frame):
        self.button_press(None, 'really_quit')


def main():
    display = LaserDisplay()
    signal.signal(signal.SIGINT, display.handle_signal)
    display.main()


if __name__ == '__main__':
    main()
