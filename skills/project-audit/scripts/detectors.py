#!/usr/bin/env python3
"""Universal, data-driven detector engine for project-audit/scripts/scan.py.

Design rule: there is no per-language control flow anywhere in this file.
Every check is a ROW in one of the three tables below, so supporting another
language or adding a check means adding data, not editing code.

    LINE_RULES  (rule_id, exts, pattern, condition, flags, detail)
    FILE_RULES  (rule_id, exts, pattern, condition, flags, negpattern)
    UNIT_RULES  (rule_id, exts, unit, marker)

Fields
    rule_id   key of RULES in scan.py (severity, dimension, standard)
    exts      extensions the rule applies to; None = every code file
    pattern   compiled regex
    condition "code"     only lines that are not comments
              "comment"  only comment lines
              "any"      both
              "ident"    match the code line, then test its identifiers
              "stopword" match the code/commented line, then test its words
    flags     "notest"     skip test files
              "notconfig"  skip the configuration layer
              "raw"        match the raw line (string literals not stripped)
              "notoken"    skip token/theme files
              "pathreq"    only files whose relative path matches PATH_REQ_RE
    detail    static detail text, or None
    negpattern (FILE_RULES only) the file must NOT match this regex

Standard library only.
"""
import functools
import re

# --------------------------------------------------------------------------- language meta
CODE_EXTS = {".php", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte",
             ".py", ".go", ".rb", ".java", ".kt", ".cs", ".rs"}
STYLE_EXTS = {".css", ".scss"}
JS_EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte"}
PHP_EXTS = {".php"}
TS_EXTS = {".ts", ".tsx"}

PATH_REQ_RE = re.compile(r"^(app|src|tests|database)/")
CONFIG_RE = re.compile(r"(^|/)(config|settings|conf)/|(^|/)config\.[a-z]+$|\.d\.ts$|^config\.[a-z]+$")
TOKEN_FILE_RE = re.compile(r"(token|theme|tailwind\.config|colors?)", re.I)

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghsa_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|secret|passwd|password|token|private[_-]?key)[\"']?\s*(?:=>|[:=])\s*[\"'][A-Za-z0-9/+=_\-]{16,}[\"']"),
]
SECRET_SKIP = re.compile(r"(?i)example|your_|changeme|xxxx|placeholder|dummy|<.*>|\$\{")

# --------------------------------------------------------------------------- text helpers
_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
_WORD_RE = re.compile(r"[a-z]+")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_IDENT_PART_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])")
_SECRET_HINTS = ('"', "'", "AKIA", "BEGIN", "ghp_", "github_pat_", "gho_", "ghu_", "ghs_", "ghr_", "ghsa_", "AIza", "sk-", "xox")


def strip_strings(line):
    if '"' not in line and "'" not in line and "`" not in line:
        return line  # nothing to strip: the common case, and by far the cheapest
    return _STRING_RE.sub('""', line)


def is_comment(stripped, ext):
    if ext in {".php", ".rs"} and stripped.startswith(("#[", "#![")):
        return False  # attributes, not comments
    return stripped.startswith(("//", "/*", "*", "#"))


def words(text):
    return _WORD_RE.findall(text.lower())


@functools.lru_cache(maxsize=None)
def ident_tokens(ident):
    """Lower-cased camelCase / snake_case parts of an identifier (cached: identifiers repeat a lot)."""
    return tuple(t.lower() for t in _IDENT_PART_RE.findall(ident))


def prev_code_line(lines, i):
    j = i - 1
    while j >= 0:
        s = lines[j].strip()
        if s and not s.startswith(("#[", "@")) and not (s.startswith("[") and s.endswith("]")):
            return s  # attributes / annotations between a doc comment and its unit are skipped
        j -= 1
    return ""


