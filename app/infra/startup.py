"""Windows startup registration helpers."""

from __future__ import annotations

import subprocess
import sys
import traceback
from pathlib import Path


SHORTCUT_NAME = "Break Reminder App.lnk"


def get_startup_shortcut_path() -> Path:
    """Return the per-user Startup folder shortcut path."""
    startup_dir = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
    return startup_dir / SHORTCUT_NAME


def is_startup_enabled() -> bool:
    """Return whether startup shortcut currently exists."""
    return get_startup_shortcut_path().exists()


def apply_startup_setting(enabled: bool, app_root: Path | None = None) -> bool:
    """Enable or disable Windows startup shortcut."""
    if sys.platform != "win32":
        return False
    if enabled:
        return create_startup_shortcut(app_root=app_root)
    return remove_startup_shortcut()


def create_startup_shortcut(app_root: Path | None = None) -> bool:
    """Create a Startup .lnk file for this app."""
    if sys.platform != "win32":
        return False
    try:
        root = (app_root or _default_app_root()).resolve()
        shortcut_path = get_startup_shortcut_path()
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)

        target_path, arguments = _build_shortcut_target(root)
        script = _build_shortcut_powershell(
            shortcut_path=shortcut_path,
            target_path=target_path,
            arguments=arguments,
            working_dir=root,
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            startupinfo=_hidden_startupinfo(),
        )
        return shortcut_path.exists()
    except Exception:
        traceback.print_exc()
        return False


def remove_startup_shortcut() -> bool:
    """Remove Startup .lnk file when present."""
    if sys.platform != "win32":
        return False
    try:
        shortcut_path = get_startup_shortcut_path()
        if shortcut_path.exists():
            shortcut_path.unlink()
        return True
    except Exception:
        traceback.print_exc()
        return False


def _build_shortcut_target(app_root: Path) -> tuple[Path, str]:
    """Build shortcut target path and arguments for python/exe scenarios."""
    executable = Path(sys.executable).resolve()
    python_like = executable.stem.lower().startswith("python")
    if python_like:
        pythonw_path = executable.with_name("pythonw.exe")
        if pythonw_path.exists():
            executable = pythonw_path
        script_path = (app_root / "main.py").resolve()
        return executable, f'"{script_path}"'
    return executable, ""


def _build_shortcut_powershell(
    shortcut_path: Path,
    target_path: Path,
    arguments: str,
    working_dir: Path,
) -> str:
    """Build PowerShell code that creates a .lnk shortcut."""
    shortcut_s = _ps_quote(shortcut_path)
    target_s = _ps_quote(target_path)
    arguments_s = _ps_quote_raw(arguments)
    working_s = _ps_quote(working_dir)
    icon_s = _ps_quote_raw(f"{target_path},0")
    return "\n".join(
        [
            "$wsh = New-Object -ComObject WScript.Shell",
            f"$shortcut = $wsh.CreateShortcut('{shortcut_s}')",
            f"$shortcut.TargetPath = '{target_s}'",
            f"$shortcut.Arguments = '{arguments_s}'",
            f"$shortcut.WorkingDirectory = '{working_s}'",
            f"$shortcut.IconLocation = '{icon_s}'",
            "$shortcut.Save()",
        ]
    )


def _ps_quote(path_value: Path) -> str:
    """Escape path for single-quoted PowerShell string."""
    return str(path_value).replace("'", "''")


def _ps_quote_raw(value: str) -> str:
    """Escape plain string for single-quoted PowerShell string."""
    return value.replace("'", "''")


def _default_app_root() -> Path:
    """Resolve repository root from this module location."""
    return Path(__file__).resolve().parents[2]


def _hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    """Return hidden-window startup info for Windows subprocess."""
    startupinfo_cls = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_cls is None:
        return None
    startupinfo = startupinfo_cls()
    startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    startupinfo.wShowWindow = 0
    return startupinfo
