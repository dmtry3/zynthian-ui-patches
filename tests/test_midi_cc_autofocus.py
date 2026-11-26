#!/usr/bin/env python3
"""Unit tests for the Zynthian UI MIDI CC Auto-Focus patch."""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock

ZYNTHIAN_UI_DIR = os.environ.get("ZYNTHIAN_UI_DIR", "/zynthian/zynthian-ui")


def install_stubs():
    """Install minimal stubs for hardware/C/Tk dependencies so we can import the patched modules directly."""
    # Stub zynconf
    zynconf_mod = types.ModuleType("zynconf")
    zynconf_mod.save_config = MagicMock()
    zynconf_mod.load_plain_envars = MagicMock()
    zynconf_mod.NoteCuiaDefault = {}
    zynconf_mod.get_external_storage_dirs = MagicMock(return_value=[])
    sys.modules["zynconf"] = zynconf_mod

    # Stub zynautoconnect
    zynauto_mod = types.ModuleType("zynautoconnect")
    zynauto_mod.ctrl_fb_procs = []
    zynauto_mod.get_midi_in_devid = MagicMock(return_value="USB_MIDI")
    zynauto_mod.request_audio_connect = MagicMock()
    zynauto_mod.request_midi_connect = MagicMock()
    sys.modules["zynautoconnect"] = zynauto_mod

    # Stub zyncoder.zyncore
    zyncoder_pkg = types.ModuleType("zyncoder")
    zyncore_mod = types.ModuleType("zyncoder.zyncore")
    lib_zyncore = MagicMock()
    lib_zyncore.zmop_get_num_chains.return_value = 17
    lib_zyncore.zmip_get_num_devs.return_value = 16
    lib_zyncore.zmop_get_num_devs.return_value = 16
    lib_zyncore.zmip_get_seq_index.return_value = 16
    lib_zyncore.zmip_get_step_index.return_value = 17
    lib_zyncore.zmip_get_int_index.return_value = 18
    lib_zyncore.zmip_get_ctrl_index.return_value = 19
    lib_zyncore.zmop_get_mod_index.return_value = 17
    lib_zyncore.zmop_get_step_index.return_value = 18
    zyncore_mod.lib_zyncore = lib_zyncore
    zyncoder_pkg.zyncore = zyncore_mod
    sys.modules["zyncoder"] = zyncoder_pkg
    sys.modules["zyncoder.zyncore"] = zyncore_mod

    # Stub zyngine signal manager
    sig_mod = types.ModuleType("zyngine.zynthian_signal_manager")
    sig_mod.zynsigman = MagicMock()
    sys.modules["zyngine.zynthian_signal_manager"] = sig_mod

    # Stub base GUI classes to avoid needing an X11 display
    base_mod = types.ModuleType("zyngui.zynthian_gui_base")
    base_mod.zynthian_gui_base = type("zynthian_gui_base", (object,), {})
    sys.modules["zyngui.zynthian_gui_base"] = base_mod

    sel_mod = types.ModuleType("zyngui.zynthian_gui_selector")

    class DummySelector:
        def fill_list(self):
            pass

        def select(self, index=None, set_zctrl=True):
            if index is not None:
                self.index = index

    sel_mod.zynthian_gui_selector = DummySelector
    sys.modules["zyngui.zynthian_gui_selector"] = sel_mod

    sel_info_mod = types.ModuleType("zyngui.zynthian_gui_selector_info")

    class DummySelectorInfo:
        def fill_list(self):
            pass

        def update_list(self):
            self.fill_list()

    sel_info_mod.zynthian_gui_selector_info = DummySelectorInfo
    sys.modules["zyngui.zynthian_gui_selector_info"] = sel_info_mod

    ctrl_widget_mod = types.ModuleType("zyngui.zynthian_gui_controller")
    ctrl_widget_mod.zynthian_gui_controller = MagicMock
    sys.modules["zyngui.zynthian_gui_controller"] = ctrl_widget_mod

    if ZYNTHIAN_UI_DIR not in sys.path:
        sys.path.insert(0, ZYNTHIAN_UI_DIR)


install_stubs()

import zynconf  # noqa: E402
from zyngui import zynthian_gui_config  # noqa: E402
from zyngui.zynthian_gui_control import (  # noqa: E402
    MIDI_LEARNING_CHAIN,
    MIDI_LEARNING_DISABLED,
    zynthian_gui_control,
)
from zyngui.zynthian_gui_chain_options import zynthian_gui_chain_options  # noqa: E402


