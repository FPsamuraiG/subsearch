#!/usr/bin/env python3
"""
Subtitle Search Script
Searches for a specific term across multiple .srt and .vtt subtitle files and returns timestamps.
Supports both standard SRT files and YouTube-generated VTT files.
"""

import os
import re
import glob
import argparse
import sys
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SubtitleMatch:
    """Class to store subtitle search matches"""
    file_path: str
    timestamp: str
    subtitle_number: int
    text: str


def parse_srt_file(file_path: str) -> List[Dict]:
    """
    Parse an SRT file and return a list of subtitle entries.
    
    Args:
        file_path (str): Path to the SRT file
        
    Returns:
        List[Dict]: List of subtitle entries with number, timestamp, and text
    """
    subtitles = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                content = file.read().strip()
        except Exception as e:
            print(f"Could not read file {file_path}: {e}")
            return []
    except Exception as e:
        print(f"Could not read file {file_path}: {e}")
        return []
    
    # Split content into subtitle blocks
    blocks = re.split(r'\n\s*\n', content)
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        try:
            # First line: subtitle number
            subtitle_num = int(lines[0].strip())
            
            # Second line: timestamp
            timestamp = lines[1].strip()
            
            # Remaining lines: subtitle text
            text = '\n'.join(lines[2:]).strip()
            
            subtitles.append({
                'number': subtitle_num,
                'timestamp': timestamp,
                'text': text
            })
            
        except (ValueError, IndexError):
            # Skip malformed subtitle blocks
            continue
    
    return subtitles


def parse_vtt_file(file_path: str) -> List[Dict]:
    """
    Parse a VTT (WebVTT) file and return a list of subtitle entries.
    Handles YouTube-generated VTT files with their specific format.
    
    Args:
        file_path (str): Path to the VTT file
        
    Returns:
        List[Dict]: List of subtitle entries with number, timestamp, and text
    """
    subtitles = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                content = file.read().strip()
        except Exception as e:
            print(f"Could not read file {file_path}: {e}")
            return []
    except Exception as e:
        print(f"Could not read file {file_path}: {e}")
        return []
    
    lines = content.split('\n')
    subtitle_num = 0
    i = 0
    
    # Skip header lines (WEBVTT, NOTE, etc.)
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('WEBVTT') or line.startswith('NOTE') or line.startswith('Kind:') or line.startswith('Language:') or not line:
            i += 1
            continue
        break
    
    while i < len(lines):
        # Look for timestamp line (contains -->)
        if '-->' in lines[i]:
            subtitle_num += 1
            timestamp_line = lines[i].strip()
            
            # Clean up timestamp line - remove positioning info
            timestamp = re.sub(r'\s+(align|position|size|line):[^\s]+', '', timestamp_line)
            # Convert VTT timestamp to SRT-like format for consistency
            # VTT uses dots for milliseconds, SRT uses commas
            timestamp = timestamp.replace('.', ',')
            
            i += 1
            text_lines = []
            
            # Collect text lines until empty line or end of file
            while i < len(lines) and lines[i].strip():
                text_line = lines[i].strip()
                # Remove VTT formatting tags like <c.yellow>, <i>, etc.
                text_line = re.sub(r'<[^>]*>', '', text_line)
                # Remove alignment and positioning cues
                text_line = re.sub(r'\{[^}]*\}', '', text_line)
                # Clean up HTML entities
                text_line = text_line.replace('&nbsp;', ' ')
                text_line = re.sub(r'&[a-zA-Z]+;', '', text_line)  # Remove other HTML entities
                if text_line:
                    text_lines.append(text_line)
                i += 1
            
            if text_lines:
                text = '\n'.join(text_lines)
                subtitles.append({
                    'number': subtitle_num,
                    'timestamp': timestamp,
                    'text': text
                })
        else:
            i += 1
    
    return subtitles