# how each language spells a function definition - data, not branches
FUNCTION_RE = {
    ".php": re.compile(r"\bfunction\s+&?\s*(\w+)\s*\("),
    ".py": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)"),
    ".go": re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*[\[(]"),
    ".rb": re.compile(r"^\s*def\s+(?:self\.)?(\w+[?!=]?)"),
    ".java": re.compile(r"^\s*(?:public|private|protected|static|final|\s)+[\w<>\[\],.]+\s+(\w+)\s*\("),
    ".kt": re.compile(r"\bfun\s+(?:<[^>]*>\s*)?(?:[\w.<>?,\s]*?\.)?(\w+)\s*\("),
    ".cs": re.compile(r"^\s*(?:public|private|protected|internal|static|async|override|virtual|sealed|\s)+[\w<>\[\],.?]+\s+(\w+)\s*\("),
    ".rs": re.compile(r"\bfn\s+(\w+)"),
}
_FUNCTION_JS = re.compile(r"\bfunction\b\s*\*?\s*(\w*)\s*\(|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*(?::[^=]+)?=>\s*\{\s*$")
# how each language delimits a function body: "brace" (default), "indent" (Python), "end" (Ruby)
FUNCTION_STYLE = {".py": "indent", ".rb": "end"}


def _indent_of(line):
    return len(line) - len(line.lstrip())


def _function_end(lines, i, style):
    """Index of the last line of the function that starts at line i, or None when it cannot be told."""
    if style == "indent":
        base, last = _indent_of(lines[i]), i
        for j in range(i + 1, len(lines)):
            t = lines[j]
            s = t.strip()
            if not s or s.startswith("#"):
                continue
            if _indent_of(t) <= base and not s.startswith((")", "]", "}")):
                break
            last = j
        return last
    if style == "end":
        base = _indent_of(lines[i])
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == "end" and _indent_of(lines[j]) == base:
                return j
        return None
    depth, started = 0, False
    for j in range(i, min(len(lines), i + 3000)):
        t = re.sub(r"//.*$", "", strip_strings(lines[j]))
        if not started and ";" in t and "{" not in t:
            return None
        if not started and j - i > 10:
            return None
        for ch in t:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return j
    return None


def find_functions(lines, ext):
    """Yield (name, start_line, length) for every function whose body can be delimited."""
    pat = FUNCTION_RE.get(ext, _FUNCTION_JS)
    style = FUNCTION_STYLE.get(ext, "brace")
    for i, raw in enumerate(lines):
        s = raw.strip()
        if is_comment(s, ext) or not s:
            continue
        if not pat.search(raw):
            continue  # cheap necessary condition; the precise match below ignores string contents
        m = pat.search(strip_strings(raw))
        if not m:
            continue
        name = next((g for g in m.groups() if g), "(anonymous)")
        end = _function_end(lines, i, style)
        if end is not None:
            yield name, i + 1, end - i + 1


# --------------------------------------------------------------------------- the rule tables
# --- universal checks (every code file)
_UNIVERSAL = [
    ("debug.leftover", None,
     re.compile(r"\b(?:breakpoint|pdb\.set_trace)\s*\(|\bdebugger\s*(?:;|$)|(?<![\w.])(?:byebug|binding\.pry|binding\.irb)\b"
                r"|\bdbg!\s*\(|\.printStackTrace\s*\(|(?<![\w>:$.])(?:dd|dump|var_dump|print_r|ray)\s*\("
                r"|\bconsole\.(?:log|debug|dir)\s*\("),
     "code", (), None),
    ("env.read-outside-config", None,
     re.compile(r"\bos\.environ(?:\s*[\[(]|\s*\.\s*\w+)|\bos\.getenv\s*\(|\bgetenv\s*\(|(?<![\w>:])env\s*\(|process\.env\.[A-Za-z_]\w*"
                r"|(?<![\w.])ENV\s*(?:\[|\.fetch\b)|\bos\.Getenv\s*\(|\bSystem\.getenv\s*\("
                r"|\bEnvironment\.GetEnvironmentVariable\s*\(|\benv::var\s*\("),
     "code", ("notconfig",), None),
    ("comment.todo", None, re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.I), "any", ("raw",), None),
    ("comment.prd-reference", None,
     re.compile(r"\b(?:F-\d{3}|US-\d{3}|AC-F\d{3}-\d+|SCR-\d{3}|API-\d{3}|T-\d{3}|Q-\d{3})\b"),
     "code", ("raw",), None),
    ("comment.prd-reference", None, re.compile(r"\bPRD\b|docs/(?:prd|audit|build)/"), "comment", ("raw",), None),
    ("secret.possible", None, None, "code", ("raw",), "value masked"),
]

