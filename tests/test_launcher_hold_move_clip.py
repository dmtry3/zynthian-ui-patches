#!/usr/bin/env python3
"""Unit tests for the Zynthian UI PAD/Launcher Hold-F4 Move/Swap Clip patch."""

import os
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import MagicMock, patch

ZYNTHIAN_UI_DIR = os.environ.get("ZYNTHIAN_UI_DIR", "/zynthian/zynthian-ui")


def install_stubs():
    """Install minimal stubs for hardware/C/Tk dependencies so we can import the patched modules directly."""
    if ZYNTHIAN_UI_DIR not in sys.path:
        sys.path.insert(0, ZYNTHIAN_UI_DIR)

    # Stub tkinter if not headless-safe or to avoid needing X11
    if "PIL" not in sys.modules:
        pil_mod = types.ModuleType("PIL")
        pil_mod.Image = MagicMock()
        pil_mod.ImageTk = MagicMock()
        pil_mod.ImageDraw = MagicMock()
        pil_mod.ImageFont = MagicMock()
        sys.modules["PIL"] = pil_mod

    if "zyngine" not in sys.modules:
        zyngine_pkg = types.ModuleType("zyngine")
        zyngine_pkg.__path__ = [os.path.join(ZYNTHIAN_UI_DIR, "zyngine")]
        sys.modules["zyngine"] = zyngine_pkg

    if "zynlibs.zynaudioplayer" not in sys.modules:
        zynlibs_pkg = sys.modules.setdefault("zynlibs", types.ModuleType("zynlibs"))
        zap_mod = types.ModuleType("zynlibs.zynaudioplayer")
        zap_mod.__all__ = []
        zynlibs_pkg.zynaudioplayer = zap_mod
        sys.modules["zynlibs.zynaudioplayer"] = zap_mod

    if "zynconf" not in sys.modules:
        zynconf_mod = types.ModuleType("zynconf")
        zynconf_mod.save_config = MagicMock()
        zynconf_mod.load_plain_envars = MagicMock()
        zynconf_mod.NoteCuiaDefault = {}
        zynconf_mod.get_external_storage_dirs = MagicMock(return_value=[])
        sys.modules["zynconf"] = zynconf_mod

    if "zynautoconnect" not in sys.modules:
        zynauto_mod = types.ModuleType("zynautoconnect")
        zynauto_mod.ctrl_fb_procs = []
        zynauto_mod.get_midi_in_devid = MagicMock(return_value="USB_MIDI")
        zynauto_mod.get_midi_in_dev_mode = MagicMock(return_value=1)
        zynauto_mod.get_jackd_samplerate = MagicMock(return_value=48000)
        zynauto_mod.request_audio_connect = MagicMock()
        zynauto_mod.request_midi_connect = MagicMock()
        sys.modules["zynautoconnect"] = zynauto_mod

    if "zyncoder.zyncore" not in sys.modules:
        zyncoder_pkg = types.ModuleType("zyncoder")
        zyncore_mod = types.ModuleType("zyncoder.zyncore")
        lib_zyncore = MagicMock()
        zyncore_mod.lib_zyncore = lib_zyncore
        zyncoder_pkg.zyncore = zyncore_mod
        sys.modules["zyncoder"] = zyncoder_pkg
        sys.modules["zyncoder.zyncore"] = zyncore_mod

    if "zyngine.zynthian_signal_manager" not in sys.modules:
        sig_mod = types.ModuleType("zyngine.zynthian_signal_manager")
        sig_mod.zynsigman = MagicMock()
        sys.modules["zyngine.zynthian_signal_manager"] = sig_mod

    if "zynlibs.zynseq" not in sys.modules:
        zynlibs_pkg = sys.modules.setdefault("zynlibs", types.ModuleType("zynlibs"))
        zynseq_pkg = types.ModuleType("zynlibs.zynseq")
        zynseq_mod = types.ModuleType("zynlibs.zynseq.zynseq")
        zynseq_mod.PHRASE_CHANNEL = 32
        zynseq_mod.SEQ_STOPPED = 0
        zynseq_mod.SEQ_PLAYING = 1
        zynseq_mod.SEQ_STARTING = 2
        zynseq_mod.SEQ_STOPPING = 3
        zynseq_mod.SEQ_STOPPING_SYNC = 4
        zynseq_mod.SEQ_CHILD_PLAYING = 5
        zynseq_mod.SEQ_CHILD_STOPPING = 6
        zynseq_mod.FOLLOW_ACTION_NONE = 0
        zynseq_mod.FOLLOW_ACTION_RELATIVE = 1
        zynseq_mod.CHANNEL_CHARS = [chr(65 + i) for i in range(32)]
        zynseq_pkg.zynseq = zynseq_mod
        zynlibs_pkg.zynseq = zynseq_pkg
        sys.modules["zynlibs.zynseq"] = zynseq_pkg
        sys.modules["zynlibs.zynseq.zynseq"] = zynseq_mod

    if "zyngui.zynthian_gui_base" not in sys.modules:
        base_mod = types.ModuleType("zyngui.zynthian_gui_base")

        class DummyBase:
            def switch_select(self, t="S"):
                return False

            def hide(self):
                self.shown = False

            def set_title(self, title="", fg=None, bg=None, timeout=None):
                pass

        base_mod.zynthian_gui_base = DummyBase
        sys.modules["zyngui.zynthian_gui_base"] = base_mod
    else:
        base_cls = sys.modules["zyngui.zynthian_gui_base"].zynthian_gui_base
        if not hasattr(base_cls, "switch_select"):
            base_cls.switch_select = lambda self, t="S": False
        if not hasattr(base_cls, "hide"):
            base_cls.hide = lambda self: setattr(self, "shown", False)
        if not hasattr(base_cls, "set_title"):
            base_cls.set_title = lambda self, title="", fg=None, bg=None, timeout=None: None

    if "zyngui.zynthian_gui_dpm" not in sys.modules:
        dpm_mod = types.ModuleType("zyngui.zynthian_gui_dpm")
        dpm_mod.zynthian_gui_dpm = MagicMock()
        sys.modules["zyngui.zynthian_gui_dpm"] = dpm_mod

    if "zyngui.zynthian_gui_mixer_base" not in sys.modules:
        pass

    if "zyngine.zynthian_engine" not in sys.modules:
        eng_mod = types.ModuleType("zyngine.zynthian_engine")

        class DummyEngine:
            def __init__(self, state_manager=None):
                self.state_manager = state_manager

        eng_mod.zynthian_engine = DummyEngine
        sys.modules["zyngine.zynthian_engine"] = eng_mod

    if "zyngine.zynthian_controller" not in sys.modules:
        ctrl_mod = types.ModuleType("zyngine.zynthian_controller")
        ctrl_mod.zynthian_controller = MagicMock()
        sys.modules["zyngine.zynthian_controller"] = ctrl_mod


