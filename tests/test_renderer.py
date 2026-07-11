import tempfile
import unittest
from datetime import date
from pathlib import Path

from PIL import Image

from daily_brief.renderer import (
    WIDTH,
    format_dutch_date,
    print_escpos,
    render_png,
    render_text,
)
from daily_brief.models import FormulaOneResult, SynologyStatus
from daily_brief.sample_data import make_sample_brief


class RendererTests(unittest.TestCase):
    def test_date_is_always_dutch(self) -> None:
        self.assertEqual(format_dutch_date(date(2026, 7, 2)), "donderdag 02-07-2026")

    def test_text_contains_main_sections(self) -> None:
        text = render_text(make_sample_brief())
        for heading in ("WEER", "AGENDA", "PRIO'S", "TELETEKST", "NIEUWS"):
            self.assertIn(heading, text)
        self.assertNotIn("FOCUS", text)

    def test_text_places_moon_at_bottom_before_quote(self) -> None:
        from daily_brief.models import MoonInsight

        brief = make_sample_brief()
        brief.moon = MoonInsight("Volle Maan", "Kreeft", "Intens.", "Rust.")

        text = render_text(brief)

        self.assertGreater(text.index("MAAN"), text.index("NIEUWS"))
        self.assertLess(text.index("MAAN"), text.index(brief.quote))

    def test_png_supports_birthdays_and_formula_one(self) -> None:
        brief = make_sample_brief()
        brief.birthdays = ["Anna"]
        brief.formula_one = FormulaOneResult(
            "Dutch Grand Prix",
            ["1. Lando Norris", "2. Max Verstappen", "3. Oscar Piastri"],
            "Max Verstappen: P2",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "brief.png"
            render_png(brief, output)
            self.assertTrue(output.exists())

    def test_text_hides_healthy_nas(self) -> None:
        brief = make_sample_brief()
        brief.synology_status = SynologyStatus(reachable=True, warnings=[])

        self.assertNotIn("NAS SECURITY", render_text(brief))

    def test_png_has_receipt_width(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "brief.png"
            render_png(make_sample_brief(), output)
            with Image.open(output) as image:
                self.assertEqual(image.width, WIDTH)
                self.assertGreater(image.height, image.width)

    def test_escpos_output_has_raster_feed_and_cut(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "brief.png"
            device = Path(directory) / "printer"
            Image.new("1", (16, 2), "white").save(image_path)

            print_escpos(image_path, device)

            output = device.read_bytes()
            self.assertTrue(output.startswith(b"\x1b@\x1dv0\x00"))
            self.assertTrue(output.endswith(b"\n" * 6 + b"\x1dV\x00"))

    def test_escpos_can_shift_raster_left(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "brief.png"
            device = Path(directory) / "printer"
            image = Image.new("1", (16, 1), "white")
            image.putpixel((8, 0), 0)
            image.save(image_path)

            print_escpos(image_path, device, horizontal_offset=-8)

            output = device.read_bytes()
            self.assertEqual(output[10:12], b"\x80\x00")


if __name__ == "__main__":
    unittest.main()
