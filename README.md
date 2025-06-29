# Subsearch

A Python script for searching specific terms across multiple subtitle files (SRT and VTT formats) and returning timestamped results. Particularly useful for finding specific moments in video content when you have subtitle files.

## Features

- **Multi-format support**: Works with both SRT (SubRip) and VTT (WebVTT) subtitle files
- **YouTube VTT optimization**: Handles YouTube-generated VTT files with automatic deduplication
- **Flexible search options**: Case-sensitive/insensitive search
- **Smart deduplication**: Removes duplicate/similar matches (especially useful for YouTube VTT files)
- **Multiple input methods**: Search specific files, directories, or use interactive mode
- **Output options**: Display results in console and/or save to file
- **Encoding support**: Handles UTF-8 and Latin-1 encoded files

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## Installation

1. Clone this repository or download the script:
```bash
git clone https://github.com/yourusername/subtitle-search-tool.git
cd subtitle-search-tool
```

2. Make the script executable (optional):
```bash
chmod +x subsearch.py
```

## Usage

### Interactive Mode

Run the script without arguments for an interactive experience:

```bash
python subsearch.py
```

The script will guide you through:
- Entering your search term
- Choosing search options (case sensitivity, deduplication)
- Selecting input source (current directory, specific directory, or specific files)
- Configuring output options

### Command Line Mode

#### Basic Examples

Search for "hello world" in current directory:
```bash
python subsearch.py "hello world"
```

Search in a specific directory:
```bash
python subsearch.py "tutorial" -d ./subtitles
```

Search specific files:
```bash
python subsearch.py "error" -f video1.srt video2.vtt video3.srt
```

#### Advanced Examples

Case-sensitive search with custom output directory:
```bash
python subsearch.py "Python" -d ./subtitles -c -o ./results
```

Search with custom deduplication settings:
```bash
python subsearch.py "python" -d ./subtitles --similarity-threshold 0.9 --time-window 15
```

Aggressive deduplication mode (removes more duplicates):
```bash
python subsearch.py "tutorial" -d . --aggressive-dedupe
```

Quiet mode (minimal output):
```bash
python subsearch.py "error" -d . -q
```

Disable deduplication (keep all matches):
```bash
python subsearch.py "hello" -d . --no-dedupe
```

Don't save results to file:
```bash
python subsearch.py "test" -d . --no-save
```

## Command Line Arguments

### Required
- `search_term`: The term to search for in subtitle files

### Input Options (mutually exclusive)
- `-d, --directory`: Directory to search for subtitle files
- `-f, --files`: Specific subtitle files to search (space-separated)

### Search Options
- `-c, --case-sensitive`: Enable case-sensitive search
- `--no-dedupe`: Disable deduplication (keep all matches)
- `--similarity-threshold`: Text similarity threshold for deduplication (0.0-1.0, default: 0.8)
- `--time-window`: Time window in seconds for deduplication (default: 5.0)
- `--aggressive-dedupe`: Use aggressive deduplication mode

### Output Options
- `-o, --output-dir`: Directory to save results file (default: current directory)
- `--no-save`: Don't save results to file
- `-q, --quiet`: Quiet mode with minimal output

### Help
- `-h, --help`: Show help message and exit

## Output Format

### Console Output
```
Found 3 matches for 'python':
============================================================

File: tutorial_video.srt
----------------------------------------
  Subtitle #45
  Time: 00:02:30,150 --> 00:02:33,200
  Text: In this tutorial, we'll learn Python basics.

  Subtitle #78
  Time: 00:05:12,400 --> 00:05:15,800
  Text: Python is a powerful programming language.
```

### File Output
Results are automatically saved to a text file named `search_results_[search_term].txt` in the specified output directory (unless `--no-save` is used).

## Deduplication

The script includes smart deduplication features, especially useful for YouTube VTT files which often contain duplicate or near-duplicate subtitle entries.

### Deduplication Modes

1. **Strict Mode** (default): Safer approach that keeps more results
   - Removes matches that are both highly similar AND close in time
   - Or very close in time (≤2 seconds) with moderate similarity

2. **Aggressive Mode** (`--aggressive-dedupe`): More aggressive removal
   - Removes matches that are either highly similar OR close in time
   - May remove some valid matches but better for heavily duplicated files

### Customization Options

- `--similarity-threshold`: How similar text must be to consider deduplication (0.0-1.0)
- `--time-window`: Time window in seconds for considering matches as potential duplicates
- `--no-dedupe`: Completely disable deduplication

## File Format Support

### SRT (SubRip) Files
Standard format with numbered subtitles, timestamps, and text:
```
1
00:00:12,400 --> 00:00:15,600
This is the first subtitle.

2
00:00:16,200 --> 00:00:18,800
This is the second subtitle.
```

### VTT (WebVTT) Files
Web Video Text Tracks format, including YouTube-generated files:
```
WEBVTT

00:00:12.400 --> 00:00:15.600
This is the first subtitle.

00:00:16.200 --> 00:00:18.800 align:start position:20%
This is the second subtitle.
```

The script automatically handles VTT-specific features like:
- Positioning and styling cues
- HTML-like formatting tags
- Different timestamp formats
- Header information

## Use Cases

- **Content Research**: Find specific topics discussed in video content
- **Quote Finding**: Locate exact quotes or phrases from videos
- **Educational Content**: Search lecture or tutorial videos for specific concepts
- **Accessibility**: Help locate specific content for users with hearing impairments
- **Content Creation**: Find clips or segments for video editing
- **Transcription Analysis**: Analyze patterns in spoken content

## Troubleshooting

### Common Issues

1. **No files found**: Ensure you're in the correct directory and have .srt or .vtt files
2. **Encoding errors**: The script automatically tries UTF-8 and Latin-1 encodings
3. **Too many duplicates**: Try using `--aggressive-dedupe` or adjusting `--similarity-threshold`
4. **Missing matches**: Try disabling deduplication with `--no-dedupe`

### File Encoding

The script automatically handles:
- UTF-8 encoding (default)
- Latin-1 encoding (fallback)

If you have files in other encodings, consider converting them to UTF-8 first.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is released into the public domain under The Unlicense - see the [LICENSE](LICENSE) file for details.

## Changelog

### Version 1.0.0
- Initial release
- Support for SRT and VTT files
- Interactive and command-line modes
- Smart deduplication features
- Flexible search options