_SQL = r"(?:select\b[^\"'`;]*?\bfrom\b|insert\s+into\b|update\s+[\w.\"`]+\s+set\b|delete\s+from\b)"
_Q = r"[\"'`]"
_SQL_BUILT = re.compile("(?i)" + "|".join([
    r"(?:\bf|\$)[\"'][^\"']*" + _SQL + r"[^\"']*\{",                          # f-string, C# interpolated string
    _Q + r"[^\"'`]*" + _SQL + r"[^\"'`]*" + _Q + r"\s*(?:\+|\.format|%\s*[(\w])",  # concatenation, .format, % formatting
    r"`[^`]*" + _SQL + r"[^`]*\$\{",                                           # JS template literal
    r"\"[^\"\n]*" + _SQL + r"[^\"\n]*(?:#\{|\$\{|\$[A-Za-z_])",                # Ruby #{}, Kotlin/Groovy ${}, PHP $var
    r"(?:Sprintf|String\.format|String\.Format|format!)\s*\(\s*" + _Q + r"[^\"'`]*" + _SQL
    + r"[^\"'`]*(?:%[-+# 0-9.]*[sdvqxXfT]|\{\d*\}|\{\})",                      # Go, Java, C#, Rust formatting
]))

_FILE_UNIVERSAL = [
    ("sql.string-built", None, _SQL_BUILT, "code", (), None),
    ("error.swallowed", None,
     re.compile(r"except[^:\n]*:\s*\n\s*pass\b|^\s*except\s*:\s*\n\s*pass\b"
                r"|catch\s*\([^)]*\)\s*\{\s*\}|if\s+err\s*!=\s*nil\s*\{\s*\}"
                r"|rescue(?:[ \t]+[\w:]+)*(?:[ \t]*=>[ \t]*\w+)?[ \t]*\n\s*end\b|Err\(_\)\s*=>\s*\{\s*\}"),
     "any", (), None),
]

