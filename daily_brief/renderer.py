import re
from pathlib import Path
from typing import Iterable, List

from PIL import Image, ImageDraw, ImageFont

from .models import DailyBrief


WIDTH = 576
MARGIN = 32
CONTENT_WIDTH = WIDTH - (2 * MARGIN)
DEFAULT_PRINTER_DEVICE = Path("/dev/usb/lp0")
PRINT_HORIZONTAL_OFFSET = -24
DUTCH_WEEKDAYS = (
    "maandag",
    "dinsdag",
    "woensdag",
    "donderdag",
    "vrijdag",
    "zaterdag",
    "zondag",
)


def format_dutch_date(value) -> str:
    return f"{DUTCH_WEEKDAYS[value.weekday()]} {value:%d-%m-%Y}"


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        proposal = f"{current} {word}".strip()
        if draw.textbbox((0, 0), proposal, font=font)[2] <= CONTENT_WIDTH:
            current = proposal
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_text(brief: DailyBrief) -> str:
    birthdays = "\n".join(f"- {name}" for name in brief.birthdays)
    moon = ""
    if brief.moon:
        moon_lines = [
            f"{brief.moon.phase_name} in {brief.moon.zodiac_sign}",
            brief.moon.summary,
            f"Doe: {brief.moon.tip}",
        ]
        if brief.moon.personal_note:
            moon_lines.append(brief.moon.personal_note)
        moon = "\n".join(moon_lines)
    formula_one = ""
    if brief.formula_one:
        formula_one = "\n".join(
            [brief.formula_one.race_name, *brief.formula_one.top_three, brief.formula_one.max_result]
        )
    agenda = "\n".join(
        f"{item.time}  {item.title}" + (f" ({item.location})" if item.location else "")
        for item in brief.agenda
    ) or "Geen afspraken"
    tasks = (
        "\n".join(f"{'!' if task.important else '-'} {task.title}" for task in brief.tasks)
        or "Geen Q1-prio's"
    )
    teletekst = (
        "\n".join(f"- {headline}" for headline in brief.teletekst)
        or "Geen Teletekst-headlines beschikbaar"
    )
    news = (
        "\n".join(
            f"- {item.title}\n{item.summary}".rstrip()
            for item in brief.news
        )
        or "Geen AI-nieuws beschikbaar"
    )
    if brief.synology_status and brief.synology_status.reachable:
        storage = (
            f"Opslag: {brief.synology_status.storage_percent}% gebruikt"
            if brief.synology_status.storage_percent is not None
            else "Opslaggebruik onbekend"
        )
        warnings = (
            ", ".join(brief.synology_status.warnings)
            if brief.synology_status.warnings
            else "Geen waarschuwingen"
        )
        nas = f"Online\n{storage}\n{warnings}"
    else:
        nas = "Niet bereikbaar"
    sections = [
            brief.greeting,
            format_dutch_date(brief.day),
            f"JARIG VANDAAG\n{birthdays}" if birthdays else "",
            f"FORMULE 1\n{formula_one}" if formula_one else "",
            (
                f"WEER{f' - {brief.weather.location}' if brief.weather.location else ''}\n"
                f"{brief.weather.summary} | Kans op regen: {brief.weather.rain_chance}%\n"
                f"{brief.weather.low_c} <-------------------> {brief.weather.high_c} C"
            ),
            f"AGENDA\n{agenda}",
            f"PRIO'S\n{tasks}",
            f"TELETEKST\n{teletekst}",
            f"NIEUWS\n{news}",
            f"NAS SECURITY\n{nas}"
            if brief.synology_status
            and brief.synology_status.reachable
            and brief.synology_status.warnings
            else "",
            f"MAAN\n{moon}" if moon else "",
            brief.quote,
    ]
    return "\n\n".join(section for section in sections if section)


