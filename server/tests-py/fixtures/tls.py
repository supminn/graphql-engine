import enum
import http.server
import pathlib
from typing import NamedTuple
import pytest
import ssl
import subprocess


class TLSTrust(enum.Enum):
    INSECURE = enum.auto()
    SECURE = enum.auto()


class TLSCAConfiguration(NamedTuple):
    cert_file: str
    key_file: str

    tmp_path: pathlib.Path

    def configure(
        self,
        server: http.server.HTTPServer,
        trust: TLSTrust,
    ) -> http.server.HTTPServer:
        config_file = pathlib.Path(__file__).parent / 'webhook.cnf'
        key_file = self.tmp_path / 'webhook-key.pem'
        csr_file = self.tmp_path / 'webhook.csr'
        cert_file = self.tmp_path / 'webhook.pem'
        # generate a private key
        subprocess.run(['openssl', 'genrsa', '-out', key_file, '2048']).check_returncode()
        # generate a certificate signing request for the private key
        subprocess.run(['openssl', 'req', '-new', '-key', key_file, '-out', csr_file, '-subj', '/CN=hge-webhook', '-config', config_file]).check_returncode()
        if trust == TLSTrust.INSECURE:
            # self-sign the certificate with its own key, making it untrusted
            subprocess.run(['openssl', 'x509', '-req', '-in', csr_file, '-signkey', key_file, '-out', cert_file, '-days', '10', '-extensions', 'v3_req', '-extfile', config_file]).check_returncode()
        else:
            # sign the certificate with the provided CA key, which should be trusted
            subprocess.run(['openssl', 'x509', '-req', '-in', csr_file, '-CA', self.cert_file, '-CAkey', self.key_file, '-CAcreateserial', '-out', cert_file, '-days', '10', '-extensions', 'v3_req', '-extfile', config_file]).check_returncode()

        server.socket = ssl.wrap_socket(
            server.socket,
            certfile=cert_file,
            keyfile=key_file,
            server_side=True,
            ssl_version=ssl.PROTOCOL_SSLv23,
        )
        return server
