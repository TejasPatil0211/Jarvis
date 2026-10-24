"""
simple_vad.py - Pure-Python voice activity detection.

Drop in replacement for webrtcvad on Python versions where its C extension isn't available

Usage:
    from simple_vad import SimpleVAD
    vad = SimpleVAD(aggressiveness=2)
    is_speech = vad.is_speech(pcm_bytes)
"""
import logging
import struct
from typing import ClassVar

logger = logging.getLogger(__name__)

class SimpleVAD:
    """Energy-based VAD. Compares RMS amplitude to a threshold."""

    THRESHOLDS: ClassVar[dict[int, int]] = {
        0: 200,
        1: 400,
        2: 700,
        3: 1200,
    }

    def __init__(self, aggressiveness: int = 2):
        self.threshold = self.THRESHOLDS

    def is_speech(self, audio_bytes: bytes, sample_rate: int = 16000) -> bool:
        if not audio_bytes or len(audio_bytes) < 2:
            return False
        try:
            n = len(audio_bytes) // 2
            samples = struct.unpack(f"<{n}h", audio_bytes[: n * 2])
            if not samples:
                return False
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            return rms > self.threshold
        except struct.error as e:
            logger.debug(f"SimpleVAD error: {e}")
            return False
        