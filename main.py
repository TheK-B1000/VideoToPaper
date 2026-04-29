from src.data.json_store import load_json, save_json
from src.core.transcript_processor import process_transcript

def main():
    config_path = "configs/default_config.json"
    input_path = "data/raw/raw_transcript.json"
    output_path = "data/processed/clean_transcript.json"

    config = load_json(config_path)
    raw_transcript = load_json(input_path)

    clean_transcript = process_transcript(raw_transcript, config)

    save_json(clean_transcript, output_path)

    print("Transcript processing complete")
    print(f"input: {input_path}")
    print(f"output: {output_path}")
    print(f"Segments processed: {len(clean_transcript)}")


if __name__ == "__main__":
    main()
