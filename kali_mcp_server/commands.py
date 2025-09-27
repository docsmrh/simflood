"""Allow-listed command specifications for the Kali MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import shutil
from typing import Iterable, Sequence

_ALLOWED_VALUE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:,/@?=&%+*-{}[]\"'~"
_SAFE_VALUE_PATTERN = re.compile(rf"^[{re.escape(_ALLOWED_VALUE_CHARS)}]+$")


@dataclass(frozen=True)
class CommandSpec:
    """Metadata describing how a command may be executed safely."""

    name: str
    binary: str
    description: str
    default_args: tuple[str, ...] = field(default_factory=tuple)
    allowed_flags: frozenset[str] = field(default_factory=frozenset)
    allowed_flag_prefixes: tuple[str, ...] = field(default_factory=tuple)
    allow_positional: bool = True
    example: str | None = None
    notes: str | None = None
    timeout: float = 300.0
    max_arguments: int = 16

    def normalize_arguments(self, user_arguments: Sequence[str] | None) -> list[str]:
        """Validate and normalise arguments according to the specification."""

        arguments: list[str] = list(self.default_args)
        if not user_arguments:
            return arguments

        if len(user_arguments) > self.max_arguments:
            raise ValueError(
                f"Too many arguments provided for {self.name}. Limit is {self.max_arguments}."
            )

        for raw_arg in user_arguments:
            arg = raw_arg.strip()
            if not arg:
                raise ValueError("Empty arguments are not permitted.")

            if arg.startswith("-"):
                if arg in self.allowed_flags or any(
                    arg.startswith(prefix) for prefix in self.allowed_flag_prefixes
                ):
                    arguments.append(arg)
                    continue
                raise ValueError(
                    f"Flag '{arg}' is not in the allow list for {self.name}."
                )

            if not self.allow_positional:
                raise ValueError(
                    f"Positional arguments are disabled for {self.name}; please use explicit flags."
                )

            if not _SAFE_VALUE_PATTERN.match(arg):
                raise ValueError(
                    "Only alphanumeric characters and _ . : , / @ ? = % + * - are allowed in positional values."
                )

            arguments.append(arg)

        return arguments

    def is_installed(self) -> bool:
        """Return True when the binary exists in PATH."""

        return shutil.which(self.binary) is not None


def _flags(*items: str) -> frozenset[str]:
    return frozenset(items)


def _prefixes(*items: str) -> tuple[str, ...]:
    return tuple(items)


COMMANDS: dict[str, CommandSpec] = {
    spec.name: spec
    for spec in [
        CommandSpec(
            name="nmap",
            binary="nmap",
            description="Network mapper for discovery, port scanning and service detection.",
            default_args=("-Pn",),
            allowed_flags=_flags(
                "-sV",
                "-sS",
                "-O",
                "-A",
                "-Pn",
                "-vv",
                "-vvv",
                "-n",
                "-6",
                "--open",
                "--reason",
                "--traceroute",
                "--disable-arp-ping",
            ),
            allowed_flag_prefixes=_prefixes(
                "-p",
                "-T",
                "--top-ports",
                "-o",
                "--script",
                "--max-retries",
                "--min-rate",
                "--max-rate",
            ),
            example="nmap -sV -p 80,443 example.com",
            notes="Large scans may take a long time; consider limiting the port range.",
            timeout=420.0,
        ),
        CommandSpec(
            name="sqlmap",
            binary="sqlmap",
            description="Automated SQL injection detection and exploitation framework.",
            allowed_flags=_flags(
                "--batch",
                "--random-agent",
                "--flush-session",
                "--threads",
                "--tor",
                "--tor-type",
                "--risk",
                "--level",
                "--forms",
                "-v",
                "-o",
                "-r",
                "-c",
                "-p",
            ),
            allowed_flag_prefixes=_prefixes(
                "-u",
                "--risk",
                "--level",
                "--technique",
                "--tamper",
                "--threads",
                "--time-sec",
                "--delay",
                "--timeout",
            ),
            example="sqlmap -u https://example.com/page.php?id=1 --batch",
            notes="sqlmap can generate significant traffic; ensure you have permission before scanning.",
            timeout=600.0,
        ),
        CommandSpec(
            name="subfinder",
            binary="subfinder",
            description="Passive subdomain discovery utility.",
            allowed_flags=_flags(
                "-silent",
                "-all",
                "-recursive",
                "-nc",
            ),
            allowed_flag_prefixes=_prefixes(
                "-d",
                "-dL",
                "-o",
                "-oJ",
                "-oD",
                "-t",
            ),
            example="subfinder -d example.com -silent",
        ),
        CommandSpec(
            name="nikto",
            binary="nikto",
            description="Web server vulnerability scanner.",
            allowed_flags=_flags(
                "-ssl",
                "-useproxy",
                "-Plugins",
                "-Tuning",
                "-no404",
                "-mutate",
                "-Display",
                "-Cgidirs",
                "-maxtime",
            ),
            allowed_flag_prefixes=_prefixes(
                "-h",
                "-p",
                "-o",
                "-Format",
                "-Tuning",
                "-timeout",
            ),
            example="nikto -h https://example.com -ssl",
        ),
        CommandSpec(
            name="gobuster",
            binary="gobuster",
            description="Directory, DNS and VHost brute forcing utility.",
            allowed_flags=_flags(
                "-k",
                "-r",
                "-fw",
                "-fa",
                "-q",
                "-v",
            ),
            allowed_flag_prefixes=_prefixes(
                "dir",
                "dns",
                "vhost",
                "fuzz",
                "-u",
                "-w",
                "-t",
                "-p",
                "-o",
                "-s",
                "-x",
                "-b",
            ),
            example="gobuster dir -u https://example.com -w /path/to/wordlist.txt",
            notes="Specify the mode as the first argument (dir/dns/vhost/fuzz).",
        ),
        CommandSpec(
            name="theharvester",
            binary="theHarvester",
            description="Information gathering tool for emails, domains and hosts.",
            allowed_flags=_flags(
                "-v",
                "-f",
                "-n",
                "-c",
            ),
            allowed_flag_prefixes=_prefixes(
                "-d",
                "-l",
                "-b",
                "-h",
                "-s",
                "-g",
                "-p",
            ),
            example="theHarvester -d example.com -b bing",
        ),
        CommandSpec(
            name="tshark",
            binary="tshark",
            description="Terminal network protocol analyser from the Wireshark suite.",
            allowed_flags=_flags(
                "-V",
                "-r",
                "-l",
                "-t",
                "-q",
                "-O",
            ),
            allowed_flag_prefixes=_prefixes(
                "-i",
                "-f",
                "-Y",
                "-T",
                "-o",
            ),
            example="tshark -i eth0 -Y http",
            notes="Capturing may require elevated permissions; ensure you comply with local policies.",
        ),
        CommandSpec(
            name="john",
            binary="john",
            description="John the Ripper password cracking utility.",
            allowed_flags=_flags(
                "--show",
                "--test",
                "--wordlist",
                "--rules",
                "--incremental",
                "--format",
            ),
            allowed_flag_prefixes=_prefixes(
                "--wordlist",
                "--rules",
                "--format",
                "--session",
                "--restore",
            ),
            example="john --wordlist=/path/to/wordlist.txt hashes.txt",
            notes="Be mindful of resource consumption when running intensive cracking jobs.",
            timeout=900.0,
        ),
        CommandSpec(
            name="tcpdump",
            binary="tcpdump",
            description="Packet capture tool for network troubleshooting and analysis.",
            allowed_flags=_flags(
                "-n",
                "-nn",
                "-e",
                "-q",
                "-v",
                "-vv",
                "-vvv",
                "-X",
                "-XX",
                "-w",
                "-r",
                "-tt",
                "-tttt",
            ),
            allowed_flag_prefixes=_prefixes(
                "-i",
                "-s",
                "-c",
                "-G",
                "-W",
                "-C",
                "-F",
                "-E",
                "-Z",
            ),
            example="tcpdump -i eth0 -c 100 port 443",
            notes="Requires capture privileges; output can grow quickly so consider limiting packet count.",
        ),
        CommandSpec(
            name="curl",
            binary="curl",
            description="Command line transfer tool supporting numerous protocols.",
            allowed_flags=_flags(
                "-I",
                "-L",
                "-k",
                "-v",
                "-s",
                "-S",
                "-o",
                "-O",
                "-X",
                "-u",
                "--data",
                "--data-binary",
                "--data-urlencode",
                "--header",
                "--head",
                "--compressed",
                "--resolve",
            ),
            allowed_flag_prefixes=_prefixes(
                "http://",
                "https://",
                "ftp://",
                "--url",
                "--user",
                "--proxy",
                "--max-time",
                "--connect-timeout",
            ),
            example="curl -I https://example.com",
            notes="Use --data/--data-binary to submit payloads explicitly; positional values are treated as URLs.",
            timeout=180.0,
        ),
        CommandSpec(
            name="wget",
            binary="wget",
            description="Non-interactive network downloader.",
            allowed_flags=_flags(
                "-q",
                "-v",
                "-O",
                "-o",
                "-c",
                "-r",
                "-np",
                "-nH",
                "--cut-dirs",
                "--limit-rate",
                "--user",
                "--password",
            ),
            allowed_flag_prefixes=_prefixes(
                "http://",
                "https://",
                "ftp://",
                "--user",
                "--password",
                "--limit-rate",
                "--reject",
                "--accept",
            ),
            example="wget https://example.com/index.html",
        ),
        CommandSpec(
            name="ssh",
            binary="ssh",
            description="OpenSSH secure remote login client.",
            allowed_flags=_flags(
                "-i",
                "-p",
                "-v",
                "-vv",
                "-vvv",
                "-o",
                "-J",
                "-L",
                "-R",
                "-D",
                "-N",
                "-T",
                "-f",
                "-F",
                "-4",
                "-6",
            ),
            allowed_flag_prefixes=_prefixes(
                "-p",
                "-i",
                "-o",
                "-L",
                "-R",
                "-D",
                "-J",
            ),
            example="ssh -p 2222 user@example.com",
            notes="Interactive sessions will stream until the command completes; consider using -N for port forwarding only.",
            timeout=600.0,
        ),
        CommandSpec(
            name="searchsploit",
            binary="searchsploit",
            description="Exploit Database command line search utility.",
            allowed_flags=_flags(
                "-m",
                "-x",
                "-v",
                "-j",
                "-u",
                "-p",
                "-w",
                "-t",
                "-s",
            ),
            allowed_flag_prefixes=_prefixes(
                "-c",
                "-e",
                "-p",
            ),
            example="searchsploit -t wordpress",
        ),
    ]
}


def get_command(name: str) -> CommandSpec:
    """Retrieve a command specification by name, raising KeyError when missing."""

    key = name.strip().lower()
    if key not in COMMANDS:
        raise KeyError(f"Unknown command '{name}'.")
    return COMMANDS[key]


def iter_commands() -> Iterable[CommandSpec]:
    """Return an iterable of all available command specifications."""

    return COMMANDS.values()


__all__ = ["CommandSpec", "COMMANDS", "get_command", "iter_commands"]
