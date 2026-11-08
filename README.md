# exif-clean

Photos from phones and cameras carry more than pixels: camera model, serial
number, timestamps and, when location access was on, the GPS coordinates of
where the picture was taken. Upload that file to a marketplace, a forum or a
support chat and you publish all of it.

`exif-clean` removes the EXIF and XMP metadata blocks from JPEG files while
leaving the compressed image data untouched. No re-encoding, no quality loss, no
dependencies, no network access.

## Usage

```bash
# Writes photo.clean.jpg next to the original
exif-clean photo.jpg

# Check first, write nothing
exif-clean photo.jpg --dry-run

# Several files at once, replace the originals
exif-clean *.jpg --in-place

# A whole camera dump, keeping the originals
exif-clean ~/Pictures/holiday --recursive
```

```text
$ exif-clean holiday.jpg
holiday.jpg: removed EXIF, XMP (3128 bytes) -> holiday.clean.jpg
```

| Option | Meaning |
| --- | --- |
| `--dry-run` | report what would be removed, change nothing |
| `--in-place` | overwrite the original files instead of writing `*.clean.jpg` |
| `--keep-xmp` | remove EXIF, keep XMP (useful for edit history) |
| `--recursive` | treat a folder argument as a folder and clean every `.jpg`/`.jpeg` inside |
| `--version` | print the version and exit |

The default is deliberately non-destructive: the original stays exactly as it
was, and you decide when to replace it.

## What is removed

- the `Exif` APP1 segment (camera model, serial, timestamps, orientation, GPS,
  and the embedded thumbnail);
- the XMP APP1 segment, unless `--keep-xmp` is given.

Everything else stays: JFIF headers, colour profiles, comments and the scan data
after `SOS`, byte for byte. The output is the same picture with less metadata.

## What is not supported

- PNG, HEIC and TIFF files: they store metadata differently, and a half-correct
  cleaner is worse than none.
- Detecting metadata in the pixels themselves (screenshots of documents,
  visible faces, reflections). This is a metadata tool, not an anonymiser for
  content.
- Files where metadata lives in a sidecar (`.xmp` next to the photo). Delete the
  sidecar yourself.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The suite builds JPEGs with and without metadata, checks that EXIF and XMP
segments disappear, that the scan data and JFIF header survive, and that the
error paths (not a JPEG, truncated segment) do not crash the CLI. CI runs it on
Linux.

A manual check with a real encoder also works:

```python
from PIL import Image
image = Image.Exif()
image[0x0110] = "TestModel"
Image.new("RGB", (120, 80)).save("camera.jpg", exif=image)
```

`Image.open("camera.clean.jpg").getexif()` should be empty afterwards.

## Requirements

- Python 3.10 or newer
- No third-party packages for the tool itself

## License

MIT
