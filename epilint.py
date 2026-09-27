#!/usr/bin/env python3
"""Conservative Epitech C style checker and formatter (Python 3.9+).

No third-party dependencies. Run `epilint.py --help` for usage. This tool does
not claim to replace the school's checker or to rewrite semantic C rules.
"""

from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    line: int
    col: int
    rule: str
    message: str
    fix: str = "manual"


KEYWORDS = {"if", "while", "for", "switch", "return", "else", "catch"}
CONTROLS = {"if", "while", "for", "switch", "else", "do"}
OPERATORS = {"=", "+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==",
             "!=", "&&", "||", "+=", "-=", "*=", "/=", "%=", "&=", "|=",
             "^=", "<<=", ">>=", "<<", ">>", "|", "^", "&"}
MULTI = ("...", "<<=", ">>=", "->", "++", "--", "==", "!=", "<=", ">=",
         "&&", "||", "<<", ">>", "+=", "-=", "*=", "/=", "%=", "&=", "|=",
         "^=", "##")
TYPE_WORDS = {"void", "char", "short", "int", "long", "float", "double", "signed",
              "unsigned", "const", "volatile", "restrict", "static", "extern",
              "struct", "union", "enum", "size_t", "ssize_t", "bool", "_Bool",
              "typedef", "inline", "auto", "register"}
TOKEN = re.compile(r"[A-Za-z_]\w*|(?:0[xX][\da-fA-F]+|\d+(?:\.\d+)?)|"
                   + "|".join(map(re.escape, MULTI)) + r"|[^\s]", re.ASCII)
HEADER = re.compile(r"\A/\*\s*\n\*\* EPITECH PROJECT,", re.ASCII)


def mask_literals(source: str) -> str:
    """Keep offsets/newlines intact, replace comments and quoted text by spaces."""
    out = list(source)
    i = 0
    state = "code"
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if ch == "/" and nxt in "/*" and nxt:
                state = "block" if nxt == "*" else "line"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch in "\"'":
                state = ch
                out[i] = " "
        elif state == "line":
            if ch == "\n":
                state = "code"
            else:
                out[i] = " "
        elif state == "block":
            if ch == "*" and nxt == "/":
                out[i] = out[i + 1] = " "
                state = "code"
                i += 2
                continue
            if ch != "\n":
                out[i] = " "
        else:
            if ch == "\\" and nxt:
                out[i] = " "
                if nxt != "\n":
                    out[i + 1] = " "
                i += 2
                continue
            if ch == state:
                state = "code"
            if ch != "\n":
                out[i] = " "
        i += 1
    return "".join(out)


def directive_lines(lines: list[str]) -> set[int]:
    result = set()
    continuation = False
    for n, line in enumerate(lines):
        if continuation or line.lstrip().startswith("#"):
            result.add(n)
            continuation = line.rstrip().endswith("\\")
        else:
            continuation = False
    return result


def token_pairs(code: str):
    matches = list(TOKEN.finditer(code))
    for idx in range(1, len(matches)):
        left, right = matches[idx - 1], matches[idx]
        yield (matches[idx - 2].group() if idx >= 2 else "",
               left.group(), right.group(),
               matches[idx + 1].group() if idx + 1 < len(matches) else "",
               left.end(), right.start())


def desired_gap(prev: str, a: str, b: str, following: str, actual: str) -> str | None:
    """Only make token-adjacent changes when their lexical role is clear."""
    if a == "," or (a == ";" and prev != ";" and b != ")"):
        return " "
    if b in {",", ";"}:
        return ""
    if a in {"?", ":"} or b in {"?", ":"}:
        # Labels, bit-fields and the GNU ?: extension need a parser.
        return " " if a == "?" or b == "?" else None
    if b == "(" and (a in KEYWORDS or a == "sizeof"):
        return "" if a == "sizeof" else " "
    if b == "(" and (a.isidentifier() or a in {"*", ")"}):
        return ""
    if a == "(" or b == ")" or a == "[" or b == "]" or b == "[":
        return ""
    if a in {".", "->"} or b in {".", "->"}:
        return ""
    if a in {"++", "--", "!", "~"} or b in {"++", "--"}:
        return ""
    if b in {"=", "+=", "-=", "*=", "/=", "%=", "==", "!=", "<=", ">=", "&&", "||"}:
        return " "
    if a in {"=", "+=", "-=", "*=", "/=", "%=", "==", "!=", "<=", ">=", "&&", "||"}:
        return " "
    if a in {"+", "-", "/", "%", "<", ">", "|", "^"} and b not in {"+", "-", ">", "<"}:
        if prev in {"", "(", "[", "=", ",", "return", ":", "?"} and a in {"+", "-"}:
            return ""
        return " "
    if b in {"+", "-", "/", "%", "<", ">", "|", "^"} and a not in {"+", "-", ">", "<"}:
        if b in {"+", "-"} and a in {"(", "[", "=", ",", "return", ":", "?"}:
            return " " if a in {"=", "return", ","} else ""
        return " "
    # Clear declaration and unary forms; ambiguous products are left alone.
    if b == "*" and (a in TYPE_WORDS or a == "return" or a == "("):
        return "" if a == "(" else " "
    if a == "*" and (prev in TYPE_WORDS or prev in {"return", "(", "=", ",", "?", ":"}):
        return ""
    if a == "{" and b not in {"}", ";"}:
        return None
    if b == "{" and a not in {"=", ","}:
        return " "
    return None