def parse_subtitle_file(file_path: str) -> List[Dict]:
    """
    Parse a subtitle file (SRT or VTT) and return a list of subtitle entries.
    
    Args:
        file_path (str): Path to the subtitle file
        
    Returns:
        List[Dict]: List of subtitle entries with number, timestamp, and text
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.srt':
        return parse_srt_file(file_path)
    elif file_extension == '.vtt':
        return parse_vtt_file(file_path)
    else:
        print(f"Unsupported file format: {file_extension}")
        return []


def deduplicate_matches(matches: List[SubtitleMatch], 
                       similarity_threshold: float = 0.8,
                       time_window: float = 30.0,
                       strict_mode: bool = True) -> List[SubtitleMatch]:
    """
    Remove duplicate matches that are very similar (common in YouTube VTT files).
    
    Args:
        matches (List[SubtitleMatch]): List of matches to deduplicate
        similarity_threshold (float): Threshold for considering matches similar (0.0-1.0)
        time_window (float): Time window in seconds for considering matches as potential duplicates
        strict_mode (bool): If True, requires both similarity AND time proximity for deduplication.
                           If False, uses OR logic (more aggressive deduplication)
        
    Returns:
        List[SubtitleMatch]: Deduplicated list of matches
    """
    if not matches:
        return matches
    
    def text_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)
    
    def parse_timestamp(timestamp: str) -> float:
        """Convert timestamp to seconds for comparison."""
        try:
            # Extract start time from "HH:MM:SS,mmm --> HH:MM:SS,mmm" format
            start_time = timestamp.split(' --> ')[0]
            parts = start_time.replace(',', '.').split(':')
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0.0
    
    # Group matches by file
    file_groups = {}
    for match in matches:
        if match.file_path not in file_groups:
            file_groups[match.file_path] = []
        file_groups[match.file_path].append(match)
    
    deduplicated = []
    
    for file_path, file_matches in file_groups.items():
        # Sort matches by timestamp
        file_matches.sort(key=lambda x: parse_timestamp(x.timestamp))
        
        filtered_matches = []
        for current_match in file_matches:
            is_duplicate = False
            
            # Check against already filtered matches
            for existing_match in filtered_matches:
                # Check if texts are similar
                similarity = text_similarity(current_match.text, existing_match.text)
                
                # Check if timestamps are close (within 5 seconds)
                current_time = parse_timestamp(current_match.timestamp)
                existing_time = parse_timestamp(existing_match.timestamp)
                time_diff = abs(current_time - existing_time)
                
                # Consider it a duplicate based on the deduplication mode
                if strict_mode:
                    # Strict mode: High similarity AND close in time, OR very close in time with moderate similarity
                    if (similarity >= similarity_threshold and time_diff <= time_window) or \
                       (time_diff <= 2.0 and similarity >= 0.5):
                        is_duplicate = True
                        break
                else:
                    # Aggressive mode: High similarity OR close in time
                    if similarity >= similarity_threshold or time_diff <= time_window:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                filtered_matches.append(current_match)
        
        deduplicated.extend(filtered_matches)
    
    return deduplicated


def search_in_subtitle_files(file_paths: List[str], search_term: str, case_sensitive: bool = False, 
                           deduplicate: bool = True, similarity_threshold: float = 0.8,
                           time_window: float = 30.0, strict_dedup: bool = True) -> List[SubtitleMatch]:
    """
    Search for a term in multiple subtitle files (SRT or VTT).
    
    Args:
        file_paths (List[str]): List of subtitle file paths
        search_term (str): Term to search for
        case_sensitive (bool): Whether search should be case sensitive
        deduplicate (bool): Whether to remove duplicate/similar matches (useful for VTT files)
        similarity_threshold (float): Threshold for text similarity in deduplication (0.0-1.0)
        time_window (float): Time window in seconds for deduplication
        strict_dedup (bool): Use strict deduplication mode (safer, keeps more results)
        
    Returns:
        List[SubtitleMatch]: List of matches found
    """
    matches = []
    
    for file_path in file_paths:
        print(f"Searching in: {os.path.basename(file_path)}")
        
        subtitles = parse_subtitle_file(file_path)
        
        for subtitle in subtitles:
            text = subtitle['text']
            search_text = text if case_sensitive else text.lower()
            term = search_term if case_sensitive else search_term.lower()
            
            if term in search_text:
                matches.append(SubtitleMatch(
                    file_path=file_path,
                    timestamp=subtitle['timestamp'],
                    subtitle_number=subtitle['number'],
                    text=text
                ))
    
    # Deduplicate matches if requested (especially useful for VTT files)
    if deduplicate:
        original_count = len(matches)
        matches = deduplicate_matches(matches, similarity_threshold, time_window, strict_dedup)
        if original_count > len(matches):
            print(f"Removed {original_count - len(matches)} duplicate/similar matches")
    
    return matches


def find_subtitle_files(directory: str) -> List[str]:
    """
    Find all .srt and .vtt files in a directory.
    
    Args:
        directory (str): Directory to search in
        
    Returns:
        List[str]: List of subtitle file paths
    """
    srt_pattern = os.path.join(directory, "*.srt")
    vtt_pattern = os.path.join(directory, "*.vtt")
    
    srt_files = glob.glob(srt_pattern)
    vtt_files = glob.glob(vtt_pattern)
    
    return srt_files + vtt_files


def print_results(matches: List[SubtitleMatch], search_term: str):
    """
    Print search results in a formatted way.
    
    Args:
        matches (List[SubtitleMatch]): List of matches to print
        search_term (str): The search term used
    """
    if not matches:
        print(f"\nNo matches found for '{search_term}'")
        return
    
    print(f"\nFound {len(matches)} matches for '{search_term}':")
    print("=" * 60)
    
    current_file = None
    for match in matches:
        if match.file_path != current_file:
            current_file = match.file_path
            print(f"\nFile: {os.path.basename(match.file_path)}")
            print("-" * 40)
        
        print(f"  Subtitle #{match.subtitle_number}")
        print(f"  Time: {match.timestamp}")
        print(f"  Text: {match.text}")
        print()


def save_results_to_file(matches: List[SubtitleMatch], search_term: str, output_path: str) -> str:
    """
    Save search results to a file.
    
    Args:
        matches (List[SubtitleMatch]): List of matches to save
        search_term (str): The search term used
        output_path (str): Path where to save the file
        
    Returns:
        str: Full path of the saved file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Generate filename
    safe_search_term = re.sub(r'[^\w\s-]', '', search_term).strip()
    safe_search_term = re.sub(r'[-\s]+', '_', safe_search_term)
    output_file = os.path.join(output_path, f"search_results_{safe_search_term}.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Search Results for '{search_term}'\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total matches found: {len(matches)}\n\n")
        
        if not matches:
            f.write("No matches found.\n")
            return output_file
        
        current_file = None
        for match in matches:
            if match.file_path != current_file:
                current_file = match.file_path
                f.write(f"File: {os.path.basename(match.file_path)}\n")
                f.write("-" * 40 + "\n")
            
            f.write(f"Subtitle #{match.subtitle_number}\n")
            f.write(f"Time: {match.timestamp}\n")
            f.write(f"Text: {match.text}\n\n")
    
    return output_file


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Search for terms in subtitle files (SRT and VTT formats)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python subsearch.py

  # Search in current directory
  python subsearch.py "hello world" -d .

  # Search specific files
  python subsearch.py "tutorial" -f video1.srt video2.vtt

  # Search with advanced deduplication options
  python subsearch.py "python" -d ./subtitles --similarity-threshold 0.9 --time-window 15

  # Aggressive deduplication mode
  python subsearch.py "error" -d . --aggressive-dedupe

  # Quiet mode with output
  python subsearch.py "error" -d . -o ./output --quiet
        """
    )
    
    parser.add_argument('search_term', nargs='?', help='Term to search for')
    
    # Input source (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument('-d', '--directory', 
                             help='Directory to search for subtitle files')
    source_group.add_argument('-f', '--files', nargs='+', 
                             help='Specific subtitle files to search')
    
    # Search options
    parser.add_argument('-c', '--case-sensitive', action='store_true',
                       help='Case sensitive search')
    parser.add_argument('--no-dedupe', action='store_true',
                       help='Disable deduplication (keep all matches)')
    parser.add_argument('--similarity-threshold', type=float, default=0.8,
                       help='Text similarity threshold for deduplication (0.0-1.0, default: 0.8)')
    parser.add_argument('--time-window', type=float, default=5.0,
                       help='Time window in seconds for deduplication (default: 5.0)')
    parser.add_argument('--aggressive-dedupe', action='store_true',
                       help='Use aggressive deduplication (removes more matches, may remove valid ones)')
    
    # Output options
    parser.add_argument('-o', '--output-dir', default='.',
                       help='Directory to save results file (default: current directory)')
    parser.add_argument('--no-save', action='store_true',
                       help='Don\'t save results to file')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Quiet mode - minimal output')
    
    return parser.parse_args()


def run_interactive():
    """Run the program in interactive mode."""
    print("Subtitle Search Tool (SRT & VTT)")
    print("=" * 35)
    
    # Get search parameters from user
    search_term = input("Enter search term: ").strip()
    if not search_term:
        print("Search term cannot be empty!")
        return False
    
    case_sensitive = input("Case sensitive search? (y/n): ").lower().startswith('y')
    
    # Ask about deduplication options
    deduplicate = input("Remove duplicate/similar results? (recommended for YouTube VTT files) (y/n): ").lower().startswith('y')
    
    similarity_threshold = 0.8
    time_window = 30.0
    strict_dedup = True
    
    if deduplicate:
        advanced_options = input("Configure advanced deduplication options? (y/n): ").lower().startswith('y')
        if advanced_options:
            try:
                threshold_input = input(f"Text similarity threshold (0.0-1.0, default {similarity_threshold}): ").strip()
                if threshold_input:
                    similarity_threshold = float(threshold_input)
                    similarity_threshold = max(0.0, min(1.0, similarity_threshold))  # Clamp to valid range
                
                time_input = input(f"Time window in seconds (default {time_window}): ").strip()
                if time_input:
                    time_window = float(time_input)
                    time_window = max(1.0, time_window)  # Minimum 1 second
                
                strict_input = input("Use strict deduplication mode? (safer, keeps more results) (y/n): ").lower()
                strict_dedup = not strict_input.startswith('n')  # Default to True
                
            except ValueError:
                print("Invalid input, using default values")
                similarity_threshold = 0.8
                time_window = 30.0
                strict_dedup = True
    
    # Get file source
    source_choice = input("\nSearch in:\n1. Current directory\n2. Specific directory\n3. Specific files\nChoice (1-3): ").strip()
    
    file_paths = []
    
    if source_choice == '1':
        file_paths = find_subtitle_files('.')
    elif source_choice == '2':
        directory = input("Enter directory path: ").strip()
        if os.path.isdir(directory):
            file_paths = find_subtitle_files(directory)
        else:
            print("Invalid directory path!")
            return False
    elif source_choice == '3':
        files_input = input("Enter subtitle file paths (comma-separated): ").strip()
        file_paths = [path.strip() for path in files_input.split(',')]
        # Filter only existing subtitle files
        file_paths = [path for path in file_paths if os.path.isfile(path) and 
                     (path.lower().endswith('.srt') or path.lower().endswith('.vtt'))]
    else:
        print("Invalid choice!")
        return False
    
    if not file_paths:
        print("No subtitle files found!")
        return False
    
    print(f"\nFound {len(file_paths)} subtitle file(s) to search")
    
    # Show file types found
    srt_count = sum(1 for f in file_paths if f.lower().endswith('.srt'))
    vtt_count = sum(1 for f in file_paths if f.lower().endswith('.vtt'))
    if srt_count > 0:
        print(f"  - {srt_count} SRT file(s)")
    if vtt_count > 0:
        print(f"  - {vtt_count} VTT file(s)")
    
    # Perform search
    matches = search_in_subtitle_files(file_paths, search_term, case_sensitive, deduplicate, 
                                     similarity_threshold, time_window, strict_dedup)
    
    # Print results
    print_results(matches, search_term)
    
    # Optional: Save results to file
    save_results = input("\nSave results to file? (y/n): ").lower().startswith('y')
    if save_results and matches:
        output_dir = input("Enter output directory (press Enter for current directory): ").strip()
        if not output_dir:
            output_dir = '.'
        
        output_file = save_results_to_file(matches, search_term, output_dir)
        print(f"Results saved to: {output_file}")
    
    return True


def run_command_line(args):
    """Run the program with command line arguments."""
    search_term = args.search_term
    
    # Determine file paths
    if args.directory:
        if not os.path.isdir(args.directory):
            print(f"Error: Directory '{args.directory}' does not exist", file=sys.stderr)
            return False
        file_paths = find_subtitle_files(args.directory)
    elif args.files:
        # Validate files exist and are subtitle files
        file_paths = []
        for file_path in args.files:
            if not os.path.isfile(file_path):
                print(f"Warning: File '{file_path}' does not exist", file=sys.stderr)
                continue
            if not (file_path.lower().endswith('.srt') or file_path.lower().endswith('.vtt')):
                print(f"Warning: File '{file_path}' is not a subtitle file", file=sys.stderr)
                continue
            file_paths.append(file_path)
    else:
        # Default to current directory
        file_paths = find_subtitle_files('.')
    
    if not file_paths:
        print("Error: No subtitle files found", file=sys.stderr)
        return False
    
    if not args.quiet:
        print(f"Searching {len(file_paths)} subtitle file(s) for '{search_term}'")
        
        # Show file types found
        srt_count = sum(1 for f in file_paths if f.lower().endswith('.srt'))
        vtt_count = sum(1 for f in file_paths if f.lower().endswith('.vtt'))
        if srt_count > 0:
            print(f"  - {srt_count} SRT file(s)")
        if vtt_count > 0:
            print(f"  - {vtt_count} VTT file(s)")
    
    # Perform search
    deduplicate = not args.no_dedupe
    strict_dedup = not args.aggressive_dedupe
    matches = search_in_subtitle_files(file_paths, search_term, args.case_sensitive, 
                                     deduplicate, args.similarity_threshold, 
                                     args.time_window, strict_dedup)
    
    if not args.quiet:
        # Print results to console
        print_results(matches, search_term)
    
    # Save results to file (unless disabled)
    if not args.no_save:
        output_file = save_results_to_file(matches, search_term, args.output_dir)
        if not args.quiet:
            print(f"\nResults saved to: {output_file}")
        else:
            print(output_file)  # In quiet mode, just print the output file path
    
    return True


def main():
    """Main function to run the subtitle search."""
    args = parse_arguments()
    
    if args.search_term:
        # Command line mode
        success = run_command_line(args)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        success = run_interactive()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()