#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestrador ESTATICO do GATE 5 (verificacoes locais de seguranca) — PREPARACAO.

ETAPA 2P-E-C5-TOOLING-PREP: esta ferramenta PREPARA, de forma deterministica,
auditavel e testavel, a futura execucao controlada do GATE 5. Ela NAO executa o
GATE 5 sobre o artefato real, NAO materializa o WARP, NAO executa scanner real e
NAO acessa a rede.

Contratos:
  - entrada:  client/warp-audit/schemas/binary-audit-gate-05-input.schema.json
  - evidencia: client/warp-audit/schemas/binary-audit-gate-05-evidence.schema.json

Principios (ver docs/44 e docs/45):
  * NAO inicia, carrega, importa, emula, desassembla nem abre por associacao o
    arquivo analisado; scanners locais, quando um dia autorizados, recebem o
    arquivo como ARGUMENTO — nunca como executavel.
  * Somente mecanismos LOCAIS; nenhum upload externo, reputacao, DNS ou telemetria.
  * Fail-closed: qualquer condicao inesperada resulta em erro/parada segura; nada
    e interpretado como aprovacao.
  * Sem bibliotecas de rede (requests/urllib.request/http.client/socket/ftplib/
    smtplib/paramiko). Usa apenas a biblioteca padrao, minima.

Modos:
  --validate-only  valida configuracao/ambiente/argumentos, sem chamar scanners.
  --fixture-mode   opera apenas sobre fixtures SINTETICAS (adapter sintetico puro,
                   sem subprocess); produz evidencia FIXTURE_VALIDATION_PASS.
  (modo real)      BLOQUEADO nesta etapa: falha com
                   'GATE 5 REAL EXECUTION IS NOT AUTHORIZED'.

Nenhum estado desta ferramenta autoriza o GATE 5, a execucao do PE, o uso no
cliente ou a distribuicao. gate_5_authorized permanece false.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess  # usado apenas por run_local_command (shell=False); NAO no artefato real
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Identidade da ferramenta e constantes.
# --------------------------------------------------------------------------- #
TOOL_ID = "warp-audit-gate-05"
TOOL_VERSION = "0.1.0-prep"
SCHEMA_VERSION = 1
GATE_ID = 5
GATE_NAME = "Verificacoes locais de seguranca"

REAL_EXECUTION_BLOCK_MESSAGE = "GATE 5 REAL EXECUTION IS NOT AUTHORIZED"

# Estados procedurais FECHADOS por adapter.
STATE_NOT_RUN = "NOT_RUN"
STATE_PASS = "PASS"
STATE_FINDING = "FINDING"
STATE_ERROR = "ERROR"
STATE_TIMEOUT = "TIMEOUT"
STATE_STOP_PATH = "STOP_PATH"
ADAPTER_STATES = (
    STATE_NOT_RUN, STATE_PASS, STATE_FINDING, STATE_ERROR, STATE_TIMEOUT, STATE_STOP_PATH,
)

# Outcome do gate nesta etapa (fixture): NUNCA GATE_PASSED para o artefato real.
OUTCOME_FIXTURE_PASS = "FIXTURE_VALIDATION_PASS"
OUTCOME_VALIDATE_ONLY = "CONFIG_VALIDATION_PASS"

# Vereditos que NAO podem ser conclusao do FaithRO (apenas valor bruto de ferramenta).
NON_CONCLUSION_TERMS = ("SAFE", "BENIGN", "TRUSTED", "MALICIOUS", "CLEAN", "INFECTED")

# Modulos de rede proibidos (usado pelo self-check de imports).
FORBIDDEN_NET_MODULES = (
    "requests", "urllib.request", "urllib2", "http.client", "httplib",
    "socket", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib",
    "asyncio", "ssl", "paramiko", "aiohttp",
)

# Limites defensivos (fail-closed: rejeita excesso em vez de gerar arquivo ilimitado).
MAX_STDOUT_CHARS = 4000
MAX_STDERR_CHARS = 4000
MAX_MESSAGE_CHARS = 500
MAX_FINDINGS = 100
MAX_ADAPTER_NAME = 64
MAX_TIMEOUT_SECONDS = 3600
MAX_INPUT_BYTES = 64 * 1024 * 1024  # limite defensivo de leitura de fixture