install_stubs()

from zynlibs.zynseq import zynseq as zynseq_const  # noqa: E402
from zyngine.zynthian_engine_clippy import zctrl_symbols, zynthian_engine_clippy  # noqa: E402
from zyngui.zynthian_gui_mixer import zynthian_gui_mixer  # noqa: E402


class FakeZCtrl:
    def __init__(self, symbol, value):
        self.symbol = symbol
        self.value = value
        self.set_value_calls = []

    def set_value(self, val):
        self.value = val
        self.set_value_calls.append(val)

    def get_value(self):
        return self.value


class FakeLibSeq:
    def __init__(self):
        # (scene, phrase, chan) -> pattern_id
        self.patterns = {}
        # pattern_id -> bool empty
        self.empty_patterns = {}
        # (scene, phrase, chan) -> name (raw string)
        self.names = {}
        # (scene, phrase, chan) -> repeat int
        self.repeats = {}
        # (scene, phrase, chan) -> play_state
        self.play_states = {}
        # pattern_id -> beats
        self.pattern_beats = {}
        self.tempo = 120.0
        self.midi_commands = []
        self.cleared_patterns = []
        self.update_info_calls = 0

    def getPattern(self, scene, phrase, chan, track, pos):
        return self.patterns.get((scene, phrase, chan), 0xFFFFFFFF)

    def getBeatsInPattern(self, pat):
        return self.pattern_beats.get(pat, 4)

    def getTempo(self):
        return self.tempo

    def setSequenceRepeat(self, scene, phrase, chan, repeat):
        self.repeats[(scene, phrase, chan)] = repeat

    def removePattern(self, scene, phrase, chan, track, pos):
        self.patterns.pop((scene, phrase, chan), None)

    def addPattern(self, scene, phrase, chan, track, pos, pat, force):
        self.patterns[(scene, phrase, chan)] = pat
        return True

    def isPatternEmpty(self, pat):
        return self.empty_patterns.get(pat, True)

    def clearPattern(self, pat):
        self.empty_patterns[pat] = True
        self.cleared_patterns.append(pat)

    def getSequenceName(self, scene, phrase, chan):
        return self.names.get((scene, phrase, chan), "").encode("utf-8")

    def getSequenceRepeat(self, scene, phrase, chan):
        return self.repeats.get((scene, phrase, chan), 255)

    def getPlayState(self, scene, phrase, chan):
        return self.play_states.get((scene, phrase, chan), zynseq_const.SEQ_STOPPED)

    def setPlayState(self, scene, phrase, chan, state):
        self.play_states[(scene, phrase, chan)] = state

    def sendMidiCommand(self, status, data1, data2):
        self.midi_commands.append((status, data1, data2))

    def updateSequenceInfo(self):
        self.update_info_calls += 1


class FakeZynSeq:
    def __init__(self, phrases=4):
        self.scene = 0
        self.phrase = 0
        self.phrases = phrases
        self.chan = 0
        self.libseq = FakeLibSeq()
        self.refresh_calls = 0

    def is_pattern_empty(self, pat):
        return self.libseq.isPatternEmpty(pat)

    def get_sequence_name(self, scene, phrase, chan):
        raw = self.libseq.getSequenceName(scene, phrase, chan).decode("utf-8")
        if raw:
            return raw
        return f"{zynseq_const.CHANNEL_CHARS[chan]}{phrase + 1}"

    def set_sequence_param(self, scene, phrase, chan, param, value):
        if param == "name":
            self.libseq.names[(scene, phrase, chan)] = value
        elif param == "repeat":
            self.libseq.repeats[(scene, phrase, chan)] = value
        return True

    def refresh_state(self):
        self.refresh_calls += 1


