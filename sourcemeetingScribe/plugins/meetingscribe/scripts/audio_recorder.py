"""
MeetingScribe v3 - Audio recording with mic and system audio
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
from pathlib import Path
from typing import Callable, Optional
import logging

from utils import DEFAULT_AUDIO_SAMPLE_RATE, CHUNK_DURATION_SECONDS

# Pause-triggered early transcription settings
SILENCE_RMS_THRESHOLD = 0.004   # raw RMS below this = silence
SILENCE_TRIGGER_SECS  = 1.5     # silence duration before early flush
MIN_PAUSE_CHUNK_SECS  = 3.0     # don't flush unless we have at least this much audio

class AudioRecorder:
    """Records microphone and system audio simultaneously"""
    
    def __init__(self, session_path: Path, sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE,
                 mic_device=None):
        self.session_path = session_path
        self.sample_rate = sample_rate
        self.chunk_duration = CHUNK_DURATION_SECONDS
        self._mic_device_override = mic_device  # None = use system default
        
        # Audio streams
        self.mic_stream = None
        self.system_stream = None
        
        # Recording state
        self.is_recording = False
        self.chunk_number = 1
        
        # Audio data queues
        self.mic_queue = queue.Queue()
        self.system_queue = queue.Queue()
        self.combined_queue = queue.Queue()
        
        # Callback for chunk processing (e.g., transcription)
        self.chunk_callback: Optional[Callable] = None

        # Level callback: called with RMS float every mic block
        self.level_callback: Optional[Callable] = None

        # System audio level callback: called with RMS float every system audio block
        self.system_level_callback: Optional[Callable] = None
        
        # Worker threads
        self.mixer_thread = None
        self.writer_thread = None
        
        # Full recording data
        self.full_mic_data = []
        self.full_system_data = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def set_chunk_callback(self, callback: Callable):
        """Set callback function to call when chunk is ready"""
        self.chunk_callback = callback

    def set_level_callback(self, callback: Callable):
        """Set callback to receive mic RMS level on every audio block"""
        self.level_callback = callback

    def set_system_level_callback(self, callback: Callable):
        """Set callback to receive system audio RMS level on every audio block"""
        self.system_level_callback = callback
        
    def list_audio_devices(self):
        """List available audio devices"""
        devices = sd.query_devices()
        print("Available audio devices:")
        for i, device in enumerate(devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append("INPUT")
            if device['max_output_channels'] > 0:
                device_type.append("OUTPUT")
            
            print(f"{i}: {device['name']} ({', '.join(device_type)})")
            
    def get_default_devices(self):
        """Get default input and system audio devices"""
        try:
            # Default input device (microphone)
            default_input = sd.default.device[0]
            
            # For Windows, try to find system audio (WASAPI loopback)
            # This is a simplified approach - in practice, you'd need to use
            # platform-specific code or libraries like PyAudio with WASAPI
            devices = sd.query_devices()
            system_device = None
            
            # Look for a loopback device or stereo mix
            for i, device in enumerate(devices):
                name = device['name'].lower()
                if ('stereo mix' in name or 'what u hear' in name or 
                    'loopback' in name or device.get('hostapi_name') == 'WASAPI'):
                    if device['max_input_channels'] > 0:
                        system_device = i
                        break
            
            return default_input, system_device
            
        except Exception as e:
            self.logger.error(f"Error getting default devices: {e}")
            return None, None
    
    def start_recording(self):
        """Start recording from both microphone and system audio"""
        if self.is_recording:
            self.logger.warning("Recording already in progress")
            return False
            
        self.logger.info("Starting audio recording...")

        # Use explicit override if set, otherwise detect default
        if self._mic_device_override is not None:
            mic_device = self._mic_device_override
            _, system_device = self.get_default_devices()
            self.logger.info(f"Using selected mic device: {mic_device}")
        else:
            mic_device, system_device = self.get_default_devices()

        if mic_device is None:
            self.logger.error("No microphone device found")
            return False

        # Log which device we're actually using
        try:
            import sounddevice as sd
            dev_info = sd.query_devices(mic_device)
            self.logger.info(f"Mic device: [{mic_device}] {dev_info['name']} "
                             f"(channels={dev_info['max_input_channels']})")
        except Exception:
            pass
            
        # Note: System audio recording requires special setup on Windows
        # For now, we'll record microphone only and note this limitation
        if system_device is None:
            self.logger.warning("No system audio device found - recording microphone only")
            
        try:
            self.is_recording = True
            self.chunk_number = 1
            
            # Start microphone recording
            self.mic_stream = sd.InputStream(
                device=mic_device,
                channels=1,
                samplerate=self.sample_rate,
                callback=self._mic_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            )
            
            # Start system audio recording if available
            if system_device is not None:
                try:
                    self.system_stream = sd.InputStream(
                        device=system_device,
                        channels=2,  # Stereo for system audio
                        samplerate=self.sample_rate,
                        callback=self._system_callback,
                        blocksize=int(self.sample_rate * 0.1)
                    )
                    self.system_stream.start()
                except Exception as e:
                    self.logger.warning(f"Could not start system audio recording: {e}")
                    self.system_stream = None
            
            self.mic_stream.start()
            
            # Start worker threads
            self.mixer_thread = threading.Thread(target=self._audio_mixer_worker)
            self.writer_thread = threading.Thread(target=self._chunk_writer_worker)
            
            self.mixer_thread.start()
            self.writer_thread.start()
            
            self.logger.info("Audio recording started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting audio recording: {e}")
            self.stop_recording()
            return False
    
    def stop_recording(self):
        """Stop recording and save final audio file"""
        if not self.is_recording:
            return
            
        self.logger.info("Stopping audio recording...")
        self.is_recording = False
        
        # Stop streams
        if self.mic_stream:
            self.mic_stream.stop()
            self.mic_stream.close()
            self.mic_stream = None
            
        if self.system_stream:
            self.system_stream.stop()
            self.system_stream.close()
            self.system_stream = None
        
        # Wait for worker threads to finish
        if self.mixer_thread and self.mixer_thread.is_alive():
            self.mixer_thread.join(timeout=5)
            
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5)
        
        # Save full recording
        self._save_full_recording()
        
        self.logger.info("Audio recording stopped and saved")
    
    def _mic_callback(self, indata, frames, time, status):
        """Callback for microphone audio"""
        if status:
            self.logger.warning(f"Microphone callback status: {status}")

        if self.is_recording:
            # Store for full recording
            self.full_mic_data.append(indata.copy())

            # Add to queue for chunking
            self.mic_queue.put(indata.copy())

            # Emit level for VU meter
            if self.level_callback:
                try:
                    rms = float(np.sqrt(np.mean(indata ** 2)))
                    self.level_callback(min(rms * 30, 1.0))
                except Exception:
                    pass
    
    def _system_callback(self, indata, frames, time, status):
        """Callback for system audio"""
        if status:
            self.logger.warning(f"System audio callback status: {status}")

        if self.is_recording:
            # Convert stereo to mono for consistency
            mono_data = np.mean(indata, axis=1, keepdims=True) if indata.shape[1] > 1 else indata

            # Store for full recording
            self.full_system_data.append(mono_data.copy())

            # Add to queue for chunking
            self.system_queue.put(mono_data.copy())

            # Emit level for system VU meter
            if self.system_level_callback:
                try:
                    rms = float(np.sqrt(np.mean(indata ** 2)))
                    self.system_level_callback(min(rms * 30, 1.0))
                except Exception:
                    pass
    
    def _flush_mic_buffer(self, mic_buffer, system_buffer, n_samples):
        """Helper: build a mixed chunk from the first n_samples of the buffers."""
        mic_all = np.concatenate(mic_buffer)
        mic_chunk = mic_all[:n_samples]

        if system_buffer:
            sys_all = np.concatenate(system_buffer)
            sys_chunk = sys_all[:n_samples] if len(sys_all) >= n_samples else \
                np.pad(sys_all, ((0, n_samples - len(sys_all)), (0, 0)))
            mixed = (mic_chunk + sys_chunk) / 2
        else:
            mixed = mic_chunk

        self.combined_queue.put(mixed)

        # Return remaining data
        remaining_mic = mic_all[n_samples:]
        new_mic = [remaining_mic] if len(remaining_mic) > 0 else []

        new_sys = []
        if system_buffer:
            sys_all = np.concatenate(system_buffer)
            remaining_sys = sys_all[n_samples:]
            new_sys = [remaining_sys] if len(remaining_sys) > 0 else []

        return new_mic, new_sys

    def _audio_mixer_worker(self):
        """Worker thread to mix audio streams and create chunks"""
        mic_buffer = []
        system_buffer = []

        samples_per_chunk = int(self.sample_rate * self.chunk_duration)
        min_pause_samples = int(self.sample_rate * MIN_PAUSE_CHUNK_SECS)

        last_sound_time = time.time()

        while self.is_recording or not self.mic_queue.empty():
            try:
                # Get mic data
                try:
                    mic_data = self.mic_queue.get(timeout=0.1)
                    mic_buffer.append(mic_data)

                    # Track silence for pause-triggered flush
                    rms = float(np.sqrt(np.mean(mic_data ** 2)))
                    if rms > SILENCE_RMS_THRESHOLD:
                        last_sound_time = time.time()

                except queue.Empty:
                    pass

                # Get system data
                try:
                    system_data = self.system_queue.get(timeout=0.1)
                    system_buffer.append(system_data)
                except queue.Empty:
                    pass

                mic_samples = sum(len(d) for d in mic_buffer)

                # Normal full-chunk flush
                if mic_samples >= samples_per_chunk:
                    mic_buffer, system_buffer = self._flush_mic_buffer(
                        mic_buffer, system_buffer, samples_per_chunk)
                    last_sound_time = time.time()  # reset after flush

                # Pause-triggered early flush
                elif (mic_samples >= min_pause_samples and
                      time.time() - last_sound_time >= SILENCE_TRIGGER_SECS):
                    self.logger.info(
                        f"Pause detected — flushing {mic_samples / self.sample_rate:.1f}s early")
                    mic_buffer, system_buffer = self._flush_mic_buffer(
                        mic_buffer, system_buffer, mic_samples)
                    last_sound_time = time.time()

            except Exception as e:
                self.logger.error(f"Error in audio mixer: {e}")
                time.sleep(0.1)
    
    def _chunk_writer_worker(self):
        """Worker thread to write audio chunks to files"""
        while self.is_recording or not self.combined_queue.empty():
            try:
                # Get mixed audio chunk
                mixed_chunk = self.combined_queue.get(timeout=1.0)
                
                # Save chunk file
                chunk_filename = f"chunk_{self.chunk_number:03d}.wav"
                chunk_path = self.session_path / "audio" / "chunks" / chunk_filename
                
                sf.write(str(chunk_path), mixed_chunk, self.sample_rate)
                
                self.logger.info(f"Saved audio chunk: {chunk_filename}")
                
                # Call callback if set (for transcription)
                if self.chunk_callback:
                    try:
                        self.chunk_callback(str(chunk_path), self.chunk_number)
                    except Exception as e:
                        self.logger.error(f"Error in chunk callback: {e}")
                
                self.chunk_number += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error writing audio chunk: {e}")
    
    def _save_full_recording(self):
        """Save the complete recording as a single file"""
        try:
            if self.full_mic_data:
                # Combine all microphone data
                full_mic = np.concatenate(self.full_mic_data)
                
                if self.full_system_data:
                    # Combine system audio and mix
                    full_system = np.concatenate(self.full_system_data)
                    
                    # Ensure same length
                    min_len = min(len(full_mic), len(full_system))
                    full_mic = full_mic[:min_len]
                    full_system = full_system[:min_len]
                    
                    # Mix the audio
                    full_mixed = (full_mic + full_system) / 2
                else:
                    full_mixed = full_mic
                
                # Save full recording
                full_path = self.session_path / "audio" / "full_recording.wav"
                sf.write(str(full_path), full_mixed, self.sample_rate)
                
                self.logger.info(f"Saved full recording: {full_path}")
                
        except Exception as e:
            self.logger.error(f"Error saving full recording: {e}")

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    
    def test_chunk_callback(chunk_path, chunk_number):
        print(f"New chunk ready: {chunk_path} (#{chunk_number})")
    
    # Create test session
    session = MeetingSession("audio_test")
    session.create_directories()
    
    # Create recorder
    recorder = AudioRecorder(session.session_path)
    recorder.set_chunk_callback(test_chunk_callback)
    
    print("Audio devices:")
    recorder.list_audio_devices()
    
    print("\nStarting 10-second test recording...")
    if recorder.start_recording():
        time.sleep(10)
        recorder.stop_recording()
        print("Test recording complete!")