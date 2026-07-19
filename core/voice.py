"""
DEBBY! -- core/voice.py
Offline speech-to-text. Records a fixed duration from the microphone,
transcribes it locally with faster-whisper -- no internet, no API keys.
Only triggered when the user types "/voice" in brain.py, not automatic.
"""

import os
import tempfile
import wave

import pyaudio

_whisper_model = None  # loaded once, reused across calls in the same session


def _get_model(model_size: str = "tiny.en"):
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print(f"[Loading speech model '{model_size}' -- first use only, cached after this]")
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _whisper_model


def record_audio(filepath: str, duration: int = 5, samplerate: int = 16000):
    """Records `duration` seconds from the default microphone to a WAV file."""
    p = pyaudio.PyAudio()
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=samplerate,
            input=True,
            frames_per_buffer=1024,
        )
    except Exception as e:
        p.terminate()
        raise RuntimeError(
            f"Could not open microphone: {e}. "
            f"If running in a VM, check that audio input is enabled in "
            f"your VM's audio settings and the host has granted mic access."
        )

    frames = []
    for _ in range(int(samplerate / 1024 * duration)):
        frames.append(stream.read(1024, exception_on_overflow=False))

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filepath, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(samplerate)
    wf.writeframes(b"".join(frames))
    wf.close()


def transcribe_audio(filepath: str, model_size: str = "tiny.en") -> str:
    model = _get_model(model_size)
    segments, _info = model.transcribe(filepath)
    return " ".join(segment.text for segment in segments).strip()


def listen_and_transcribe(duration: int = 5, model_size: str = "tiny.en") -> dict:
    """
    Full pipeline: record -> transcribe -> clean up temp file.
    Returns {"success": bool, "text": str} or {"success": False, "error": str}
    """
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)

        record_audio(tmp_path, duration=duration)
        text = transcribe_audio(tmp_path, model_size=model_size)

        if not text:
            return {"success": False, "error": "Didn't catch any speech -- try again, speak clearly."}
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