def format_tokens(line: str, masked: str) -> str:
    changes = []
    for prev, a, b, following, start, end in token_pairs(masked):
        if start > end or "\n" in line[start:end]:
            continue
        old = line[start:end]
        if any(c not in " \t" for c in old):
            continue
        target = desired_gap(prev, a, b, following, old)
        if (a == ":" or b == ":") and "?" in masked[:end]:
            target = " "
        if target is not None and old != target:
            changes.append((start, end, target))
    for start, end, replacement in reversed(changes):
        line = line[:start] + replacement + line[end:]
    return line


def function_open(line: str) -> bool:
    # Only detect a complete top-level function signature on one line.
    s = line.strip()
    if not s.endswith("{") or not re.search(r"\)\s*\{$", s):
        return False
    if re.match(r"^(?:if|while|for|switch|else|do)\b", s):
        return False
    return bool(re.match(r"^(?:[\w*]+\s+)+[*\s]*[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{$", s))


def function_signature(line: str) -> bool:
    """Recognize only plain, single-line definitions; avoid guessing macros."""
    s = line.strip()
    if re.match(r"^(?:if|while|for|switch|else|do)\b", s):
        return False
    return bool(re.match(r"^(?:[\w*]+\s+)+[*\s]*[A-Za-z_]\w*\s*\([^;{}]*\)\s*(?:\{|$)", s))


def bare_function_signature(line: str) -> bool:
    """Old-style implicit-int definition, accepted only with its opening brace."""
    return bool(re.match(r"^\s*[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{", line)) and not re.match(
        r"^\s*(?:if|for|while|switch)\b", line)


def safe_format(source: str) -> str:
    lines = source.split("\n")
    masks = mask_literals(source).split("\n")
    directives = directive_lines(lines)
    out = []
    for n, (line, mask) in enumerate(zip(lines, masks)):
        # Preserve preprocessor continuations and whitespace within comments.
        if n in directives or not mask.strip():
            out.append(line.rstrip(" \t") if mask.strip() == line.strip() else line)
            continue
        line = line.rstrip(" \t")
        mask = mask[:len(line)]
        leading = len(line) - len(line.lstrip(" \t"))
        prefix = line[:leading].expandtabs(4)
        body = format_tokens(line[leading:], mask[leading:])
        out.append(prefix + body)
    return "\n".join(out)


