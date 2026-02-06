"""Command-line interface for images2kmz."""

import argparse
import os
import sys
from datetime import datetime
from typing import Optional, Dict

from rich.console import Console

from .core import KMZGenerator
from .image_processor import ImageProcessor
from .heic_handler import HEICHandler, is_heic_supported, batch_convert_heic
from .utils import get_absolute_path
from .progress import ProgressBar, create_progress_callback


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


def print_summary(
    processor_stats: Dict,
    kmz_generator: Optional[KMZGenerator],
    output_path: Optional[str],
    console: Optional[Console] = None,
):
    """
    Print processing summary with colored output.
    
    Args:
        processor_stats: Statistics from ImageProcessor
        kmz_generator: KMZGenerator instance
        output_path: Path to output KMZ file
        console: Optional Console instance for rich output
    """
    if console is None:
        console = Console()
    
    separator = "=" * 60
    console.print(f"\n[bold magenta]{separator}[/bold magenta]")
    console.print("[bold magenta]Summary:[/bold magenta]")
    console.print(f"[bold magenta]{separator}[/bold magenta]")
    
    # Processing stats
    processed = processor_stats['processed']
    skipped = processor_stats['skipped_no_gps']
    errors = processor_stats['errors']
    
    if processed > 0:
        console.print(f"[green]✓ Processed: {processed} photo{'s' if processed != 1 else ''} with GPS data[/green]")
    
    if skipped > 0:
        console.print(f"[yellow]⊗ Skipped: {skipped} photo{'s' if skipped != 1 else ''} (no GPS data)[/yellow]")
    
    if errors > 0:
        console.print(f"[red]✗ Errors: {errors} photo{'s' if errors != 1 else ''} (processing failed)[/red]")
    
    # Output file info
    if processed > 0 and kmz_generator and output_path:
        file_size = kmz_generator.get_formatted_file_size()
        if file_size:
            console.print(f"[green]📦 Output: {os.path.basename(output_path)} ({file_size})[/green]")
        else:
            console.print(f"[green]📦 Output: {os.path.basename(output_path)}[/green]")
        console.print(f"   [dim]Path: {output_path}[/dim]")
    else:
        console.print("\n[bold yellow]⚠ No photos with GPS data found. KMZ file not created.[/bold yellow]")
    
    console.print(f"[bold magenta]{separator}[/bold magenta]\n")


def run(args: Optional[list] = None) -> int:
    """
    Run the CLI application.
    
    Args:
        args: Command-line arguments (None to use sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Initialize console for colored output
    console = Console()
    
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
            console.print(f"\n[bold red]Error: Input directory does not exist: {input_dir}[/bold red]")
            return 1
    
    console.print(f"\n[cyan]Input directory: {input_dir}[/cyan]")
    console.print(f"[cyan]Recursive search: {'Yes' if parsed_args.recursive else 'No'}[/cyan]")
    console.print(f"[cyan]Thumbnail size: {parsed_args.thumbnail_size[0]}x{parsed_args.thumbnail_size[1]}[/cyan]")
    
    # Handle HEIC files
    console.print("\n[bold cyan]🔍 Scanning for images...[/bold cyan]")
    heic_handler = HEICHandler(input_dir, parsed_args.recursive)
    num_heic = heic_handler.scan()
    
    if num_heic > 0:
        if parsed_args.convert_heic:
            # Auto-convert without prompting
            if is_heic_supported():
                console.print(f"\n[yellow]Found {num_heic} HEIC file{'s' if num_heic != 1 else ''}[/yellow]")
                console.print("[dim yellow]Converting HEIC files...[/dim yellow]")
                batch_convert_heic(
                    heic_handler.heic_files,
                    output_dir=input_dir,
                    move_originals=True
                )
            else:
                console.print(f"\n[yellow]Warning: Found {num_heic} HEIC file{'s' if num_heic != 1 else ''}, but HEIC support not available.[/yellow]")
                console.print("[yellow]Install pillow-heif to enable conversion: pip install pillow-heif[/yellow]")
        else:
            # Prompt user
            heic_handler.prompt_and_convert()
    
    # Phase 2: Process images with progress bar
    thumbnail_size = tuple(parsed_args.thumbnail_size)
    processor = ImageProcessor(thumbnail_size=thumbnail_size)
    
    from .image_processor import get_image_files
    
    image_files = get_image_files(input_dir, parsed_args.recursive)
    num_images = len(image_files)
    console.print(f"[cyan]Found {num_images} JPG file{'s' if num_images != 1 else ''}[/cyan]\n")
    
    console.print("[bold cyan]⚙️  Processing images...[/bold cyan]")
    
    try:
        stats = processor.get_stats()
        
        if num_images > 0:
            progress_bar = ProgressBar("Processing")
            progress_bar.start(num_images)
            try:
                processed_images = processor.process_directory(
                    input_dir,
                    parsed_args.recursive,
                    progress_callback=create_progress_callback(progress_bar),
                )
            finally:
                progress_bar.finish()
        else:
            processed_images = []
        
        stats = processor.get_stats()
        
    except Exception as e:
        console.print(f"\n[bold red]Error processing images: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1
    
    # Show processing results
    if stats['processed'] > 0:
        console.print(f"   [green]Processed: {stats['processed']} files[/green]")
    if stats['skipped_no_gps'] > 0:
        console.print(f"   [yellow]Skipped: {stats['skipped_no_gps']} (no GPS data)[/yellow]")
    
    # Completion timestamp
    complete_time = datetime.now().strftime("%I:%M:%S %p")
    console.print(f"\n[dim cyan]✓ Processing complete at {complete_time}[/dim cyan]")
    
    # Check if we have any images to process
    if not processed_images:
        print_summary(stats, None, None, console)
        return 0
    
    # Phase 3: Generate KMZ with progress bar
    console.print(f"\n[bold cyan]📦 Generating KMZ file...[/bold cyan]")
    
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
        
        kmz_progress = ProgressBar("Adding photos")
        kmz_progress.start(len(processed_images))
        
        # Add all processed images
        for index, img_data in enumerate(processed_images, 1):
            kmz_gen.add_photo(
                photo_path=img_data['path'],
                gps_data=img_data['gps'],
                thumbnail_bytes=img_data['thumbnail'],
                name=img_data.get('custom_name', img_data['filename']),
                description_text=img_data.get('description_text'),
                bearing=img_data.get('bearing'),
            )
            
            filename = os.path.basename(img_data['path'])
            kmz_progress.update(index, len(processed_images), filename)
        
        kmz_progress.finish()
        
        # Save KMZ file
        output_path = kmz_gen.save()
        
    except Exception as e:
        console.print(f"\n[bold red]Error generating KMZ file: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print summary with colored output
    print_summary(stats, kmz_gen, output_path, console)
    
    return 0


def main():
    """Entry point for command-line execution."""
    sys.exit(run())


if __name__ == '__main__':
    main()
