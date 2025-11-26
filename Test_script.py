import socket
import ssl
import time
from typing import List, Tuple

TARGETS: List[Tuple[str, int]] = [
    ("peer0.org1.example.com", 7051),
    ("peer1.org1.example.com", 7051),
    ("orderer.example.com", 7050),
    # Add more known hosts/ports in your *own* environment
]

TLS_TIMEOUT = 3.0

def check_endpoint(host: str, port: int):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # we just want metadata, not trust

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TLS_TIMEOUT)

    try:
        s.connect((host, port))
    except Exception as e:
        return {
            "host": host,
            "port": port,
            "status": "no-tcp",
            "error": str(e),
        }

    try:
        with context.wrap_socket(s, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
            # Send HTTP/2 / gRPC preface to see if it responds as gRPC
            try:
                ssock.sendall(
                    b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"  # HTTP/2 connection preface
                )
            except Exception:
                pass

            return {
                "host": host,
                "port": port,
                "status": "tls-ok",
                "subject": cert.get("subject"),
                "issuer": cert.get("issuer"),
            }
    except Exception as e:
        return {
            "host": host,
            "port": port,
            "status": "tls-failed",
            "error": str(e),
        }


def fuzz_targets():
    results = []
    start = time.time()
    for host, port in TARGETS:
        res = check_endpoint(host, port)
        results.append(res)
        print(res)
    print(f"Scanned {len(TARGETS)} endpoints in {time.time() - start:.2f}s")
    return results


if __name__ == "__main__":
    fuzz_targets()
