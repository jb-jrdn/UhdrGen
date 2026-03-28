from gen import sdr_hdr_to_uhdr

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert SDR + HDR images to Ultra HDR (gainmap JPEG)",
            epilog="""
Examples:

  Single image:
    main.py --mode sdr_hdr_uhdr --sdr img_sdr.jpg --hdr img_hdr.avif
    main.py --mode sdr_hdr_uhdr --sdr img_sdr.jpg --hdr img_hdr.avif --output myUhdr.jpg

  Batch on folder: process all SDR & HDR pair in the folder (ex: img_sdr.jpg & img_hdr.avif)
    main.py --mode sdr_hdr_uhdr --input_dir ./images
"""
    )
    parser.add_argument(
        "--mode",
        default="sdr_hdr_uhdr",
        choices=["sdr_hdr_uhdr"],
        help="Processing mode (currently only sdr_hdr_uhdr supported)",
    )
    parser.add_argument(
        "--sdr",
        help="Path to SDR image (.jpg), for single convertion",
    )
    parser.add_argument(
        "--hdr",
        help="Path to HDR image (.avif), for single convertion",
    )
    parser.add_argument(
        "--output",
        help="Output file, for single mode",
    )
    parser.add_argument(
        "--dir",
        help="Directory containing SDR/HDR image pairs (same folder, same name)"
    )

    args = parser.parse_args()

    if args.sdr and args.hdr:

        if args.mode == "sdr_hdr_uhdr":
            process = sdr_hdr_to_uhdr.SdrHdrToUhdr(
                sdr_path=args.sdr,
                hdr_path=args.hdr,
                uhdr_path=args.output,
            )

        process.validate()
        process.run()

    elif args.dir:

        if args.mode == "sdr_hdr_uhdr":
            sdr_hdr_to_uhdr.process_folder(
                input_directory=args.dir,
            )


if __name__ == "__main__":
    main()