# Load get_midi_cc_zctrls from zynthian_chain_manager without importing heavy LV2/engine backends
def load_chain_manager_method():
    path = os.path.join(ZYNTHIAN_UI_DIR, "zyngine", "zynthian_chain_manager.py")
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    # Extract method definition cleanly via AST
    import ast

    tree = ast.parse(src, filename=path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "zynthian_chain_manager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "get_midi_cc_zctrls":
                    mod = ast.Module(body=[item], type_ignores=[])
                    ns = {
                        "MAX_NUM_MIDI_DEVS": 16,
                        "zynthian_gui_config": zynthian_gui_config,
                    }
                    exec(compile(mod, path, "exec"), ns)
                    return ns["get_midi_cc_zctrls"]
    raise RuntimeError("get_midi_cc_zctrls not found in zynthian_chain_manager.py")


get_midi_cc_zctrls_fn = load_chain_manager_method()


class FakeZCtrl:
    def __init__(self, symbol, processor=None):
        self.symbol = symbol
        self.name = symbol
        self.short_name = symbol
        self.group_symbol = "grp"
        self.processor = processor
        self.is_path = False
        self.is_toggle = False
        self.midi_cc_mode = 0
        self.range_reversed = False


class FakeProcessor:
    def __init__(self, proc_id, name, chain_id, ctrl_screens, chain=None):
        self.id = proc_id
        self.name = name
        self.chain_id = chain_id
        self.chain = chain
        self.engine = types.SimpleNamespace(name=name)
        self.ctrl_screens_dict = ctrl_screens
        self.current_screen_index = 0

    def get_ctrl_screens(self):
        return self.ctrl_screens_dict

    def get_ctrl_screen(self, key):
        return self.ctrl_screens_dict.get(key, [])

    def get_current_screen_index(self):
        return self.current_screen_index

    def set_current_screen_index(self, idx):
        self.current_screen_index = idx


class FakeChain:
    def __init__(self, chain_id, processors=None, zctrls=None):
        self.chain_id = chain_id
        self.processors = processors or []
        self.zctrls = zctrls or []
        self.current_processor = self.processors[0] if self.processors else None

    def set_current_processor(self, proc):
        self.current_processor = proc

    def get_processor_count(self, ptype=None):
        return len(self.processors)

    def is_midi(self):
        return True

    def is_audio(self):
        return True

    def get_name(self):
        return f"Chain {self.chain_id}"


class FakeChainManager:
    get_midi_cc_zctrls = get_midi_cc_zctrls_fn

    def __init__(self, chains, active_chain):
        self.chains = chains
        self.active_chain = active_chain
        self.absolute_midi_cc_binding = {}
        self.chain_midi_cc_binding = {}
        self._midi_chan_2_chain_ids = [[] for _ in range(16)]
        self.set_active_chain_calls = []

    def get_processors(self, chain_id):
        return list(self.chains[chain_id].processors)

    def set_active_chain_by_id(self, chain_id):
        self.set_active_chain_calls.append(chain_id)
        self.active_chain = self.chains[chain_id]
        return chain_id

    def get_midi_learn_from_zctrl(self, zctrl, chain=True, abs=True, zynstep=True):
        return None


def make_control_screen(chain_manager, zyngui, parent=None, list_data=None, zcontrollers=None):
    """Build a zynthian_gui_control instance without running Tkinter __init__."""
    ctrl = object.__new__(zynthian_gui_control)
    ctrl.parent = parent
    ctrl.zyngui = zyngui
    ctrl.chain_manager = chain_manager
    ctrl.shown = True
    ctrl.mode = "control"
    ctrl.midi_learning = MIDI_LEARNING_DISABLED
    ctrl.list_data = list_data or []
    ctrl.zcontrollers = zcontrollers or []
    ctrl.zgui_controllers = []
    ctrl.processors = []
    ctrl.index = 0
    ctrl.selected_indices = []

    def fake_select(index=None, set_zctrl=True):
        ctrl.index = index
        ctrl.selected_indices.append(index)
        if index is not None and 0 <= index < len(ctrl.list_data):
            row = ctrl.list_data[index]
            if row[1] == -1:
                ctrl.zcontrollers = row[5]
            elif row[1] and row[1] > 0:
                ctrl.zcontrollers = row[3].get_ctrl_screen(row[2])

    ctrl.select = fake_select
    ctrl.fill_list = MagicMock()
    ctrl.midi_learn_bind = MagicMock()
    return ctrl


class TestMidiCCAutoFocus(unittest.TestCase):
    def setUp(self):
        zynconf.save_config.reset_mock()
        zynthian_gui_config.midi_cc_autofocus = 1
        zynthian_gui_config.midi_bank_change = 0

        # Chain 1: Synth (2 pages) + Reverb FX (2 pages)
        self.z1_p0 = FakeZCtrl("cutoff")
        self.z1_p1 = FakeZCtrl("resonance")
        self.z1_fx_p0 = FakeZCtrl("dry_wet")
        self.z1_fx_p1 = FakeZCtrl("decay")
        self.z1_chain_only = FakeZCtrl("fav_only")

        self.chain1 = FakeChain(1)
        self.proc1_synth = FakeProcessor(
            1, "Synth1", 1, {"Page1": [self.z1_p0], "Page2": [self.z1_p1]}, chain=self.chain1
        )
        self.proc1_fx = FakeProcessor(
            2, "Reverb1", 1, {"Mix": [self.z1_fx_p0], "Tail": [self.z1_fx_p1]}, chain=self.chain1
        )
        self.z1_p0.processor = self.proc1_synth
        self.z1_p1.processor = self.proc1_synth
        self.z1_fx_p0.processor = self.proc1_fx
        self.z1_fx_p1.processor = self.proc1_fx
        self.z1_chain_only.processor = self.proc1_synth
        self.chain1.processors = [self.proc1_synth, self.proc1_fx]
        self.chain1.current_processor = self.proc1_synth

        # Chain 2: Synth2 (2 pages)
        self.z2_p0 = FakeZCtrl("osc_tune")
        self.z2_p1 = FakeZCtrl("env_attack")
        self.chain2 = FakeChain(2)
        self.proc2_synth = FakeProcessor(
            3, "Synth2", 2, {"Osc": [self.z2_p0], "Env": [self.z2_p1]}, chain=self.chain2
        )
        self.z2_p0.processor = self.proc2_synth
        self.z2_p1.processor = self.proc2_synth
        self.chain2.processors = [self.proc2_synth]
        self.chain2.current_processor = self.proc2_synth

        # Special processor: ALSA mixer (id = -2)
        self.z_alsa_p0 = FakeZCtrl("headphone")
        self.z_alsa_p1 = FakeZCtrl("line_out")
        self.proc_alsa = FakeProcessor(
            -2, "ALSA Mixer", None, {"Outputs": [self.z_alsa_p0], "Extra": [self.z_alsa_p1]}
        )
        self.z_alsa_p0.processor = self.proc_alsa
        self.z_alsa_p1.processor = self.proc_alsa

        self.cm = FakeChainManager({1: self.chain1, 2: self.chain2}, self.chain1)

        self.state_manager = MagicMock()
        self.state_manager.is_busy.return_value = False
        self.state_manager.get_max_num_midi_devs.return_value = 16
        self.state_manager.midi_learn_zctrl = None
        self.state_manager.alsa_mixer_processor = self.proc_alsa
        self.state_manager.audio_player = None
        self.state_manager.tempo_processor = None
        self.state_manager.zctrl_x = None
        self.state_manager.zctrl_y = None

        self.zyngui = MagicMock()
        self.zyngui.current_screen = "chain_control"
        self.zyngui.state_manager = self.state_manager
        self.zyngui.SCREEN_HMODE_REPLACE = 2

        self.list_data_chain1 = [
            (None, None, "> Synth1", self.proc1_synth),
            ("grp", 1, "Page1", self.proc1_synth, 0),
            ("grp", 2, "Page2", self.proc1_synth, 1),
            (None, None, "> Reverb1", self.proc1_fx),
            ("grp", 4, "Mix", self.proc1_fx, 0),
            ("grp", 5, "Tail", self.proc1_fx, 1),
        ]

        self.parent = types.SimpleNamespace(
            chain_id=1,
            subscreen=None,
            chain_canvas=types.SimpleNamespace(selected_index=2),
        )
        self.ctrl = make_control_screen(
            self.cm,
            self.zyngui,
            parent=self.parent,
            list_data=self.list_data_chain1,
            zcontrollers=[self.z1_p0],
        )
        self.parent.subscreen = self.ctrl

    def test_same_chain_switches_processor_and_encoder_page(self):
        # Chain-learn CC 74 on active chain -> Reverb1 / Tail (page 1, list index 5)
        key = (1 << 16) | (0 << 8) | 74
        self.cm.chain_midi_cc_binding[key] = [self.z1_fx_p1]

        self.ctrl.cb_midi_cc(izmip=0, chan=0, num=74, val=64)

        self.assertEqual(self.ctrl.selected_indices, [5])
        self.assertEqual(self.proc1_fx.current_screen_index, 1)
        self.assertEqual(self.chain1.current_processor, self.proc1_fx)
        self.assertEqual(self.cm.set_active_chain_calls, [])

    def test_channel_unbound_chain_binding_triggers_autofocus(self):
        # Auto-learned/unbound chain CC 71 -> Synth1 / Page2 (list index 2)
        key = (1 << 16) | (0xFF << 8) | 71
        self.cm.chain_midi_cc_binding[key] = [self.z1_p1]

        self.ctrl.cb_midi_cc(izmip=1, chan=5, num=71, val=100)

        self.assertEqual(self.ctrl.selected_indices, [2])
        self.assertEqual(self.proc1_synth.current_screen_index, 1)

    def test_cross_chain_global_binding_switches_chain_proc_and_page(self):
        # Global learn on zmip=2, ch=0, cc=10 -> Chain 2 / Synth2 / Env (page 1)
        key = (2 << 16) | (0 << 8) | 10
        self.cm.absolute_midi_cc_binding[key] = [self.z2_p1]

        self.ctrl.cb_midi_cc(izmip=2, chan=0, num=10, val=80)

        self.assertEqual(self.cm.set_active_chain_calls, [2])
        self.assertEqual(self.chain2.current_processor, self.proc2_synth)
        self.assertEqual(self.proc2_synth.current_screen_index, 1)
        self.assertIsNone(self.parent.chain_canvas.selected_index)

        # Second rapid CC tick before queued SS_SET_ACTIVE_CHAIN updates parent.chain_id:
        # must NOT re-trigger set_active_chain_by_id or select on stale chain1 list_data
        self.ctrl.cb_midi_cc(izmip=2, chan=0, num=10, val=85)
        self.assertEqual(self.cm.set_active_chain_calls, [2])
        self.assertEqual(self.ctrl.selected_indices, [])

    def test_already_visible_control_is_noop(self):
        # z1_p0 is already in self.ctrl.zcontrollers
        key = (1 << 16) | (0 << 8) | 74
        self.cm.chain_midi_cc_binding[key] = [self.z1_p0, self.z1_fx_p1]

        self.ctrl.cb_midi_cc(izmip=0, chan=0, num=74, val=50)

        self.assertEqual(self.ctrl.selected_indices, [])
        self.assertEqual(self.cm.set_active_chain_calls, [])

    def test_disabled_option_does_nothing(self):
        zynthian_gui_config.midi_cc_autofocus = 0
        key = (1 << 16) | (0 << 8) | 74
        self.cm.chain_midi_cc_binding[key] = [self.z1_fx_p1]

        self.ctrl.cb_midi_cc(izmip=0, chan=0, num=74, val=64)

        self.assertEqual(self.ctrl.selected_indices, [])

    def test_ignored_when_not_on_control_screen_or_select_mode_or_learning_or_busy(self):
        key = (1 << 16) | (0 << 8) | 74
        self.cm.chain_midi_cc_binding[key] = [self.z1_fx_p1]

        # On mixer screen
        self.zyngui.current_screen = "mixer"
        self.ctrl.cb_midi_cc(0, 0, 74, 64)
        self.assertEqual(self.ctrl.selected_indices, [])
        self.zyngui.current_screen = "chain_control"

        # In select mode
        self.ctrl.mode = "select"
        self.ctrl.cb_midi_cc(0, 0, 74, 64)
        self.assertEqual(self.ctrl.selected_indices, [])
        self.ctrl.mode = "control"

        # In MIDI learning mode
        self.ctrl.midi_learning = MIDI_LEARNING_CHAIN
        self.ctrl.cb_midi_cc(0, 0, 74, 64)
        self.assertEqual(self.ctrl.selected_indices, [])
        self.ctrl.midi_learning = MIDI_LEARNING_DISABLED

        # Busy
        self.state_manager.is_busy.return_value = True
        self.ctrl.cb_midi_cc(0, 0, 74, 64)
        self.assertEqual(self.ctrl.selected_indices, [])
        self.state_manager.is_busy.return_value = False

        # Internal / ZynStep / feedback ZMIP (>= 16)
        self.ctrl.cb_midi_cc(17, 0, 74, 64)
        self.assertEqual(self.ctrl.selected_indices, [])

    def test_bank_change_cc_ignored_when_enabled(self):
        zynthian_gui_config.midi_bank_change = 1
        self.cm._midi_chan_2_chain_ids[0] = [1]
        key = (1 << 16) | (0 << 8) | 0
        self.cm.chain_midi_cc_binding[key] = [self.z1_fx_p1]

        self.assertEqual(self.cm.get_midi_cc_zctrls(0, 0, 0), [])

    def test_special_processor_alsa_mixer_switch_both_directions(self):
        # From chain_control -> global binding to ALSA Mixer page 1
        key = (0 << 16) | (0 << 8) | 20
        self.cm.absolute_midi_cc_binding[key] = [self.z_alsa_p1]

        self.ctrl.cb_midi_cc(0, 0, 20, 90)
        self.assertEqual(self.proc_alsa.current_screen_index, 1)
        self.zyngui.show_screen.assert_called_once_with("alsa_mixer", hmode=self.zyngui.SCREEN_HMODE_REPLACE)

        # From standalone alsa_mixer -> global binding to Chain 2 / Synth2 / Env
        self.zyngui.current_screen = "alsa_mixer"
        standalone = make_control_screen(
            self.cm,
            self.zyngui,
            parent=None,
            list_data=[
                (None, None, "> ALSA Mixer", self.proc_alsa),
                ("grp", 1, "Outputs", self.proc_alsa, 0),
                ("grp", 2, "Extra", self.proc_alsa, 1),
            ],
            zcontrollers=[self.z_alsa_p1],
        )
        key2 = (0 << 16) | (0 << 8) | 21
        self.cm.absolute_midi_cc_binding[key2] = [self.z2_p1]

        standalone.cb_midi_cc(0, 0, 21, 55)
        self.zyngui.chain_control.assert_called_once_with(
            chain_id=2,
            processor=self.proc2_synth,
            hmode=self.zyngui.SCREEN_HMODE_REPLACE,
            reset=True,
        )
        self.assertEqual(self.proc2_synth.current_screen_index, 1)

    def test_chain_controllers_page_fallback(self):
        self.chain1.zctrls = [self.z1_chain_only]
        self.ctrl.list_data = [
            (None, None, "> CHAIN", None),
            ("CHAIN_0", -1, "Controllers 1", self.proc1_synth, 0, [self.z1_chain_only]),
        ] + self.list_data_chain1
        key = (1 << 16) | (0 << 8) | 99
        self.cm.chain_midi_cc_binding[key] = [self.z1_chain_only]

        self.ctrl.cb_midi_cc(0, 0, 99, 127)
        self.assertEqual(self.ctrl.selected_indices, [1])

    def test_control_options_toggle_and_persistence(self):
        self.ctrl.processors = [self.proc1_synth]
        self.ctrl.zgui_controllers = [types.SimpleNamespace(zctrl=self.z1_p0)]
        self.ctrl.exit_midi_learn = MagicMock()
        option_screen = MagicMock()
        self.zyngui.screens = {"option": option_screen}

        # Open Control Options -> should show checked MIDI Auto-Focus
        self.ctrl.controller_options(0)
        _, options, cb = option_screen.config.call_args.args[:3]
        self.assertIn("\u2612 MIDI Auto-Focus", options)
        self.assertEqual(cb, self.ctrl.controller_options_cb)

        # Toggle OFF via callback -> saves config and refreshes menu with unchecked box
        self.ctrl.controller_options_cb("\u2612 MIDI Auto-Focus", 0)
        self.assertEqual(zynthian_gui_config.midi_cc_autofocus, 0)
        zynconf.save_config.assert_called_with({"ZYNTHIAN_UI_MIDI_CC_AUTOFOCUS": "0"})
        _, options_after, _ = option_screen.config.call_args.args[:3]
        self.assertIn("\u2610 MIDI Auto-Focus", options_after)

    def test_chain_options_toggle_and_persistence(self):
        ch_opt = object.__new__(zynthian_gui_chain_options)
        ch_opt.chain = self.chain1
        ch_opt.zyngui = self.zyngui
        ch_opt.list_data = []

        ch_opt.fill_list()
        titles = [item[2] for item in ch_opt.list_data]
        self.assertIn("\u2612 MIDI Auto-Focus", titles)

        ch_opt.toggle_midi_cc_autofocus()
        self.assertEqual(zynthian_gui_config.midi_cc_autofocus, 0)
        zynconf.save_config.assert_called_with({"ZYNTHIAN_UI_MIDI_CC_AUTOFOCUS": "0"})
        titles_after = [item[2] for item in ch_opt.list_data]
        self.assertIn("\u2610 MIDI Auto-Focus", titles_after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
