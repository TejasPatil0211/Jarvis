import pvporcupine
import pyaudio
import struct
import threading
import logging

logger = logging.getLogger(_name_)

class WakeWordListner:
    def _init_(self, access_key, callback):
        self.access_key = access_key
        self.callback = callback
        self.porcupine = None
        self.running = False 
        self.thread = None

    def start(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.audio_stream:
            self.audio_stream.close()
        if self.porcupine:
            self.porcupine.delete()

    def _listen(self):
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=["jarvis"]
            )
            pa = pyaudio.PyAudio()
            self.audio_stream = pa.open(
                rate=self.porcupine.sample_rate,
                channels=1
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
                if self.porcupine:
                    self.porcupine.delete()
                pa.terminate()