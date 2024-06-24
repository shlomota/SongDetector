import subprocess
import tempfile
from pydub import AudioSegment
import os
import hashlib
import re
from find_midi_matches_library import best_matches, midi_to_pitches_and_times, load_chunks_from_directory
from mido import MidiFile, MidiTrack, Message
import streamlit as st

LIBRARY_DIR = "data/library"
MIDIS_DIR = "data/midis"
METADATA_DIR = "data/metadata"

def sanitize_filename(filename):
    """Sanitize the filename by replacing problematic characters."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def convert_to_midi(audio_file, midi_file):
    cmd = [
        "/usr/local/bin/python2", 
        "audio_to_midi_melodia/audio_to_midi_melodia.py",
        audio_file,
        midi_file,
        "120",  # BPM, you might want to make this adjustable
        "--smooth", "0.25",
        "--minduration", "0.1"
    ]
    print(f"Running command: {' '.join(cmd)}")  # Debugging line
    subprocess.run(cmd, check=True)

def trim_audio(audio_segment, duration_ms=20000):
    """Trim the audio to the specified duration in milliseconds."""
    return audio_segment[:duration_ms]

def process_audio(audio_file_path):
    if not os.path.exists(MIDIS_DIR):
        os.makedirs(MIDIS_DIR)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as temp_midi:
        midi_file_path = temp_midi.name

    try:
        convert_to_midi(audio_file_path, midi_file_path)
        st.success("Audio converted to MIDI successfully!")


        # Load the query MIDI file
        query_pitches, query_times = midi_to_pitches_and_times(midi_file_path)
        
        # Load reference MIDI files
        result = load_chunks_from_directory(MIDIS_DIR)
        all_chunks, all_start_times, track_names = load_chunks_from_directory(MIDIS_DIR)

        st.info("Finding the best matches...")

        # Find best matches
        top_matches = best_matches(query_pitches, all_chunks, all_start_times, track_names=track_names, top_n=3)

        return top_matches, midi_file_path
    except Exception as e:
        print(f"Error processing audio file: {e}")
        return None, None

def extract_vocals(mp3_file, output_dir):
    cmd = [
        "demucs",
        "-o", output_dir,
        mp3_file
    ]
    subprocess.run(cmd, check=True)

def is_in_library(query):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    midi_file = os.path.join(MIDIS_DIR, f"{query_hash}.mid")
    return os.path.exists(midi_file)

def split_midi(pitches, times, chunk_length=20, overlap=10):
    chunks = []
    start_times = []
    
    num_chunks = (len(times) - overlap) // (chunk_length - overlap)
    
    for i in range(num_chunks):
        start_idx = i * (chunk_length - overlap)
        end_idx = start_idx + chunk_length
        
        chunk_pitches = pitches[start_idx:end_idx]
        chunk_times = times[start_idx:end_idx]
        
        chunks.append((chunk_pitches, chunk_times))
        start_times.append(times[start_idx])
        
    return chunks, start_times

def extract_midi_chunk(midi_file_path, start_time, duration=20):
    try:
        midi = MidiFile(midi_file_path)
        chunk = MidiFile()
        for i, track in enumerate(midi.tracks):
            new_track = MidiTrack()
            current_time = 0
            for msg in track:
                current_time += msg.time
                if start_time <= current_time <= start_time + duration:
                    new_track.append(msg)
            chunk.tracks.append(new_track)
        return chunk
    except Exception as e:
        print(f"Error extracting MIDI chunk: {e}")
        return None

def save_midi_chunk(chunk, output_path):
    try:
        chunk.save(output_path)
    except Exception as e:
        print(f"Error saving MIDI chunk: {e}")


