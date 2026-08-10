"""Portable linked-path expansion and validation."""

from __future__ import annotations

import os
import re
from pathlib import Path

import bpy

VARIABLE_PATTERN = re.compile(r"%([^%]+)%")
SUPPORTED_EXTENSIONS = {".fbx", ".obj"}


def addon_preferences():
    addon_id = __package__
    addon = bpy.context.preferences.addons.get(addon_id)
    return addon.preferences if addon else None


def local_variables() -> dict[str, str]:
    preferences = addon_preferences()
    if not preferences:
        return {}
    return {
        item.name.casefold(): item.value
        for item in preferences.variables
        if item.name.strip()
    }


def expand_variables(raw_path: str) -> str:
    variables = local_variables()

    def replace(match: re.Match) -> str:
        name = match.group(1)
        return variables.get(name.casefold(), os.environ.get(name, match.group(0)))

    return VARIABLE_PATTERN.sub(replace, raw_path.strip())


def resolved_path(raw_path: str) -> str:
    expanded = expand_variables(raw_path)
    if not expanded:
        return ""
    return str(Path(bpy.path.abspath(expanded)).expanduser().resolve(strict=False))


def relative_path(raw_path: str) -> str:
    if not bpy.data.filepath:
        raise ValueError("Save the .blend file before creating a relative link")
    return bpy.path.relpath(resolved_path(raw_path))


def validation_error(raw_path: str, require_exists: bool = True) -> str | None:
    path = resolved_path(raw_path)
    if not path:
        return "No linked file path is set"
    if VARIABLE_PATTERN.search(expand_variables(raw_path)):
        return "The path contains an undefined %VARIABLE%"
    if Path(path).suffix.lower() not in SUPPORTED_EXTENSIONS:
        return "Only .fbx and .obj files are supported"
    if require_exists and not Path(path).is_file():
        return "The linked file does not exist"
    return None

