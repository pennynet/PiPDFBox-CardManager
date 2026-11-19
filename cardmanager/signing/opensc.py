"""PDF signing through OpenSC and a protected PKCS#11 authentication path."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from asn1crypto import x509 as asn1_x509
from cryptography import x509 as crypto_x509
from cryptography.hazmat.primitives.asymmetric import rsa
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import fields, signers


class OpenSCPdfSigningError(RuntimeError):
    """Raised when OpenSC-backed PDF signing fails."""


class _OpenSCExternalSigner(signers.ExternalSigner):
    def __init__(
        self,
        certificate: asn1_x509.Certificate,
        signature_size: int,
        module_path: str,
        pkcs11_tool_path: str,
        slot_id: int,
        key_id: bytes,
    ) -> None:
        super().__init__(signing_cert=certificate, cert_registry=None)
        self._signature_size = signature_size
        self._module_path = module_path
        self._pkcs11_tool_path = pkcs11_tool_path
        self._slot_id = slot_id
        self._key_id = key_id

    async def async_sign_raw(
        self,
        data: bytes,
        digest_algorithm: str,
        dry_run: bool = False,
    ) -> bytes:
        if digest_algorithm.lower() != "sha256":
            raise OpenSCPdfSigningError("Only SHA-256 signing is supported")

        if dry_run:
            return b"\x00" * self._signature_size

        with tempfile.TemporaryDirectory(prefix="cardmanager-opensc-") as tmp:
            input_file = Path(tmp) / "signed-attributes.der"
            output_file = Path(tmp) / "signature.bin"
            input_file.write_bytes(data)

            command = [
                self._pkcs11_tool_path,
                "--module", self._module_path,
                "--slot", str(self._slot_id),
                "--login",
                "--sign",
                "--mechanism", "SHA256-RSA-PKCS",
                "--id", self._key_id.hex(),
                "--input-file", str(input_file),
                "--output-file", str(output_file),
            ]

            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    _stdout, _stderr = await asyncio.wait_for(
                        process.communicate(), timeout=120
                    )
                except TimeoutError:
                    process.kill()
                    await process.wait()
                    raise OpenSCPdfSigningError(
                        "OpenSC signing timed out"
                    ) from None
            except OSError:
                raise OpenSCPdfSigningError(
                    "OpenSC could not be started"
                ) from None

            if process.returncode != 0:
                raise OpenSCPdfSigningError(
                    f"OpenSC signing failed (exit {process.returncode})"
                )

            try:
                signature = output_file.read_bytes()
            except OSError:
                raise OpenSCPdfSigningError(
                    "OpenSC did not produce a signature"
                ) from None

            if len(signature) != self._signature_size:
                raise OpenSCPdfSigningError(
                    "OpenSC returned an unexpected signature size"
                )

            return signature


class OpenSCPdfSigner:
    """Create a PDF signature using a D-TRUST certificate and OpenSC."""

    def __init__(
        self,
        module_path: str,
        certificate_der: bytes,
        *,
        pkcs11_tool_path: str = "/opt/opensc-0.27.1/bin/pkcs11-tool",
        slot_id: int = 1,
        key_id: bytes = b"\x02",
    ) -> None:
        if not module_path or not Path(module_path).is_absolute():
            raise ValueError("module_path must be an absolute path")
        if not pkcs11_tool_path or not Path(pkcs11_tool_path).is_absolute():
            raise ValueError("pkcs11_tool_path must be an absolute path")
        if slot_id < 0:
            raise ValueError("slot_id must not be negative")
        if not isinstance(key_id, bytes) or not key_id:
            raise ValueError("key_id must be non-empty bytes")

        try:
            crypto_certificate = crypto_x509.load_der_x509_certificate(
                certificate_der
            )
            public_key = crypto_certificate.public_key()
            if not isinstance(public_key, rsa.RSAPublicKey):
                raise TypeError("certificate does not contain an RSA key")

            self._certificate = asn1_x509.Certificate.load(certificate_der)
            self._signature_size = (public_key.key_size + 7) // 8
        except Exception as exc:
            raise ValueError("invalid RSA signing certificate") from exc

        self._module_path = module_path
        self._pkcs11_tool_path = pkcs11_tool_path
        self._slot_id = slot_id
        self._key_id = key_id

    def sign_pdf(
        self,
        input_pdf: str | Path,
        output_pdf: str | Path,
        *,
        field_name: str = "Signature1",
        reason: str | None = None,
    ) -> Path:
        source_path = Path(input_pdf)
        output_path = Path(output_pdf)

        if not source_path.is_file():
            raise FileNotFoundError("Input PDF does not exist")
        if source_path.resolve() == output_path.resolve():
            raise ValueError("Input and output PDF must be different files")
        if not field_name or not field_name.strip():
            raise ValueError("field_name must not be empty")

        metadata = signers.PdfSignatureMetadata(
            field_name=field_name,
            md_algorithm="sha256",
            reason=reason,
        )
        external_signer = _OpenSCExternalSigner(
            self._certificate,
            self._signature_size,
            self._module_path,
            self._pkcs11_tool_path,
            self._slot_id,
            self._key_id,
        )
        pdf_signer = signers.PdfSigner(
            metadata,
            external_signer,
            new_field_spec=fields.SigFieldSpec(
                sig_field_name=field_name,
                on_page=0,
                box=(48, 48, 547, 115),
            ),
        )

        if output_path.exists():
            raise FileExistsError("Output PDF already exists")
        created_output = False
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with source_path.open("rb") as source:
                writer = IncrementalPdfFileWriter(source)
                with output_path.open("xb") as destination:
                    created_output = True
                    pdf_signer.sign_pdf(writer, output=destination)
        except OpenSCPdfSigningError:
            raise
        except Exception as exc:
            if created_output:
                try:
                    output_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise OpenSCPdfSigningError(
                "PDF signing failed"
            ) from exc

        return output_path