class FakePad:
    def __init__(self, chain, phrase):
        self.chain = chain
        self.phrase = phrase
        self.last_state = {"dummy": True}
        self.outline = ""
        self.draw_calls = 0

    def highlight(self, color="yellow"):
        self.outline = color

    def draw(self, force=False):
        self.draw_calls += 1


class FakeChain:
    def __init__(self, chain_id, midi_chan, processors=None, mixer_chan=None):
        self.chain_id = chain_id
        self.midi_chan = midi_chan
        self._processors = processors or []
        if mixer_chan is not None:
            self.zynmixer_proc = types.SimpleNamespace(eng_code="MI", mixer_chan=mixer_chan)
        else:
            self.zynmixer_proc = None

    def get_processors(self):
        return self._processors


class FakeStrip:
    def __init__(self, chain, phrases):
        self.chain = chain
        self.chan = 32 if chain.chain_id == 0 else chain.midi_chan
        self.launchers = [FakePad(chain, p) for p in range(phrases)]


class FakeClippyEngine(zynthian_engine_clippy):
    def __init__(self, zynseq):
        self.zynseq = zynseq
        self.libseq = zynseq.libseq
        self.libclippy = MagicMock()
        self.set_file_calls = []

    def is_clip_busy(self, proc, phrase):
        return bool(proc.controllers_dict[f"file {phrase + 1}"].value)

    def set_state_pre_note(self, processor, note):
        return f"file {note}" in processor.controllers_dict

    def set_state_post_note(self, processor, note):
        phrase = note - 1
        self.set_file_calls.append((processor, phrase, processor.controllers_dict[f"file {note}"].value))
        return True

    def set_file(self, processor, phrase, autoreset=True):
        note = phrase + 1
        self.set_file_calls.append((processor, phrase, processor.controllers_dict[f"file {note}"].value))


def make_clippy_proc(engine, midi_chan, phrases=4, clip_files=None):
    clip_files = clip_files or {}
    proc = types.SimpleNamespace(
        engine=engine,
        midi_chan=midi_chan,
        set_state_flag=False,
        controllers_dict={},
    )
    defaults = {
        "file": "",
        "crop_start": 0,
        "crop_end": 999999999,
        "zoom": 1,
        "gain": 0.0,
        "warp": 1,
        "beats": 4,
        "mode": 1,
        "beat_slice": 1,
    }
    for p in range(phrases):
        note = p + 1
        overrides = clip_files.get(p, {})
        for sym in zctrl_symbols:
            val = overrides.get(sym, defaults[sym])
            proc.controllers_dict[f"{sym} {note}"] = FakeZCtrl(f"{sym} {note}", val)
    return proc


