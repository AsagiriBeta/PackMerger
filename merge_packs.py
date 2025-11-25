#!/usr/bin/env python3
"""
Minecraft resource pack merger

Merges multiple resource packs (directories or zip files) into a single output pack with controlled priority.
Default behavior autodetects all valid resource pack folders in the current directory and merges them alphabetically.

Rules:
- File-level last-wins for non-JSON files and JSON files not explicitly handled.
- JSON smart merges for:
  * assets/*/lang/*.json            => dict merge, later packs override keys.
  * assets/*/sounds.json            => dict merge, later packs override keys.
  * assets/*/font/*.json            => merge providers arrays + dedupe.
  * assets/*/atlases/*.json         => merge sources arrays + dedupe.
  * data/*/tags/**/*.json           => union values arrays + dedupe.
- pack.png comes from highest priority pack (if present).
- pack.mcmeta generated with max pack_format (or --pack-format) and descriptive merged description (or --description).

Usage:
  python3 merge_packs.py \
      --output merged_pack \
      --packs "pack1" "pack2" "pack3" \
      --clean --summary

You can also run without --packs to autodetect all resource pack folders.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, Optional
from fnmatch import fnmatch


DEFAULT_EXCLUDES = {".DS_Store", "Thumbs.db", "desktop.ini"}


@dataclass
class PackInfo:
    path: Path
    name: str
    pack_format: Optional[int]
    description: Optional[str]
    has_pack_png: bool
    is_temp: bool = False  # Track if this is from a temp extracted zip


def is_valid_resource_pack(path: Path) -> bool:
    """Check if a directory is a valid Minecraft resource pack."""
    if not path.is_dir():
        return False
    # Must have pack.mcmeta to be a valid resource pack
    meta_path = path / "pack.mcmeta"
    if not meta_path.exists():
        return False
    # Try to read it to ensure it's valid JSON
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            # Should have pack.pack_format at minimum
            if isinstance(data, dict) and "pack" in data:
                return True
    except (json.JSONDecodeError, OSError):
        pass
    return False


def extract_zip_pack(zip_path: Path, temp_dir: Path) -> Optional[Path]:
    """Extract a zip file to a temporary directory if it's a valid resource pack."""
    try:
        extract_path = temp_dir / zip_path.stem
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_path)
        # Check if it's valid at root
        if is_valid_resource_pack(extract_path):
            return extract_path
        # Sometimes the pack is nested in a subfolder - search recursively up to 3 levels deep
        def find_pack_recursive(base: Path, max_depth: int = 3, current_depth: int = 0) -> Optional[Path]:
            if current_depth >= max_depth:
                return None
            for child in base.iterdir():
                if child.is_dir():
                    if is_valid_resource_pack(child):
                        return child
                    # Recurse into subdirectory
                    found = find_pack_recursive(child, max_depth, current_depth + 1)
                    if found:
                        return found
            return None
        return find_pack_recursive(extract_path)
    except (zipfile.BadZipFile, OSError) as e:
        sys.stderr.write(f"WARNING: Failed to extract {zip_path}: {e}\n")
    return None


def detect_packs(base: Path, temp_dir: Optional[Path] = None) -> List[Path]:
    """
    Autodetect all valid resource packs in the base directory.
    Returns them sorted alphabetically by name.
    Also handles .zip files if temp_dir is provided.
    """
    found = []

    # Find all directories that are valid resource packs
    for item in base.iterdir():
        if item.is_dir() and is_valid_resource_pack(item):
            # Skip common output directories
            if item.name.startswith("merged_pack"):
                continue
            found.append(item)
        elif temp_dir and item.is_file() and item.suffix.lower() == ".zip":
            # Try to extract and validate zip files
            extracted = extract_zip_pack(item, temp_dir)
            if extracted:
                found.append(extracted)

    # Sort alphabetically for consistent ordering
    found.sort(key=lambda p: p.name.lower())
    return found


def read_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        sys.stderr.write(f"WARNING: Failed to parse JSON {path}: {e}\n")
        return None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")




