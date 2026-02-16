from __future__ import annotations

"""Command-line interface for images2kmz."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

from .core import KMZGenerator
from .image_processor import ImageProcessor
from .heic_handler import HEICHandler, batch_convert_heic
from .utils import get_absolute_path
from .progress import ProgressBar, create_progress_callback
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


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
        version='%(prog)s 0.2.0'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose console output'
    )
    
    parser.add_argument(
        '-l', '--log-file',
        type=str,
        default='',
        help='Path to log file for detailed logging (default: input directory as images2kmz_log_YYYY-MM-DDTHHMM.log)'
    )
    
    # CSV Export options
    parser.add_argument(
        '--csv',
        type=str,
        default='',
        help='Output CSV file path for survey data (optional; enables CSV export with UTM coordinates)'
    )

    parser.add_argument(
        '--coordinate-system',
        type=str,
        default='EPSG:4269',
        help='Coordinate system for UTM conversion (default: EPSG:4269 for NAD83)'
    )
    
    return parser


def print_header(console: Console | None = None) -> None:
    """Print application header."""
    if console is None:
        console = Console()
    separator = "=" * 60
    console.print(f"\n[bold magenta]{separator}[/bold magenta]")
    console.print("[bold cyan]images2kmz - Geotagged Photo KMZ Generator[/bold cyan]")
    console.print(f"[bold magenta]{separator}[/bold magenta]\n")


def prompt_for_directory(console: Console | None = None) -> str:
    """
    Prompt user to input a directory path for image scanning.
    Supports relative paths, absolute paths, and Windows-style paths.
    Creates directory if it doesn't exist and user confirms.
    
    Returns:
        Absolute path to the validated/created directory
    """
    if console is None:
        console = Console()
    
    while True:
        user_input = input('Please provide a directory containing images to process: ').strip()
        
        if not user_input:
            console.print('[bold red]Error: Path cannot be empty. Please try again.[/bold red]')
            continue
        
        # Handle various path formats (relative, absolute, Windows-style)
        abs_path = get_absolute_path(user_input)
        
        if not Path(abs_path).is_dir():
            # Directory doesn't exist - ask user if they want to create it
            response = input(f'Directory does not exist: {abs_path}. Create it? (y/n): ').strip().lower()
            
            if response in ('y', 'yes'):
                try:
                    Path(abs_path).mkdir(parents=True, exist_ok=True)
                    console.print(f'[green]Created directory: {abs_path}[/green]')
                    return abs_path
                except Exception as e:
                    console.print(f'[bold red]Error creating directory: {e}[/bold red]')
                    console.print('[yellow]Please try again.[/yellow]')
                    continue
            else:
                console.print('[yellow]Exiting gracefully.[/yellow]')
                sys.exit(0)
        else:
            return abs_path


def print_summary(
    processor_stats: dict,
    kmz_generator: KMZGenerator | None,
    output_path: str | None,
    console: Console | None = None,
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
            console.print(f"[green]📦 Output: {Path(output_path).name} ({file_size})[/green]")
        else:
            console.print(f"[green]📦 Output: {Path(output_path).name}[/green]")
        console.print(f"   [dim]Path: {output_path}[/dim]")
    else:
        console.print("\n[bold yellow]⚠ No photos with GPS data found. KMZ file not created.[/bold yellow]")
    
    console.print(f"[bold magenta]{separator}[/bold magenta]\n")


def run(args: list | None = None) -> int:
    """
    Run the CLI application.
    
    Args:
        args: Command-line arguments (None to use sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Initialize console for colored output
    console = Console()
    kmz_gen = None
    
    try:
        # Parse arguments
        parser = create_parser()
        parsed_args = parser.parse_args(args)
        
        # Handle optional input directory - prompt if not provided
        # (Must be done before logging setup to determine default log file location)
        if parsed_args.input_dir is None:
            input_dir = prompt_for_directory(console)
        else:
            input_dir = get_absolute_path(parsed_args.input_dir)
            if not Path(input_dir).is_dir():
                console.print(f"\n[bold red]Error: Input directory does not exist: {input_dir}[/bold red]")
                return 1
        
        # Setup logging based on command-line arguments
        # Default log file: input directory with timestamp format images2kmz_log_YYYY-MM-DDTHHMM.log
        if parsed_args.log_file:
            log_file_path = Path(parsed_args.log_file)
            # Resolve relative paths relative to input directory
            if not log_file_path.is_absolute():
                log_file_path = Path(input_dir) / log_file_path
        elif parsed_args.verbose:  # Only create default log file in verbose mode
            timestamp = datetime.now().strftime("%Y-%m-%dT%H%M")
            log_file_path = Path(input_dir) / f"images2kmz_log_{timestamp}.log"
        else:
            log_file_path = None
        
        setup_logging(verbose=parsed_args.verbose, log_file=log_file_path)
        
        logger.info("=== images2kmz started ===")
        logger.info(f"Command-line arguments: {args}")
        
        # Print header
        print_header(console)
        
        logger.info(f"Input directory: {input_dir}")
        logger.info(f"Recursive search: {parsed_args.recursive}")
        logger.info(f"Thumbnail size: {parsed_args.thumbnail_size}")
        console.print(f"\n[cyan]Input directory: {input_dir}[/cyan]")
        console.print(f"[cyan]Recursive search: {'Yes' if parsed_args.recursive else 'No'}[/cyan]")
        console.print(f"[cyan]Thumbnail size: {parsed_args.thumbnail_size[0]}x{parsed_args.thumbnail_size[1]}[/cyan]")
        
        # Handle HEIC files
        console.print("\n[bold cyan]🔍 Scanning for images...[/bold cyan]")
        heic_handler = HEICHandler(input_dir, parsed_args.recursive)
        num_heic = heic_handler.scan()
        logger.info(f"Found {num_heic} HEIC files")
        
        if num_heic > 0:
            if parsed_args.convert_heic:
                # Auto-convert without prompting
                logger.info(f"Auto-converting {num_heic} HEIC files")
                console.print(f"\n[yellow]Found {num_heic} HEIC file{'s' if num_heic != 1 else ''}[/yellow]")
                console.print("[dim yellow]Converting HEIC files...[/dim yellow]")
                batch_convert_heic(
                    heic_handler.heic_files,
                    output_dir=input_dir,
                    move_originals=True
                )
            else:
                # Prompt user
                logger.info("Prompting user for HEIC conversion")
                heic_handler.prompt_and_convert()
        
        # Phase 2: Process images with progress bar
        thumbnail_size = tuple(parsed_args.thumbnail_size)
        processor = ImageProcessor(thumbnail_size=thumbnail_size)
        
        from .image_processor import get_image_files
        
        image_files = get_image_files(input_dir, parsed_args.recursive)
        num_images = len(image_files)
        logger.info(f"Found {num_images} image files to process")
        console.print(f"[cyan]Found {num_images} JPG file{'s' if num_images != 1 else ''}[/cyan]\n")
        
        console.print("[bold cyan]⚙️  Processing images...[/bold cyan]")
        logger.info("Starting image processing...")
        
        try:
            stats = processor.get_stats()
            
            if num_images > 0:
                progress_bar = ProgressBar("Processing", console=console)
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
            logger.error(f"Error processing images: {e}", exc_info=True)
            console.print(f"\n[bold red]Error processing images: {e}[/bold red]")
            import traceback
            traceback.print_exc()
            return 1
        
        # Show processing results
        logger.info(f"Processing complete - Processed: {stats['processed']}, Skipped: {stats['skipped_no_gps']}, Errors: {stats['errors']}")
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
        logger.info(f"Starting KMZ generation with {len(processed_images)} images")
        
        # Determine output path
        # If -o flag wasn't explicitly provided, use input_dir as default location
        if parsed_args.output == 'photos.kmz':  # Check if using default value
            # No explicit -o provided, use input directory as output location
            output_path = get_absolute_path(Path(input_dir) / parsed_args.output)
        else:
            # Explicit -o provided, use as specified (could be relative or absolute)
            output_path = get_absolute_path(parsed_args.output)
        
        logger.info(f"Output path: {output_path}")
        
        try:
            with KMZGenerator(output_path, thumbnail_size=thumbnail_size) as kmz_gen:
                kmz_progress = ProgressBar("Adding photos", console=console)
                kmz_progress.start(len(processed_images))
                try:
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
                        
                        filename = Path(img_data['path']).name
                        kmz_progress.update(index, len(processed_images), filename)
                finally:
                    kmz_progress.finish()
                
                # Save KMZ file
                logger.info("Saving KMZ file...")
                output_path = kmz_gen.save()
                logger.info(f"KMZ file saved: {output_path}")
                
                # Print summary with colored output
                print_summary(stats, kmz_gen, output_path, console)
            
        except Exception as e:
            logger.error(f"Error generating KMZ file: {e}", exc_info=True)
            console.print(f"\n[bold red]Error generating KMZ file: {e}[/bold red]")
            import traceback
            traceback.print_exc()
            return 1
        
        logger.info("=== images2kmz completed successfully ===")
        return 0
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        console.print("\n[bold yellow]Operation cancelled by user.[/bold yellow]")
        return 130
        
        logger.info("=== images2kmz completed successfully ===")
        return 0
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        console.print("\n[bold yellow]Operation cancelled by user.[/bold yellow]")
        return 130


def main():
    """Entry point for command-line execution."""
    sys.exit(run())


if __name__ == '__main__':
    main()
