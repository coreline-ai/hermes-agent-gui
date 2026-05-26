from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class BridgeInfo:
    name: str
    binary: str
    available: bool
    path: str | None
    install_url: str

    def to_dict(self) -> dict:
        return self.__dict__


class AbstractCliBridge:
    name = "abstract"
    binary = ""
    install_url = ""

    def detect(self) -> BridgeInfo:
        path = shutil.which(self.binary)
        return BridgeInfo(self.name, self.binary, bool(path), path, self.install_url)

    def spawn(self) -> None:
        raise NotImplementedError

    def send(self, prompt: str) -> str:
        info = self.detect()
        if not info.path:
            raise FileNotFoundError("binary_not_found")
        proc = subprocess.run([info.path], input=prompt, text=True, capture_output=True, timeout=30, check=False)
        return proc.stdout or proc.stderr

    def recv_stream(self, prompt: str):
        yield self.send(prompt)

    def kill(self) -> None:
        return None
