import os
from dataclasses import dataclass
import subprocess
import numpy as np
import cv2


ULTRAHDR_APP = r"ultrahdr_app"


@dataclass
class UhdrMetadata:
    min_content_boost: float | None = None
    max_content_boost: float | None = None
    gamma: float = 1.0
    sdr_offset: float = 1/64
    hdr_offset: float = 1/64
    min_hdr_capacity: float = 1.0
    max_hdr_capacity: float = 10000/203
    use_base_color_space: int = 1

    def is_valid(self) -> bool:
        return (
            self.min_content_boost is not None and
            self.max_content_boost is not None and
            self.max_hdr_capacity >= 1 and 
            self.min_hdr_capacity >= 1 and
            self.max_content_boost >= self.min_content_boost and
            self.sdr_offset > 0 and
            self.hdr_offset > 0 and
            self.use_base_color_space in [0,1]
        )


def create_uhdr_metadata(
    metadata_path: str,
    metadata: UhdrMetadata,
) -> None:
    """
    Generate a metadata configuration file for Ultra HDR gain maps.

    Args:
        metadata_path: Destination path for the metadata file (e.g., "metadata.cfg").
        metadata: UhdrMetadata dataclass containing metadata parameters.

    Raises:
        ValueError: If metadata is not valid.
        IOError: If the file cannot be written.
    """
    if not metadata.is_valid():
        raise ValueError("Metadata is not valid.")

    used_max_hdr_capacity = max(min(metadata.max_hdr_capacity, metadata.max_content_boost), 1.1)

    content_lines = [
        f"--minContentBoost {metadata.min_content_boost:.3f}",
        f"--maxContentBoost {metadata.max_content_boost:.3f}",
        f"--gamma {metadata.gamma:.3f}",
        f"--offsetSdr {metadata.sdr_offset:.6f}",
        f"--offsetHdr {metadata.hdr_offset:.6f}",
        f"--hdrCapacityMin {metadata.min_hdr_capacity:.3f}",
        f"--hdrCapacityMax {used_max_hdr_capacity:.3f}",
        f"--useBaseColorSpace {metadata.use_base_color_space}",
    ]
    content = "\n".join(content_lines)

    try:
        with open(metadata_path, 'w', encoding='utf-8') as file:
            file.write(content)
    except IOError as e:
        raise IOError(f"Failed to write metadata file: {e}")


def get_uhdr_gainmap(
    sdr_np_image_linear: np.ndarray,
    hdr_np_image_linear: np.ndarray,
    metadata: UhdrMetadata,
    min_gain: float = 0.8,
    max_gain: float = 10000/203,
) -> tuple[np.ndarray, float, float]:
    """
    Get Ultra HDR gainmap from linear SDR and HDR images.

    Args:
        sdr_np_image_linear: Linear SDR image [0-1].
        hdr_np_image_linear: Linear HDR image (1 is the SDR white level).
        metadata: Metadata used to compute the gainmap.
        min_gain: Minimum gain value.
        max_gain: Maximum gain value.

    Returns:
        tuple[np.ndarray, float, float]: gainmap, min_content_boost, max_content_boost

    Raises:
        ValueError: If input images have different shapes.
    """
    if sdr_np_image_linear.shape != hdr_np_image_linear.shape:
        raise ValueError("SDR and HDR images must have the same shape.")

    gain = (hdr_np_image_linear + metadata.hdr_offset) / (sdr_np_image_linear + metadata.sdr_offset)

    gain = get_gain_optimized_for_luminance(gain)

    min_content_boost = np.clip(np.min(gain), min_gain, max_gain)
    max_content_boost = np.clip(np.max(gain), min_gain, max_gain)

    min_map_log2 = np.log2(min_content_boost)
    max_map_log2 = np.log2(max_content_boost)

    print(f"min gain: {min_content_boost:.2f}x -> {min_map_log2:.2f} ev")
    print(f"max gain: {max_content_boost:.2f}x -> {max_map_log2:.2f} ev")

    log_recovery = (np.log2(gain) - min_map_log2) / (max_map_log2 - min_map_log2)
    clamped_recovery = np.clip(log_recovery, 0.0, 1.0)
    recovery = np.power(clamped_recovery, metadata.gamma)
    gainmap = np.round(recovery * 255).astype(np.uint8)
    return gainmap, min_content_boost, max_content_boost


