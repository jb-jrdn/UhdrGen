import os
from dataclasses import dataclass
import subprocess
import numpy as np
import cv2


ULTRAHDR_APP = r"ultrahdr_app"


@dataclass
class UhdrMetadata:
    min_content_boost: float
    max_content_boost: float
    gamma: float = 1.0
    sdr_offset: float = 1/64
    hdr_offset: float = 1/64
    min_hdr_capacity: float = 1.0
    max_hdr_capacity: float = 10000/203
    use_base_color_space: int = 1

    def is_valid(self) -> bool:
        return (
            self.max_hdr_capacity >= self.min_hdr_capacity > 1 and
            self.max_content_boost >= self.min_content_boost > 0 and
            self.use_base_color_space in [0,1]
        )


def create_uhdr_metadata(
    metadata_path: str,
    metadata: UhdrMetadata,
) -> None:
    """
    Generate a metadata configuration file for ultrahdr gain maps.

    Args:
        metedata_path: Destination path for the metadata file (typically "metadata.cfg").
        metadata: UhdrMetadata dataClass
    """
    used_max_hdr_capacity = min(metadata.max_hdr_capacity, metadata.max_content_boost)

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

    with open(metadata_path, 'w', encoding='utf-8') as file:
        file.write(content)


def get_uhdr_gainmap(
    sdr_np_image_linear: np.ndarray,
    hdr_np_image_linear: np.ndarray,
    metadata: UhdrMetadata,
    min_gain: float = 1.0,
    max_gain: float = 10000/203,
) -> tuple[np.ndarray, float, float]:
    """
    Get uhdr gainmap from linear SDR and HDR.
    Update min_content_boost and max_content_boost with gainmap data.

    Args:
        sdr_np_image_linear: Linear SDR image 0-1].
        hdr_np_image_linear: Linear HDR image -> 1 is the sdr white level.
        metadata: metedata used to compute the gainmap.
        min_gain: Minimum gain value to clamp the gainmap.
        max_gain: Maximum gain value to clamp the gainmap.

    Returns:
        tuple[np.ndarray, float, float]: gainmap, min_content_boost, max_content_boost
    """
    gain = (hdr_np_image_linear + metadata.hdr_offset) / (sdr_np_image_linear + metadata.sdr_offset)

    min_content_boost = np.clip(np.min(gain), min_gain, max_gain)
    max_content_boost = np.clip(np.max(gain), min_gain, max_gain)

    min_map_log2 = np.log2(min_content_boost)
    max_map_log2 = np.log2(max_content_boost)

    print(f"min: {min_content_boost:.2f}x -> {min_map_log2:.2f} ev")
    print(f"max: {max_content_boost:.2f}x -> {max_map_log2:.2f} ev")

    log_recovery = (np.log2(gain) - min_map_log2) / (max_map_log2 - min_map_log2)
    clamped_recovery = np.clip(log_recovery, 0.0, 1.0)
    recovery = np.power(clamped_recovery, metadata.gamma)
    gainmap = np.round(recovery * 255 + 0.5).astype(np.uint8)
    return gainmap, min_content_boost, max_content_boost


def write_gainmap(
    gainmap: np.ndarray,
    gainmap_path: str,
    quality: int = 95,
) -> None:
    cv2.imwrite(
        gainmap_path,
        cv2.cvtColor(gainmap, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, quality],
    )


def create_uhdr_image_from_sdr_and_gainmap(
    sdr_path: str,
    gainmap_path: str,
    metadata_path: str,
    output_uhdr_path: str | None = None,
    base_image_quality: int = 95,
    gainmap_image_quality:int = 95,
) -> str:
    """
    Generates a UHDR image from an SDR image, gainmap, and metadata.

    Args:
        sdr_path: Path to the input SDR image.
        gainmap_path: Path to the gainmap image.
        metadata_path: Path to the metadata file.
        uhdr_path: Output path for the generated UHDR image. If None, a default path is constructed.
        base_image_quality: Quality of the base image (0-100). Defaults to 100.
        gainmap_image_quality: Quality of the gainmap image (0-100). Defaults to 100.

    Returns:
        str: Path to the generated UHDR image.
    """

    # checks
    if not os.path.exists(sdr_path):
        raise FileNotFoundError(f"SDR image not found: {sdr_path}")
    if not os.path.exists(gainmap_path):
        raise FileNotFoundError(f"Gain map not found: {gainmap_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    if not 0 <= base_image_quality <= 100:
        raise ValueError(f"base_image_quality must be in [0-100]. {base_image_quality} given.")
    if not 0 <= gainmap_image_quality <= 100:
        raise ValueError(f"base_image_quality must be in [0-100]. {gainmap_image_quality} given.")

    uhdr_path = output_uhdr_path or f"{os.path.splitext(sdr_path)[0]}_uhdr.jpg"
    command = [
        ULTRAHDR_APP,
        "-m", "0",
        "-i", sdr_path,
        "-g", gainmap_path,
        "-f", metadata_path,
        "-z", uhdr_path,
        "-q", str(base_image_quality),
        "-Q", str(gainmap_image_quality),
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Process completed successfully: {uhdr_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error while running the command: {e}")
        print(f"Return code: {e.returncode}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return uhdr_path

