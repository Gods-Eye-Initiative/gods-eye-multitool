import struct
import unittest
import queue
from types import SimpleNamespace
import tkinter as tk
from unittest.mock import patch

try:
    from reconkit.gui_kivy import ReconKitMobile
except ImportError:
    ReconKitMobile = None

from reconkit.gui_common import PALETTE
from reconkit.gui_tk import ReconKitDesktop, logo_asset_path, window_icon_asset_path


@unittest.skipIf(ReconKitMobile is None, "Kivy is an optional GUI dependency")
class KivyLayoutTests(unittest.TestCase):
    def test_labels_wrap_to_their_allocated_width_and_grow(self):
        label = SimpleNamespace(
            padding=(8, 6), width=160, _minimum_height=24, text_size=None, height=24,
        )

        ReconKitMobile._update_label_width(label, 160)
        self.assertEqual(label.text_size, (144, None))

        ReconKitMobile._update_label_height(label, (144, 48))
        self.assertEqual(label.height, 60)

    def test_copy_confirms_success_and_reports_clipboard_failures(self):
        app = ReconKitMobile.__new__(ReconKitMobile)
        app.output = SimpleNamespace(text="risultato")
        app.status = SimpleNamespace(text="", color=None)

        with patch("reconkit.gui_kivy.Clipboard.copy") as copy:
            app._copy_output()
        copy.assert_called_once_with("risultato")
        self.assertIn("COPIATO", app.status.text)

        with patch("reconkit.gui_kivy.Clipboard.copy", side_effect=OSError("clipboard offline")):
            app._copy_output()
        self.assertIn("clipboard offline", app.status.text)

    def test_copy_without_result_is_explicit(self):
        app = ReconKitMobile.__new__(ReconKitMobile)
        app.output = SimpleNamespace(text="")
        app.status = SimpleNamespace(text="", color=None)

        app._copy_output()

        self.assertIn("Nessun risultato", app.status.text)


class TkFormScrollTests(unittest.TestCase):
    def test_sidebar_logo_resource_and_primary_palette_are_available(self):
        logo_path = logo_asset_path()
        icon_path = window_icon_asset_path()

        self.assertTrue(logo_path.is_file())
        self.assertEqual(logo_path.name, "logo_sidebar.png")
        with logo_path.open("rb") as logo_file:
            header = logo_file.read(24)
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", header[16:24]), (184, 120))
        self.assertTrue(icon_path.is_file())
        self.assertEqual(icon_path.name, "logo.png")
        with icon_path.open("rb") as icon_file:
            icon_header = icon_file.read(24)
        self.assertEqual(icon_header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", icon_header[16:24]), (434, 282))
        self.assertEqual(PALETTE["primary"], "#a78bfa")
        self.assertNotIn("cyan", PALETTE)

    def test_sidebar_loads_the_pre_scaled_asset_without_tk_subsampling(self):
        app = ReconKitDesktop.__new__(ReconKitDesktop)
        image = SimpleNamespace(width=lambda: 184, height=lambda: 120)

        with patch("reconkit.gui_tk.tk.PhotoImage", return_value=image) as photo_image:
            self.assertIs(app._load_logo(), image)

        photo_image.assert_called_once_with(file=str(logo_asset_path()))

    def test_window_icon_loads_the_original_asset_and_is_separately_retained(self):
        app = ReconKitDesktop.__new__(ReconKitDesktop)
        icon_image = SimpleNamespace(width=lambda: 434, height=lambda: 282)

        with patch("reconkit.gui_tk.tk.PhotoImage", return_value=icon_image) as photo_image:
            app.window_icon_image = app._load_window_icon()

        self.assertIs(app.window_icon_image, icon_image)
        photo_image.assert_called_once_with(file=str(window_icon_asset_path()))

    def test_unsupported_logo_loading_falls_back_without_raising(self):
        app = ReconKitDesktop.__new__(ReconKitDesktop)
        with patch("reconkit.gui_tk.tk.PhotoImage", side_effect=tk.TclError("unsupported image")):
            self.assertIsNone(app._load_logo())

    def test_unsupported_window_icon_loading_falls_back_without_raising(self):
        app = ReconKitDesktop.__new__(ReconKitDesktop)
        with patch("reconkit.gui_tk.tk.PhotoImage", side_effect=tk.TclError("unsupported image")):
            self.assertIsNone(app._load_window_icon())

    def test_live_logs_are_replaced_by_the_final_result(self):
        class FakeOutput:
            def __init__(self):
                self.text = ""

            def configure(self, **_kwargs):
                pass

            def delete(self, _start, _end):
                self.text = ""

            def insert(self, index, text):
                if index == "end":
                    self.text += text
                else:
                    self.text = text

            def see(self, _index):
                pass

        app = ReconKitDesktop.__new__(ReconKitDesktop)
        app.results = queue.Queue()
        app.root = SimpleNamespace(after=lambda *_args: None)
        app.run_button = SimpleNamespace(configure=lambda **_kwargs: None)
        app.state_label = SimpleNamespace(configure=lambda **_kwargs: None)
        app.status_detail = SimpleNamespace(configure=lambda **_kwargs: None)
        app.output_title = SimpleNamespace(configure=lambda **_kwargs: None)
        app.output = FakeOutput()
        app.running = True
        app._has_live_output = False

        app.results.put(("log", "Scansione avviata...\n"))
        app._poll_results()
        self.assertEqual(app.output.text, "Scansione avviata...\n")

        app.results.put(("done", True, "Risultato finale"))
        app._poll_results()
        self.assertEqual(app.output.text, "Risultato finale")
        self.assertFalse(app.running)

    def test_long_form_scrolls_without_hiding_actions_at_minimum_size(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest("Tk display unavailable: {}".format(exc))
        try:
            desktop = ReconKitDesktop(root)
            self.assertIsNotNone(desktop.logo_image)
            self.assertIsNotNone(desktop.window_icon_image)
            self.assertIsNotNone(desktop.logo_label)
            self.assertEqual(desktop.logo_label.winfo_manager(), "pack")
            root.geometry("860x620")
            root.update()
            self.assertEqual(desktop.logo_image.width(), 184)
            self.assertEqual(desktop.logo_image.height(), 120)
            self.assertEqual(desktop.window_icon_image.width(), 434)
            self.assertEqual(desktop.window_icon_image.height(), 282)
            self.assertEqual(desktop.logo_label.winfo_width(), 188)

            scroll_region = tuple(
                int(value) for value in desktop.form_canvas.cget("scrollregion").split())
            self.assertGreater(scroll_region[3], desktop.form_canvas.winfo_height())
            button_bottom = (
                desktop.run_button.winfo_rooty() - root.winfo_rooty()
                + desktop.run_button.winfo_height()
            )
            self.assertLessEqual(button_bottom, root.winfo_height())
        finally:
            root.destroy()

    def test_scroll_handler_supports_windows_and_linux_wheel_events(self):
        app = ReconKitDesktop.__new__(ReconKitDesktop)
        calls = []
        app.form_canvas = SimpleNamespace(
            yview_scroll=lambda amount, units: calls.append((amount, units)))

        for event, expected in (
            (SimpleNamespace(delta=120, num=None), -1),
            (SimpleNamespace(delta=-120, num=None), 1),
            (SimpleNamespace(delta=0, num=4), -1),
            (SimpleNamespace(delta=0, num=5), 1),
        ):
            self.assertEqual(app._scroll_form(event), "break")
            self.assertEqual(calls[-1], (expected, "units"))


if __name__ == "__main__":
    unittest.main()