def force_format(source: str) -> str:
    """Split short inline C statements, format braces and reindent braced code."""
    lines = source.splitlines(keepends=False)
    masks = mask_literals(source).splitlines(keepends=False)
    directives = directive_lines(lines)
    output: list[str] = []
    depth = 0
    for n, (line, mask) in enumerate(zip(lines, masks)):
        if n in directives or not mask.strip():
            output.append(line)
            continue
        # Preserve inline comments, composite literals and macros rather than
        # moving their contents to an unrelated line.
        if "//" in line or "/*" in line or "*/" in line:
            output.append(line)
            depth = max(0, depth + mask.count("{") - mask.count("}"))
            continue
        if depth == 0 and bare_function_signature(mask):
            line = "int " + line.lstrip()
            mask = "int " + mask.lstrip()
        is_function = depth == 0 and (function_signature(mask) or bare_function_signature(mask))
        # Avoid splitting structure/enum declarations and initializers.
        if re.search(r"\b(?:struct|union|enum)\b[^;]*\{", mask) or re.search(r"=\s*\{", mask):
            output.append(line)
            depth = max(0, depth + mask.count("{") - mask.count("}"))
            continue
        chunk = ""
        parens = 0
        for i, ch in enumerate(line):
            code = mask[i]
            if code == "(":
                parens += 1
            elif code == ")":
                parens = max(0, parens - 1)
            if code == "{" and parens == 0:
                prefix = chunk.rstrip()
                if is_function and depth == 0:
                    if prefix:
                        output.append(prefix)
                    output.append("{")
                else:
                    output.append(prefix + " {")
                chunk = ""
                is_function = False
                depth += 1
            elif code == ";" and parens == 0:
                chunk += ch
                if chunk.strip():
                    output.append(chunk.strip())
                chunk = ""
            elif code == "}" and parens == 0:
                if chunk.strip():
                    output.append(chunk.strip())
                output.append("}")
                chunk = ""
                depth = max(0, depth - 1)
            else:
                chunk += ch
        if chunk.strip():
            output.append(chunk.strip())
    # Join else with a closing brace, as required by C-L4.
    joined = []
    for line in output:
        if joined and re.match(r"^else\b", line.lstrip()) and joined[-1].strip() == "}":
            joined[-1] += " " + line.lstrip()
        else:
            joined.append(line)
    output = []
    depth = 0
    for line in joined:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            output.append(line)
            continue
        level = max(0, depth - int(stripped.startswith("}")))
        # Keep a continued expression's indentation when no braces tell us its level.
        output.append(" " * (4 * level) + stripped)
        code = mask_literals(stripped)
        depth = max(0, depth + code.count("{") - code.count("}"))
    return safe_format("\n".join(output) + ("\n" if source.endswith("\n") else ""))


def diagnose(source: str) -> list[Issue]:
    issues = []
    lines = source.splitlines(keepends=True)
    masks = mask_literals(source).splitlines(keepends=True)
    directives = directive_lines(lines)
    if source and not HEADER.match(source):
        issues.append(Issue(1, 1, "C-G1", "en-tête Epitech absent ou incorrect"))
    if "\r" in source:
        issues.append(Issue(1, 1, "C-G6", "caractère CR : utiliser LF", "safe"))
    if lines and lines[0].strip() == "":
        issues.append(Issue(1, 1, "C-G8", "ligne vide au début", "force"))
    if source and not source.endswith("\n"):
        issues.append(Issue(len(lines), len(lines[-1]) + 1, "C-A3", "saut de ligne final manquant", "safe"))
    if source.endswith("\n\n\n"):
        issues.append(Issue(len(lines) - 1, 1, "C-G8", "trop de lignes vides à la fin", "force"))
    depth = 0
    function_start = None
    pending_function = None
    for n, (line, mask) in enumerate(zip(lines, masks), 1):
        content = line.rstrip("\r\n")
        code = mask.rstrip("\r\n")
        if content.endswith((" ", "\t")):
            issues.append(Issue(n, len(content), "C-G7", "espaces en fin de ligne", "safe"))
        if "\t" in content:
            issues.append(Issue(n, content.index("\t") + 1, "C-L2", "tabulation", "safe" if n - 1 not in directives else "manual"))
        if len(content.expandtabs(4)) + (1 if line.endswith("\n") else 0) > 80:
            issues.append(Issue(n, 81, "C-F3", "ligne de plus de 80 colonnes"))
        if n - 1 in directives or not code.strip():
            continue
        leading = len(content) - len(content.lstrip(" \t"))
        effective_depth = max(0, depth - (1 if code.lstrip().startswith("}") else 0))
        if content[:leading].replace(" ", "") == "" and content.strip() and (
                leading % 4 != 0 or leading != 4 * effective_depth):
            # This is diagnostic only: C without braces, labels, macro scopes,
            # initializers and continuations require a real parser.
            if not re.match(r"^(?:case\b|default\s*:|[A-Za-z_]\w*\s*:)", code.lstrip()):
                issues.append(Issue(n, 1, "C-L2", "indentation à vérifier"))
        fixed = format_tokens(content[leading:], code[leading:])
        if fixed != content[leading:]:
            issues.append(Issue(n, leading + 1, "C-L3", "espacement des tokens", "safe"))
        inline_function = (depth == 0 and "{" in code and
                           (function_signature(code) or bare_function_signature(code)))
        if inline_function:
            issues.append(Issue(n, code.rfind("{") + 1, "C-L4", "accolade de fonction sur une ligne séparée", "force"))
        if depth == 0 and bare_function_signature(code):
            issues.append(Issue(n, 1, "C-A2", "type de retour implicite : int", "force"))
        if depth == 0 and function_signature(code):
            pending_function = n
        if depth == 0 and code.strip() == "{" and pending_function is not None:
            function_start = n
            pending_function = None
        elif inline_function:
            function_start = n
            pending_function = None
        # Only count semicolons outside strings/comments; for loops are exempt.
        semis = code.count(";")
        if semis > 1 and not re.search(r"\bfor\s*\(", code):
            issues.append(Issue(n, 1, "C-L1", "plusieurs instructions sur la même ligne"))
        depth = max(0, depth + code.count("{") - code.count("}"))
        if depth == 0 and function_start is not None:
            length = n - function_start - 1
            if length > 20:
                issues.append(Issue(function_start, 1, "C-F4", f"corps de fonction : {length} lignes (maximum 20)"))
            function_start = None
    return sorted(issues, key=lambda item: (item.line, item.col, item.rule))


