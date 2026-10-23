"""Show Pillow images in Tk without needing the extra python3-pil.imagetk package."""

from __future__ import annotations

import io
import tkinter as tk


def to_photo(img, master=None) -> tk.PhotoImage:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PPM")
    return tk.PhotoImage(data=buf.getvalue(), format="PPM", master=master)