def load_pack_info(path: Path) -> PackInfo:
    meta_path = path / "pack.mcmeta"
    meta = read_json(meta_path)
    pack_format = None
    description = None
    if isinstance(meta, dict):
        pack = meta.get("pack")
        if isinstance(pack, dict):
            pf = pack.get("pack_format")
            if isinstance(pf, int):
                pack_format = pf
            description = pack.get("description")
    return PackInfo(
        path=path,
        name=path.name,
        pack_format=pack_format,
        description=str(description) if description is not None else None,
        has_pack_png=(path / "pack.png").exists(),
    )


def is_lang_file(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 4 and parts[0] == "assets" and parts[2] == "lang" and rel.suffix == ".json"


def is_sounds_json(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 3 and parts[0] == "assets" and parts[2] == "sounds.json"


def is_font_json(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 4 and parts[0] == "assets" and parts[2] == "font" and rel.suffix == ".json"


def is_atlases_json(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 4 and parts[0] == "assets" and parts[2] == "atlases" and rel.suffix == ".json"


def is_tag_file(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 4 and parts[0] == "data" and parts[2] == "tags" and rel.suffix == ".json"


@dataclass
class MergeStats:
    copied: int = 0
    overwritten: int = 0
    merged_json: int = 0
    skipped: int = 0
    errors: int = 0


class Merger:
    def __init__(self, packs: List[PackInfo], out_dir: Path, dry_run: bool = False, clean: bool = False,
                 exclude_patterns: Optional[List[str]] = None,
                 pack_format_override: Optional[int] = None,
                 description_override: Optional[str] = None):
        self.packs = packs
        self.out_dir = out_dir
        self.dry_run = dry_run
        self.clean = clean
        self.stats = MergeStats()
        self.exclude_patterns = exclude_patterns or []
        self.pack_format_override = pack_format_override
        self.description_override = description_override

    def run(self) -> None:
        if self.clean and self.out_dir.exists():
            if self.dry_run:
                print(f"[dry-run] Would remove output directory: {self.out_dir}")
            else:
                shutil.rmtree(self.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self._write_pack_png()
        self._write_pack_mcmeta()

        # Merge assets and data
        handled_rel_paths: set[Path] = set()
        for pack in self.packs:
            for rel_path in self._iter_payload_files(pack.path):
                if self._is_excluded(rel_path):
                    self.stats.skipped += 1
                    continue
                out_path = self.out_dir / rel_path
                if is_lang_file(rel_path):
                    self._merge_lang_file(pack.path / rel_path, out_path)
                elif is_sounds_json(rel_path):
                    self._merge_sounds_json(pack.path / rel_path, out_path)
                elif is_font_json(rel_path):
                    self._merge_font_json(pack.path / rel_path, out_path)
                elif is_atlases_json(rel_path):
                    self._merge_atlases_json(pack.path / rel_path, out_path)
                elif is_tag_file(rel_path):
                    self._merge_tag_json(pack.path / rel_path, out_path)
                else:
                    self._copy_last_wins(pack.path / rel_path, out_path)
                handled_rel_paths.add(rel_path)

    def _is_excluded(self, rel: Path) -> bool:
        name = rel.name
        if name in DEFAULT_EXCLUDES:
            return True
        rel_str = str(rel)
        for pat in self.exclude_patterns:
            if fnmatch(rel_str, pat):
                return True
        return False

    def _iter_payload_files(self, base: Path):
        # Yield all files under 'assets' and 'data' only
        for root_name in ("assets", "data"):
            root = base / root_name
            if not root.exists():
                continue
            for p in root.rglob('*'):
                if p.is_file():
                    rel = p.relative_to(base)
                    yield rel

    def _write_pack_png(self):
        # Use pack.png from highest priority pack that has one
        for pack in reversed(self.packs):  # highest first
            src = pack.path / "pack.png"
            if src.exists():
                dst = self.out_dir / "pack.png"
                if self.dry_run:
                    print(f"[dry-run] Would copy pack.png from '{pack.name}' -> {dst}")
                else:
                    shutil.copy2(src, dst)
                return
        # If none, do nothing

    def _write_pack_mcmeta(self):
        if self.pack_format_override is not None:
            max_pf = int(self.pack_format_override)
        else:
            # Determine max pack_format among packs; avoid Optional comparisons
            max_seen = -1
            for pack in self.packs:
                if isinstance(pack.pack_format, int) and pack.pack_format > max_seen:
                    max_seen = pack.pack_format
            max_pf = max_seen if max_seen >= 0 else 15  # fallback known-good default for 1.20.x
        if self.description_override is not None:
            description = self.description_override
        else:
            descriptions = [pack.name for pack in self.packs]
            description = f"Merged: {' + '.join(descriptions)}"
        meta = {
            "pack": {
                "pack_format": max_pf,
                "description": description,
            }
        }
        dst = self.out_dir / "pack.mcmeta"
        if self.dry_run:
            print(f"[dry-run] Would write pack.mcmeta to {dst} with pack_format={max_pf}")
        else:
            write_json(dst, meta)

    def _merge_json_base(self, src: Path, dst: Path, merge_fn):
        src_data = read_json(src)
        if src_data is None:
            self.stats.skipped += 1
            return
        if dst.exists():
            dst_data = read_json(dst)
        else:
            dst_data = None
        try:
            if dst_data is None:
                if self.dry_run:
                    print(f"[dry-run] Would create {dst} (from {src})")
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    write_json(dst, src_data)
                self.stats.copied += 1
            else:
                merged = merge_fn(dst_data, src_data)
                if self.dry_run:
                    print(f"[dry-run] Would merge JSON into {dst} (from {src})")
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    write_json(dst, merged)
                self.stats.merged_json += 1
        except Exception as e:
            self.stats.errors += 1
            sys.stderr.write(f"ERROR: Failed to merge {src} -> {dst}: {e}\n")

    def _merge_lang_file(self, src: Path, dst: Path):
        def merge(dst_data, src_data):
            if not isinstance(dst_data, dict):
                dst_data = {}
            if not isinstance(src_data, dict):
                return dst_data
            out = dict(dst_data)
            out.update(src_data)  # later packs override
            return out
        self._merge_json_base(src, dst, merge)

    def _merge_sounds_json(self, src: Path, dst: Path):
        def merge(dst_data, src_data):
            if not isinstance(dst_data, dict):
                dst_data = {}
            if not isinstance(src_data, dict):
                return dst_data
            out = dict(dst_data)
            out.update(src_data)
            return out
        self._merge_json_base(src, dst, merge)

    def _merge_font_json(self, src: Path, dst: Path):
        def merge(dst_data, src_data):
            # Merge providers arrays
            def providers(data):
                if isinstance(data, dict):
                    prov = data.get("providers")
                    return prov if isinstance(prov, list) else []
                return []
            existing = providers(dst_data)
            incoming = providers(src_data)
            merged_list = _dedupe_json_array(existing + incoming)
            base = dst_data if isinstance(dst_data, dict) else {}
            base = dict(base)
            base["providers"] = merged_list
            return base
        self._merge_json_base(src, dst, merge)

    def _merge_atlases_json(self, src: Path, dst: Path):
        def merge(dst_data, src_data):
            def sources(data):
                if isinstance(data, dict):
                    arr = data.get("sources")
                    return arr if isinstance(arr, list) else []
                return []
            existing = sources(dst_data)
            incoming = sources(src_data)
            merged_list = _dedupe_json_array(existing + incoming)
            base = dst_data if isinstance(dst_data, dict) else {}
            base = dict(base)
            base["sources"] = merged_list
            return base
        self._merge_json_base(src, dst, merge)

    def _merge_tag_json(self, src: Path, dst: Path):
        def merge(dst_data, src_data):
            # Union of values arrays; preserve replace flag if present in incoming
            def arr(data):
                if isinstance(data, dict):
                    a = data.get("values")
                    return a if isinstance(a, list) else []
                return []
            existing = arr(dst_data)
            incoming = arr(src_data)
            merged_values = _dedupe_json_array(existing + incoming)
            replace_flag = None
            if isinstance(src_data, dict) and isinstance(src_data.get("replace"), bool):
                replace_flag = src_data["replace"]
            base = dst_data if isinstance(dst_data, dict) else {}
            base = dict(base)
            base["values"] = merged_values
            if replace_flag is not None:
                base["replace"] = replace_flag
            return base
        self._merge_json_base(src, dst, merge)

    def _copy_last_wins(self, src: Path, dst: Path):
        if not src.exists():
            self.stats.skipped += 1
            return
        if dst.exists():
            action = "overwrite"
        else:
            action = "copy"
        if self.dry_run:
            print(f"[dry-run] Would {action} {dst} (from {src})")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        if action == "overwrite":
            self.stats.overwritten += 1
        else:
            self.stats.copied += 1


def _dedupe_json_array(items: List[Any]) -> List[Any]:
    seen = set()
    out = []
    for it in items:
        try:
            key = json.dumps(it, sort_keys=True)
        except TypeError:
            # Unserializable -> fallback to str
            key = str(it)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge multiple Minecraft resource packs into one.")
    p.add_argument("--packs", nargs="*", help="Pack directories (lowest -> highest priority). If omitted, autodetect defaults.")
    p.add_argument("--output", required=False, default="merged_pack", help="Output directory for the merged pack.")
    p.add_argument("--dry-run", action="store_true", help="Don't write files; just print planned actions.")
    p.add_argument("--clean", action="store_true", help="Remove output directory before merging.")
    p.add_argument("--summary", action="store_true", help="Print a summary of actions at the end.")
    p.add_argument("--exclude", action="append", default=[], help="Glob pattern to exclude files (can be passed multiple times).")
    p.add_argument("--pack-format", type=int, dest="pack_format", help="Override pack_format for generated pack.mcmeta.")
    p.add_argument("--description", type=str, dest="description", help="Override description for generated pack.mcmeta.")
    p.add_argument("--zip", dest="zip_output", action="store_true", help="Create a .zip of the merged pack in addition to the folder.")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    cwd = Path.cwd()

    if args.packs:
        pack_paths = [Path(p) if Path(p).is_absolute() else cwd / p for p in args.packs]
    else:
        pack_paths = detect_packs(cwd)

    missing = [str(p) for p in pack_paths if not p.exists()]
    if missing:
        print("ERROR: The following pack paths do not exist:")
        for m in missing:
            print(f"  - {m}")
        return 2

    if not pack_paths:
        print("ERROR: No packs provided and none autodetected.")
        print("Provide pack directories with --packs or place the known folders next to this script.")
        return 2

    packs = [load_pack_info(p) for p in pack_paths]

    print("Merging packs with priority (lowest -> highest):")
    for i, pk in enumerate(packs, 1):
        pf = pk.pack_format if pk.pack_format is not None else "?"
        print(f"  {i}. {pk.name} (pack_format={pf})")

    out_dir = (Path(args.output) if Path(args.output).is_absolute() else cwd / args.output)
    merger = Merger(
        packs,
        out_dir=out_dir,
        dry_run=args.dry_run,
        clean=args.clean,
        exclude_patterns=args.exclude,
        pack_format_override=args.pack_format,
        description_override=args.description,
    )
    merger.run()

    if args.summary:
        s = merger.stats
        print("Summary:")
        print(f"  Copied:      {s.copied}")
        print(f"  Overwritten: {s.overwritten}")
        print(f"  Merged JSON: {s.merged_json}")
        print(f"  Skipped:     {s.skipped}")
        print(f"  Errors:      {s.errors}")

    # Optionally pack to zip
    if args.zip_output and not args.dry_run:
        base_name = out_dir.with_suffix("")  # ensure no .zip duplicate suffix
        zip_path = out_dir.parent / f"{out_dir.name}.zip"
        if zip_path.exists():
            zip_path.unlink()
        print(f"Creating zip: {zip_path}")
        shutil.make_archive(str(zip_path.with_suffix("")), 'zip', root_dir=out_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
