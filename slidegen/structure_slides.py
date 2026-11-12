"""Structure archetypes: cover, team, agenda_divider, closing, exhibit_annotated."""
from pptx.enum.shapes import MSO_SHAPE
from .core import (MX, W, H, CW, BODY_TOP, text, box, number_badge, section_header, takeaway_bar,
                   title_and_footer, image, set_text, tint)
from .text_slides import alpha

BAR_Y = 6.1


def _backdrop(slide, spec, theme):
    """Full-bleed photo with a dark overlay (archive covers/dividers), or a solid dark brand colour."""
    if spec.get("image"):
        image(slide, spec["image"], 0, 0, W, H, theme)
        alpha(box(slide, 0, 0, W, H, fill="000000"), 55)
    else:
        box(slide, 0, 0, W, H, fill=theme["dark"])


def cover(slide, spec, theme, lang):
    _backdrop(slide, spec, theme)
    box(slide, 0.8, 2.0, 0.12, 2.4, fill=theme["primary"])
    text(slide, 1.15, 1.9, 9.5, 1.7, spec["title"], size=36, bold=True, color="FFFFFF", font=theme["heading_font"], anchor="b")
    if spec.get("subtitle"):
        text(slide, 1.15, 3.7, 9.5, 0.8, spec["subtitle"], size=18, color="E7E6E6", font=theme["body_font"])
    text(slide, 1.15, 5.2, 7, 0.4, spec["team"], size=16, bold=True, color=tint(theme["primary"], .35), font=theme["heading_font"])
    if spec.get("members"):
        text(slide, 1.15, 5.6, 7, 0.4, "  ·  ".join(spec["members"]), size=12, color="FFFFFF", font=theme["body_font"])
    text(slide, W - 5.4, 6.55, 4.6, 0.5, [spec["event"] + (f"  |  {spec['date']}" if spec.get("date") else "")],
         size=12, color="FFFFFF", font=theme["body_font"], align="r", anchor="b")


def closing(slide, spec, theme, lang):
    """Q&A / Obrigado slide mirroring the cover."""
    _backdrop(slide, spec, theme)
    word = spec.get("word") or ("Obrigado!" if lang == "pt" else "Thank you!")
    text(slide, 0, 2.3, W, 1.4, word, size=60, bold=True, color="FFFFFF", font=theme["heading_font"], align="c", anchor="m")
    box(slide, W / 2 - 0.7, 3.85, 1.4, 0.07, fill=theme["primary"])
    if spec.get("subtitle"):
        text(slide, 1, 4.1, W - 2, 0.5, spec["subtitle"], size=18, color="E7E6E6", font=theme["body_font"], align="c")
    if spec.get("contacts"):
        text(slide, 1, 5.4, W - 2, 1.2, spec["contacts"], size=12, color="FFFFFF", font=theme["body_font"], align="c")


def team(slide, spec, theme, lang):
    """Round photos (initials when no photo), name in brand colour, role below; one row up to 5, else 3+rest."""
    title_and_footer(slide, spec, theme, lang)
    m = spec["members"]; n = len(m)
    rows = [m] if n <= 5 else [m[:3], m[3:]]
    d = 1.9 if len(rows) == 1 else 1.35
    block = len(rows) * (d + 1.1) + (len(rows) - 1) * 0.3
    top = BODY_TOP + (6.7 - BODY_TOP - block) / 2
    for r, row in enumerate(rows):
        cw = CW / len(row); y = top + r * (d + 1.4)
        for i, p in enumerate(row):
            cx = MX + i * cw + cw / 2
            if p.get("photo"):
                image(slide, p["photo"], cx - d / 2, y, d, d, theme, oval=True)
            else:
                ini = "".join(w[0] for w in p["name"].split()[:2]).upper()
                set_text(box(slide, cx - d / 2, y, d, d, fill=tint(theme["primary"], .2), shape=MSO_SHAPE.OVAL),
                         ini, theme, size=28 if d > 1.5 else 22, bold=True)
            text(slide, cx - cw / 2 + 0.1, y + d + 0.15, cw - 0.2, 0.35, p["name"], size=15, bold=True,
                 color=theme["text_primary"], font=theme["heading_font"], align="c")
            text(slide, cx - cw / 2 + 0.1, y + d + 0.5, cw - 0.2, 0.5, p["role"], size=11, italic=True,
                 color="595959", font=theme["body_font"], align="c")


def agenda_divider(slide, spec, theme, lang):
    """Dark left panel with the title; numbered sections right, the active one highlighted, others dimmed."""
    lw = 4.6
    if spec.get("image"):
        image(slide, spec["image"], 0, 0, lw, H, theme); alpha(box(slide, 0, 0, lw, H, fill="000000"), 55)
    else:
        box(slide, 0, 0, lw, H, fill=theme["dark"])
    text(slide, 0.7, 2.6, lw - 1.2, 1.2, spec.get("title") or "Agenda", size=40, bold=True, color="FFFFFF",
         font=theme["heading_font"], anchor="m")
    box(slide, 0.7, 3.9, 1.0, 0.07, fill=theme["primary"])
    secs = spec["sections"]; act = spec.get("active"); x = lw + 0.7; w = W - x - 0.6
    step = min(1.3, (H - 1.6) / len(secs)); y0 = (H - step * len(secs)) / 2
    for i, s in enumerate(secs):
        y = y0 + i * step; on = act is None or i == act
        c1 = theme["text_primary"] if on else "BFBFBF"; c2 = "1A1A1A" if on else "A6A6A6"
        text(slide, x, y, 1.0, 0.7, f"{i + 1:02d}", size=32, bold=True, color=c1, font=theme["heading_font"], anchor="m")
        text(slide, x + 1.1, y + 0.02, w - 1.1, 0.42, s["name"], size=20, bold=on, color=c2,
             font=theme["heading_font"], anchor="m")
        if s.get("topics"):
            text(slide, x + 1.1, y + 0.45, w - 1.1, step - 0.5, "  ·  ".join(s["topics"]), size=12,
                 color="7F7F7F" if on else "BFBFBF", font=theme["body_font"])
        if act == i: box(slide, x - 0.25, y + 0.08, 0.08, step - 0.25, fill=theme["primary"])


def exhibit_annotated(slide, spec, theme, lang):
    """Image (screenshot, map, product mock-up, code) left + numbered explanation right. Image = the user's file."""
    title_and_footer(slide, spec, theme, lang)
    b = BAR_Y - 0.15 if spec.get("takeaway") else 6.7
    iw = 7.6
    image(slide, spec.get("image"), MX, BODY_TOP, iw, b - BODY_TOP, theme, label=spec.get("image_label", "imagem"))
    x = MX + iw + 0.4; w = W - MX - x
    section_header(slide, x, w, BODY_TOP - 0.05, spec.get("notes_title") or ("Explicação" if lang == "pt" else "Explanation"), theme)
    notes = spec["notes"]; step = min(1.1, (b - BODY_TOP - 0.6) / len(notes))
    for i, t in enumerate(notes, 1):
        y = BODY_TOP + 0.6 + (i - 1) * step
        number_badge(slide, x, y + 0.02, i, theme)
        text(slide, x + 0.42, y, w - 0.42, step - 0.08, t, size=12, font=theme["body_font"])
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


BUILDERS = {"cover": cover, "closing": closing, "team": team, "agenda_divider": agenda_divider,
            "exhibit_annotated": exhibit_annotated}