# --- language-specific checks. Adding a language = adding rows here only.
_LANG_LINE = [
    # PHP
    ("php.mass-assignment", PHP_EXTS,
     re.compile(r"(?:->|::)\s*(?:create|update|fill|forceFill|insert)\s*\(\s*\$request->all\("), "code", ("raw",), None),
    ("php.raw-sql-interpolation", PHP_EXTS,
     re.compile(r"(?:DB::raw|whereRaw|selectRaw|orderByRaw|havingRaw|groupByRaw|DB::(?:select|statement|unprepared))\s*\(\s*(?:\"[^\"]*\$[^\"]*\"|'[^']*'\s*\.\s*\$|\$\w+\s*\.)"),
     "code", ("raw",), None),
    # Python
    ("python.shell-true", {".py"},
     re.compile(r"\bsubprocess\.\w+\([^)\n]*\bshell\s*=\s*True|\bos\.(?:system|popen)\s*\("), "code", (), None),
    ("python.eval-exec", {".py"}, re.compile(r"(?<!def )(?<![\w.])(?:eval|exec)\s*\("), "code", (), None),
    ("python.unsafe-deserialization", {".py"},
     re.compile(r"\b(?:pickle|cPickle|dill|marshal)\.loads?\s*\(|\byaml\.load\s*\((?![^)\n]*Safe)"), "code", (), None),
    ("python.mutable-default", {".py"},
     re.compile(r"\bdef\s+\w+\s*\([^)]*=\s*(?:\[\]|\{\}|set\(\))"), "code", (), None),
    # Ruby
    ("ruby.sql-interpolation", {".rb"},
     re.compile(r"\.(?:where|find_by_sql|order|group|having|joins|pluck|exists\?|execute|select_all)\s*\(\s*[\"'][^\"'\n]*#\{"),
     "code", ("raw",), None),
    ("ruby.shell-interpolation", {".rb"},
     re.compile(r"\b(?:system|exec|spawn)\s*\(?\s*[\"'][^\"'\n]*#\{|%x[\[({]|`[^`\n]*#\{"), "code", ("raw",), None),
    # JavaScript / TypeScript (and Vue / Svelte)
    ("frontend.raw-html", JS_EXTS,
     re.compile(r"dangerouslySetInnerHTML|\bv-html\b|\{@html\b|\binnerHTML\s*=(?!=)|\bbypassSecurityTrust(?:Html|Script|Style|Url|ResourceUrl)\b|\[innerHTML\]"),
     "code", ("raw",), None),
    ("frontend.token-in-browser-storage", JS_EXTS,
     re.compile(r"(?i)(?:localStorage|sessionStorage)\.\s*setItem\s*\([^)]*(?:token|jwt|auth|secret)"), "code", ("raw",), None),
    ("frontend.public-env-secret", JS_EXTS,
     re.compile(r"\b(?:NEXT_PUBLIC|NUXT_PUBLIC|VITE|REACT_APP|VUE_APP|GATSBY|EXPO_PUBLIC|PUBLIC)_\w*(?:SECRET|PASSWORD|PRIVATE|TOKEN|KEY)"),
     "code", (), "variable name"),
    ("react.legacy-api", JS_EXTS,
     re.compile(r"\bforwardRef\s*\(|\.defaultProps\s*=|ReactDOM\.(?:render|hydrate)\s*\(|\.propTypes\s*="), "code", (), None),
    ("design.inline-style", {".jsx", ".tsx"}, re.compile(r"style=\{\{"), "code", ("raw",), None),
    ("ts.any", TS_EXTS, re.compile(r":\s*any\b|<any>|\bas\s+any\b"), "code", ("notest",), None),
    ("ts.ts-ignore", TS_EXTS, re.compile(r"@ts-ignore|@ts-nocheck"), "any", ("raw",), None),
    ("design.hardcoded-color", JS_EXTS | STYLE_EXTS,
     re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b"),
     "code", ("raw", "notest", "notoken"), None),
    ("design.slop-gradient-text", JS_EXTS, re.compile(r"bg-clip-text|background-clip\s*:\s*text"), "code", ("raw", "notest"), None),
    ("design.slop-purple-gradient", JS_EXTS,
     re.compile(r"(?i)(?:gradient|\bfrom-|\bvia-|\bto-).*(?:purple|violet|indigo|fuchsia|pink)"), "code", ("raw", "notest"), None),
    ("design.slop-eyebrow-caps", JS_EXTS, re.compile(r"\buppercase\b"), "code", ("raw", "notest"), "needs tracking-* on the same line"),
    ("design.slop-eyebrow-caps", STYLE_EXTS, re.compile(r"text-transform\s*:\s*uppercase"), "code", ("raw",), "needs letter-spacing on the same line"),
    ("design.slop-default-font", JS_EXTS, re.compile(r"next/font/google|\b(?:Inter|Roboto|Poppins|Open_Sans)\b"), "code", ("raw", "notest"), None),
    ("design.slop-default-font", STYLE_EXTS,
     re.compile(r"font-family\s*:\s*['\"]?(?:Inter|Roboto|Poppins|Open Sans)\b"), "code", ("raw",), None),
    ("design.slop-signature-palette", JS_EXTS, re.compile(r"(?i)#(?:D97757|F4F1EA)\b"), "code", ("raw",), None),
    ("design.slop-motion", JS_EXTS,
     re.compile(r"animate-(?:fade-in|fade-up|slide-up)|slide-in-from-bottom|hover:-translate-y-\d|hover:scale-1\d\d"), "code", ("raw",), None),
    ("design.slop-arrow-text", {".jsx", ".tsx"}, re.compile(r"\u2192"), "code", ("raw",), None),
]

# pair rules: a hit only counts when a second pattern matches the same line
_PAIR_LINE = [
    ("design.slop-eyebrow-caps", JS_EXTS, re.compile(r"\buppercase\b"), re.compile(r"tracking-(?:wide|wider|widest)"), "code", ("raw", "notest")),
    ("design.slop-eyebrow-caps", STYLE_EXTS, re.compile(r"text-transform\s*:\s*uppercase"), re.compile(r"letter-spacing"), "code", ("raw",)),
]

# word/identifier rules driven by the language word lists in scan.py
_WORD_LINE = [
    ("lang.non-english-comment", None, "comment", ("stopword",), "not_lang_dir"),
    ("lang.hardcoded-non-english-text", None, "code", ("stopword",), "not_lang_dir_not_style"),
    ("lang.non-english-identifier", None, "code", ("ident",), "not_lang_dir_not_style"),
]

_LANG_FILE = [
    ("php.missing-strict-types", PHP_EXTS, re.compile(r"declare\(\s*strict_types\s*=\s*1\s*\)"),
     "negfile", ("pathreq",), None),
    ("react.class-component", JS_EXTS,
     re.compile(r"class\s+\w+\s+extends\s+(?:React\.)?(?:Pure)?Component"),
     "posneg", (), re.compile(r"componentDidCatch|getDerivedStateFromError")),
]

