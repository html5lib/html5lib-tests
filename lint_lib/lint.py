from __future__ import unicode_literals, print_function

import codecs
import re
import json
import os
import sys
from collections import Counter, OrderedDict
from os.path import dirname, join, pardir, relpath

from ._vendor.funcparserlib.parser import NoParseError

from . import parser

text_type = type("")
binary_type = type(b"")

try:
    unichr
except NameError:
    unichr = chr

base = join(dirname(__file__), pardir)

_surrogateRe = re.compile(r"\\u([0-9A-Fa-f]{4})(?:\\u([0-9A-Fa-f]{4}))?")


def clean_path(path):
    return relpath(path, base)


def is_subsequence(l1, l2):
    """ checks if l1 is a subsequence of l2"""
    i = 0
    for x in l2:
        if l1[i] == x:
            i += 1
            if i == len(l1):
                return True
    return False


def unescape_json(obj):
    def decode_str(inp):
        """Decode \\uXXXX escapes

        This decodes \\uXXXX escapes, possibly into non-BMP characters when
        two surrogate character escapes are adjacent to each other.
        """
        # This cannot be implemented using the unicode_escape codec
        # because that requires its input be ISO-8859-1, and we need
        # arbitrary unicode as input.
        def repl(m):
            if m.group(2) is not None:
                high = int(m.group(1), 16)
                low = int(m.group(2), 16)
                if (0xD800 <= high <= 0xDBFF and
                        0xDC00 <= low <= 0xDFFF and
                        sys.maxunicode == 0x10FFFF):
                    cp = ((high - 0xD800) << 10) + (low - 0xDC00) + 0x10000
                    return unichr(cp)
                else:
                    return unichr(high) + unichr(low)
            else:
                return unichr(int(m.group(1), 16))
        return _surrogateRe.sub(repl, inp)

    if isinstance(obj, dict):
        return {decode_str(k): unescape_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [unescape_json(x) for x in obj]
    elif isinstance(obj, text_type):
        return decode_str(obj)
    else:
        return obj


def lint_dat_format(path, encoding, first_header):
    try:
        if encoding is not None:
            with codecs.open(path, "r", encoding=encoding) as fp:
                dat = fp.read()
                parsed = parser.parse(dat, first_header)
        else:
            with open(path, "rb") as fp:
                dat = fp.read()
                parsed = parser.parse(dat, first_header)
    except NoParseError as e:
        print("parse error in %s, %s" % (path, e))
        return

    for item in parsed:
        headers = Counter(x[0] for x in item)
        headers.subtract(set(headers.elements()))  # remove one instance of each
        for header in set(headers.elements()):
            c = headers[header]
            print("%s occurs %d times in one test in %s" % (header, c + 1, path))

    return [OrderedDict(x) for x in parsed]


def lint_encoding_test(path):
    parsed = lint_dat_format(path, None, b"data")
    if not parsed:
        return
    for test in parsed:
        if not is_subsequence(list(test.keys()), [b"data", b"encoding"]):
            print("unexpected test headings %r in %s" % (test.keys(), path))


def lint_encoding_tests(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if not file.endswith(".dat"):
                continue
            lint_encoding_test(clean_path(join(root, file)))


def lint_tokenizer_test(path):
    all_keys = set(["description", "input", "output", "initialStates",
                    "lastStartTag", "ignoreErrorOrder", "doubleEscaped"])
    required = set(["input", "output"])
    with codecs.open(path, "r", "utf-8") as fp:
        parsed = json.load(fp)
    if not parsed:
        return
    if not isinstance(parsed, dict):
        print("Top-level must be an object in %s" % path)
        return
    for test_group in parsed.values():
        if not isinstance(test_group, list):
            print("Test groups must be a lists in %s" % path)
            continue
        for test in test_group:
            if 'doubleEscaped' in test and test['doubleEscaped'] is True:
                test = unescape_json(test)
            keys = set(test.keys())
            if not (required <= keys):
                print("missing test properties %r in %s" % (required - keys, path))
            if not (keys <= all_keys):
                print("unknown test properties %r in %s" % (keys - all_keys, path))


def lint_tokenizer_tests(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if not file.endswith(".test"):
                continue
            lint_tokenizer_test(clean_path(join(root, file)))


def lint_tree_construction_test(path):
    parsed = lint_dat_format(path, "utf-8", "data")
    if not parsed:
        return
    seen = set()
    for test in parsed:
        if not is_subsequence(list(test.keys()), ["data", "errors", "document-fragment",
                                                  "script-off", "script-on", "document"]):
            print("unexpected test headings %r in %s" % (test.keys(), path))
            continue
        items = tuple(test.items())
        if items in seen:
            print("Duplicate test %r in %s" % (items, path))
        seen.add(items)


def lint_tree_construction_tests(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if not file.endswith(".dat"):
                continue
            lint_tree_construction_test(clean_path(join(root, file)))


def main():
    lint_encoding_tests(join(base, "encoding"))
    lint_tokenizer_tests(join(base, "tokenizer"))
    lint_tree_construction_tests(join(base, "tree-construction"))


if __name__ == "__main__":
    main()
