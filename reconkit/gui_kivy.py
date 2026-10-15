"""Interfaccia touch Kivy per ReconKit (Android)."""
import queue
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from .gui_common import PALETTE, TOOLS, TOOL_BY_ID, android_unsupported_reason, execute_tool


def _color(value):
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)) + (1,)


class ReconKitMobile(App):
    title = "ReconKit"

    def build(self):
        Window.clearcolor = _color(PALETTE["background"])
        self.results = queue.Queue()
        self.controls = {}
        self.busy = False
        self.selected_id = TOOLS[0]["id"]
        self.root_box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(10))
        header.add_widget(Label(text="[b]RECONKIT[/b]", markup=True, color=_color(PALETTE["primary"]),
                               font_size="20sp", halign="left", valign="middle", size_hint_x=0.55))
        self.selector = Spinner(
            text=TOOL_BY_ID[self.selected_id]["title"],
            values=[spec["title"] for spec in TOOLS],
            size_hint_x=0.45, background_normal="", background_color=_color(PALETTE["panel_alt"]),
            color=_color(PALETTE["text"]), font_size="14sp",
        )
        self.selector.bind(text=self._on_select)
        header.add_widget(self.selector)
        self.root_box.add_widget(header)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.body = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None,
                              padding=(0, dp(2), 0, dp(10)))
        self.body.bind(minimum_height=self.body.setter("height"))
        self.scroll.add_widget(self.body)
        self.root_box.add_widget(self.scroll)
        Clock.schedule_interval(self._poll_results, 0.15)
        self._render_tool()
        return self.root_box

    def _on_select(self, _spinner, title):
        if self.busy:
            return
        for spec in TOOLS:
            if spec["title"] == title:
                self.selected_id = spec["id"]
                self._render_tool()
                return

    def _render_tool(self):
        spec = TOOL_BY_ID[self.selected_id]
        self.body.clear_widgets()
        self.controls.clear()
        self.body.add_widget(self._label(spec["title"], 22, PALETTE["text"], bold=True, height=dp(34)))
        self.body.add_widget(self._label(spec["description"], 14, PALETTE["muted"],
                                         height=dp(46), valign="top"))
        self.body.add_widget(self._label(
            "USO AUTORIZZATO · Usa ReconKit solo su sistemi e reti di tua proprietà o per cui hai permesso.",
            12, PALETTE["amber"], background="#332919", height=dp(58), padding=(dp(10), dp(8))))

        reason = android_unsupported_reason(self.selected_id)
        if self.selected_id == "traceroute":
            reason = "Richiede privilegi amministratore e socket ICMP raw; non disponibile nell'app Android."
        self.unsupported = bool(reason)
        if reason:
            self.body.add_widget(self._label("NON DISPONIBILE SU ANDROID · " + reason, 13,
                                             PALETTE["amber"], background="#332919", height=dp(68),
                                             padding=(dp(10), dp(8))))
        if spec.get("active"):
            self.body.add_widget(self._label(
                "SCANSIONE ATTIVA · Invia sonde di rete. Verifica di avere l'autorizzazione.",
                13, PALETTE["amber"], background="#332919", height=dp(58),
                padding=(dp(10), dp(8))))

        for field in spec.get("fields", []):
            name, label, kind, placeholder, _required = field[:5]
            default = field[5] if len(field) > 5 else ""
            if kind == "check":
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52),
                                spacing=dp(8))
                check = CheckBox(size_hint=(None, None), size=(dp(48), dp(48)),
                                 active=bool(default), color=_color(PALETTE["primary"]))
                row.add_widget(check)
                row.add_widget(self._label(label, 14, PALETTE["text"], height=dp(44)))
                self.controls[name] = check
                self.body.add_widget(row)
                continue

            self.body.add_widget(self._label(label, 13, PALETTE["muted"], height=dp(24)))
            multi = kind == "multiline"
            entry = TextInput(
                text=str(default), hint_text=placeholder, multiline=multi,
                password=(kind == "password"), write_tab=False,
                size_hint_y=None, height=dp(112 if multi else 48),
                padding=(dp(12), dp(10)), font_size="15sp",
                background_normal="", background_active="",
                background_color=_color(PALETTE["panel_alt"]),
                foreground_color=_color(PALETTE["text"]),
                hint_text_color=_color(PALETTE["muted"]),
                cursor_color=_color(PALETTE["primary"]),
            )
            self.controls[name] = entry
            self.body.add_widget(entry)

        actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(54), spacing=dp(10))
        self.run_button = Button(text="Esegui analisi", size_hint_x=0.68,
                                 background_normal="", background_color=_color(PALETTE["primary"]),
                                 color=_color("#071218"), font_size="16sp", bold=True,
                                 disabled=self.unsupported)
        self.run_button.bind(on_release=self._run_selected)
        actions.add_widget(self.run_button)
        clear_button = Button(text="Pulisci", size_hint_x=0.32,
                              background_normal="", background_color=_color(PALETTE["panel_alt"]),
                              color=_color(PALETTE["text"]), font_size="14sp")
        clear_button.bind(on_release=lambda *_: self._set_output(""))
        actions.add_widget(clear_button)
        self.body.add_widget(actions)
        self.status = self._label("PRONTO · output reale del modulo selezionato", 12,
                                  PALETTE["muted"], height=dp(28))
        self.body.add_widget(self.status)
        self.copy_button = Button(
            text="Copia risultato", size_hint_y=None, height=dp(56),
            background_normal="", background_color=_color(PALETTE["panel_alt"]),
            color=_color(PALETTE["text"]), font_size="16sp",
        )
        self.copy_button.bind(on_release=self._copy_output)
        self.body.add_widget(self.copy_button)
        self.output = TextInput(text="", readonly=True, multiline=True, size_hint_y=None,
                                height=dp(240), padding=(dp(12), dp(12)), font_size="13sp",
                                background_normal="", background_active="",
                                background_color=_color("#111922"),
                                foreground_color=_color("#d5e1e9"),
                                cursor_color=_color(PALETTE["primary"]))
        self.body.add_widget(self.output)

    def _label(self, text, size, color, height, bold=False, background=None, padding=(0, 0),
               valign="middle"):
        label = Label(text=text, markup=True, size_hint=(1, None), height=height,
                      color=_color(color), font_size="{}sp".format(size),
                      bold=bold, halign="left", valign=valign,
                      padding=padding, text_size=(None, None))
        label._minimum_height = height
        label.bind(width=self._update_label_width, texture_size=self._update_label_height)
        self._update_label_width(label, label.width)
        if background:
            from kivy.graphics import Color, Rectangle
            with label.canvas.before:
                Color(*_color(background))
                label._background = Rectangle(pos=label.pos, size=label.size)
            label.bind(pos=lambda widget, pos: setattr(widget._background, "pos", pos),
                       size=lambda widget, size: setattr(widget._background, "size", size))
        return label

    @staticmethod
    def _update_label_width(label, width):
        horizontal_padding = label.padding[0] * 2
        label.text_size = (max(0, width - horizontal_padding), None)

    @staticmethod
    def _update_label_height(label, texture_size):
        vertical_padding = label.padding[1] * 2
        label.height = max(label._minimum_height, texture_size[1] + vertical_padding)

    def _collect_values(self):
        values = {}
        for name, control in self.controls.items():
            values[name] = control.active if isinstance(control, CheckBox) else control.text
        return values

    def _run_selected(self, *_):
        if self.busy or self.unsupported:
            return
        values = self._collect_values()
        spec = TOOL_BY_ID[self.selected_id]
        missing = []
        for field in spec.get("fields", []):
            name, label, kind, _placeholder, required = field[:5]
            if required and kind != "check" and not str(values.get(name, "")).strip():
                missing.append(label)
        if missing:
            self.status.text = "ERRORE · Compila: " + ", ".join(missing)
            self.status.color = _color(PALETTE["red"])
            return
        self.busy = True
        self.run_button.disabled = True
        self.status.text = "IN ESECUZIONE · elaborazione in background"
        self.status.color = _color(PALETTE["amber"])
        self._set_output("Operazione avviata…")
        threading.Thread(target=self._execute, args=(self.selected_id, values), daemon=True).start()

    def _execute(self, tool_id, values):
        try:
            self.results.put((True, execute_tool(tool_id, values)))
        except Exception as exc:
            self.results.put((False, str(exc)))

    def _poll_results(self, _dt):
        try:
            success, text = self.results.get_nowait()
        except queue.Empty:
            return
        self.busy = False
        self.run_button.disabled = self.unsupported
        self.status.text = "COMPLETATO · risultati restituiti da ReconKit" if success else "ERRORE · " + text
        self.status.color = _color(PALETTE["green"] if success else PALETTE["red"])
        self._set_output(text)

    def _set_output(self, text):
        self.output.text = text

    def _copy_output(self, *_):
        text = self.output.text
        if not text:
            self.status.text = "ERRORE · Nessun risultato da copiare"
            self.status.color = _color(PALETTE["red"])
            return
        try:
            Clipboard.copy(text)
        except Exception as exc:
            self.status.text = "ERRORE · Copia non riuscita: {}".format(exc)
            self.status.color = _color(PALETTE["red"])
            return
        self.status.text = "COPIATO · Risultato negli appunti"
        self.status.color = _color(PALETTE["green"])


def main():
    ReconKitMobile().run()


if __name__ == "__main__":
    main()
