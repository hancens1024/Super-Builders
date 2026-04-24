#!/usr/bin/env python3

from pathlib import Path
import re
import sys


def must_replace(text: str, pattern: str, repl: str, description: str) -> str:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Failed to patch {description}")
    return new_text


def ensure_line_after(text: str, anchor: str, line: str) -> str:
    if line in text:
        return text
    pattern = rf"(^\s*{re.escape(anchor)}\s*$)"
    repl = rf"\1\n{line}"
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Failed to insert line after {anchor}")
    return new_text


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: patch-anykernel3-init-boot-compat.py <anykernel.sh>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    text = path.read_text()

    text = must_replace(
        text,
        r"^is_slot_device=.*$",
        "is_slot_device=1",
        "is_slot_device",
    )
    text = must_replace(
        text,
        r"^patch_vbmeta_flag=.*$",
        "patch_vbmeta_flag=0",
        "patch_vbmeta_flag",
    )
    text = ensure_line_after(text, "patch_vbmeta_flag=0", "no_vbmeta_partition_patch=1")

    original_boot_logic = """# boot install
split_boot

if [ -f "$SPLITIMG/ramdisk.cpio" ]; then
    unpack_ramdisk
    write_boot
else
    flash_boot
fi"""

    replacement_boot_logic = """# boot install
if [ -L "/dev/block/bootdevice/by-name/init_boot_a" ] || [ -L "/dev/block/by-name/init_boot_a" ]; then
    # Devices with a dedicated init_boot partition are more stable if boot is flashed
    # directly instead of unpacking/repacking the ramdisk.
    split_boot
    flash_boot
else
    split_boot

    if [ -f "$SPLITIMG/ramdisk.cpio" ]; then
        unpack_ramdisk
        write_boot
    else
        flash_boot
    fi
fi"""

    if original_boot_logic not in text:
        raise RuntimeError("Failed to patch boot install logic")

    text = text.replace(original_boot_logic, replacement_boot_logic, 1)
    path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