class TestLauncherHoldMoveClip(unittest.TestCase):
    def setUp(self):
        self.zynseq = FakeZynSeq(phrases=4)
        self.clippy_engine = FakeClippyEngine(self.zynseq)

        # Chain 1 (MIDI ch 0): phrase 0 occupied (pat 101, "Bass", repeat=1), phrase 1 empty (pat 102)
        # Chain 2 (MIDI ch 1): phrase 0 empty (pat 201), phrase 2 occupied (pat 203, "Lead", repeat=4)
        # Chain 3 (Clippy ch 16): phrase 0 has clip1.wav (gain=-3.0), phrase 1 empty
        # Chain 4 (Clippy ch 17): phrase 1 has clip2.wav (gain=2.5)
        # Chain 0 (Main / Phrase)
        for p in range(4):
            self.zynseq.libseq.patterns[(0, p, 0)] = 101 + p
            self.zynseq.libseq.empty_patterns[101 + p] = (p != 0)
            self.zynseq.libseq.patterns[(0, p, 1)] = 201 + p
            self.zynseq.libseq.empty_patterns[201 + p] = (p != 2)

        self.zynseq.libseq.names[(0, 0, 0)] = "Bass"
        self.zynseq.libseq.repeats[(0, 0, 0)] = 1
        self.zynseq.libseq.names[(0, 2, 1)] = "Lead"
        self.zynseq.libseq.repeats[(0, 2, 1)] = 4

        self.proc_clp1 = make_clippy_proc(
            self.clippy_engine,
            16,
            4,
            {0: {"file": "/clips/loop1.wav", "gain": -3.0, "beats": 8, "crop_start": 100, "crop_end": 48000}},
        )
        self.proc_clp2 = make_clippy_proc(
            self.clippy_engine,
            17,
            4,
            {1: {"file": "/clips/loop2.wav", "gain": 2.5, "beats": 16, "crop_start": 500, "crop_end": 96000}},
        )

        self.chain_midi1 = FakeChain(1, 0, mixer_chan=0)
        self.chain_midi2 = FakeChain(2, 1, mixer_chan=1)
        self.chain_clp1 = FakeChain(3, 16, [self.proc_clp1], mixer_chan=2)
        self.chain_clp2 = FakeChain(4, 17, [self.proc_clp2], mixer_chan=3)
        self.chain_main = FakeChain(0, None)

        self.chains = [self.chain_midi1, self.chain_midi2, self.chain_clp1, self.chain_clp2, self.chain_main]
        self.active_chain = self.chain_midi1

        self.chain_manager = MagicMock()
        self.chain_manager.get_active_chain.side_effect = lambda: self.active_chain
        self.chain_manager.get_chain.side_effect = lambda cid: next(
            (c for c in self.chains if c.chain_id == cid), None
        )

        self.state_manager = MagicMock()
        self.wsleds = types.SimpleNamespace(
            wscolor_active="GREEN",
            wscolor_active2="ORANGE",
            wscolor_red="RED",
            wscolor_alt="PURPLE",
            set_led=MagicMock(),
            blink=MagicMock(),
        )
        self.zyngui = MagicMock()
        self.zyngui.tts = None
        self.zyngui.wsleds = self.wsleds
        self.zyngui.osc_clients = []

        self.mixer = object.__new__(zynthian_gui_mixer)
        self.mixer.zyngui = self.zyngui
        self.mixer.state_manager = self.state_manager
        self.mixer.chain_manager = self.chain_manager
        self.mixer.zynseq = self.zynseq
        self.mixer.shown = True
        self.mixer.alt_mode = True
        self.mixer.launcher_mode = True
        self.mixer.moving_chain = False
        self.mixer.moving_phrase = False
        self.mixer.moving_clip = None
        self.mixer._moving_phrase_hold = False
        self.mixer._move_clip_cancelled = False
        self.mixer._bounce_thread = None
        self.mixer._bounce_cancel = threading.Event()
        self.mixer._bouncing_info = None
        self.mixer.param_editor_zctrl = None
        self.mixer.clipboard = [None, None, None, None]
        self.mixer.switch_i_clipboard = [11, 15]
        self.mixer.wsleds_i_clipboard = [10, 11]
        self.mixer.switch_i_add_chain = 19
        self.mixer.wsled_i_add_chain = 12
        self.mixer.switch_i_move_clip = 23
        self.mixer.wsled_i_move_clip = 13
        self.mixer.left_canvas = MagicMock()
        self.mixer.right_canvas = MagicMock()
        self.mixer.right_canvas.after = lambda delay, fn, *args: fn(*args)
        self.mixer.launcher_height = 50
        self.mixer.fader_height = 300
        self.mixer.legend_y = 350
        self.mixer.launcher_y = 50
        self.mixer._scroll_y = 0
        self.mixer.set_title_ts = 0
        self.mixer.titles = []
        self.mixer.set_title = lambda title="", fg=None, bg=None, timeout=None: self.mixer.titles.append(
            (title, timeout)
        )
        self.mixer.refresh_launchers = MagicMock()
        self.mixer.scroll_canvas = MagicMock()
        self.mixer.toggle_launcher_mode = MagicMock()
        self.mixer.chain_strips = [FakeStrip(c, 4) for c in self.chains]
        self.mixer.highlighted_strip = self.mixer.chain_strips[0]

    def move_cursor(self, chain_idx, phrase):
        self.active_chain = self.chains[chain_idx]
        self.mixer.highlighted_strip = self.mixer.chain_strips[chain_idx]
        self.zynseq.phrase = phrase
        self.zynseq.chan = self.active_chain.midi_chan
        self.mixer.highlight_launcher()

    def test_hold_f4_move_midi_pattern_to_empty_cell(self):
        # Start on Chain 1 (MIDI ch 0), phrase 0 ("Bass", pat 101)
        res_press = self.mixer.switch(23, "P")
        self.assertFalse(res_press)  # Must return False so cuia_queue tracks press ts & avoids repeat
        self.assertIsNotNone(self.mixer.moving_clip)
        self.zyngui.zynswitch_disable_autolong.assert_called_once()
        self.assertEqual(self.mixer.chain_strips[0].launchers[0].outline, "#FF8800")

        # Move cursor to Chain 2 (MIDI ch 1), phrase 0 (empty, pat 201)
        self.move_cursor(1, 0)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "move")
        self.assertEqual(self.mixer.chain_strips[0].launchers[0].outline, "#FF8800")
        self.assertEqual(self.mixer.chain_strips[1].launchers[0].outline, "#00FF00")
        self.assertIn("Move Bass → B1", [t[0] for t in self.mixer.titles])

        # Release F4 (e.g. after long hold -> 'L')
        res_rel = self.mixer.switch(23, "L")
        self.assertTrue(res_rel)
        self.assertIsNone(self.mixer.moving_clip)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

        # Verify patterns, names, repeats swapped cleanly
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 1)], 101)
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 0)], 201)
        self.assertEqual(self.zynseq.libseq.names[(0, 0, 1)], "Bass")
        self.assertEqual(self.zynseq.libseq.names[(0, 0, 0)], "")
        self.assertEqual(self.zynseq.libseq.repeats[(0, 0, 1)], 1)
        self.assertEqual(self.zynseq.libseq.repeats[(0, 0, 0)], 255)
        self.assertEqual(self.zynseq.libseq.update_info_calls, 1)
        self.assertEqual(self.zynseq.refresh_calls, 1)
        self.assertEqual(self.mixer.titles[-1], ("Moved Bass → B1", 1.5))

    def test_hold_f4_swap_two_occupied_midi_patterns_and_stop_playing(self):
        # Mark source playing and put both patterns in clipboard
        self.zynseq.libseq.play_states[(0, 0, 0)] = zynseq_const.SEQ_PLAYING
        self.mixer.clipboard[0] = ("PAT", 0, 0, 101)
        self.mixer.clipboard[1] = ("PAT", 2, 1, 203)

        self.mixer.switch(23, "P")
        self.move_cursor(1, 2)  # Chain 2, phrase 2 ("Lead", pat 203, repeat=4)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "swap")
        self.assertIn("Swap Bass ↔ Lead", [t[0] for t in self.mixer.titles])

        self.assertTrue(self.mixer.switch(23, "B"))

        # Patterns & metadata swapped
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 0)], 203)
        self.assertEqual(self.zynseq.libseq.patterns[(0, 2, 1)], 101)
        self.assertEqual(self.zynseq.libseq.names[(0, 0, 0)], "Lead")
        self.assertEqual(self.zynseq.libseq.names[(0, 2, 1)], "Bass")
        self.assertEqual(self.zynseq.libseq.repeats[(0, 0, 0)], 4)
        self.assertEqual(self.zynseq.libseq.repeats[(0, 2, 1)], 1)

        # Playing source stopped and All Notes Off sent on ch 0
        self.assertEqual(self.zynseq.libseq.play_states[(0, 0, 0)], zynseq_const.SEQ_STOPPED)
        self.assertIn((0xB0, 123, 0), self.zynseq.libseq.midi_commands)

        # Clipboard updated to follow moved patterns
        self.assertEqual(self.mixer.clipboard[0], ("PAT", 2, 1, 101))
        self.assertEqual(self.mixer.clipboard[1], ("PAT", 0, 0, 203))
        self.assertEqual(self.mixer.titles[-1], ("Swapped Bass ↔ Lead", 1.5))

    def test_hold_f4_incompatible_target_cancels_without_changes(self):
        self.mixer.switch(23, "P")
        # Move MIDI pattern over Main / Phrase column -> invalid
        self.move_cursor(4, 0)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "invalid")
        self.assertEqual(self.mixer.chain_strips[4].launchers[0].outline, "#FF0000")

        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 0)], 101)
        self.assertEqual(self.zynseq.refresh_calls, 0)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

        # Clippy audio clip over MIDI pattern -> invalid
        self.zyngui.zynswitch_enable_autolong.reset_mock()
        self.move_cursor(2, 0)
        self.mixer.switch(23, "P")
        self.move_cursor(0, 0)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "invalid")
        self.assertEqual(self.mixer.chain_strips[0].launchers[0].outline, "#FF0000")
        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertEqual(self.proc_clp1.controllers_dict["file 1"].value, "/clips/loop1.wav")

        # Empty MIDI cell over Clippy -> invalid (no bounce of empty pattern)
        self.move_cursor(0, 1)
        self.mixer.switch(23, "P")
        self.move_cursor(2, 1)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "invalid")
        self.assertTrue(self.mixer.switch(23, "B"))

        # MIDI chain without audio mixer output over Clippy -> invalid
        self.chain_midi1.zynmixer_proc = None
        self.move_cursor(0, 0)
        self.mixer.switch(23, "P")
        self.move_cursor(2, 1)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "invalid")
        self.assertTrue(self.mixer.switch(23, "B"))

    def test_hold_f4_release_on_same_cell_is_noop(self):
        self.mixer.switch(23, "P")
        self.assertEqual(self.mixer.get_move_clip_target_status(), "same")
        self.assertTrue(self.mixer.switch(23, "S"))
        self.assertIsNone(self.mixer.moving_clip)
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 0)], 101)
        self.assertEqual(self.zynseq.refresh_calls, 0)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

    def test_back_cancels_active_hold_and_swallows_release(self):
        self.mixer.switch(23, "P")
        self.move_cursor(1, 0)

        self.assertTrue(self.mixer.back_action())
        self.assertIsNone(self.mixer.moving_clip)
        self.assertTrue(self.mixer._move_clip_cancelled)
        self.mixer.toggle_launcher_mode.assert_not_called()

        # Releasing F4 afterwards must be swallowed and NOT swap
        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertFalse(self.mixer._move_clip_cancelled)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 0)], 101)
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 1)], 201)

    def test_hold_f4_empty_midi_cell_clears_occupied_target(self):
        # Start on empty MIDI cell A2 (chain 0, phrase 1)
        self.zynseq.libseq.play_states[(0, 2, 1)] = zynseq_const.SEQ_PLAYING
        self.move_cursor(0, 1)
        self.assertFalse(self.mixer.switch(23, "P"))
        self.assertIsNotNone(self.mixer.moving_clip)
        self.assertFalse(self.mixer.moving_clip[6])  # source is empty
        self.zyngui.zynswitch_disable_autolong.assert_called_once()

        # Over another empty MIDI cell -> noop
        self.move_cursor(1, 0)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "noop")

        # Over occupied MIDI cell Lead (chain 1, phrase 2, pat 203) -> clear
        self.move_cursor(1, 2)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "clear")
        self.assertEqual(self.mixer.chain_strips[1].launchers[2].outline, "#FF4400")
        self.assertIn("Clear Lead", [t[0] for t in self.mixer.titles])

        # Release F4 -> target cleared, stopped with All Notes Off, source stays empty
        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertIn(203, self.zynseq.libseq.cleared_patterns)
        self.assertTrue(self.zynseq.libseq.empty_patterns[203])
        self.assertEqual(self.zynseq.libseq.names[(0, 2, 1)], "")
        self.assertEqual(self.zynseq.libseq.repeats[(0, 2, 1)], 255)
        self.assertEqual(self.zynseq.libseq.play_states[(0, 2, 1)], zynseq_const.SEQ_STOPPED)
        self.assertIn((0xB1, 123, 0), self.zynseq.libseq.midi_commands)
        self.assertTrue(self.zynseq.libseq.empty_patterns[102])
        self.assertEqual(self.mixer.titles[-1], ("Cleared Lead", 1.5))
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

    def test_hold_f4_empty_midi_cell_on_empty_target_is_noop(self):
        self.move_cursor(0, 1)  # empty A2
        self.mixer.switch(23, "P")
        self.move_cursor(1, 0)  # empty B1
        self.assertEqual(self.mixer.get_move_clip_target_status(), "noop")
        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertEqual(self.zynseq.libseq.cleared_patterns, [])
        self.assertEqual(self.zynseq.refresh_calls, 0)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

    def test_hold_f4_empty_clippy_cell_clears_occupied_audio_clip(self):
        # Start on empty Clippy cell (Chain 3, phrase 1)
        self.move_cursor(2, 1)
        self.mixer.switch(23, "P")
        # Move to occupied Clippy cell (Chain 4, phrase 1, loop2.wav)
        self.move_cursor(3, 1)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "clear")
        self.assertTrue(self.mixer.switch(23, "B"))

        self.assertEqual(self.proc_clp2.controllers_dict["file 2"].value, "")
        self.assertEqual(self.proc_clp2.controllers_dict["gain 2"].value, 0.0)
        self.assertFalse(self.proc_clp2.set_state_flag)
        self.assertEqual(self.proc_clp1.controllers_dict["file 2"].value, "")

    def test_f4_ignored_outside_alt_or_launcher_mode(self):
        self.mixer.alt_mode = False
        self.assertFalse(self.mixer.switch(23, "P"))
        self.assertIsNone(self.mixer.moving_clip)
        self.assertFalse(self.mixer.switch(23, "S"))
        self.assertFalse(self.mixer.switch(23, "B"))

        self.mixer.alt_mode = True
        self.mixer.launcher_mode = False
        self.assertFalse(self.mixer.switch(23, "P"))
        self.assertIsNone(self.mixer.moving_clip)
        self.assertFalse(self.mixer.switch(23, "S"))

    def test_alt_toggled_off_mid_hold_still_finishes_on_release(self):
        self.mixer.switch(23, "P")
        self.move_cursor(1, 0)
        self.mixer.alt_mode = False

        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 1)], 101)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

    def test_hold_f4_on_phrase_column_moves_phrase_while_held(self):
        self.move_cursor(4, 1)  # Main / Phrase column
        self.assertFalse(self.mixer.switch(23, "P"))
        self.assertTrue(self.mixer.moving_phrase)
        self.assertTrue(self.mixer._moving_phrase_hold)
        self.zyngui.zynswitch_disable_autolong.assert_called_once()

        self.assertTrue(self.mixer.switch(23, "B"))
        self.assertFalse(self.mixer.moving_phrase)
        self.assertFalse(self.mixer._moving_phrase_hold)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()

    def test_hold_f4_swap_and_move_clippy_audio_clips(self):
        # Start on Clippy Chain 3, phrase 0 (/clips/loop1.wav, gain -3.0)
        self.move_cursor(2, 0)
        self.mixer.clipboard[0] = ("CLP", 0, 16, self.proc_clp1)

        self.mixer.switch(23, "P")
        # Move to Clippy Chain 4, phrase 1 (/clips/loop2.wav, gain 2.5) -> SWAP
        self.move_cursor(3, 1)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "swap")
        self.assertTrue(self.mixer.switch(23, "B"))

        # Verify both clips swapped all parameters and re-applied gains
        self.assertEqual(self.proc_clp1.controllers_dict["file 1"].value, "/clips/loop2.wav")
        self.assertEqual(self.proc_clp1.controllers_dict["gain 1"].value, 2.5)
        self.assertEqual(self.proc_clp1.controllers_dict["beats 1"].value, 16)
        self.assertEqual(self.proc_clp2.controllers_dict["file 2"].value, "/clips/loop1.wav")
        self.assertEqual(self.proc_clp2.controllers_dict["gain 2"].value, -3.0)
        self.assertEqual(self.proc_clp2.controllers_dict["beats 2"].value, 8)
        self.assertFalse(self.proc_clp1.set_state_flag)
        self.assertFalse(self.proc_clp2.set_state_flag)
        self.assertEqual(self.mixer.clipboard[0], ("CLP", 1, 17, self.proc_clp2))

        # Now move loop1.wav from Chain 4 phrase 1 to empty Chain 3 phrase 1 -> MOVE (source unloaded)
        self.mixer.switch(23, "P")
        self.move_cursor(2, 1)
        self.assertEqual(self.mixer.get_move_clip_target_status(), "move")
        self.assertTrue(self.mixer.switch(23, "B"))

        self.assertEqual(self.proc_clp1.controllers_dict["file 2"].value, "/clips/loop1.wav")
        self.assertEqual(self.proc_clp2.controllers_dict["file 2"].value, "")

    def test_wsleds_reflect_move_clip_state(self):
        leds = list(range(16))

        # Idle on movable cell (occupied or empty) -> solid orange (active2)
        self.mixer.update_wsleds(leds)
        self.wsleds.set_led.assert_any_call(13, "ORANGE")

        self.wsleds.set_led.reset_mock()
        self.move_cursor(0, 1)
        self.mixer.update_wsleds(leds)
        self.wsleds.set_led.assert_any_call(13, "ORANGE")

        # Idle on non-movable audio-only chain (midi_chan=None, chain_id!=0) -> alt purple
        self.wsleds.set_led.reset_mock()
        self.active_chain = FakeChain(9, None)
        self.mixer.update_wsleds(leds)
        self.wsleds.set_led.assert_any_call(13, "PURPLE")

        # Active move on source -> blink orange; valid target -> blink green; invalid -> blink red
        self.move_cursor(0, 0)
        self.mixer.switch(23, "P")
        self.wsleds.blink.reset_mock()
        self.mixer.update_wsleds(leds)
        self.wsleds.blink.assert_called_with(13, "ORANGE")

        self.move_cursor(1, 0)
        self.wsleds.blink.reset_mock()
        self.mixer.update_wsleds(leds)
        self.wsleds.blink.assert_called_with(13, "GREEN")

        # Moving occupied MIDI pattern over Clippy -> bounce (blink green)
        self.move_cursor(2, 0)
        self.wsleds.blink.reset_mock()
        self.mixer.update_wsleds(leds)
        self.wsleds.blink.assert_called_with(13, "GREEN")

        # Moving MIDI pattern over Main / Phrase -> invalid (blink red)
        self.move_cursor(4, 0)
        self.wsleds.blink.reset_mock()
        self.mixer.update_wsleds(leds)
        self.wsleds.blink.assert_called_with(13, "RED")

    def test_hold_f4_bounce_midi_pattern_to_clippy_slot(self):
        # Source: Chain 1 (MIDI ch 0, mixer_chan 0), phrase 0 ("Bass", pat 101, repeat=255, 8 beats)
        self.zynseq.libseq.repeats[(0, 0, 0)] = 255
        self.zynseq.libseq.pattern_beats[101] = 8
        self.clippy_engine.libclippy.getFileFrames.return_value = 192000

        with tempfile.TemporaryDirectory() as tmpdir:
            self.state_manager.last_snapshot_fpath = "/zynthian/zynthian-my-data/snapshots/000/001-MyProject.zss"
            self.state_manager.get_new_capture_fpath.return_value = os.path.join(
                tmpdir, "2026-11-28_120000_001-MyProject.wav"
            )

            spawned_cmds = []

            class FakeRecProc:
                def __init__(self, cmd):
                    spawned_cmds.append(cmd)
                    self.wav_path = cmd[-1]
                    self.terminated = False
                    # Write dummy WAV > 44 bytes so size check passes
                    with open(self.wav_path, "wb") as f:
                        f.write(b"RIFF" + b"\x00" * 128)

                def poll(self):
                    return 0 if self.terminated else None

                def terminate(self):
                    self.terminated = True

                def wait(self, timeout=None):
                    return 0

                def kill(self):
                    self.terminated = True

            # Auto-stop playback immediately after SEQ_PLAYING is set
            orig_set_play_state = self.zynseq.libseq.setPlayState

            def auto_finish_play(scene, phrase, chan, state):
                if state == zynseq_const.SEQ_PLAYING:
                    orig_set_play_state(scene, phrase, chan, zynseq_const.SEQ_STOPPED)
                else:
                    orig_set_play_state(scene, phrase, chan, state)

            self.zynseq.libseq.setPlayState = auto_finish_play

            with patch("zyngui.zynthian_gui_mixer.Popen", side_effect=FakeRecProc), \
                 patch("zyngui.zynthian_gui_mixer.sleep", return_value=None), \
                 patch.object(self.mixer, "_wait_for_jack_capture_connect", return_value=True):
                # Hold F4 on MIDI pattern A1 ("Bass")
                self.assertFalse(self.mixer.switch(23, "P"))
                # Move cursor to empty Clippy slot Chain 3, phrase 1
                self.move_cursor(2, 1)
                self.assertEqual(self.mixer.get_move_clip_target_status(), "bounce")
                self.assertEqual(self.mixer.chain_strips[2].launchers[1].outline, "#00CCFF")
                self.assertIn("Bounce Bass → Q2 (8♩)", [t[0] for t in self.mixer.titles])

                # Release F4 -> starts bounce worker
                self.assertTrue(self.mixer.switch(23, "B"))
                worker = self.mixer._bounce_thread
                self.assertIsNotNone(worker)
                worker.join(timeout=5.0)

            # Verify jack_capture captured isolated synth mixer channel ports
            self.assertEqual(len(spawned_cmds), 1)
            self.assertIn("zynmixer_chan:output_00a", spawned_cmds[0])
            self.assertIn("zynmixer_chan:output_00b", spawned_cmds[0])

            # Source MIDI pattern is completely untouched (pattern, name, repeat restored)
            self.assertEqual(self.zynseq.libseq.patterns[(0, 0, 0)], 101)
            self.assertFalse(self.zynseq.libseq.empty_patterns[101])
            self.assertEqual(self.zynseq.libseq.names[(0, 0, 0)], "Bass")
            self.assertEqual(self.zynseq.libseq.repeats[(0, 0, 0)], 255)

            # Target Clippy slot loaded with bounced WAV in project subdir, exact beats, warp=1, name="Bass"
            loaded_file = self.proc_clp1.controllers_dict["file 2"].value
            self.assertEqual(os.path.basename(os.path.dirname(loaded_file)), "001-MyProject")
            self.assertEqual(os.path.basename(loaded_file), "2026-11-28_120000_Bass_120bpm.wav")
            self.assertTrue(os.path.exists(loaded_file))
            self.assertEqual(self.proc_clp1.controllers_dict["beats 2"].value, 8)
            self.assertEqual(self.proc_clp1.controllers_dict["warp 2"].value, 1)
            self.assertEqual(self.proc_clp1.controllers_dict["beat_slice 2"].value, 1)
            self.assertEqual(self.proc_clp1.controllers_dict["crop_start 2"].value, 0)
            self.assertEqual(self.proc_clp1.controllers_dict["crop_end 2"].value, 192000)
            self.assertFalse(self.proc_clp1.set_state_flag)
            self.assertEqual(self.zynseq.libseq.names[(0, 1, 16)], "Bass")
            self.assertEqual(self.mixer.titles[-1], ("Bounced Bass → Q2", 2.0))
            self.assertTrue(self.state_manager.sync)

    def test_back_cancels_active_bounce_and_restores_source_repeat(self):
        self.zynseq.libseq.repeats[(0, 0, 0)] = 4
        started = threading.Event()

        with tempfile.TemporaryDirectory() as tmpdir:
            self.state_manager.last_snapshot_fpath = "/zynthian/zynthian-my-data/snapshots/000/001-MyProject.zss"
            self.state_manager.get_new_capture_fpath.return_value = os.path.join(
                tmpdir, "2026-11-28_120000_001-MyProject.wav"
            )

            class FakeRecProc:
                def __init__(self, cmd):
                    self.wav_path = cmd[-1]
                    self.terminated = False
                    with open(self.wav_path, "wb") as f:
                        f.write(b"RIFF" + b"\x00" * 64)

                def poll(self):
                    return 0 if self.terminated else None

                def terminate(self):
                    self.terminated = True

                def wait(self, timeout=None):
                    return 0

                def kill(self):
                    self.terminated = True

            orig_set_play_state = self.zynseq.libseq.setPlayState

            def track_play(scene, phrase, chan, state):
                orig_set_play_state(scene, phrase, chan, state)
                if state == zynseq_const.SEQ_PLAYING:
                    started.set()

            self.zynseq.libseq.setPlayState = track_play

            with patch("zyngui.zynthian_gui_mixer.Popen", side_effect=FakeRecProc), \
                 patch.object(self.mixer, "_wait_for_jack_capture_connect", return_value=True):
                self.mixer.switch(23, "P")
                self.move_cursor(2, 1)
                self.mixer.switch(23, "B")
                self.assertTrue(started.wait(timeout=3.0))

                # Press BACK during bounce
                self.assertTrue(self.mixer.back_action())
                worker = self.mixer._bounce_thread
                if worker is not None:
                    worker.join(timeout=5.0)

            # Original repeat restored, playback stopped with All Notes Off, target Clippy slot untouched
            self.assertEqual(self.zynseq.libseq.repeats[(0, 0, 0)], 4)
            self.assertEqual(self.zynseq.libseq.play_states[(0, 0, 0)], zynseq_const.SEQ_STOPPED)
            self.assertIn((0xB0, 123, 0), self.zynseq.libseq.midi_commands)
            self.assertEqual(self.proc_clp1.controllers_dict["file 2"].value, "")
            self.assertEqual(self.mixer.titles[-1], ("Bounce cancelled", 1.5))

    def test_hide_cancels_move_and_reenables_autolong(self):
        self.mixer.switch(23, "P")
        self.assertIsNotNone(self.mixer.moving_clip)
        self.mixer.hide()
        self.assertIsNone(self.mixer.moving_clip)
        self.zyngui.zynswitch_enable_autolong.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