_LANG_UNIT = [
    # PHP: class-like declarations and public/protected methods need a preceding /** */
    ("doc.missing", PHP_EXTS,
     re.compile(r"^\s*(?:(?:final|abstract|readonly)\s+)*(?:class|interface|trait|enum)\s+\w+"
                r"|^\s*(?:(?:public|protected|static|final|abstract)\s+)+function\s+(\w+)"),
     "prev_block"),
    # Python: public def/class need a docstring on the next non-blank line
    ("doc.missing", {".py"},
     re.compile(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)"),
     "next_string"),
    # JavaScript / TypeScript: exported symbols need a preceding /** */
    ("doc.missing", JS_EXTS,
     re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|interface|type|enum)\s+([A-Za-z_]\w*)"),
     "prev_block"),
    # Go: exported symbols need a preceding `//` doc comment
    ("doc.missing", {".go"},
     re.compile(r"^(?:func|type|var|const)\s+([A-Z]\w*)"),
     "prev_line_comment"),
    # Ruby: definitions need a preceding # comment
    ("doc.missing", {".rb"},
     re.compile(r"^\s*(?:class|module|def)\s+([A-Za-z_]\w*)"),
     "prev_hash"),
    # Kotlin: public (default visibility) types and functions need a preceding KDoc block
    ("doc.missing", {".kt"},
     re.compile(r"^(?!\s*(?:private|internal|protected|override)\b)\s*(?:(?:public|open|abstract|data|sealed|enum|inline|suspend)\s+)*"
                r"(?:class|interface|object|fun)\s+(?:<[^>]*>\s*)?(?:[\w.<>?,\s]*?\.)?(\w+)"),
     "prev_block"),
    # Rust: pub items need a preceding /// doc comment
    ("doc.missing", {".rs"},
     re.compile(r"^\s*pub(?:\([\w:\s]+\))?\s+(?:(?:async|unsafe|const)\s+)*(?:fn|struct|enum|trait|type|mod)\s+(\w+)"),
     "prev_line_comment"),
    # C#: public types and methods need a preceding /// doc comment
    ("doc.missing", {".cs"},
     re.compile(r"^\s*public\s+(?:(?:static|sealed|abstract|partial|readonly)\s+)*(?:class|interface|enum|struct|record)\s+(\w+)"
                r"|^\s*public\s+(?:(?:static|virtual|async|abstract)\s+)*[\w<>\[\],.?]+\s+(\w+)\s*\("),
     "prev_line_comment"),
    # Java style: public types and methods
    ("doc.missing", {".java"},
     re.compile(r"^\s*(?:public|protected)\s+(?:final\s+|abstract\s+|static\s+)*(?:class|interface|enum)\s+\w+"
                r"|^\s*(?:public|protected)\s+[\w<>\[\],\s]+\s+([A-Za-z_]\w*)\s*\("),
     "prev_block"),
]

LINE_RULES = _UNIVERSAL + _LANG_LINE
FILE_RULES = _FILE_UNIVERSAL + _LANG_FILE
UNIT_RULES = _LANG_UNIT


def _flags_ok(flags, rel, is_test):
    if "notest" in flags and is_test:
        return False
    if "notconfig" in flags and CONFIG_RE.search(rel):
        return False
    if "notoken" in flags and TOKEN_FILE_RE.search(rel.rsplit("/", 1)[-1]):
        return False
    if "pathreq" in flags and not PATH_REQ_RE.match(rel):
        return False
    return True


try:  # Python 3.11+ moved the regex parser; older versions still have sre_parse
    import re._parser as _sre_parse
except ImportError:  # pragma: no cover
    import sre_parse as _sre_parse

PREFILTER = True  # set to False to compare results with and without the literal prefilter (see selftest)


