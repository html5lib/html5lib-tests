from __future__ import unicode_literals

import re

from ._vendor.funcparserlib.lexer import Token, LexerError
from ._vendor.funcparserlib.parser import (Parser, State, NoParseError,
                                           finished, many, pure, skip, some)

text_type = type("")
binary_type = type(b"")


def _make_tokenizer(specs):
    # Forked from upstream funcparserlib.lexer to fix #44 and #46
    def compile_spec(spec):
        name, args = spec
        return name, re.compile(*args)

    compiled = [compile_spec(s) for s in specs]

    def match_specs(specs, str, i, position):
        if isinstance(str, text_type):
            lf = "\n"
        else:
            lf = b"\n"
        line, pos = position
        for type, regexp in specs:
            m = regexp.match(str, i)
            if m is not None:
                value = m.group()
                nls = value.count(lf)
                n_line = line + nls
                if nls == 0:
                    n_pos = pos + len(value)
                else:
                    n_pos = len(value) - value.rfind(lf) - 1
                return Token(type, value, (line, pos + 1), (n_line, n_pos))
        else:
            errline = str.splitlines()[line - 1]
            raise LexerError((line, pos + 1), errline)

    def f(str):
        length = len(str)
        line, pos = 1, 0
        i = 0
        r = []
        while i < length:
            t = match_specs(compiled, str, i, (line, pos))
            r.append(t)
            line, pos = t.end
            i += len(t.value)
        return r

    return f


_token_specs_u = [
    ('HEADER', (r"#[^\n]*\n",)),
    ('BODY', (r"[^#\n][^\n]*\n",)),
    ('EMPTY', (r'\n',)),
]

_token_specs_b = [(name, (regexp.encode("ascii"),))
                  for (name, (regexp,)) in _token_specs_u]

_tokenizer_u = _make_tokenizer(_token_specs_u)
_tokenizer_b = _make_tokenizer(_token_specs_b)


def _tokval(tok):
    return tok.value


def _headerval(tok):
    return tok.value[1:].strip()


def _many_merge(toks):
    x, xs = toks
    return [x] + xs


def _notFollowedBy(p):
    @Parser
    def __notFollowedBy(tokens, s):
        try:
            p.run(tokens, s)
        except NoParseError as e:
            return skip(pure(None)).run(tokens, State(s.pos, e.state.max))
        else:
            raise NoParseError(u'is followed by', s)

    __notFollowedBy.name = u'(notFollowedBy %s)' % (p,)
    return __notFollowedBy


def _parser(tokens, new_test_header, tok_type):
    first_header = (some(lambda tok: tok.type == "HEADER" and
                         _headerval(tok) == new_test_header) >>
                    _headerval)
    header = (some(lambda tok: tok.type == "HEADER" and
                   _headerval(tok) != new_test_header) >>
              _headerval)
    body = some(lambda tok: tok.type == "BODY") >> _tokval
    empty = some(lambda tok: tok.type == "EMPTY") >> _tokval

    actual_body = (many(body | (empty + _notFollowedBy(first_header))) >>
                   (lambda xs: tok_type().join(xs)[:-1]))

    first_segment = first_header + actual_body >> tuple
    rest_segment = header + actual_body >> tuple

    test = first_segment + many(rest_segment) >> _many_merge

    tests = (test + many(skip(empty) + test)) >> _many_merge

    toplevel = tests + skip(finished)

    return toplevel.parse(tokens)


def parse(s, new_test_header):
    if type(s) != type(new_test_header):
        raise TypeError("s and new_test_header must have same type")

    if isinstance(s, text_type):
        return _parser(_tokenizer_u(s), new_test_header, text_type)
    elif isinstance(s, binary_type):
        return _parser(_tokenizer_b(s), new_test_header, binary_type)
    else:
        raise TypeError("s must be unicode or bytes object")
