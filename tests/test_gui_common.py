import unittest
from unittest.mock import patch

from reconkit.gui_common import (
    TOOL_BY_ID,
    android_unsupported_reason,
    build_argv,
    execute_tool,
)
class GuiDispatchTests(unittest.TestCase):
    def test_builds_cli_arguments_for_portscan(self):
        argv = build_argv("portscan", {
            "target": "192.0.2.8",
            "ports": "80,443",
            "threads": "12",
            "udp": True,
            "banners": False,
            "ping_only": False,
            "no_ping": True,
        })
        self.assertEqual(argv, ["portscan", "192.0.2.8", "-p", "80,443", "-t", "12", "-u", "-Pn"])

    def test_all_cli_tools_resolve_in_existing_parser(self):
        from reconkit.cli import build_parser

        parser = build_parser()
        for spec in TOOL_BY_ID.values():
            if spec.get("crypto"):
                continue
            with self.subTest(tool=spec["id"]):
                values = {field[0]: (field[5] if len(field) > 5 else "test") for field in spec["fields"]}
                for name, *_ in spec["fields"]:
                    if isinstance(values[name], bool):
                        values[name] = False
                    elif not values[name]:
                        values[name] = "test"
                parsed = parser.parse_args(build_argv(spec["id"], values))
                self.assertEqual(parsed.command, spec["id"])
                self.assertTrue(callable(parsed.func))

    def test_crypto_round_trip_uses_direct_api(self):
        token = execute_tool("encrypt", {"text": "testo privato", "key": "chiave di test"})
        self.assertNotEqual(token, "testo privato")
        self.assertEqual(execute_tool("decrypt", {"text": token, "key": "chiave di test"}),
                         "testo privato")

    def test_crypto_rejects_empty_key(self):
        with self.assertRaises(ValueError):
            execute_tool("encrypt", {"text": "testo", "key": ""})

    def test_generation_length_is_bounded(self):
        with self.assertRaises(ValueError):
            execute_tool("genkey", {"length": "4"})
        key = execute_tool("genkey", {"length": "32"})
        self.assertEqual(len(key), 32)

    def test_android_restrictions_are_explicit(self):
        self.assertTrue(android_unsupported_reason("traceroute"))
        self.assertTrue(android_unsupported_reason("lanscan"))
        self.assertIsNone(android_unsupported_reason("dns"))

    def test_dispatch_captures_cli_output(self):
        class FakeArgs:
            func = staticmethod(lambda _args: print("risultato reale"))

        class FakeParser:
            def parse_args(self, _argv):
                return FakeArgs()

        with patch("reconkit.gui_common.build_parser", return_value=FakeParser()):
            self.assertEqual(execute_tool("whois", {"domain": "example.com"}), "risultato reale")

    def test_dispatch_streams_live_output_and_returns_final_result(self):
        class FakeArgs:
            func = staticmethod(lambda _args: (print("fase 1"), print("fase 2")))

        class FakeParser:
            def parse_args(self, _argv):
                return FakeArgs()

        chunks = []
        with patch("reconkit.gui_common.build_parser", return_value=FakeParser()):
            result = execute_tool(
                "whois", {"domain": "example.com"}, on_output=chunks.append)

        self.assertEqual("".join(chunks), "fase 1\nfase 2\n")
        self.assertEqual(result, "fase 1\nfase 2")

    def test_invalid_cli_option_returns_visible_error(self):
        with self.assertRaisesRegex(ValueError, "invalid float value"):
            execute_tool("portscan", {"target": "example.com", "timeout": "not-a-number"})


if __name__ == "__main__":
    unittest.main()
