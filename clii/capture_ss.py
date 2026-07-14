# -*- coding: utf-8 -*-
"""Capture real TangCLI output and render as terminal-style PNG screenshots."""
import subprocess
import os, sys

os.chdir(r"C:\Users\Administrator\Desktop\All Mix\clii")
OUT_DIR = r"C:\Users\Administrator\Desktop\All Mix\clii\cli_ops\screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = None
for p in [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf", r"C:\Windows\Fonts\msgothic.ttf"]:
    if os.path.exists(p):
        FONT_PATH = p
        break

def run_cmd(cmd_args):
    """Run a TangCLI command and return stdout lines."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Remove Rich formatting for clean capture
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "cli_ops.cli_main"] + cmd_args,
        capture_output=True, timeout=15, env=env,
        cwd=r"C:\Users\Administrator\Desktop\All Mix\clii",
        encoding="utf-8", errors="replace"
    )
    # Strip log lines starting with timestamp
    lines = []
    for line in (result.stdout + result.stderr).split("\n"):
        if line.strip().startswith("202") and "[INFO]" in line:
            continue
        if line.strip().startswith("202") and "[ERROR]" in line:
            continue
        lines.append(line)
    return "\n".join(lines).strip()

def render(text, name, title="tang-cli"):
    lines = text.split("\n")
    try:
        font = ImageFont.truetype(FONT_PATH, 14) if FONT_PATH else ImageFont.load_default()
        font_title = ImageFont.truetype(FONT_PATH, 12) if FONT_PATH else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
        font_title = ImageFont.load_default()

    img_w = 900
    line_h = 20
    padding = 20
    title_h = 30
    img_h = title_h + len(lines) * line_h + padding * 2
    img_h = min(img_h, 8000)

    img = Image.new("RGB", (img_w, img_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, img_w, title_h], fill=(60, 60, 60))
    try:
        draw.text((10, 7), title, fill=(200, 200, 200), font=font_title)
    except Exception:
        draw.text((10, 7), title, fill=(200, 200, 200))

    y = title_h + padding
    for line in lines:
        if y > img_h - padding:
            break
        clean = ""
        i = 0
        while i < len(line):
            if line[i] in ("\033", "\x1b"):
                j = i + 1
                while j < len(line) and line[j] != "m":
                    j += 1
                if j < len(line):
                    i = j + 1
                else:
                    break
            else:
                clean += line[i]
                i += 1
        clean = clean.rstrip()
        if not clean:
            y += line_h
            continue
        try:
            draw.text((padding, y), clean, fill=(220, 220, 220), font=font)
        except Exception:
            draw.text((padding, y), clean, fill=(220, 220, 220))
        y += line_h

    path = os.path.join(OUT_DIR, name)
    img.save(path, "PNG")
    print(f"  {name} ({img_w}x{img_h})")

# ── Capture all screenshots ──
print("Capturing TangCLI screenshots...")

print("\n[1/10] help")
render(run_cmd(["help"]), "01_help.png", "tang-cli help")

print("[2/10] status")
render(run_cmd(["status"]), "02_status.png", "tang-cli status")

print("[3/10] config-info")
render(run_cmd(["config-info"]), "03_config_info.png", "tang-cli config-info")

print("[4/10] health")
render(run_cmd(["health"]), "04_health.png", "tang-cli health")

print("[5/10] scan")
render(run_cmd(["scan"]), "05_scan.png", "tang-cli scan")

print("[6/10] list-exports")
render(run_cmd(["list-exports"]), "06_list_exports.png", "tang-cli list-exports")

print("[7/10] check-rag")
render(run_cmd(["check-rag"]), "07_check_rag.png", "tang-cli check-rag")

print("[8/10] monitor-snap")
render(run_cmd(["monitor-snap"]), "08_monitor_snap.png", "tang-cli monitor-snap")

print("[9/10] test")
render(run_cmd(["test"]), "09_test.png", "tang-cli test")

print("[10/10] report")
render(run_cmd(["report"]), "10_report.png", "tang-cli report")

print(f"\nDone! {len(os.listdir(OUT_DIR))} screenshots in {OUT_DIR}")
