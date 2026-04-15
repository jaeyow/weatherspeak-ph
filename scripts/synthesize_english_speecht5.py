#!/usr/bin/env python3
"""Synthesize English MP3 using SpeechT5 for better pronunciation quality.

This script reads the existing TTS text file and generates high-quality English audio.
Run this after notebook 06 has generated the English TTS text file.
"""
import re
import time
import numpy as np
import torch
from pathlib import Path
from pydub import AudioSegment
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech
from datasets import load_dataset


def prepare_mms_sentences(text: str) -> list[tuple[str, bool]]:
    """Split plain text into sentences with paragraph boundary flags."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    result = []
    for paragraph in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for sent_idx, sentence in enumerate(sentences):
            is_last_in_para = (sent_idx == len(sentences) - 1)
            sentence = sentence.lower()
            # Remove all punctuation except apostrophes and hyphens
            s = re.sub(r"[^\w\s'\-]", " ", sentence)
            # Remove apostrophes/hyphens not flanked by word characters
            s = re.sub(r"(?<!\w)['\-]|['\-](?!\w)", " ", s)
            sentence = re.sub(r"\s+", " ", s).strip()
            if sentence:
                result.append((sentence, is_last_in_para))
    return result


def synthesize_english_speecht5(
    input_txt_path: Path,
    output_mp3_path: Path,
    sentence_pause_ms: int = 500,
    paragraph_pause_ms: int = 750,
):
    """Synthesize English MP3 from TTS text using SpeechT5."""
    
    print(f"Loading SpeechT5 model...")
    t0 = time.time()
    processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
    model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
    model.eval()
    
    # Load speaker embeddings
    print(f"Loading speaker embeddings...")
    embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
    speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
    print(f"✓ Model loaded in {time.time() - t0:.1f}s")
    
    # Read and prepare text
    print(f"\nReading TTS text from {input_txt_path.name}...")
    text = input_txt_path.read_text(encoding="utf-8")
    sentences = prepare_mms_sentences(text)
    print(f"✓ Prepared {len(sentences)} sentences")
    
    # Synthesize
    print(f"\nSynthesizing English audio...")
    sample_rate = model.config.sampling_rate
    combined = AudioSegment.empty()
    
    t_start = time.time()
    for idx, (sentence, is_paragraph_end) in enumerate(sentences, 1):
        if not sentence.strip():
            continue
        
        if idx % 10 == 0:
            print(f"  Progress: {idx}/{len(sentences)} sentences...")
        
        # SpeechT5 synthesis
        inputs = processor(text=sentence, return_tensors="pt")
        with torch.no_grad():
            waveform = model.generate_speech(inputs["input_ids"], speaker_embeddings)
        
        # Convert to PCM
        pcm = (waveform.numpy() * 32_767).clip(-32_768, 32_767).astype(np.int16)
        segment = AudioSegment(pcm.tobytes(), frame_rate=sample_rate, sample_width=2, channels=1)
        combined += segment
        
        # Add pause
        pause_ms = paragraph_pause_ms if is_paragraph_end else sentence_pause_ms
        combined += AudioSegment.silent(duration=pause_ms, frame_rate=sample_rate)
    
    elapsed = time.time() - t_start
    
    # Export MP3
    print(f"\nExporting MP3...")
    combined.export(str(output_mp3_path), format="mp3", bitrate="128k")
    
    size_kb = output_mp3_path.stat().st_size // 1024
    duration_s = (size_kb * 1024 * 8) / 128_000
    
    print(f"\n✓ Synthesis complete!")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Size: {size_kb} KB")
    print(f"  Duration: ~{duration_s:.0f}s audio")
    print(f"  Output: {output_mp3_path}")


if __name__ == "__main__":
    # Paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / "data" / "radio_bulletins" / "PAGASA_20-19W_Pepito_SWB#01_tts_en.txt"
    output_file = project_root / "notebooks" / "08-mms-tts-experiment" / "PAGASA_20-19W_Pepito_SWB#01_tts_en.mp3"
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Run notebook 06 first to generate the English TTS text file.")
        exit(1)
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    synthesize_english_speecht5(input_file, output_file)
