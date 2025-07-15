import sys
import csv
import collections
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import shutil
from pathlib import Path

# Assuming these are part of your Flask application setup
from app import app
from models import db, Annot

def get_time_info_from_filename(filename):
    """
    Extracts the UTC timestamp from a filename, and returns both a
    datetime object for sorting and a formatted JST string for display.
    """
    match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', filename)
    if not match:
        return None, "Time Not Found"

    utc_time_str = match.group(1)
    
    try:
        utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        jst_tz = ZoneInfo("Asia/Tokyo")
        jst_dt = utc_dt.astimezone(jst_tz)
        jst_str = jst_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        return utc_dt, jst_str
    except (ValueError, TypeError):
        return None, "Invalid Time Format"


def export_data_and_organize_files():
    """
    Outputs annotation data as CSV, then analyzes it to find, create folders
    for, and copy files from shooters with a high '悪い' label ratio.
    Also writes a detailed summary into a text file in each created folder.
    """
    # --- Configuration ---
    VIDEO_SEARCH_PATH = Path("/large/takaki/JSL/ReviewVideos/")
    OUTPUT_BASE_DIR = Path("need_contact")

    with app.app_context():
        annotations = Annot.query.all()

        if not annotations:
            print("No annotation data found.", file=sys.stderr)
            return

        # --- Part 1: CSV Export & Data Collection ---
        writer = csv.writer(sys.stdout)
        header = ['id', 'video_path', 'sign', 'user', 'time', 'label', 'comments']
        writer.writerow(header)

        shooter_stats = collections.defaultdict(lambda: collections.defaultdict(int))
        bad_files_by_shooter = collections.defaultdict(list)
        latest_user_time = {}

        for annot in annotations:
            writer.writerow([
                annot.id, annot.video_path, annot.sign, annot.user,
                annot.time.isoformat(), annot.label, annot.comments
            ])

            if annot.video_path:
                shooter = annot.video_path.split('-')[0]
                shooter_stats[shooter]['total'] += 1
                if annot.label == '悪い':
                    shooter_stats[shooter]['悪い'] += 1
                    dt_obj, jst_time_str = get_time_info_from_filename(annot.video_path)
                    bad_files_by_shooter[shooter].append((dt_obj, annot.video_path, annot.sign, jst_time_str))

            if annot.user not in latest_user_time or annot.time > latest_user_time[annot.user]:
                latest_user_time[annot.user] = annot.time

        # --- Part 2: Analysis and File Operations ---
        print("\n--- Quality Analysis & File Organization ---", file=sys.stderr)
        
        found_issues = False
        for shooter, counts in sorted(shooter_stats.items()):
            if counts['total'] == 0:
                continue

            bad_ratio = counts['悪い'] / counts['total']

            if bad_ratio > 0.3:
                found_issues = True
                print(f"\n🚨 Shooter {shooter} has a high '悪い' ratio: {bad_ratio:.1%}", file=sys.stderr)

                # 1. Create destination directory
                dest_dir = OUTPUT_BASE_DIR / shooter
                dest_dir.mkdir(parents=True, exist_ok=True)
                print(f"   -> Ensured directory exists: {dest_dir}", file=sys.stderr)

                # 2. Prepare and write the summary file
                files_to_report = bad_files_by_shooter[shooter]
                files_to_report.sort(key=lambda item: item[0] if item[0] is not None else datetime.min.replace(tzinfo=timezone.utc))

                # Build the summary content as a list of strings
                summary_lines = [
                    f"Shooter: {shooter}",
                    f"Bad Annotation Ratio: {bad_ratio:.1%} ({counts['悪い']} bad / {counts['total']} total)",
                    "---",
                    "Files Marked as '悪い':\n"
                ]

                for dt_obj, filename, sign, jst_time in files_to_report:
                    summary_lines.append(f"  Time: {jst_time}")
                    summary_lines.append(f"  Sign: {sign}")
                    summary_lines.append(f"  File: {filename}\n")
                
                # Join the lines into a single string
                summary_content = "\n".join(summary_lines)
                
                # Construct the filename and write the summary content
                report_filename = f"{counts['悪い']}_{counts['total']}.txt"
                report_file_path = dest_dir / report_filename
                report_file_path.write_text(summary_content, encoding='utf-8')
                print(f"   -> Wrote summary to: {report_filename}", file=sys.stderr)

                # 3. Find and copy each "bad" video file
                for dt_obj, filename, sign, jst_time in files_to_report:
                    print(f"   - Processing video: {filename}", file=sys.stderr)
                    
                    found_files = list(VIDEO_SEARCH_PATH.rglob(filename))
                    
                    if not found_files:
                        print(f"     -> ❌ WARNING: Video not found in {VIDEO_SEARCH_PATH}", file=sys.stderr)
                    else:
                        for source_path in found_files:
                            try:
                                shutil.copy(source_path, dest_dir)
                                print(f"     -> ✅ Copied to {dest_dir}", file=sys.stderr)
                            except Exception as e:
                                print(f"     -> ❌ ERROR copying {source_path.name}: {e}", file=sys.stderr)
        
        if not found_issues:
            print("\n✅ No shooters found with a '悪い' label ratio above 30%. No files were copied.", file=sys.stderr)

        # --- Part 3: User Activity Report ---
        print("\n--- User Last Annotation Time ---", file=sys.stderr)
        if latest_user_time:
            jst_tz = ZoneInfo("Asia/Tokyo")
            for user, last_time in sorted(latest_user_time.items()):
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                
                jst_dt = last_time.astimezone(jst_tz)
                jst_str = jst_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                print(f"  - User: {user:<15} | Last Annotation: {jst_str}", file=sys.stderr)

if __name__ == "__main__":
    export_data_and_organize_files()