def get_gain_optimized_for_luminance(
    gain: np.ndarray,
) -> np.ndarray:
    """
    Reduce higher gain value to avoid headroom compression when gain map is applied, based on max value.
    Produce slighlty lower high values (difficult to see), but better global luminance of HDR image.
    """
    max_rgb = np.max(gain, axis=-1)

    p_low = np.percentile(max_rgb, 99.8)
    p_high = np.percentile(max_rgb, 99.95)
    gmax = max_rgb.max()

    print(f"optim param -> max: {gmax:.2f} | p_low: {p_low:.2f} | p_high: {p_high:.2f}")

    eps = 1e-8
    scale = (p_high - p_low) / (gmax - p_low + eps)

    mapped = max_rgb.copy()
    mask = mapped > p_low
    mapped[mask] = p_low + (mapped[mask] - p_low) * scale

    ratio = mapped / (max_rgb + eps)

    optimized_gain = gain * ratio[..., None]
    return optimized_gain


def write_gainmap(
    gainmap: np.ndarray,
    gainmap_path: str,
    quality: int = 90,
    size_factor: int = 1,
) -> None:
    """
    Write a gainmap image to disk in JPEG format.

    Args:
        gainmap: Gainmap image as a numpy array (uint8, RGB format).
        gainmap_path: Destination path for the gainmap image.
        quality: JPEG quality (0-100). Best 100, worst 0, default 90.
        size_factor: gainmap size. Best 1, worst 128, default 1.

    Raises:
        IOError: If writing the file fails.
    """
    try:
        if size_factor != 1:
            height, width = gainmap.shape[:2]
            gainmap = cv2.resize(gainmap, (width // size_factor, height // size_factor))
        success = cv2.imwrite(
            gainmap_path,
            cv2.cvtColor(gainmap, cv2.COLOR_RGB2BGR),
            [cv2.IMWRITE_JPEG_QUALITY, quality],
        )
        if not success:
            raise IOError(f"Failed to write gainmap to {gainmap_path}.")
    except Exception as e:
        raise IOError(f"Error writing gainmap: {e}")


def create_uhdr_image_from_sdr_and_gainmap(
    sdr_path: str,
    gainmap_path: str,
    metadata_path: str,
    output_uhdr_path: str | None = None,
) -> str:
    """
    Generates a UHDR image from an SDR image, gainmap, and metadata.

    Args:
        sdr_path: Path to the input SDR image.
        gainmap_path: Path to the gainmap image.
        metadata_path: Path to the metadata file.
        output_uhdr_path: Output path for the generated UHDR image. If None, a default path is constructed.

    Returns:
        str: Path to the generated UHDR image.

    Raises:
        FileNotFoundError: If input files are not found.
        ValueError: If quality values are invalid.
        RuntimeError: If the subprocess command fails.
    """

    # checks
    if not os.path.exists(sdr_path):
        raise FileNotFoundError(f"SDR image not found: {sdr_path}")
    if not os.path.exists(gainmap_path):
        raise FileNotFoundError(f"Gain map not found: {gainmap_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    uhdr_path = output_uhdr_path or f"{os.path.splitext(sdr_path)[0]}_uhdr.jpg"
    command = [
        ULTRAHDR_APP,
        "-m", "0",
        "-i", sdr_path,
        "-g", gainmap_path,
        "-f", metadata_path,
        "-z", uhdr_path,
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Process completed successfully: {uhdr_path}")
    except subprocess.CalledProcessError as e:
        print(f"Return code: {e.returncode}")
        raise RuntimeError(f"Command failed: {e}") from e
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

    return uhdr_path