def render_png(brief: DailyBrief, output: Path) -> Path:
    title_font = _font(34, bold=True)
    date_font = _font(22)
    heading_font = _font(23, bold=True)
    body_font = _font(22)
    small_font = _font(18)

    canvas = Image.new("L", (WIDTH, 3000), "white")
    draw = ImageDraw.Draw(canvas)
    y = 34

    def centered(text: str, font: ImageFont.ImageFont, gap: int = 8) -> None:
        nonlocal y
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((WIDTH - (box[2] - box[0])) / 2, y), text, fill="black", font=font)
        y += box[3] - box[1] + gap

    def line(gap: int = 18) -> None:
        nonlocal y
        draw.line((MARGIN, y, WIDTH - MARGIN, y), fill="black", width=2)
        y += gap

    def heading(text: str) -> None:
        nonlocal y
        y += 8
        draw.text((MARGIN, y), text.upper(), fill="black", font=heading_font)
        y += 36

    def paragraph(text: str, font: ImageFont.ImageFont = body_font, indent: int = 0) -> None:
        nonlocal y
        for wrapped_line in _wrap(draw, text, font):
            draw.text((MARGIN + indent, y), wrapped_line, fill="black", font=font)
            y += 30
        y += 5

    def weather_range() -> None:
        nonlocal y
        low = f"{brief.weather.low_c}°"
        high = f"{brief.weather.high_c}°"
        low_box = draw.textbbox((0, 0), low, font=body_font)
        high_box = draw.textbbox((0, 0), high, font=body_font)
        low_width = low_box[2] - low_box[0]
        high_width = high_box[2] - high_box[0]
        draw.text((MARGIN, y), low, fill="black", font=body_font)
        draw.text((WIDTH - MARGIN - high_width, y), high, fill="black", font=body_font)
        line_y = y + 15
        start_x = MARGIN + low_width + 18
        end_x = WIDTH - MARGIN - high_width - 18
        draw.line((start_x, line_y, end_x, line_y), fill="black", width=2)
        draw.ellipse((start_x - 3, line_y - 3, start_x + 3, line_y + 3), fill="black")
        draw.ellipse((end_x - 3, line_y - 3, end_x + 3, line_y + 3), fill="black")
        y += 32
        draw.text((MARGIN, y), "min", fill="black", font=small_font)
        max_box = draw.textbbox((0, 0), "max", font=small_font)
        draw.text((WIDTH - MARGIN - (max_box[2] - max_box[0]), y), "max", fill="black", font=small_font)
        y += 34

    def teletekst_row(text: str) -> None:
        nonlocal y
        match = re.match(r"^(.*)\s+(\d{3})$", text)
        if not match:
            paragraph(f"- {text}", small_font)
            return
        title, page = match.groups()
        page_box = draw.textbbox((0, 0), page, font=small_font)
        page_width = page_box[2] - page_box[0]
        max_title_width = CONTENT_WIDTH - page_width - 20
        words = f"- {title}".split()
        current = ""
        lines: List[str] = []
        for word in words:
            proposal = f"{current} {word}".strip()
            if draw.textbbox((0, 0), proposal, font=small_font)[2] <= max_title_width:
                current = proposal
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for index, line_text in enumerate(lines or [""]):
            draw.text((MARGIN, y), line_text, fill="black", font=small_font)
            if index == 0:
                draw.text(
                    (WIDTH - MARGIN - page_width, y),
                    page,
                    fill="black",
                    font=small_font,
                )
            y += 26
        y += 4

    centered("JOS DAILY BRIEF", title_font)
    centered(format_dutch_date(brief.day), date_font, 18)
    line()
    centered(brief.greeting, heading_font, 16)

    if brief.birthdays:
        heading("Jarig")
        for name in brief.birthdays:
            paragraph(name, heading_font)

    heading(
        f"Weer - {brief.weather.location}"
        if brief.weather.location
        else "Weer"
    )
    paragraph(brief.weather.summary, body_font)
    paragraph(f"Kans op regen: {brief.weather.rain_chance}%", small_font)
    weather_range()

    if brief.formula_one:
        heading("Formule 1")
        paragraph(brief.formula_one.race_name, heading_font)
        for result in brief.formula_one.top_three:
            paragraph(result)
        paragraph(brief.formula_one.max_result, heading_font)

    heading("Agenda")
    if brief.agenda:
        for item in brief.agenda:
            paragraph(f"{item.time}  {item.title}", body_font)
            if item.location:
                paragraph(f"        {item.location}", small_font)
    else:
        paragraph("Geen afspraken")

    heading("Prio's")
    if brief.tasks:
        for task in brief.tasks:
            paragraph(f"- {task.title}")
    else:
        paragraph("Geen Q1-prio's")

    heading("Teletekst")
    if brief.teletekst:
        for headline in brief.teletekst:
            teletekst_row(headline)
    else:
        paragraph("Geen Teletekst-headlines beschikbaar")

    heading("Nieuws")
    if brief.news:
        for item in brief.news:
            paragraph(item.title, heading_font)
            if item.summary:
                for summary_line in item.summary.splitlines():
                    paragraph(summary_line, small_font)
    else:
        paragraph("Geen AI-nieuws beschikbaar")
    line()

    if (
        brief.synology_status
        and brief.synology_status.reachable
        and brief.synology_status.warnings
    ):
        heading("NAS security")
        paragraph(", ".join(brief.synology_status.warnings), heading_font)

    if brief.moon:
        heading("Maan")
        paragraph(f"{brief.moon.phase_name} in {brief.moon.zodiac_sign}", heading_font)
        paragraph(brief.moon.summary)
        paragraph(f"Doe: {brief.moon.tip}", small_font)
        if brief.moon.personal_note:
            paragraph(brief.moon.personal_note, small_font)

    line()
    centered(brief.quote, small_font, 20)
    centered("JOS DAILY BRIEF", small_font)

    receipt = canvas.crop((0, 0, WIDTH, min(y + 32, canvas.height)))
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt.save(output, format="PNG", optimize=True)
    return output


def print_escpos(
    image_path: Path,
    device: Path = DEFAULT_PRINTER_DEVICE,
    horizontal_offset: int = PRINT_HORIZONTAL_OFFSET,
) -> None:
    with Image.open(image_path) as source:
        source_image = source.convert("1")
        image = Image.new("1", source_image.size, "white")
        image.paste(source_image, (horizontal_offset, 0))
        width_bytes = (image.width + 7) // 8
        pixels = image.load()

        with device.open("wb") as printer:
            printer.write(b"\x1b@")
            for top in range(0, image.height, 256):
                height = min(256, image.height - top)
                raster = bytearray()
                for y in range(top, top + height):
                    for byte_x in range(width_bytes):
                        value = 0
                        for bit in range(8):
                            x = byte_x * 8 + bit
                            if x < image.width and pixels[x, y] == 0:
                                value |= 1 << (7 - bit)
                        raster.append(value)
                printer.write(
                    b"\x1dv0\x00"
                    + width_bytes.to_bytes(2, "little")
                    + height.to_bytes(2, "little")
                    + raster
                )
            printer.write(b"\n" * 6 + b"\x1dV\x00")
