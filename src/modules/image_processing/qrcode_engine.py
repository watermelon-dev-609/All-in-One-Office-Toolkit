"""QR Code generation and decoding engine."""

from pathlib import Path
from typing import Optional

from PIL import Image
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


class QRCodeWorker(TaskWorker):
    """Worker for QR code generation and decoding."""

    def process(self) -> list[Path]:
        operation = self.task.params.get("operation", "generate")

        if operation == "generate":
            return self._generate()
        elif operation == "decode":
            return self._decode()
        else:
            raise ValueError(f"Unknown QR operation: {operation}")

    def _generate(self) -> list[Path]:
        """Generate QR code image(s)."""
        import qrcode
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.moduledrawers import SquareModuleDrawer

        content = self.task.params.get("content", "")
        if not content:
            raise ValueError("No content specified for QR code generation")

        qr_type = self.task.params.get("qr_type", "text")  # text, url, wifi, vcard
        output_dir = self.task.params.get("output_dir", None)
        box_size = self.task.params.get("box_size", 10)
        border = self.task.params.get("border", 4)
        fill_color = self.task.params.get("fill_color", "black")
        back_color = self.task.params.get("back_color", "white")

        # Format content based on type
        if qr_type == "wifi":
            ssid = self.task.params.get("wifi_ssid", "")
            password = self.task.params.get("wifi_password", "")
            encryption = self.task.params.get("wifi_encryption", "WPA")
            content = f"WIFI:T:{encryption};S:{ssid};P:{password};;"
        elif qr_type == "vcard":
            name = self.task.params.get("vcard_name", "")
            phone = self.task.params.get("vcard_phone", "")
            email = self.task.params.get("vcard_email", "")
            content = (
                "BEGIN:VCARD\nVERSION:3.0\n"
                f"FN:{name}\nTEL:{phone}\nEMAIL:{email}\n"
                "END:VCARD"
            )

        # Generate
        qr = qrcode.QRCode(
            version=None,  # Auto
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(content)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        # Save
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = Path.cwd() / "Output"
        out_dir.mkdir(parents=True, exist_ok=True)

        filename = self.task.params.get("filename", "qrcode")
        out_path = out_dir / f"{filename}.png"
        counter = 1
        while out_path.exists():
            out_path = out_dir / f"{filename}_{counter}.png"
            counter += 1

        img.save(out_path)
        logger.info(f"QR code generated: {out_path}")
        return [out_path]

    def _decode(self) -> list[Path]:
        """Decode QR codes from images."""
        from pyzbar.pyzbar import decode
        output_dir = self.task.params.get("output_dir", None)

        total = len(self.task.input_files)
        output_files = []

        for i, file_path in enumerate(self.task.input_files):
            self.check_pause()
            if self.is_cancelled:
                break

            src = Path(file_path)
            self.report_progress(
                int((i / total) * 100),
                f"解析二维码: {src.name}"
            )

            try:
                img = Image.open(src)
                results = decode(img)

                if not results:
                    logger.debug(f"No QR code found in {src.name}")
                    continue

                # Write results
                lines = []
                for j, code in enumerate(results):
                    data = code.data.decode("utf-8", errors="replace")
                    code_type = code.type
                    lines.append(f"[{code_type}] {data}")

                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = src.parent / "Output"
                out_dir.mkdir(parents=True, exist_ok=True)

                out_path = out_dir / f"{src.stem}_qr_decode.txt"
                out_path.write_text("\n".join(lines), encoding="utf-8")
                output_files.append(out_path)

            except Exception as e:
                logger.error(f"QR decode failed for {src.name}: {e}")

        self.report_progress(100, f"解码完成: {len(output_files)} 个文件")
        return output_files
