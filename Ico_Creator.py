from PIL import Image

def make_ico(input_png, output_ico):
    # Windows‑safe icon sizes
    sizes = [
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256)
    ]

    img = Image.open(input_png)

    # Convert to RGBA to avoid issues
    img = img.convert("RGBA")

    img.save(
        output_ico,
        format="ICO",
        sizes=sizes
    )

    print(f"Created icon: {output_ico}")

if __name__ == "__main__":
    make_ico("F1_logo.png", "F1_logo.ico")