from __future__ import annotations

import errno
import importlib
import importlib.metadata
import io
import os
import runpy
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import cuid2.cli
import cuid2.generator
import cuid2.utils
from cuid2 import BIG_LENGTH, DEFAULT_LENGTH, MIN_LENGTH, create_id, is_cuid
from cuid2.cli import main as cli_main

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import Mock


def _assert_cli_exits(args: list[str], expected_code: int) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli_main(args)
    assert exc_info.value.code == expected_code


class TestCli:
    def test_cli_default_length(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that the CLI prints a default-length CUID when invoked without arguments."""
        cli_main([])
        captured = capsys.readouterr()
        assert is_cuid(captured.out.strip(), min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        assert captured.err == ""

        monkeypatch.setattr("sys.argv", ["cuid2"])
        cli_main()
        captured_default_argv = capsys.readouterr()
        assert is_cuid(captured_default_argv.out.strip(), min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        assert captured_default_argv.err == ""

    def test_cli_module_execution(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that running python -m cuid2 invokes the console entry point."""
        monkeypatch.setattr("sys.argv", ["cuid2", "--slug"])
        runpy.run_module("cuid2", run_name="__main__", alter_sys=True)
        out = capsys.readouterr().out.strip()
        assert is_cuid(out, min_length=5, max_length=5) is True

    def test_cli_console_script_entry_point(self: TestCli) -> None:
        """Tests that the installed cuid2 console script targets cuid2.cli.main."""
        (entry_point,) = importlib.metadata.entry_points(group="console_scripts", name="cuid2")
        assert entry_point.load() is cuid2.cli.main

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_cli_help(self: TestCli, flag: str, capsys: pytest.CaptureFixture[str]) -> None:
        """Tests that -h and --help print usage and flag documentation to stdout and exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main([flag])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        for expected in (
            "usage: cuid2",
            "24",
            "2..32",
            "Generation",
            "validation",
            "--slug",
            "--count",
            "--fingerprint",
            "--check",
            "--quiet",
        ):
            assert expected in captured.out
        assert captured.err == ""

    @pytest.mark.parametrize("flag", ["-V", "--version"])
    def test_cli_version(self: TestCli, flag: str, capsys: pytest.CaptureFixture[str]) -> None:
        """Tests that -V and --version print the package version to stdout and exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main([flag])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == f"cuid2 {importlib.metadata.version('cuid2')}\n"
        assert captured.err == ""

    def test_cli_lowercase_v_is_not_version(self: TestCli, capsys: pytest.CaptureFixture[str]) -> None:
        """Tests that -v is not a version alias, leaving it free for a conventional verbose flag."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["-v"])
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "unrecognized arguments: -v" in captured.err

    @pytest.mark.parametrize(
        ("args", "expected_length"),
        [
            (["2"], 2),
            (["10"], 10),
            (["32"], 32),
            (["-l", "10"], 10),
            (["-l", "2"], MIN_LENGTH),
            (["-l", "32"], BIG_LENGTH),
            (["--length", "16"], 16),
            (["--slug"], 5),
        ],
    )
    def test_cli_custom_length(
        self: TestCli,
        args: list[str],
        expected_length: int,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that the CLI prints a CUID of the requested custom length."""
        cli_main(args)
        captured = capsys.readouterr()
        assert is_cuid(captured.out.strip(), min_length=expected_length, max_length=expected_length) is True
        assert captured.err == ""

    @pytest.mark.parametrize(
        ("args", "expected_substring"),
        [
            (["1"], "length must be at least 2 characters"),
            (["-l", "1"], "length must be at least 2 characters"),
            (["0"], "length must be at least 2 characters"),
            (["-l", "0"], "length must be at least 2 characters"),
            (["-5"], "length must be at least 2 characters"),
            (["--", "-5"], "length must be at least 2 characters"),
            (["-l", "-5"], "length must be at least 2 characters"),
            (["--length=-5"], "length must be at least 2 characters"),
            (["--check", "ab", "-l", "1"], "length must be at least 2 characters"),
            (["--check", "ab", "1"], "length must be at least 2 characters"),
            ([str(BIG_LENGTH + 1)], "length must never exceed 32 characters"),
            (["-l", str(BIG_LENGTH + 1)], "length must never exceed 32 characters"),
            (["--length", str(BIG_LENGTH + 1)], "length must never exceed 32 characters"),
            (["98"], "length must never exceed 32 characters"),
            (["99"], "length must never exceed 32 characters"),
            (["--check", "ab", "-l", "40"], "length must never exceed 32 characters"),
            (["invalid"], "invalid int value:"),
            (["-l", "abc"], "invalid int value:"),
        ],
    )
    def test_cli_invalid_lengths(
        self: TestCli,
        args: list[str],
        expected_substring: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that the CLI exits with code 2 when given an invalid or out-of-range length."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main(args)
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "cuid2: error:" in err
        assert expected_substring in err

    @pytest.mark.parametrize(
        "args",
        [
            ["10", "-l", "12"],
            ["10", "--slug"],
            ["-l", "10", "--slug"],
            ["10", "-l", "12", "--slug"],
        ],
    )
    def test_cli_conflicting_length_arguments(
        self: TestCli,
        args: list[str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that specifying multiple length options exits with code 2."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main(args)
        assert exc_info.value.code == 2
        assert "conflicting length arguments" in capsys.readouterr().err

    @pytest.mark.parametrize("flag", [["-n", "5"], ["-c", "5"], ["--count", "5"]])
    def test_cli_batch_count(
        self: TestCli,
        flag: list[str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that batch count flags print multiple unique CUIDs and instantiate Cuid once."""
        cli_main(flag)
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 5
        assert len(set(lines)) == 5
        assert all(is_cuid(item, min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True for item in lines)

        cli_main(["-l", "12", "-n", "3"])
        captured = capsys.readouterr()
        batch = captured.out.splitlines()
        assert len(batch) == 3
        assert len(set(batch)) == 3
        assert all(is_cuid(item, min_length=12, max_length=12) is True for item in batch)
        assert captured.err == ""

    @pytest.mark.parametrize(
        ("args", "expected_substring"),
        [
            (["-n", "0"], "count must be at least 1"),
            (["-c", "-2"], "count must be at least 1"),
            (["--count", "abc"], "invalid int value"),
        ],
    )
    def test_cli_invalid_count(
        self: TestCli,
        args: list[str],
        expected_substring: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that invalid count values exit with code 2."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main(args)
        assert exc_info.value.code == 2
        assert expected_substring in capsys.readouterr().err

    def test_cli_custom_fingerprint(
        self: TestCli,
        mocker: Mock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that -f/--fingerprint is hashed verbatim (like upstream) and rejects empty strings."""
        hash_spy = mocker.spy(cuid2.utils, "_create_hash_slice")
        cli_main(["-f", "host-a", "-n", "2"])
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 2
        assert all(is_cuid(item, min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True for item in lines)
        assert hash_spy.call_count == 2
        assert all(call.args[0].endswith("host-a") for call in hash_spy.call_args_list)

        hash_spy.reset_mock()
        cli_main(["--fingerprint", "host-b"])
        single = capsys.readouterr().out.strip()
        assert is_cuid(single, min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        hash_spy.assert_called_once()
        assert hash_spy.call_args.args[0].endswith("host-b")

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["-f", ""])
        assert exc_info.value.code == 2
        assert "fingerprint must not be empty" in capsys.readouterr().err

    def test_cli_check_direct_argument(self: TestCli, capsys: pytest.CaptureFixture[str]) -> None:
        """Tests --check and --validate with direct candidate arguments and optional length constraints."""
        valid_id = create_id()
        short_id = create_id(length=10)
        big_id = create_id(length=BIG_LENGTH)

        for flag in ("--check", "--validate"):
            with pytest.raises(SystemExit) as exc_info:
                cli_main([flag, valid_id])
            assert exc_info.value.code == 0
            assert capsys.readouterr().out == f"{valid_id}: valid\n"

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "NotACuid!"])
        assert exc_info.value.code == 1
        assert capsys.readouterr().out == "NotACuid!: invalid\n"

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", ""])
        assert exc_info.value.code == 1
        assert capsys.readouterr().out == "<empty>: invalid\n"

        for raw, escaped in (("a\x1b[31m\rX", "a\\x1b[31m\\rX"), ("é", "\\xe9")):
            with pytest.raises(SystemExit) as exc_info:
                cli_main(["--check", raw])
            assert exc_info.value.code == 1
            assert capsys.readouterr().out == f"{escaped}: invalid\n"

        for check_args in (
            ["--check", short_id, "-l", "10"],
            ["10", "--check", short_id],
            ["--slug", "--check", create_id(length=5)],
        ):
            with pytest.raises(SystemExit) as exc_info:
                cli_main(check_args)
            assert exc_info.value.code == 0
            capsys.readouterr()

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", valid_id, "-l", "10"])
        assert exc_info.value.code == 1
        assert capsys.readouterr().out == f"{valid_id}: invalid\n"

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", big_id, "-l", str(BIG_LENGTH)])
        assert exc_info.value.code == 0
        assert capsys.readouterr().out == f"{big_id}: valid\n"

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", big_id])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == f"{big_id}: valid\n"
        assert captured.err == ""

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "a" * (BIG_LENGTH + 1)])
        assert exc_info.value.code == 1
        assert capsys.readouterr().out == f"{'a' * (BIG_LENGTH + 1)}: invalid\n"

    def test_cli_check_stdin_and_quiet(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests --check with '-' stdin streams and -q/--quiet suppression."""
        id1 = create_id()
        id2 = create_id()

        monkeypatch.setattr("sys.stdin", io.StringIO(f"{id1}\n{id2}\r\n"))
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "-"])
        assert exc_info.value.code == 0
        assert capsys.readouterr().out == f"{id1}: valid\n{id2}: valid\n"

        monkeypatch.setattr("sys.stdin", io.StringIO(f"{id1}\nBAD_ID\n"))
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "-"])
        assert exc_info.value.code == 1
        assert capsys.readouterr().out == f"{id1}: valid\nBAD_ID: invalid\n"

        monkeypatch.setattr("sys.stdin", io.StringIO(f"\n{id1}\n\r\n{id2}\n\n"))
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "-"])
        assert exc_info.value.code == 0
        assert capsys.readouterr().out == f"{id1}: valid\n{id2}: valid\n"

        for empty_stdin in ("", "\n\r\n"):
            monkeypatch.setattr("sys.stdin", io.StringIO(empty_stdin))
            with pytest.raises(SystemExit) as exc_info:
                cli_main(["--check", "-"])
            assert exc_info.value.code == 1
            assert capsys.readouterr().out == "<empty>: invalid\n"

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", id1, "-q"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--validate", "BAD_ID", "--quiet"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "-", "-q"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_cli_check_invalid_flag_combinations(
        self: TestCli,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that incompatible flag combinations with --check or -q exit with code 2."""
        valid_id = create_id()

        with pytest.raises(SystemExit) as exc_info:
            cli_main(["-q"])
        assert exc_info.value.code == 2
        assert "argument -q/--quiet: only allowed with --check/--validate" in capsys.readouterr().err

        for bad_args in (["--check", valid_id, "-n", "1"], ["--check", valid_id, "-f", "srv"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_main(bad_args)
            assert exc_info.value.code == 2
            assert "not allowed with --check/--validate" in capsys.readouterr().err

    def test_cli_broken_pipe(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        mocker: Mock,
    ) -> None:
        """Tests that BrokenPipeError on stdout redirects stdout fd to devnull and flushes before closing."""
        fake_stdout = io.StringIO()
        monkeypatch.setattr("sys.stdout", fake_stdout)
        write_mock = mocker.patch.object(fake_stdout, "write", side_effect=BrokenPipeError)
        cli_main(["-n", "5"])
        write_mock.assert_called_once()
        assert fake_stdout.getvalue() == ""

        calls: list[str] = []
        mocker.patch.object(fake_stdout, "fileno", return_value=1)
        open_mock = mocker.patch("os.open", return_value=99)
        dup2_mock = mocker.patch("os.dup2", side_effect=lambda *_args: calls.append("dup2"))
        flush_mock = mocker.patch.object(fake_stdout, "flush", side_effect=lambda: calls.append("flush"))
        close_mock = mocker.patch("os.close", side_effect=lambda *_args: calls.append("close"))
        cli_main(["-n", "5"])
        open_mock.assert_called_once_with(os.devnull, os.O_WRONLY)
        dup2_mock.assert_called_once_with(99, 1)
        flush_mock.assert_called_once_with()
        close_mock.assert_called_once_with(99)
        assert calls == ["dup2", "flush", "close"]

    def test_cli_check_broken_pipe_is_not_success(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        mocker: Mock,
    ) -> None:
        """Tests that --check exits 1 when stdout closes before every candidate is validated."""
        fake_stdout = io.StringIO()
        monkeypatch.setattr("sys.stdout", fake_stdout)
        mocker.patch.object(fake_stdout, "write", side_effect=BrokenPipeError)
        monkeypatch.setattr("sys.stdin", io.StringIO(f"{create_id()}\n{create_id()}\n"))
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--check", "-"])
        assert exc_info.value.code == 1

    def test_cli_check_invalid_utf8_stdin(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that --check - reconfigures TextIOWrapper stdin with surrogateescape instead of crashing."""
        valid_id = create_id()

        with monkeypatch.context() as mp:
            mp.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"\xff\xfe\n"), encoding="utf-8", errors="strict"))
            _assert_cli_exits(["--check", "-"], 1)
            captured = capsys.readouterr()
            assert captured.out == "\\udcff\\udcfe: invalid\n"
            assert captured.err == ""

        with monkeypatch.context() as mp:
            mp.setattr(
                "sys.stdin",
                io.TextIOWrapper(io.BytesIO(f"{valid_id}\n".encode() + b"a\x80\n"), encoding="utf-8", errors="strict"),
            )
            _assert_cli_exits(["--check", "-"], 1)
            captured = capsys.readouterr()
            assert captured.out == f"{valid_id}: valid\na\\udc80: invalid\n"
            assert captured.err == ""

    def test_cli_closed_stdio(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        mocker: Mock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests generation, --version, and --check behavior when stdin or stdout is closed."""
        valid_id = create_id()

        with monkeypatch.context() as mp:
            mp.setattr("sys.stdout", None)
            cli_main([])
            _assert_cli_exits(["-V"], 0)
            _assert_cli_exits(["-h"], 0)
            assert capsys.readouterr().err == ""
            _assert_cli_exits(["--check", valid_id, "-q"], 0)
            _assert_cli_exits(["--check", "BAD_ID", "-q"], 1)
            _assert_cli_exits(["--check", valid_id], 1)

        with monkeypatch.context() as mp:
            closed_out = io.StringIO()
            closed_out.close()
            mp.setattr("sys.stdout", closed_out)
            cli_main(["-n", "2"])
            _assert_cli_exits(["-V"], 0)
            _assert_cli_exits(["-h"], 0)
            assert sys.stdout is closed_out
            _assert_cli_exits(["--check", valid_id, "-q"], 0)

        with monkeypatch.context() as mp:
            fake_stdout = io.StringIO()
            mp.setattr("sys.stdout", fake_stdout)
            mocker.patch.object(fake_stdout, "flush", side_effect=OSError(errno.EBADF, "Bad file descriptor"))
            _assert_cli_exits(["--check", valid_id], 1)

        with monkeypatch.context() as mp:
            mp.setattr("sys.stdin", None)
            _assert_cli_exits(["--check", "-"], 1)
            captured_stdin_none = capsys.readouterr()
            assert captured_stdin_none.out == ""
            assert captured_stdin_none.err == ""
            _assert_cli_exits(["--check", "-", "-q"], 1)
            captured_stdin_none_quiet = capsys.readouterr()
            assert captured_stdin_none_quiet.out == ""
            assert captured_stdin_none_quiet.err == ""

        with monkeypatch.context() as mp:
            closed_in = io.StringIO()
            closed_in.close()
            mp.setattr("sys.stdin", closed_in)
            _assert_cli_exits(["--check", "-"], 1)
            captured_closed_in = capsys.readouterr()
            assert captured_closed_in.out == ""
            assert captured_closed_in.err == ""

    def test_cli_duck_typed_stdout(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests minimal duck-typed stdout writers without .closed or .fileno attributes."""
        chunks: list[str] = []
        broken = False

        class _MinimalWriter:
            def write(self: _MinimalWriter, s: str) -> int:
                if broken:
                    raise BrokenPipeError
                chunks.append(s)
                return len(s)

            def flush(self: _MinimalWriter) -> None:
                return None

        writer = _MinimalWriter()
        assert not hasattr(writer, "closed")
        assert not hasattr(writer, "fileno")
        monkeypatch.setattr("sys.stdout", writer)

        cli_main([])
        assert is_cuid("".join(chunks).strip(), min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        chunks.clear()

        _assert_cli_exits(["-h"], 0)
        assert "usage: cuid2" in "".join(chunks)
        chunks.clear()

        broken = True
        cli_main([])
        _assert_cli_exits(["-h"], 0)
        assert chunks == []
        assert capsys.readouterr().err == ""

    def test_cli_real_io_errors_propagate(
        self: TestCli,
        monkeypatch: pytest.MonkeyPatch,
        mocker: Mock,
    ) -> None:
        """Tests that non-closed OSErrors on stdout, CSPRNG generation, and stdin propagate."""
        with monkeypatch.context() as mp:
            fake_stdout = io.StringIO()
            mp.setattr("sys.stdout", fake_stdout)
            mocker.patch.object(fake_stdout, "write", side_effect=OSError(errno.ENOSPC, "No space left on device"))
            with pytest.raises(OSError, match="No space left on device") as exc_info:
                cli_main(["-n", "2"])
            assert exc_info.value.errno == errno.ENOSPC

        with monkeypatch.context() as mp:
            fake_stdout = io.StringIO()
            mp.setattr("sys.stdout", fake_stdout)
            mocker.patch.object(fake_stdout, "flush", side_effect=OSError(errno.ENOSPC, "No space left on device"))
            with pytest.raises(OSError, match="No space left on device") as exc_info:
                cli_main(["-n", "2"])
            assert exc_info.value.errno == errno.ENOSPC

        with monkeypatch.context() as mp:

            class _BrokenStdin:
                def __iter__(self: _BrokenStdin) -> Iterator[str]:
                    err_msg = "Input/output error"
                    raise OSError(errno.EIO, err_msg)

            mp.setattr("sys.stdin", _BrokenStdin())
            with pytest.raises(OSError, match="Input/output error") as exc_info:
                cli_main(["--check", "-"])
            assert exc_info.value.errno == errno.EIO

        mocker.patch("cuid2.generator.Cuid.generate", side_effect=OSError(errno.EIO, "Input/output error"))
        with pytest.raises(OSError, match="Input/output error") as exc_info:
            cli_main(["-n", "2"])
        assert exc_info.value.errno == errno.EIO

    @pytest.mark.parametrize(
        ("cmd", "stdin_bytes", "expected_rc", "expected_stdout"),
        [
            pytest.param(
                ["-m", "cuid2", "--check", "-"],
                b"\xff\xfe\n",
                1,
                b"\\udcff\\udcfe: invalid\n",
                id="invalid_utf8_stdin",
            ),
            pytest.param(
                ["-c", "import os, cuid2.cli; os.close(1); cuid2.cli.main(['--check', 'ab'])"],
                None,
                1,
                b"",
                id="close_fd1_check",
            ),
            pytest.param(
                ["-c", "import os, cuid2.cli; os.close(1); cuid2.cli.main(['--check', 'ab', '-q'])"],
                None,
                0,
                b"",
                id="close_fd1_check_quiet",
            ),
            pytest.param(
                ["-c", "import os, cuid2.cli; os.close(0); cuid2.cli.main(['--check', '-'])"],
                None,
                1,
                b"",
                id="close_fd0_check_stdin",
            ),
            pytest.param(
                ["-c", "import os, cuid2.cli; os.close(1); cuid2.cli.main([])"],
                None,
                0,
                b"",
                id="close_fd1_generate",
            ),
            pytest.param(
                ["-c", "import os, cuid2.cli; os.close(1); cuid2.cli.main(['-V'])"],
                None,
                0,
                b"",
                id="close_fd1_version",
            ),
            pytest.param(
                ["-c", "import os, cuid2.cli; os.close(1); cuid2.cli.main(['-h'])"],
                None,
                0,
                b"",
                id="close_fd1_help",
            ),
        ],
    )
    def test_cli_closed_stdio_subprocess(
        self: TestCli,
        cmd: list[str],
        stdin_bytes: bytes | None,
        expected_rc: int,
        expected_stdout: bytes,
    ) -> None:
        """Tests real OS descriptor closure and invalid UTF-8 stdin in isolated child interpreters."""
        res = subprocess.run(  # noqa: S603
            [sys.executable, "-I", *cmd],
            input=stdin_bytes,
            stdin=None if stdin_bytes is not None else subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        assert res.returncode == expected_rc
        assert res.stdout.replace(b"\r\n", b"\n") == expected_stdout
        assert res.stderr == b""

    def test_cli_does_not_initialize_generator_on_import(
        self: TestCli,
        mocker: Mock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Tests that importing cuid2.cli does not initialize a CUID generator or version metadata until needed."""
        try:
            cuid_spy = mocker.spy(cuid2.generator, "Cuid")
            version_spy = mocker.spy(importlib.metadata, "version")
            importlib.reload(cuid2.cli)
            assert cuid_spy.call_count == 0
            assert version_spy.call_count == 0
            assert cuid2.generator._default_generator is None
            assert not hasattr(cuid2.cli, "generate_cuid")
            cuid2.cli.main([])
            assert cuid_spy.call_count == 1
            assert version_spy.call_count == 0
            assert cuid2.generator._default_generator is None
            output = capsys.readouterr().out.strip()
            assert len(output) == DEFAULT_LENGTH
        finally:
            mocker.stopall()
            importlib.reload(cuid2.cli)