def _branch_literals(nodes):
    """Any-of literals that one alternative of a pattern certainly needs, or None when none can be derived.

    Candidates: the longest run of mandatory literal characters, or the alternatives of a mandatory
    group such as (?:a|b). The smallest, longest candidate wins.
    """
    options, run = [], ""
    for op, av in nodes:
        if op == _sre_parse.LITERAL:
            run += chr(av)
            continue
        if len(run) >= 2:
            options.append((run,))
        run = ""
        parts = None
        if op == _sre_parse.SUBPATTERN:
            inner = list(av[-1])
            parts = inner[0][1][1] if len(inner) == 1 and inner[0][0] == _sre_parse.BRANCH else [inner]
        elif op == _sre_parse.BRANCH:  # the parser inlines non-capturing groups such as (?:a|b)
            parts = av[1]
        if parts is not None:
            got = [_branch_literals(list(part)) for part in parts]
            if all(got):
                options.append(tuple(lit for g in got for lit in g))
    if len(run) >= 2:
        options.append((run,))
    return min(options, key=lambda o: (len(o), -min(len(x) for x in o))) if options else None


def _required_literals(pat):
    """Literals (lower-cased when the pattern ignores case), at least one of which occurs in every text
    the pattern can match. None when no safe literal can be derived (then no prefilter is used).

    Only requirements that are mandatory at the top level of an alternative are used, so the result is
    a necessary condition: if none of them occurs in a text, the pattern cannot match that text.
    """
    try:
        nodes = list(_sre_parse.parse(pat.pattern, pat.flags))
        branches = nodes[0][1][1] if len(nodes) == 1 and nodes[0][0] == _sre_parse.BRANCH else [nodes]
        out = []
        for branch in branches:
            lits = _branch_literals(list(branch))
            if not lits:
                return None
            out.extend(lits)
        ci = bool(pat.flags & re.I)
        return tuple(sorted({x.lower() if ci else x for x in out}))
    except Exception:
        return None


class _Text:
    """A file text plus its lower-cased copy (made only if a case-insensitive rule asks for it)."""
    __slots__ = ("text", "_lower")

    def __init__(self, text):
        self.text, self._lower = text, None

    @property
    def lower(self):
        if self._lower is None:
            self._lower = self.text.lower()
        return self._lower


_GATES = {}


def _gate_entry(pat):
    g = _GATES.get(pat)
    if g is None:
        g = _GATES[pat] = (_required_literals(pat), re.compile(pat.pattern, pat.flags | re.M), bool(pat.flags & re.I))
    return g


def _literal_ok(pat, hay):
    """False only when `pat` certainly cannot match `hay` (a _Text): none of its mandatory literals occurs."""
    if not PREFILTER:
        return True
    lits, _, ci = _gate_entry(pat)
    if lits is None:
        return True
    text = hay.lower if ci else hay.text
    return any(lit in text for lit in lits)


def _gate(pat, hay):
    """Can this rule match anywhere in the file? (MULTILINE: a match inside one line is a match in the file.)"""
    return _literal_ok(pat, hay) and _gate_entry(pat)[1].search(hay.text) is not None


