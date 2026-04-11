import sys
import pulse_check
import generate_summary
import os

def main():
    # Allow force generation via environment variable
    force_gen = os.getenv("FORCE_AI_SUMMARY", "false").lower() == "true"
    
    # 1. Update data and check if anything changed
    print("🔄 Starting Pulse Check...")
    data_changed = pulse_check.update_dashboard_data()
    
    # 2. Only run AI summary if data changed or force_gen is True
    if data_changed or force_gen:
        if force_gen:
            print("⚡ Force generation enabled.")
        else:
            print("📈 New data detected. Triggering AI analysis...")
            
        generate_summary.generate_summary(force=force_gen)
    else:
        print("⏸️ No new data found. Skipping AI summary generation to save costs.")

if __name__ == "__main__":
    main()
