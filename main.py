from src.data.json_store import load_json, save_json
from src.core.transcript_processor import process_transcript
from src.ops.run_tracker import (
    create_run_log,
    record_metric,
    record_error,
    finish_run_log,
    save_run_log
)

def main():
    config_path = "configs/default_config.json"
    input_path = "data/raw/raw_transcript.json"
    output_path = "data/processed/clean_transcript.json"

    run_log = create_run_log(
        config_path=config_path,
        input_path=input_path,
        output_path=output_path
    )

    try:
        config = load_json(config_path)
        raw_transcript = load_json(input_path)

        record_metric(run_log, "raw_segment_count", len(raw_transcript))

        clean_transcript = process_transcript(raw_transcript, config)

        record_metric(run_log, "clean_segment_count", len(clean_transcript))

        save_json(clean_transcript, output_path)

        finish_run_log(run_log, "success")

        print("Transcript processing complete")
        print(f"input: {input_path}")
        print(f"output: {output_path}")
        print(f"Segments processed: {len(clean_transcript)}")
    
    except Exception as e:
        record_error(run_log, str(e))
        finish_run_log(run_log, "failed")
        raise
        
    finally:
        save_run_path = save_run_log(run_log)
        print(f"Run log saved to: {save_run_path}")
    


if __name__ == "__main__":
    main()
