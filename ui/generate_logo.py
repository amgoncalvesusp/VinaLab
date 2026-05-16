"""Generate the VinaLab caffeine molecule logo."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

CAFFEINE_ATOMS = {
    "N1": (-1.2, 0.7),
    "C2": (-0.5, 1.5),
    "N3": (0.7, 1.5),
    "C4": (1.3, 0.6),
    "C5": (0.6, -0.3),
    "C6": (-0.7, -0.3),
    "N7": (1.4, -0.9),
    "C8": (0.7, -1.8),
    "N9": (-0.5, -1.8),
    "O10": (-1.3, -1.1),
    "O11": (2.5, 0.6),
    "Me1": (-2.5, 0.7),
    "Me3": (1.2, 2.7),
    "Me7": (2.7, -0.9),
}
CAFFEINE_BONDS = [
    ("N1", "C2"),
    ("C2", "N3"),
    ("N3", "C4"),
    ("C4", "C5"),
    ("C5", "C6"),
    ("C6", "N1"),
    ("C4", "N9"),
    ("N9", "C8"),
    ("C8", "N7"),
    ("N7", "C5"),
    ("C6", "O10"),
    ("C4", "O11"),
    ("N1", "Me1"),
    ("N3", "Me3"),
    ("N7", "Me7"),
]
ATOM_COLORS = {"N": "#4A90D9", "C": "#2C2C2C", "O": "#E74C3C", "Me": "#27AE60"}
VDW_RADII = {"N": 0.75, "C": 0.77, "O": 0.73, "Me": 0.8}


def generate_coffee_logo() -> None:
    """Generate icon.png and icon.ico with a stylized caffeine molecule."""
    output_dir = Path(__file__).resolve().parent
    png_path = output_dir / "icon.png"
    ico_path = output_dir / "icon.ico"

    fig, ax = plt.subplots(figsize=(2.56, 2.56), dpi=100)
    gradient = np.linspace(0, 1, 256)
    bg = np.vstack([gradient] * 256)
    ax.imshow(bg, extent=(-4, 4, -4, 4), cmap="twilight_shifted", alpha=0.55)
    ax.set_facecolor("#1a1a2e")

    for atom_a, atom_b in CAFFEINE_BONDS:
        x1, y1 = CAFFEINE_ATOMS[atom_a]
        x2, y2 = CAFFEINE_ATOMS[atom_b]
        ax.plot([x1, x2], [y1, y2], color="#111827", linewidth=5, alpha=0.85, solid_capstyle="round")
        ax.plot([x1, x2], [y1, y2], color="#a8b3cf", linewidth=2, alpha=0.75, solid_capstyle="round")

    for index, (name, (x_pos, y_pos)) in enumerate(CAFFEINE_ATOMS.items()):
        element = "Me" if name.startswith("Me") else name[0]
        radius = VDW_RADII[element] * (0.19 + index * 0.003)
        ax.add_patch(plt.Circle((x_pos + 0.08, y_pos - 0.08), radius * 1.15, color="black", alpha=0.22))
        ax.add_patch(plt.Circle((x_pos, y_pos), radius, color=ATOM_COLORS[element], ec="white", lw=0.8))

    ax.text(0, -3.15, "V i n a G U I", color="white", ha="center", va="center", fontsize=14, fontweight="bold")
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.7, 3.4)
    ax.axis("off")
    fig.savefig(png_path, transparent=False, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    image = Image.open(png_path).convert("RGBA")
    image.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    generate_coffee_logo()