def iter_line_findings(rel, ext, lines, is_test, stopwords, id_words, in_lang_dir, secret_patterns, secret_skip):
    """Yield (rule_id, rel, line_no, detail) for every line-level rule.

    Two cheap decisions are made once per file instead of once per line:
      1. which rules apply at all (extension, path, test or not);
      2. which of those can match anywhere in the file. A pattern that matches inside one line also
         matches in the whole file in MULTILINE mode, so a rule that does not is skipped without
         changing any result. Most files then need no per-line work at all.
    """
    code_lines = [strip_strings(l) for l in lines]
    code_text = "\n".join(code_lines)
    raw_text = "\n".join(lines)
    code_hay, raw_hay = _Text(code_text), _Text(raw_text)

    rules = [(rid, pat, cond, use_raw, detail)
             for rid, exts, pat, cond, flags, detail in LINE_RULES
             if pat is not None and (exts is None or ext in exts) and _flags_ok(flags, rel, is_test)
             for use_raw in ("raw" in flags,)
             if _gate(pat, raw_hay if use_raw else code_hay)]
    pairs = [(rid, first, second, cond, use_raw)
             for rid, exts, first, second, cond, flags in _PAIR_LINE
             if (exts is None or ext in exts) and _flags_ok(flags, rel, is_test)
             for use_raw in ("raw" in flags,)
             if _gate(first, raw_hay if use_raw else code_hay) and _gate(second, raw_hay if use_raw else code_hay)]

    word_rules = []
    file_words = file_idents = None
    for rid, exts, cond, kind, guard in _WORD_LINE:
        if exts is not None and ext not in exts:
            continue
        if ("not_lang_dir" in guard and in_lang_dir) or ("not_style" in guard and ext in STYLE_EXTS):
            continue
        if kind == "stopword":
            if file_words is None:
                file_words = set(words(raw_text))
            if len(file_words & stopwords) < 2:
                continue
        else:
            if file_idents is None:
                file_idents = {tok for ident in set(_IDENT_RE.findall(code_text.replace("$", " "))) for tok in ident_tokens(ident)}
            if not (file_idents & id_words):
                continue
        word_rules.append((rid, cond, kind))

    secrets_possible = any(h in raw_text for h in _SECRET_HINTS)
    if not (rules or pairs or word_rules or secrets_possible):
        return

    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            continue
        commented = is_comment(s, ext)
        code_line = code_lines[i - 1]

        for rid, pat, cond, use_raw, detail in rules:
            if (cond == "code" and commented) or (cond == "comment" and not commented):
                continue
            if pat.search(raw if use_raw else code_line):
                yield rid, rel, i, detail

        for rid, first, second, cond, use_raw in pairs:
            if cond == "code" and commented:
                continue
            hay = raw if use_raw else code_line
            if first.search(hay) and second.search(hay):
                yield rid, rel, i, None

        for rid, cond, kind in word_rules:
            if (cond == "comment" and not commented) or (cond == "code" and commented):
                continue
            if kind == "stopword":
                if len(set(words(raw)) & stopwords) >= 2:
                    yield rid, rel, i, None
            else:
                toks = {tok for ident in _IDENT_RE.findall(code_line.replace("$", " ")) for tok in ident_tokens(ident)}
                hit = toks & id_words
                if hit:
                    yield rid, rel, i, ", ".join(sorted(hit)[:3])

        if secrets_possible and not commented and any(h in raw for h in _SECRET_HINTS):
            for pat in secret_patterns:
                if pat.search(raw) and not secret_skip.search(raw):
                    yield "secret.possible", rel, i, "value masked"
                    break


def iter_file_findings(rel, ext, text, lines, is_test):
    """Yield (rule_id, rel, 1, detail) for every file-level rule."""
    hay = _Text(text)
    for rid, exts, pat, cond, flags, neg in FILE_RULES:
        if exts is not None and ext not in exts:
            continue
        if not _flags_ok(flags, rel, is_test):
            continue
        if cond != "negfile" and not _literal_ok(pat, hay):
            continue
        if cond == "negfile":
            if not pat.search(text):
                yield rid, rel, 1, None
        elif cond == "posneg":
            if pat.search(text) and not neg.search(text):
                yield rid, rel, 1, None
        else:
            if pat.search(text):
                yield rid, rel, 1, None

    # file header metadata (@author, @ai) - universal for every code file
    if ext in CODE_EXTS and len(lines) >= 5 and not is_test and not TOKEN_FILE_RE.search(rel.rsplit("/", 1)[-1]):
        if not CONFIG_RE.search(rel):
            head = "\n".join(lines[:60])
            missing = [tag for tag in ("@author", "@ai") if tag not in head]
            if missing:
                yield "comment.missing-metadata", rel, 1, "missing: " + ", ".join(missing)


def iter_unit_findings(rel, ext, lines, is_test, stats=None):
    """Yield (rule_id, rel, line_no, name) for documentation rules.

    When `stats` is a dict with "total" and "missing", every matched unit is counted in it.
    """
    if ext not in CODE_EXTS or is_test:
        return
    for rid, exts, unit, marker in UNIT_RULES:
        if exts is not None and ext not in exts:
            continue
        for i, raw in enumerate(lines):
            if not unit.match(raw):
                continue
            name = next((g for g in unit.match(raw).groups() if g), "")
            if marker == "prev_block":
                ok = prev_code_line(lines, i).endswith("*/")
            elif marker == "next_string":
                nxt = next((l for l in lines[i + 1:] if l.strip()), "")
                ok = nxt.lstrip().startswith(('"', "'"))
            elif marker == "prev_line_comment":
                ok = prev_code_line(lines, i).startswith(("//", "#"))
            elif marker == "prev_hash":
                ok = prev_code_line(lines, i).startswith("#")
            else:
                ok = True
            if stats is not None:
                stats["total"] += 1
                stats["missing"] += 0 if ok else 1
            if not ok:
                yield rid, rel, i + 1, name or "(anonymous)"
