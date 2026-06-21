"""
SMTP backends for hosts with no IPv6 egress (e.g. Railway).

Python's smtplib resolves the mail host via getaddrinfo and may try IPv6 first.
Containers often have no IPv6 route, so the connect hangs until it times out
(seen in logs as ``SMTPServerDisconnected: Connection unexpectedly closed: timed out``)
or fails with ``OSError: [Errno 101] Network is unreachable``.

We connect using ``AF_INET`` only; TLS still uses the real hostname for cert/SNI.
Production normally uses the Resend HTTPS API (django-anymail); this backend is the
SMTP fallback (set ``EMAIL_BACKEND`` to it, or let prod.py swap it in on Railway).
"""

from __future__ import annotations

import logging
import socket
import smtplib

from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend

logger = logging.getLogger(__name__)


def _tcp_connect_ipv4(
    host: str,
    port: int,
    timeout: float | None,
    source_address: tuple[str, int] | None,
) -> socket.socket:
    infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    last_exc: BaseException | None = None
    for _fam, _kind, _proto, _canon, sockaddr in infos:
        ip = sockaddr[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            if source_address is not None:
                sock.bind(source_address)
            sock.connect(sockaddr)
            logger.info("SMTP TCP connected (IPv4) %s:%s", ip, port)
            return sock
        except OSError as exc:
            last_exc = exc
            logger.warning(
                "SMTP TCP failed %s:%s - %s: %s", ip, port, type(exc).__name__, exc
            )
            sock.close()
            continue
    if last_exc is not None:
        raise last_exc
    raise OSError(f"No IPv4 address found for SMTP host {host!r}")


class SMTPIPv4(smtplib.SMTP):
    """Plain SMTP (e.g. port 587 + STARTTLS); TCP over IPv4 only."""

    def _get_socket(self, host, port, timeout):
        return _tcp_connect_ipv4(host, port, timeout, self.source_address)


class SMTP_SSL_IPv4(smtplib.SMTP_SSL):
    """SMTP over implicit TLS (e.g. port 465); TCP over IPv4 only."""

    def _get_socket(self, host, port, timeout):
        new_socket = _tcp_connect_ipv4(host, port, timeout, self.source_address)
        return self.context.wrap_socket(new_socket, server_hostname=self._host)


class IPv4EmailBackend(DjangoSMTPBackend):
    """Django's SMTP backend, but only uses IPv4 for the initial TCP connection."""

    @property
    def connection_class(self):
        return SMTP_SSL_IPv4 if self.use_ssl else SMTPIPv4
