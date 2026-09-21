import pvporcupine
import pyaudio
import struct
import threading
import logging

logger = logging.getLogger(__name__)


class WakeWordListener:
    def __init__(self, access_key, callback):
        self.access_key = access_key
        self.callback = callback
        self.porcupine = None
        self.audio_stream = None
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None

    def _listen(self):
        pa = None
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=["jarvis"]
            )
            pa = pyaudio.PyAudio()
            self.audio_stream = pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )

            logger.info("Wake word listener started, listening for 'Jarvis'...")
            while self.running:
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    logger.info("Wake word detected!")
                    threading.Thread(target=self.callback, daemon=True).start()
        except Exception as e:
            logger.error(f"Wake word listener error: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.close()
                self.audio_stream = None
            if self.porcupine:
                self.porcupine.delete()
                self.porcupine = None
            if pa:
                pa.terminate()