class Gate5Error(Exception):
    """Erro fail-closed do orquestrador do GATE 5."""


class RealExecutionNotAuthorized(Gate5Error):
    """Tentativa de usar o modo real (nao autorizado nesta etapa)."""


# --------------------------------------------------------------------------- #
# Sanitizacao e privacidade.
# --------------------------------------------------------------------------- #
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DRIVE_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"'|]+")
_POSIX_HOME_RE = re.compile(r"/(?:home|Users|root)/[^\s/\"']+")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.\-]*://[^\s\"']+")
_SECRET_RE = re.compile(
    r"(?i)\b(?:token|secret|password|passwd|api[_-]?key|authorization|bearer)\b\s*[:=]?\s*\S+"
)


def sanitize_text(value: Optional[str], limit: int = MAX_STDOUT_CHARS) -> str:
    """Redige caminhos/usuarios/IPs/URLs/segredos e trunca; remove controles."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise Gate5Error("sanitize_text: esperado str")
    text = _SECRET_RE.sub("<redacted-secret>", value)
    text = _URL_RE.sub("<redacted-url>", text)
    text = _DRIVE_PATH_RE.sub("<redacted-path>", text)
    text = _POSIX_HOME_RE.sub("<redacted-path>", text)
    text = _IPV4_RE.sub("<redacted-ip>", text)
    text = _CONTROL_RE.sub(" ", text)
    if len(text) > limit:
        text = text[:limit] + "…[TRUNCADO]"
    return text


def sanitize_message(value: Optional[str]) -> str:
    return sanitize_text(value, MAX_MESSAGE_CHARS)


# --------------------------------------------------------------------------- #
# Execucao local de comando (shell=False). NAO usada sobre o artefato real nesta
# etapa; existe para o futuro modo real (bloqueado) e e validada por um comando
# local trivial nos testes. NUNCA passa o artefato como executavel.
# --------------------------------------------------------------------------- #
def run_local_command(argv: List[str], timeout_seconds: int) -> Dict[str, object]:
    """Executa um comando LOCAL como lista de argumentos, sem shell, com timeout.

    Fail-closed: TimeoutExpired -> TIMEOUT; qualquer OSError -> ERROR. Sempre
    executa com shell desabilitado; nunca concatena string de comando; nunca
    acessa a rede.
    """
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
        raise Gate5Error("run_local_command: argv deve ser lista nao vazia de str")
    if not isinstance(timeout_seconds, int) or not (0 < timeout_seconds <= MAX_TIMEOUT_SECONDS):
        raise Gate5Error("run_local_command: timeout invalido")
    start = datetime.datetime.now(datetime.timezone.utc)
    try:
        proc = subprocess.run(  # noqa: S603 - shell=False, argv lista; sem input nao confiavel no argv[0]
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        dur = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds()
        return {"state": STATE_TIMEOUT, "exit_code": None, "stdout": "",
                "stderr": "timeout", "duration_ms": int(dur * 1000)}
    except OSError as exc:
        dur = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds()
        return {"state": STATE_ERROR, "exit_code": None, "stdout": "",
                "stderr": sanitize_message(str(exc)), "duration_ms": int(dur * 1000)}
    dur = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds()
    return {
        "state": STATE_PASS if proc.returncode == 0 else STATE_FINDING,
        "exit_code": proc.returncode,
        "stdout": sanitize_text(proc.stdout),
        "stderr": sanitize_text(proc.stderr, MAX_STDERR_CHARS),
        "duration_ms": int(dur * 1000),
    }


# --------------------------------------------------------------------------- #
# Adapters.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AdapterResult:
    adapter: str
    availability: str            # available | unavailable | simulated | not_run
    command_id: str
    timeout_seconds: int
    exit_code: Optional[int]
    classification: str          # um de ADAPTER_STATES
    stdout_sanitized: str
    stderr_sanitized: str
    duration_ms: int
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        if self.classification not in ADAPTER_STATES:
            raise Gate5Error("classificacao de adapter fora do conjunto fechado: %r"
                             % self.classification)
        if len(self.adapter) > MAX_ADAPTER_NAME:
            raise Gate5Error("nome de adapter excede limite")
        return {
            "adapter": self.adapter,
            "availability": self.availability,
            "command_id": self.command_id,
            "timeout_seconds": self.timeout_seconds,
            "exit_code": self.exit_code,
            "classification": self.classification,
            "stdout_sanitized": sanitize_text(self.stdout_sanitized),
            "stderr_sanitized": sanitize_text(self.stderr_sanitized, MAX_STDERR_CHARS),
            "duration_ms": self.duration_ms,
            "limitations": [sanitize_message(x) for x in self.limitations[:MAX_FINDINGS]],
        }


class BaseAdapter:
    adapter_id = "base"
    platform = "any"
    enabled_in_fixture = False
    requires_future_authorization = True

    def detect_available(self) -> bool:
        return False

    def build_command(self, input_path: str) -> List[str]:
        raise Gate5Error("build_command nao implementado")

    def parse_output(self, stdout: str, stderr: str, exit_code: Optional[int]) -> str:
        raise Gate5Error("parse_output nao implementado")


class SyntheticAdapter(BaseAdapter):
    """Adapter puramente sintetico (sem subprocess, sem scanner externo).

    Recebe bytes sinteticos e produz resultados previsiveis para exercitar
    PASS/FINDING/ERROR/TIMEOUT em testes. NAO chama executavel algum.
    """
    adapter_id = "synthetic-local"
    platform = "any"
    enabled_in_fixture = True
    requires_future_authorization = False

    def detect_available(self) -> bool:
        return True

    def analyze_bytes(self, blob: bytes, timeout_seconds: int = 5) -> AdapterResult:
        if not isinstance(blob, (bytes, bytearray)):
            raise Gate5Error("synthetic: blob deve ser bytes")
        marker = bytes(blob[:16])
        # Convencao sintetica de fixture (nao e formato executavel valido):
        if marker.startswith(b"SYN-FINDING"):
            cls, out, err, rc = STATE_FINDING, "regra sintetica correspondeu", "", 1
        elif marker.startswith(b"SYN-ERROR"):
            cls, out, err, rc = STATE_ERROR, "", "erro sintetico do adapter", 2
        elif marker.startswith(b"SYN-TIMEOUT"):
            cls, out, err, rc = STATE_TIMEOUT, "", "timeout sintetico", None
        else:
            cls, out, err, rc = STATE_PASS, "nenhuma correspondencia sintetica", "", 0
        return AdapterResult(
            adapter=self.adapter_id,
            availability="simulated",
            command_id="synthetic:analyze_bytes",
            timeout_seconds=timeout_seconds,
            exit_code=rc,
            classification=cls,
            stdout_sanitized=out,
            stderr_sanitized=err,
            duration_ms=0,
            limitations=["Resultado sintetico; NAO reflete o WARP real."],
        )


class DefenderAdapter(BaseAdapter):
    """Contrato do Defender/AV local. NAO executado nesta etapa.

    detect_available() apenas verifica presenca do executavel no PATH (sem rede).
    build_command() monta argv com o artefato como ARGUMENTO (-File), nunca como
    executavel. parse_output() e testado com stdout/stderr simulados.
    """
    adapter_id = "windows-defender-local"
    platform = "windows"
    enabled_in_fixture = False
    requires_future_authorization = True
    executable = "MpCmdRun.exe"

    def detect_available(self) -> bool:
        return _which(self.executable) is not None

    def build_command(self, input_path: str) -> List[str]:
        p = _validate_local_path(input_path)
        return [self.executable, "-Scan", "-ScanType", "3", "-File", str(p), "-DisableRemediation"]

    def parse_output(self, stdout: str, stderr: str, exit_code: Optional[int]) -> str:
        if exit_code is None:
            return STATE_TIMEOUT
        text = (stdout or "") + "\n" + (stderr or "")
        if re.search(r"(?i)threat|malware|detected", text):
            return STATE_FINDING
        if exit_code == 0:
            return STATE_PASS
        return STATE_ERROR if exit_code == 2 else STATE_FINDING


class YaraAdapter(BaseAdapter):
    """Contrato do YARA local. NAO executado nesta etapa.

    Sem baixar/instalar regras; sem regra proprietaria. build_command() recebe um
    caminho de regras LOCAL ja fornecido e o artefato como ARGUMENTO. parse_output()
    e testado com respostas simuladas ou regra sintetica criada no teste.
    """
    adapter_id = "yara-local"
    platform = "any"
    enabled_in_fixture = False
    requires_future_authorization = True
    executable = "yara"

    def detect_available(self) -> bool:
        return _which(self.executable) is not None

    def build_command(self, input_path: str, rules_path: str = "<rules>") -> List[str]:
        p = _validate_local_path(input_path)
        return [self.executable, "-r", rules_path, str(p)]

    def parse_output(self, stdout: str, stderr: str, exit_code: Optional[int]) -> str:
        if exit_code is None:
            return STATE_TIMEOUT
        if exit_code != 0:
            return STATE_ERROR
        # YARA imprime uma linha por regra correspondente; vazio = sem match.
        return STATE_FINDING if (stdout or "").strip() else STATE_PASS


ADAPTERS: Dict[str, BaseAdapter] = {
    SyntheticAdapter.adapter_id: SyntheticAdapter(),
    DefenderAdapter.adapter_id: DefenderAdapter(),
    YaraAdapter.adapter_id: YaraAdapter(),
}


# --------------------------------------------------------------------------- #
# Utilitarios de caminho (sem rede).
# --------------------------------------------------------------------------- #
def _which(executable: str) -> Optional[str]:
    """Localiza um executavel no PATH sem usar shutil (implementacao minima)."""
    paths = os.environ.get("PATH", "").split(os.pathsep)
    exts = os.environ.get("PATHEXT", "").split(os.pathsep) if os.name == "nt" else [""]
    for d in paths:
        if not d:
            continue
        base = os.path.join(d, executable)
        for ext in exts:
            cand = base + ext if ext and not base.lower().endswith(ext.lower()) else base
            if os.path.isfile(cand):
                return cand
    return None


def _validate_local_path(path: str) -> Path:
    """Valida que o caminho existe, e arquivo regular e NAO e symlink (fail-closed)."""
    if not isinstance(path, str) or not path:
        raise Gate5Error("caminho de entrada invalido")
    p = Path(path)
    if p.is_symlink():
        raise Gate5Error("symlink inesperado na entrada: %s" % sanitize_message(path))
    if not p.is_file():
        raise Gate5Error("entrada inexistente ou nao e arquivo regular")
    return p


def _sha256_file(p: Path) -> Dict[str, object]:
    size = p.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise Gate5Error("entrada excede limite defensivo de leitura")
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return {"sha256": h.hexdigest(), "size_bytes": size}


# --------------------------------------------------------------------------- #
# Validacao de configuracao (contrato de entrada).
# --------------------------------------------------------------------------- #
REQUIRED_FALSE_FLAGS = (
    "gate_5_authorized",
    "execution_authorized",
    "local_security_scan_authorized",
    "external_reputation_upload_authorized",
)


def validate_config(config: Dict[str, object]) -> None:
    """Fail-closed: valida o contrato de entrada e as flags obrigatorias em false."""
    if not isinstance(config, dict):
        raise Gate5Error("config deve ser objeto JSON")
    if config.get("schema_version") != SCHEMA_VERSION:
        raise Gate5Error("schema_version invalido")
    if config.get("gate_id") != GATE_ID:
        raise Gate5Error("gate_id invalido")
    mode = config.get("mode")
    if mode not in ("validate-only", "fixture", "real"):
        raise Gate5Error("mode invalido")
    flags = config.get("authorization_flags")
    if not isinstance(flags, dict):
        raise Gate5Error("authorization_flags ausente")
    for key in REQUIRED_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise Gate5Error("flag '%s' deve ser false nesta etapa" % key)
    if config.get("network_policy") != "blocked":
        raise Gate5Error("network_policy deve ser 'blocked'")
    if config.get("execution_policy") != "artifact_never_executed":
        raise Gate5Error("execution_policy deve ser 'artifact_never_executed'")
    to = config.get("timeout_seconds")
    if not isinstance(to, int) or not (0 < to <= MAX_TIMEOUT_SECONDS):
        raise Gate5Error("timeout_seconds invalido")
    for key in ("input_path", "output_directory"):
        val = config.get(key)
        if not isinstance(val, str) or not val:
            raise Gate5Error("campo '%s' invalido" % key)
    adapters = config.get("enabled_adapters")
    if not isinstance(adapters, list) or not adapters:
        raise Gate5Error("enabled_adapters invalido")
    for a in adapters:
        if a not in ADAPTERS:
            raise Gate5Error("adapter nao permitido: %s" % sanitize_message(str(a)))


# --------------------------------------------------------------------------- #
# Geracao de evidencia.
# --------------------------------------------------------------------------- #
def _iso(ts: datetime.datetime) -> str:
    return ts.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_evidence(config: Dict[str, object],
                   identity: Dict[str, object],
                   adapter_results: List[AdapterResult],
                   started: datetime.datetime,
                   finished: datetime.datetime,
                   outcome: str) -> Dict[str, object]:
    """Monta a evidencia FECHADA e sanitizada. NUNCA emite GATE_PASSED para o real."""
    if outcome not in (OUTCOME_FIXTURE_PASS, OUTCOME_VALIDATE_ONLY):
        raise Gate5Error("outcome nao permitido nesta etapa: %r" % outcome)
    results = [r.to_dict() for r in adapter_results]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "warp-audit-gate-05-evidence",
        "gate_id": GATE_ID,
        "gate_name": GATE_NAME,
        "mode": config.get("mode"),
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "identity": {
            "logical_path": sanitize_message(str(identity.get("logical_path", ""))),
            "sha256": identity.get("sha256", ""),
            "size_bytes": identity.get("size_bytes", 0),
            "started_utc": _iso(started),
            "finished_utc": _iso(finished),
        },
        "environment": {
            "os_family": os.name,
            "python_version": "%d.%d.%d" % sys.version_info[:3],
            "logical_working_directory": "<repo>",
            "network_policy": "blocked",
            "adapters_enabled": sorted(str(a) for a in config.get("enabled_adapters", [])),
            "timeout_seconds": config.get("timeout_seconds"),
        },
        "adapter_results": results,
        "procedural_classification": outcome,
        "outcome": outcome,
        "artifact_executed": False,
        "network_access": False,
        "authorization_flags": {
            "gate_5_authorized": False,
            "execution_authorized": False,
            "local_security_scan_authorized": False,
            "external_reputation_upload_authorized": False,
            "client_preparation_authorized": False,
        },
        "limitations": [
            "Resultado de fixture sintetica; NAO reflete o WARP real.",
            "Um resultado local NAO prova que o binario e seguro, benigno ou malicioso.",
            "Ausencia de deteccao NAO prova seguranca.",
            "Nenhuma conclusao depende de uma unica metrica.",
            "O GATE 5 NAO foi executado sobre o artefato real; execucao real exige nova decisao humana.",
        ],
    }


# --------------------------------------------------------------------------- #
# Orquestracao por modo.
# --------------------------------------------------------------------------- #
def _resolve_output_dir(config: Dict[str, object], allowed_base: Optional[Path]) -> Path:
    out = Path(str(config.get("output_directory"))).resolve()
    if allowed_base is not None:
        base = allowed_base.resolve()
        if base not in out.parents and out != base:
            raise Gate5Error("output_directory fora do diretorio autorizado")
    return out


def run(config: Dict[str, object],
        allowed_output_base: Optional[Path] = None,
        clock: Optional[Callable[[], datetime.datetime]] = None) -> Dict[str, object]:
    """Executa o modo declarado no config. Fail-closed.

    - real   -> RealExecutionNotAuthorized (nao autorizado nesta etapa).
    - validate-only -> valida contrato/ambiente e retorna evidencia CONFIG_VALIDATION_PASS
                       (adapters NOT_RUN).
    - fixture -> roda apenas o adapter sintetico sobre a fixture; FIXTURE_VALIDATION_PASS.
    """
    now = clock or (lambda: datetime.datetime.now(datetime.timezone.utc))
    validate_config(config)
    mode = config.get("mode")

    if mode == "real":
        raise RealExecutionNotAuthorized(REAL_EXECUTION_BLOCK_MESSAGE)

    _resolve_output_dir(config, allowed_output_base)
    started = now()

    if mode == "validate-only":
        finished = now()
        identity = {"logical_path": config.get("input_path"), "sha256": "", "size_bytes": 0}
        results: List[AdapterResult] = []
        for aid in config.get("enabled_adapters", []):
            results.append(AdapterResult(
                adapter=str(aid), availability="not_run", command_id="",
                timeout_seconds=int(config.get("timeout_seconds", 0)), exit_code=None,
                classification=STATE_NOT_RUN, stdout_sanitized="", stderr_sanitized="",
                duration_ms=0, limitations=["validate-only: scanner nao chamado."],
            ))
        return build_evidence(config, identity, results, started, finished, OUTCOME_VALIDATE_ONLY)

    # mode == "fixture"
    p = _validate_local_path(str(config.get("input_path")))
    ident = _sha256_file(p)
    expected = config.get("expected_sha256")
    if expected:
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise Gate5Error("expected_sha256 malformado")
        if str(expected) != ident["sha256"]:
            raise Gate5Error("hash divergente da fixture (fail-closed)")
    with open(p, "rb") as fh:
        blob = fh.read(MAX_INPUT_BYTES + 1)
    if len(blob) > MAX_INPUT_BYTES:
        raise Gate5Error("fixture excede limite defensivo")

    synth = ADAPTERS[SyntheticAdapter.adapter_id]
    results = []
    for aid in config.get("enabled_adapters", []):
        adapter = ADAPTERS[aid]
        if not adapter.enabled_in_fixture:
            raise Gate5Error("adapter '%s' nao habilitado em fixture-mode" % aid)
        if isinstance(adapter, SyntheticAdapter):
            results.append(adapter.analyze_bytes(blob, int(config.get("timeout_seconds", 5))))
        else:
            raise Gate5Error("fixture-mode so admite o adapter sintetico")

    finished = now()
    identity = {"logical_path": config.get("input_path"), **ident}
    return build_evidence(config, identity, results, started, finished, OUTCOME_FIXTURE_PASS)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def _load_json(path: str) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="warp-audit-gate-05.py",
        description="Orquestrador estatico do GATE 5 (preparacao; sem execucao real).",
    )
    parser.add_argument("--config", required=True, help="caminho do JSON de entrada")
    parser.add_argument("--output", help="caminho do JSON de evidencia (default: stdout)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--validate-only", action="store_true",
                       help="valida contrato/ambiente sem chamar scanners")
    group.add_argument("--fixture-mode", action="store_true",
                       help="opera apenas sobre fixtures sinteticas")
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit:
        return 2

    try:
        config = _load_json(args.config)
    except (OSError, ValueError) as exc:
        sys.stderr.write("config invalido: %s\n" % sanitize_message(str(exc)))
        return 2

    # A flag de CLI, quando presente, deve ser coerente com o mode do config.
    if args.validate_only:
        config["mode"] = "validate-only"
    elif args.fixture_mode:
        config["mode"] = "fixture"

    if config.get("mode") == "real":
        sys.stderr.write(REAL_EXECUTION_BLOCK_MESSAGE + "\n")
        return 3

    try:
        evidence = run(config)
    except RealExecutionNotAuthorized:
        sys.stderr.write(REAL_EXECUTION_BLOCK_MESSAGE + "\n")
        return 3
    except Gate5Error as exc:
        sys.stderr.write("GATE 5 (fail-closed): %s\n" % sanitize_message(str(exc)))
        return 2

    payload = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output:
        out = Path(args.output)
        if out.exists():
            sys.stderr.write("recusa sobrescrever evidencia existente: %s\n"
                             % sanitize_message(str(out)))
            return 2
        out.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
