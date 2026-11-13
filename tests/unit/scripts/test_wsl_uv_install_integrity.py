"""Execute the pinned installer against synthetic archives without network access."""

import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("exit_code", [0, 7])
def test_powershell_51_preserves_script_bytes_and_native_arguments(tmp_path, exit_code):
    """Exercise the declared Windows runtime without invoking WSL or networking."""
    powershell = Path(os.environ.get("SystemRoot", "C:/Windows")) / (
        "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    if os.name != "nt" or not powershell.exists():
        pytest.skip("Windows PowerShell 5.1 is required for the native transport test")
    source = ROOT / "scripts/engineering/dev/setup_bioetl_wsl.ps1"
    installer = (
        source.read_text().split("$uvInstallCommand = @'\n", 1)[1].split("\n'@", 1)[0]
    )
    payload = installer + '\r\nprintf "%s" "кавычки и пробелы"\r\n'
    payload_path = tmp_path / "payload.txt"
    payload_path.write_bytes(payload.encode("utf-8"))
    fake = tmp_path / "fake wsl.exe"
    harness = tmp_path / "transport.ps1"
    harness.write_text(
        r"""$ErrorActionPreference = 'Stop'
Add-Type -OutputAssembly $env:AUDIT_EXE -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.IO;
using System.Text;
public class FakeWsl {
    public static int Main(string[] args) {
        using (var target = File.Create(Environment.GetEnvironmentVariable("AUDIT_INPUT")))
            Console.OpenStandardInput().CopyTo(target);
        File.WriteAllLines(Environment.GetEnvironmentVariable("AUDIT_ARGS"),
            Array.ConvertAll(args, x => Convert.ToBase64String(Encoding.UTF8.GetBytes(x))));
        Console.WriteLine("transport-ok");
        Console.Error.WriteLine("fixture-diagnostic");
        return Int32.Parse(Environment.GetEnvironmentVariable("AUDIT_EXIT"));
    }
}
'@
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($env:AUDIT_SOURCE, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw $errors[0] }
foreach ($name in @('Convert-ToNativeArgument', 'Invoke-WslScript')) {
    $function = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
    }, $true)
    Invoke-Expression $function.Extent.Text
}
$Distro = $env:AUDIT_DISTRO
$script = [IO.File]::ReadAllText($env:AUDIT_PAYLOAD, [Text.Encoding]::UTF8)
try {
    $result = Invoke-WslScript -Script $script -Executable $env:AUDIT_EXE
    if ($env:AUDIT_EXIT -ne '0') { throw 'Expected native failure' }
    if ($result -ne 'transport-ok') { throw 'Unexpected native output' }
} catch {
    if ($env:AUDIT_EXIT -eq '0' -or $_.Exception.Message -notmatch 'exit code 7: fixture-diagnostic') { throw }
}
""",
        encoding="utf-8-sig",
    )
    distro = 'Ubuntu space "quoted" кириллица\\'
    env = dict(
        os.environ,
        AUDIT_EXE=str(fake),
        AUDIT_SOURCE=str(source),
        AUDIT_INPUT=str(tmp_path / "stdin.bin"),
        AUDIT_ARGS=str(tmp_path / "args.txt"),
        AUDIT_EXIT=str(exit_code),
        AUDIT_DISTRO=distro,
        AUDIT_PAYLOAD=str(payload_path),
    )
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-File", str(harness)],
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert (tmp_path / "stdin.bin").read_bytes() == payload.replace(
        "\r\n", "\n"
    ).encode("utf-8")
    import base64

    args = [
        base64.b64decode(line).decode("utf-8")
        for line in (tmp_path / "args.txt").read_text(encoding="utf-8-sig").splitlines()
    ]
    assert args == ["--distribution", distro, "--exec", "bash", "-s"]


@pytest.mark.parametrize(
    "mode", ["valid", "bad_hash", "unsupported_arch", "download_failure"]
)
def test_install_verifies_archive_before_replacing_binaries(tmp_path, mode):
    valid = mode == "valid"
    bash = Path("C:/Program Files/Git/bin/bash.exe")
    if not bash.exists():
        found = shutil.which("bash")
        if not found:
            pytest.skip("Bash is required for the isolated shell fixture")
        bash = Path(found)
    source = (ROOT / "scripts/engineering/dev/setup_bioetl_wsl.ps1").read_text()
    script = source.split("$uvInstallCommand = @'\n", 1)[1].split("\n'@", 1)[0]
    assert "astral.sh/uv/install.sh" not in source
    assert script.index("sha256sum --check") < script.index("tar -xzf")
    archive = tmp_path / "fixture.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        for name in ("uv", "uvx"):
            data = b"synthetic-binary"
            info = tarfile.TarInfo("uv-x86_64-unknown-linux-gnu/" + name)
            info.size = len(data)
            handle.addfile(info, io.BytesIO(data))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest() if valid else "0" * 64
    script = re.sub(r"[0-9a-f]{64}", digest, script).replace("$HOME", "$AUDIT_HOME")
    target = tmp_path / "home/.local/bin"
    target.mkdir(parents=True)
    (target / "uv").write_bytes(b"previous-install")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "curl").write_text(
        '#!/bin/sh\nwhile [ "$1" != "--output" ]; do shift; done\n'
        'cp "$AUDIT_ARCHIVE" "$2"\n',
        newline="\n",
    )
    (fake_bin / "curl").chmod(0o755)
    if mode == "unsupported_arch":
        (fake_bin / "uname").write_text("#!/bin/sh\necho aarch64\n", newline="\n")
        (fake_bin / "uname").chmod(0o755)
    if mode == "download_failure":
        (fake_bin / "curl").write_text("#!/bin/sh\nexit 7\n", newline="\n")

    def shell_path(path):
        value = str(path).replace("\\", "/")
        return (
            "/" + value[0].lower() + value[2:]
            if len(value) > 1 and value[1] == ":"
            else value
        )

    script = (
        'export PATH="$AUDIT_BIN:$PATH"\ntest "$(command -v curl)" = "$AUDIT_BIN/curl" || exit 99\n'
        + script
    )
    env = dict(
        os.environ,
        AUDIT_HOME=shell_path(tmp_path / "home"),
        AUDIT_ARCHIVE=shell_path(archive),
        AUDIT_BIN=shell_path(fake_bin),
    )
    # The fixture owns all temporary paths and never modifies the real user home.
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
    env["TMPDIR"] = shell_path(tmp_path)
    result = subprocess.run(
        [str(bash), "--noprofile", "--norc", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert (result.returncode == 0) is valid, result.stderr
    assert (target / "uv").read_bytes() == (
        b"synthetic-binary" if valid else b"previous-install"
    )
    assert (target / "uvx").exists() is valid
