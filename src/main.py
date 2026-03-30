from gen import sdr_hdr_to_uhdr

SUPPORTED_MODES = ["sdr_hdr_uhdr"]

def main():
    """
    Entry point of the script. Parses the command-line arguments and starts the processing.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert SDR + HDR images to Ultra HDR (gainmap JPEG)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
    Single image:
        main.py --sdr img_sdr.jpg --hdr img_hdr.avif
        main.py --mode sdr_hdr_uhdr --sdr img_sdr.jpg --hdr img_hdr.avif -o myUhdr.jpg

    Batch on folder: process all SDR & HDR pair in the folder (ex: img_sdr.jpg & img_hdr.avif)
        main.py --mode sdr_hdr_uhdr --dir '/Users/my/Desktop/export'

"""
    )
    parser.add_argument(
        "-m", "--mode",
        default="sdr_hdr_uhdr",
        choices=SUPPORTED_MODES,
        help="Processing mode",
    )
    parser.add_argument("--sdr", help="Path to SDR image (.jpg)")
    parser.add_argument("--hdr", help="Path to HDR image (.avif)")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("-d", "--dir",help="Directory containing SDR/HDR image pairs")
    parser.add_argument(
        "-k", "--keep-temp-files",
        action="store_true",
        help="Keep gainmap and metadata files",
    )

    args = parser.parse_args()

    if args.sdr and args.hdr:
        process_single_image(args)
    elif args.dir:
        process_folder(args)

def process_single_image(args):
    """Processes a pair of SDR/HDR images."""
    try:
        if args.mode == "sdr_hdr_uhdr":
            process = sdr_hdr_to_uhdr.SdrHdrToUhdr(
                sdr_path=args.sdr,
                hdr_path=args.hdr,
                uhdr_path=args.output,
                keep_temp_files=args.keep_temp_files,
            )
        else:
            return
        process.validate()
        process.run()
    except Exception as e:
        print(f"Error during processing : {e}")

def process_folder(args):
    """Processes a folder containing SDR/HDR pairs."""
    try:
        if args.mode == "sdr_hdr_uhdr":
            sdr_hdr_to_uhdr.process_folder(
                input_directory=args.dir,
                keep_temp_files=args.keep_temp_files,
            )
        else:
            return
    except Exception as e:
        print(f"Error processing image folder : {e}")

if __name__ == "__main__":
    main()
