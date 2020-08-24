Encoding Tests
==============

Each file containing encoding tests has any number of tests separated by
two newlines (LF) and a single newline before the end of the file:

    [TEST]LF
    LF
    [TEST]LF
    LF
    [TEST]LF

...where [TEST] is the format documented below.

Encoding test format
====================

Each test must begin with a string "\#data", followed by a newline (LF).
All subsequent lines until a line that says "\#encoding" are the test data
and must be passed to the system being tested unchanged, except with the
final newline (on the last line) removed.

Then there must be a line that says "\#encoding", followed by a newline
(LF), followed by string indicating an encoding name, followed by a newline
(LF). The encoding name indicated is the expected character encoding for
the output with the given test data as input.

For the tests in the `preparsed` subdirectory, the encoding name indicated
is the expected result of running the *encoding sniffing algorithm* at
https://html.spec.whatwg.org/#encoding-sniffing-algorithm with the given
test data as input; this is, it's the expected result of running *only* the
*encoding sniffing algorithm* — without also running the tokenization state
machine and tree-construction stage defined in the spec — and specifically,
for running the *prescan the byte stream to determine its encoding*
https://html.spec.whatwg.org/#prescan-a-byte-stream-to-determine-its-encoding
algorithm on only the first 1024 bytes of the test data.

For all tests outside the subdirectory named `preparsed`, the encoding name
indicated is instead the expected character encoding for the output after
fully parsing the given test data; that is, it's the expected character
encoding for the output after running the tokenization state machine and
tree-construction stage.
