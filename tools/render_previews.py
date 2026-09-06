"""Render theme previews from the actual login HTML with headless Chrome."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
VIEWPORT = (360, 640)


def chrome_path() -> Path:
    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError("Chrome or Edge is required to render previews")


def prepared_html(source: str, *, transparent: bool) -> str:
    source = source.replace("{{SHOP_NAME}}", "Shop Name")
    source = re.sub(r"\\?\$\((username|error)\)", "", source)
    source = re.sub(r"\\?\$\([^)]+\)", "#", source)
    background_override = (
        "background:transparent!important;background-image:none!important;"
        if transparent
        else ""
    )
    override = (
        "<style>html,body{width:360px!important;max-width:360px!important;"
        f"min-height:640px!important;{background_override}}}"
        ".wrap{width:324px!important;max-width:324px!important}"
        "body>.card{width:324px!important;max-width:324px!important}</style>"
    )
    source = source.replace("</head>", f"{override}</head>", 1)
    return source


def render_html(source: str, output: Path, *, transparent: bool) -> None:
    browser = chrome_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="portal-preview-") as temporary:
        temporary_path = Path(temporary)
        html_path = temporary_path / "preview.html"
        html_path.write_text(
            prepared_html(source, transparent=transparent),
            encoding="utf-8",
        )
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-sandbox",
            "--force-device-scale-factor=1",
            f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}",
            f"--user-data-dir={temporary_path / 'profile'}",
            f"--screenshot={output.resolve()}",
        ]
        if transparent:
            command.append("--default-background-color=00000000")
        command.append(html_path.resolve().as_uri())
        subprocess.run(command, check=True, capture_output=True)
    with Image.open(output) as rendered:
        if rendered.size != VIEWPORT:
            rendered.resize(VIEWPORT, Image.Resampling.LANCZOS).save(output)


def render_theme_previews() -> None:
    for login_path in sorted(ROOT.glob("themes/*/*/login.html")):
        source = login_path.read_text(encoding="utf-8")
        render_html(source, login_path.with_name("preview.png"), transparent=False)
        render_html(
            source,
            login_path.with_name("preview-overlay.png"),
            transparent=True,
        )


if __name__ == "__main__":
    render_theme_previews()
