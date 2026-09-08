import pyaudio
import wave
import io 
import logging
from google.cloud import speech_v1

logger = logging.getLogger(_name_)

class listener:
    def _init_(self):
        self.client = speech_v1.SpeechClient()
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.record_seconds = 5

    def capture_command(self):
        """Record 5 seconds of audio and transcribe using Google Cloud Speech-to-Text."""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        logger.info("Recording.....")
        frames[]
        for _ in range(0, int(self.rate / self.chunk * self.record_seconds)):
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)
        logger.info("Recording finished.")

        stream.stop_stream()
        stream.close()
        p.terminate()

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(self.audio_format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
        wav_buffer.seek(0)

        try:
            audio = speech_v1.RecognitionAudio(content=wav_buffer.read())
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.rate,
                language_code="en-US",
            )
            response = self.client.recognize(config=config, audio=audio)
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                logger.info(f"Transcribed: {transcript}")
                return transcript
            else:
                logger.warning("No transcription returned.")
                return None
            except Exception as e:
                logger.error(f"STT error: {e}")
                return None