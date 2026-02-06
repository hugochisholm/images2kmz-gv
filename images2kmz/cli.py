"""Command-line interface for images2kmz."""

import argparse
import os
import sys
from typing import Optional

from .core import KMZGenerator
from .image_processor import ImageProcessor
from .heic_handler import HEICHandler, is_heic_supported, batch_convert_heic
from .utils import get_absolute_path


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='images2kmz',
        description='Create KMZ files from geotagged photos with embedded thumbnails.',
        epilog='Examples: images2kmz (interactive) | images2kmz ~/photos | images2kmz . -o output.kmz -r'
    )
    
    parser.add_argument(
        'input_dir',
        type=str,
        nargs='?',
        default=None,
        help='Directory containing photos (optional; will prompt if not provided)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='photos.kmz',
        help='Output KMZ file path (default: photos.kmz)'
    )
    
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Recursively search subdirectories for photos'
    )
    
    parser.add_argument(
        '--thumbnail-size',
        type=int,
         nargs=2,
         metavar=('WIDTH', 'HEIGHT'),
         default=[800, 600],
         help='Maximum thumbnail dimensions in pixels (default: 800 600)'
     )
    
    parser.add_argument(
        '--convert-heic',
        action='store_true',
        help='Automatically convert HEIC files without prompting'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    return parser


def print_header():
    """Print application header."""
    print("=" * 60)
    print("images2kmz - Geotagged Photo KMZ Generator")
    print("=" * 60)


def prompt_for_directory() -> str:
    """
    Prompt user to input a directory path for image scanning.
    Supports relative paths, absolute paths, and Windows-style paths.
    Creates directory if it doesn't exist and user confirms.
    
    Returns:
        Absolute path to the validated/created directory
    """
    while True:
        user_input = input('Please provide a directory containing images to process: ').strip()
        
        if not user_input:
            print('Error: Path cannot be empty. Please try again.')
            continue
        
        # Handle various path formats (relative, absolute, Windows-style)
        abs_path = get_absolute_path(user_input)
        
        if not os.path.isdir(abs_path):
            # Directory doesn't exist - ask user if they want to create it
            response = input(f'Directory does not exist: {abs_path}. Create it? (y/n): ').strip().lower()
            
            if response in ('y', 'yes'):
                try:
                    os.makedirs(abs_path, exist_ok=True)
                    print(f'Created directory: {abs_path}')
                    return abs_path
                except Exception as e:
                    print(f'Error creating directory: {e}')
                    print('Please try again.')
                    continue
            else:
                print('Exiting gracefully.')
                sys.exit(0)
        else:
            return abs_path


def print_summary(processor_stats: dict, kmz_generator: Optional[KMZGenerator], output_path: Optional[str]):
    """
    Print processing summary.
    
    Args:
        processor_stats: Statistics from ImageProcessor
        kmz_generator: KMZGenerator instance
        output_path: Path to output KMZ file
    """
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    # Processing stats
    total = processor_stats['total_found']
    processed = processor_stats['processed']
    skipped = processor_stats['skipped_no_gps']
    errors = processor_stats['errors']
    
    if processed > 0:
        print(f"✓ Processed: {processed} photo{'s' if processed != 1 else ''} with GPS data")
    
    if skipped > 0:
        print(f"⊗ Skipped: {skipped} photo{'s' if skipped != 1 else ''} (no GPS data)")
    
    if errors > 0:
        print(f"✗ Errors: {errors} photo{'s' if errors != 1 else ''} (processing failed)")
    
    # Output file info
    if processed > 0 and kmz_generator and output_path:
        file_size = kmz_generator.get_formatted_file_size()
        if file_size:
            print(f"📦 Output: {os.path.basename(output_path)} ({file_size})")
        else:
            print(f"📦 Output: {os.path.basename(output_path)}")
        print(f"   Path: {output_path}")
    else:
        print("\n⚠ No photos with GPS data found. KMZ file not created.")
    
    print("=" * 60)


def run(args: Optional[list] = None) -> int:
    """
    Run the CLI application.
    
    Args:
        args: Command-line arguments (None to use sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse arguments
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Print header
    print_header()
    
    # Handle optional input directory - prompt if not provided
    if parsed_args.input_dir is None:
        input_dir = prompt_for_directory()
    else:
        input_dir = get_absolute_path(parsed_args.input_dir)
        if not os.path.isdir(input_dir):
            print(f"\nError: Input directory does not exist: {input_dir}")
            return 1
    
    print(f"\nInput directory: {input_dir}")
    print(f"Recursive search: {'Yes' if parsed_args.recursive else 'No'}")
    print(f"Thumbnail size: {parsed_args.thumbnail_size[0]}x{parsed_args.thumbnail_size[1]}")
    
    # Handle HEIC files
    print(f"\nScanning for images...")
    heic_handler = HEICHandler(input_dir, parsed_args.recursive)
    num_heic = heic_handler.scan()
    
    if num_heic > 0:
        if parsed_args.convert_heic:
            # Auto-convert without prompting
            if is_heic_supported():
                print(f"\nFound {num_heic} HEIC file{'s' if num_heic != 1 else ''}")
                print("Converting HEIC files...")
                batch_convert_heic(
                    heic_handler.heic_files,
                    output_dir=input_dir,
                    move_originals=True
                )
            else:
                print(f"\nWarning: Found {num_heic} HEIC file{'s' if num_heic != 1 else ''}, but HEIC support not available.")
                print("Install pillow-heif to enable conversion: pip install pillow-heif")
        else:
            # Prompt user
            heic_handler.prompt_and_convert()
    
    # Process images
    print(f"\nProcessing JPG images...")
    thumbnail_size = tuple(parsed_args.thumbnail_size)
    processor = ImageProcessor(thumbnail_size=thumbnail_size)
    
    try:
        processed_images = processor.process_directory(input_dir, parsed_args.recursive)
    except Exception as e:
        print(f"\nError processing images: {e}")
        return 1
    
    stats = processor.get_stats()
    
    print(f"Found {stats['total_found']} JPG file{'s' if stats['total_found'] != 1 else ''}")
    
    # Check if we have any images to process
    if not processed_images:
        print_summary(stats, None, None)
        return 0
    
    # Generate KMZ
    print(f"\nGenerating KMZ file...")
    
    # Determine output path
    # If -o flag wasn't explicitly provided, use input_dir as default location
    if parsed_args.output == 'photos.kmz':  # Check if using default value
        # No explicit -o provided, use input directory as output location
        output_path = get_absolute_path(os.path.join(input_dir, parsed_args.output))
    else:
        # Explicit -o provided, use as specified (could be relative or absolute)
        output_path = get_absolute_path(parsed_args.output)
    
    try:
        kmz_gen = KMZGenerator(output_path, thumbnail_size=thumbnail_size)
        
        # Add all processed images
        for img_data in processed_images:
            kmz_gen.add_photo(
                photo_path=img_data['path'],
                gps_data=img_data['gps'],
                thumbnail_bytes=img_data['thumbnail'],
                name=img_data.get('custom_name', img_data['filename']),
                description_text=img_data.get('description_text'),
                bearing=img_data.get('bearing')
            )
        
        # Save KMZ file
        output_path = kmz_gen.save()
        
    except Exception as e:
        print(f"\nError generating KMZ file: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print summary
    print_summary(stats, kmz_gen, output_path)
    
    return 0


def main():
    """Entry point for command-line execution."""
    sys.exit(run())


if __name__ == '__main__':
    main()