def paths_from(args: list[str]):
    found = set()
    for raw in args:
        path = Path(raw)
        if path.is_file() and (path.suffix in {".c", ".h"} or len(args) == 1):
            found.add(path)
        elif path.is_dir():
            for root, dirs, names in os.walk(path):
                dirs[:] = sorted(d for d in dirs if d not in {".git", "build", ".venv", "venv"})
                for name in names:
                    if name.endswith((".c", ".h")):
                        found.add(Path(root) / name)
        else:
            raise ValueError(f"chemin introuvable ou fichier non C : {raw}")
    return sorted(found)


def write_atomic(path: Path, content: bytes):
    original_mode = stat.S_IMODE(path.stat().st_mode)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.chmod(temp, original_mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", metavar="FICHIER|DOSSIER")
    parser.add_argument("-w", "--fix", action="store_true", help="corriger les espaces sans déplacer de lignes")
    parser.add_argument("-f", "--force", action="store_true", help="avec --fix, autoriser les changements de lignes sûrs")
    parser.add_argument("--diff", "--dry-run", action="store_true", help="afficher les changements sans écrire")
    parser.add_argument("--check", action="store_true", help="échouer si des corrections sont possibles")
    opts = parser.parse_args(argv)
    if opts.force and not (opts.fix or opts.diff or opts.check):
        parser.error("-f nécessite --fix, --diff ou --check")
    count = 0
    changed = 0
    errors = 0
    try:
        paths = paths_from(opts.paths)
        if not paths:
            parser.error("aucun fichier .c ou .h trouvé")
        for path in paths:
            data = path.read_bytes()
            if b"\0" in data:
                print(f"{path}: fichier binaire ignoré", file=sys.stderr)
                errors += 1
                continue
            source = data.decode("utf-8", errors="surrogateescape")
            normalized = source.replace("\r\n", "\n").replace("\r", "\n")
            formatted = safe_format(normalized)
            if opts.force:
                formatted = force_format(formatted)
                formatted = formatted.lstrip("\n")
                formatted = formatted.rstrip("\n") + "\n" if formatted.strip() else ""
            if formatted and not formatted.endswith("\n"):
                formatted += "\n"
            if not opts.force and source.count("\n") != formatted.count("\n") - (not source.endswith("\n") and bool(source)):
                # In safe mode a missing final LF is the sole allowed change.
                raise ValueError(f"le mode sûr a modifié le nombre de lignes : {path}")
            pending = formatted != source
            if opts.diff and pending:
                sys.stdout.writelines(difflib.unified_diff(source.splitlines(True), formatted.splitlines(True),
                                  fromfile=str(path), tofile=str(path) + " (proposé)"))
            if opts.fix and not opts.diff and pending:
                write_atomic(path, formatted.encode("utf-8", errors="surrogateescape"))
                changed += 1
            current = formatted if opts.fix and not opts.diff else source
            for issue in diagnose(current):
                print(f"{path}:{issue.line}:{issue.col}: {issue.rule}: {issue.message} [{issue.fix}]")
                count += 1
            if opts.check and pending:
                errors += 1
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"epilint: {exc}", file=sys.stderr)
        return 2
    if opts.fix and not opts.diff:
        print(f"{changed} fichier(s) modifié(s) ; {count} diagnostic(s) restant(s)")
    return 1 if count or errors else 0


if __name__ == "__main__":
    sys.exit(run())
