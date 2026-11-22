"""Read or explicitly update the root Codex context window configuration."""

import argparse
import copy
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib


KEY = "model_context_window"
ASSIGNMENT = re.compile(
    r"""(?m)^[ \t]*(?P<key>model_context_window|"(?:[^"\\\r\n]|\\[^\r\n])*"|'model_context_window')"""
    r"[ \t]*=[ \t]*(?P<value>[+-]?[0-9a-fA-F_oxb]+)(?=[ \t]*(?:#|\r?$))"
)


class ConfigError(Exception):
    pass


def read_toml(source):
    try:
        return tomllib.loads(source)
    except (ValueError, RecursionError):
        raise ConfigError("Configuration is not valid TOML.") from None


def same_toml(before, after):
    # NaN is valid TOML but does not compare equal to itself.
    if type(before) is not type(after):
        return False
    if isinstance(before, dict):
        return before.keys() == after.keys() and all(
            same_toml(value, after[key]) for key, value in before.items()
        )
    if isinstance(before, list):
        return len(before) == len(after) and all(
            same_toml(left, right) for left, right in zip(before, after)
        )
    if isinstance(before, float) and math.isnan(before):
        return math.isnan(after)
    return before == after


def updated_toml(source, parsed, new_value):
    expected = copy.deepcopy(parsed)
    expected[KEY] = new_value
    if KEY in parsed:
        candidates = []
        for match in ASSIGNMENT.finditer(source):
            try:
                single_key = read_toml(f'{match.group("key")} = 0')
            except ConfigError:
                continue
            if KEY in single_key:
                candidates.append(
                    source[:match.start("value")] + str(new_value) + source[match.end("value"):]
                )
    else:
        first_newline = re.search(r"\r?\n", source)
        newline = first_newline.group() if first_newline else "\n"
        candidates = (f"{KEY} = {new_value}" + (newline + source if source else newline),)

    for candidate in candidates:
        try:
            result = read_toml(candidate)
        except ConfigError:
            continue
        if same_toml(expected, result):
            return candidate
    raise ConfigError("Could not safely update the root context window setting.")


def write_config(path, original, replacement):
    lock_path = path.with_name(path.name + ".context-window.lock")
    try:
        lock = lock_path.open("xb")
    except FileExistsError:
        raise ConfigError("Another context window update holds the configuration lock.") from None
    temporary_path = None
    try:
        with lock:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(replacement)
                temporary.flush()
                os.fsync(temporary.fileno())
            if original is not None:
                temporary_path.chmod(stat.S_IMODE(path.stat().st_mode))
            if (path.read_bytes() if path.exists() else None) != original:
                raise ConfigError("Configuration changed during the update. Retry after checking it.")
            os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)


def positive_integer(value):
    if not re.fullmatch(r"[0-9]{1,19}", value):
        raise argparse.ArgumentTypeError("provide a positive integer")
    number = int(value)
    if not 0 < number <= 2**63 - 1:
        raise argparse.ArgumentTypeError("provide a positive 64-bit integer")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--set", dest="new_value", type=positive_integer)
    args = parser.parse_args()

    try:
        codex_home = os.environ.get("CODEX_HOME")
        config = args.config or (Path(codex_home) if codex_home else Path.home() / ".codex") / "config.toml"
        path = config.expanduser().resolve()
        try:
            original = path.read_bytes()
        except FileNotFoundError:
            original = None
        source = (original or b"").decode("utf-8")
        parsed = read_toml(source)
        current = parsed.get(KEY)
        if KEY in parsed and (type(current) is not int or current <= 0):
            raise ConfigError("The existing root context window is not a positive integer.")

        if args.new_value is not None and args.new_value != current:
            replacement = updated_toml(source, parsed, args.new_value)
            write_config(path, original, replacement.encode("utf-8"))
            current = args.new_value
        print(f"{KEY} = {current}" if current is not None else f"{KEY}: unset")
    except UnicodeDecodeError:
        parser.exit(1, "Configuration is not valid UTF-8.\n")
    except ConfigError as error:
        parser.exit(1, f"{error}\n")
    except (OSError, RuntimeError):
        parser.exit(1, "Unable to access the Codex configuration.\n")


if __name__ == "__main__":
    main()
