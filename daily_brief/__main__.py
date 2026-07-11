import argparse
from pathlib import Path

from .brief import build_daily_brief
from .renderer import DEFAULT_PRINTER_DEVICE, print_escpos, render_png, render_text
from .settings import load_env_file


def main() -> None:
    load_env_file()
    parser = argparse.ArgumentParser(description="Maak de Jos Daily Brief-proefbon.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/daily-brief.png"),
        help="Bestand waarin de PNG wordt opgeslagen.",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Toon de bon als tekst in plaats van een PNG te maken.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_receipt",
        help="Print de gemaakte bon via het raw ESC/POS-device.",
    )
    parser.add_argument(
        "--device",
        type=Path,
        default=DEFAULT_PRINTER_DEVICE,
        help="Raw printerdevice (standaard: /dev/usb/lp0).",
    )
    args = parser.parse_args()

    brief = build_daily_brief()

    if args.text:
        print(render_text(brief))
        return

    path = render_png(brief, args.output)
    print(f"Proefbon gemaakt: {path.resolve()}")
    if args.print_receipt:
        print_escpos(path, args.device)
        print(f"Bon geprint via: {args.device}")


if __name__ == "__main__":
    main()
