import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk
from bidi.algorithm import get_display
from pathlib import Path
import sys, csv, arabic_reshaper, threading

# ── globals ────────────────────────────────────────────────────────────────────
scale          = None
display_width  = display_height = 0
move_this_rect = None
last_x = last_y = 0
rectangles     = []
csv_headers    = []
csv_rows       = []
image_for_generating = None
tk_image_ref   = None
preview_img = None
status_var = None
drag_locked = False

def set_drag_locked(state):
    global drag_locked
    drag_locked = state

# ── grade tiers (highest threshold first) ─────────────────────────────────────
GRADE_TIERS = [
    (80, "ممتاز"),
    (60, "جيد جداً"),
    (40, "جيد"),
    (0,  "مقبول"),
]

# ── resource path ──────────────────────────────────────────────────────────────
def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path

default_font_path = str(get_resource_path("fonts/Amiri-Regular.ttf"))

# ── helpers ────────────────────────────────────────────────────────────────────
def is_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)

def prepare_text(raw, font_path_str, max_width_px, max_font_size):
    if is_arabic(raw):
        reshaped    = arabic_reshaper.reshape(raw)
        display_txt = get_display(reshaped, base_dir='R')
    else:
        display_txt = raw
    font_size = max(1, int(max_font_size))
    font      = ImageFont.load_default()
    while font_size >= 1:
        try:
            f = ImageFont.truetype(font_path_str, font_size)
        except OSError:
            break
        if f.getlength(display_txt) <= max_width_px:
            font = f
            break
        font_size -= 1
    return display_txt, font

def get_grade_label(score_string):
    """Parse 'X / Y' score string, return Arabic grade label or original string on failure."""
    try:
        parts      = score_string.split("/")
        user_score = int(float(parts[0].strip()))
        total      = int(float(parts[1].strip()))
        if total == 0:
            return score_string
        pct = (user_score / total) * 100
        for threshold, label in GRADE_TIERS:
            if pct >= threshold:
                return label
        return score_string
    except Exception:
        return score_string

# ── canvas mouse events ────────────────────────────────────────────────────────
def on_mouse_press(event):
    global move_this_rect, last_x, last_y
    if drag_locked:
        return
    clicked = canvas.find_overlapping(event.x, event.y, event.x, event.y)
    for r in rectangles:
        if r['rect_id'] in clicked:
            move_this_rect = r
            last_x, last_y = event.x, event.y
            break

def on_mouse_drag(event):
    global last_x, last_y
    if move_this_rect is None:
        return
    dx = event.x - last_x
    dy = event.y - last_y
    canvas.move(move_this_rect['rect_id'], dx, dy)
    canvas.move(move_this_rect['text_id'], dx, dy)
    last_x, last_y = event.x, event.y
    coords = canvas.coords(move_this_rect['rect_id'])
    move_this_rect['x_var'].set(str(int(coords[0])))
    move_this_rect['y_var'].set(str(int(coords[1])))

def on_mouse_release(event):
    global move_this_rect
    move_this_rect = None

# ── CSV selection ──────────────────────────────────────────────────────────────
def csv_file_selection():
    global csv_headers, csv_rows, preview_img, tk_image_ref
    path = filedialog.askopenfilename(filetypes=[("CSV file", "*.csv")])
    if not path:
        return
    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader      = csv.DictReader(f)
        csv_headers = list(reader.fieldnames)
        csv_rows    = list(reader)
    csv_label.config(text=f"CSV: {Path(path).name}  ({len(csv_rows)} rows, {len(csv_headers)} columns)")
    progress_var.set(f"0 / {len(csv_rows)}")
    score_chkbutton.config(state=tk.NORMAL)
    gender_chkbutton.config(state=tk.NORMAL)
    if image_for_generating:
        createbutton.config(state=tk.NORMAL)

    # refresh rectangle column dropdowns
    if rectangles:
        for r in rectangles:
            r['frame'].destroy()
            canvas.delete(r['rect_id'])
            canvas.delete(r['text_id'])
        rectangles.clear()
        _refresh_scroll()


    removebutton.config(state=tk.DISABLED)
    previewbutton.config(state=tk.DISABLED)

    if scale is not None and preview_img is not None:
        canvas.delete("all")
        tk_image_ref = ImageTk.PhotoImage(preview_img)
        canvas.create_image(0, 0, anchor="nw", image=tk_image_ref)
        canvas.image_ref = tk_image_ref


    # refresh gender and score column dropdowns
    for var, menu_widget in [(gender_col_var, gender_col_menu),
                             (score_col_var,  score_col_menu)]:
        menu_widget['menu'].delete(0, 'end')
        for h in csv_headers:
            menu_widget['menu'].add_command(label=h, command=tk._setit(var, h))
        if csv_headers:
            var.set(csv_headers[0])

# ── Image selection ────────────────────────────────────────────────────────────
def image_file_selection():
    global image_for_generating, tk_image_ref, scale, display_width, display_height, preview_img
    path = filedialog.askopenfilename(
        title="Select Background Image",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp")]
    )
    if not path:
        return
    for r in rectangles:
        r['frame'].destroy()
    rectangles.clear()
    canvas.delete("all")
    removebutton.config(state=tk.DISABLED)
    previewbutton.config(state=tk.DISABLED)
    preview_label.config(text="")

    orig = Image.open(path)
    image_for_generating = orig.copy()
    display_width  = min(800, orig.width)
    scale          = display_width / orig.width
    display_height = int(orig.height * scale)
    preview_img    = image_for_generating.resize((display_width, display_height))

    canvas.config(width=display_width, height=display_height)
    tk_image_ref = ImageTk.PhotoImage(preview_img)
    canvas.create_image(0, 0, anchor="nw", image=tk_image_ref)
    canvas.image_ref = tk_image_ref

    canvas.bind("<ButtonPress-1>",   on_mouse_press)
    canvas.bind("<B1-Motion>",       on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_release)

    img_label.config(text=f"Image: {Path(path).name}  ({orig.width}×{orig.height})")
    if csv_headers:
        createbutton.config(state=tk.NORMAL)

# ── Rectangle management ───────────────────────────────────────────────────────
RECT_W, RECT_H = 200, 50

def create_rectangle():
    if len(rectangles) >= len(csv_headers):
        messagebox.showinfo("CSV_Image Combiner", "All column headers already have a rectangle.")
        return

    default_col = csv_headers[len(rectangles)]
    rx1, ry1    = 80, 80
    rx2, ry2    = rx1 + RECT_W, ry1 + RECT_H

    rect_id = canvas.create_rectangle(rx1, ry1, rx2, ry2, outline="blue", fill="", width=6)
    text_id = canvas.create_text((rx1+rx2)//2, (ry1+ry2)//2, text=default_col, fill="blue")

    idx   = len(rectangles)
    outer = tk.LabelFrame(settings_inner, text=f"Rect {idx+1}", padx=4, pady=4)
    outer.pack(fill=tk.X, pady=4, padx=2)

    col_var = tk.StringVar(value=default_col)
    tk.Label(outer, text="Column:").grid(row=0, column=0, sticky="w")
    col_menu = tk.OptionMenu(outer, col_var, *csv_headers)
    col_menu.config(width=12)
    col_menu.grid(row=0, column=1, columnspan=2, sticky="ew")

    font_var = tk.StringVar(value=default_font_path)
    tk.Label(outer, text="Font:").grid(row=1, column=0, sticky="w")
    font_lbl = tk.Label(outer, text="Amiri (default)", width=12, anchor="w", relief="sunken")
    font_lbl.grid(row=1, column=1, sticky="ew")
    font_select_btn = tk.Button(outer, text="…", width=2,
              command=lambda fv=font_var, fl=font_lbl: pick_font(fv, fl)
              )
    font_select_btn.grid(row=1, column=2)

    color_var = tk.StringVar(value="#000000")
    tk.Label(outer, text="Color:").grid(row=2, column=0, sticky="w")
    color_preview = tk.Label(outer, bg="#000000", width=4, relief="sunken")
    color_preview.grid(row=2, column=1, sticky="w")
    color_pick_btn = tk.Button(outer, text="Pick",
              command=lambda cv=color_var, cp=color_preview: pick_color(cv, cp)
              )
    color_pick_btn.grid(row=2, column=2)

    tk.Label(outer, text="Font Size:").grid(row=3, column=0, sticky="w")
    maxfont_var = tk.StringVar(value="36")
    font_size_entry = tk.Entry(outer, textvariable=maxfont_var, width=6)
    font_size_entry.grid(row=3, column=1, sticky="w")

    w_var = tk.StringVar(value=str(RECT_W))
    h_var = tk.StringVar(value=str(RECT_H))
    tk.Label(outer, text="Width:").grid(row=4, column=0, sticky="w")
    rect_width_entry = tk.Entry(outer, textvariable=w_var, width=6)
    rect_width_entry.grid(row=4, column=1, sticky="w")
    tk.Label(outer, text="Height:").grid(row=5, column=0, sticky="w")
    rect_height_entry = tk.Entry(outer, textvariable=h_var, width=6)
    rect_height_entry.grid(row=5, column=1, sticky="w")

    x_var = tk.StringVar(value=str(rx1))
    y_var = tk.StringVar(value=str(ry1))

    r = {
        'rect_id':     rect_id,
        'text_id':     text_id,
        'frame':       outer,
        'col_var':     col_var,
        'col_menu':    col_menu,
        'font_var':    font_var,
        'color_var':   color_var,
        'maxfont_var': maxfont_var,
        'w_var':       w_var,
        'h_var':       h_var,
        'x_var':       x_var,
        'y_var':       y_var,
        'col_menu':        col_menu,
        'font_btn':        font_select_btn,
        'color_btn':       color_pick_btn,
        'fontsize_entry':  font_size_entry,
        'width_entry':     rect_width_entry,
        'height_entry':    rect_height_entry,
    }
    rectangles.append(r)

    def apply_geometry(*_, r=r):
        try:
            x1 = int(r['x_var'].get()); y1 = int(r['y_var'].get())
            w  = int(r['w_var'].get());  h  = int(r['h_var'].get())
        except ValueError:
            return
        canvas.coords(r['rect_id'], x1, y1, x1+w, y1+h)
        canvas.coords(r['text_id'], x1 + w//2, y1 + h//2)

    for var in (w_var, h_var, x_var, y_var):
        var.trace_add('write', apply_geometry)

    col_var.trace_add('write',
        lambda *_, r=r: canvas.itemconfig(r['text_id'], text=r['col_var'].get()))

    removebutton.config(state=tk.NORMAL)
    previewbutton.config(state=tk.NORMAL)
    _refresh_scroll()

def remove_rectangle():
    if not rectangles:
        return
    r = rectangles.pop()
    canvas.delete(r['rect_id'])
    canvas.delete(r['text_id'])
    r['frame'].destroy()
    _refresh_scroll()
    if not rectangles:
        removebutton.config(state=tk.DISABLED)
        previewbutton.config(state=tk.DISABLED)

def pick_font(font_var, font_lbl):
    path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf *.otf")])
    if path:
        font_var.set(path)
        font_lbl.config(text=Path(path).stem[:12])

def pick_color(color_var, color_preview):
    result = colorchooser.askcolor(color=color_var.get())
    if result[1]:
        color_var.set(result[1])
        color_preview.config(bg=result[1])

# ── toggle show/hide feature settings ─────────────────────────────────────────
def toggle_gender_settings():
    if gender_toggle_var.get():
        gender_settings_frame.pack(side=tk.LEFT, padx=6, fill=tk.Y)
    else:
        gender_settings_frame.pack_forget()

def toggle_score_settings():
    if score_toggle_var.get():
        score_settings_frame.pack(side=tk.LEFT, padx=6, fill=tk.Y)
    else:
        score_settings_frame.pack_forget()

# ── Preview ────────────────────────────────────────────────────────────────────
def preview():
    global tk_image_ref
    if not csv_rows:
        messagebox.showinfo("CSV_Image Combiner", "No CSV data loaded yet.")
        return
    if not rectangles:
        messagebox.showinfo("CSV_Image Combiner", "No rectangles placed yet.")
        return

    row_data = csv_rows[0]
    preview_label.config(text=f"Previewing row 1 of {len(csv_rows)}")

    fresh = image_for_generating.copy().resize((display_width, display_height))
    draw  = ImageDraw.Draw(fresh)

    for r in rectangles:
        col      = r['col_var'].get()
        raw_text = row_data.get(col, "")

        # score conversion applies in preview too
        if score_toggle_var.get() and col == score_col_var.get():
            raw_text = get_grade_label(raw_text)

        coords = canvas.coords(r['rect_id'])
        if not coords:
            continue
        x1, y1, x2, y2 = coords
        max_w = x2 - x1
        try:
            max_font = int(r['maxfont_var'].get())
        except ValueError:
            max_font = 36
        disp_text, font = prepare_text(raw_text, r['font_var'].get(), max_w, max_font)
        draw.text(((x1+x2)/2, (y1+y2)/2), disp_text,
                  font=font, fill=r['color_var'].get(), anchor="mm")

    tk_image_ref = ImageTk.PhotoImage(fresh)
    canvas.create_image(0, 0, anchor="nw", image=tk_image_ref)
    canvas.image_ref = tk_image_ref
    for r in rectangles:
        canvas.tag_raise(r['rect_id'])
        canvas.tag_raise(r['text_id'])

# ── Generate all images ────────────────────────────────────────────────────────
def generate():
    global drag_locked

    # ── validations first ──────────────────────────────
    if not image_for_generating:
        messagebox.showinfo("CSV_Image Combiner", "No image loaded.")
        return
    if not csv_rows:
        messagebox.showinfo("CSV_Image Combiner", "No CSV data loaded.")
        return
    if not rectangles:
        messagebox.showinfo("CSV_Image Combiner", "No rectangles placed.")
        return

    out_dir = filedialog.askdirectory(title="Select output folder")
    if not out_dir:
        return

    out_path = Path(out_dir)
    existing_files = list(out_path.iterdir())
    if existing_files:
        confirm = messagebox.askyesno(
            "Folder Not Empty",
            f"The selected folder already contains {len(existing_files)} item(s).\n"
            "Files with the same name will be overwritten.\n\n"
            "Continue anyway?"
        )
        if not confirm:
            return

    # ── setup before thread starts ─────────────────────
    prefix = prefix_var.get().strip()
    fmt    = format_var.get()
    ext    = "jpeg" if fmt == "JPG" else fmt.lower()

    progress_var.set(f"0 / {len(csv_rows)}")
    progress_label.config(fg="green")
    status_var.set("Working...")
    status_label.config(fg="green")
    generatebutton.config(state=tk.DISABLED)
    score_chkbutton.config(state=tk.DISABLED)
    gender_chkbutton.config(state=tk.DISABLED)
    createbutton.config(state=tk.DISABLED)
    removebutton.config(state=tk.DISABLED)
    previewbutton.config(state=tk.DISABLED)
    gender_col_menu.config(state=tk.DISABLED)
    male_entry.config(state=tk.DISABLED)
    female_entry.config(state=tk.DISABLED)
    score_col_menu.config(state=tk.DISABLED)
    filename_entry.config(state=tk.DISABLED)
    format_menu.config(state=tk.DISABLED)
    selectimg_button.config(state=tk.DISABLED)
    selectcsv_button.config(state=tk.DISABLED)
    for r in rectangles:
        r['col_menu'].config(state=tk.DISABLED)
        r['font_btn'].config(state=tk.DISABLED)
        r['color_btn'].config(state=tk.DISABLED)
        r['fontsize_entry'].config(state=tk.DISABLED)
        r['width_entry'].config(state=tk.DISABLED)
        r['height_entry'].config(state=tk.DISABLED)
    drag_locked = True

    # ── generation logic runs in background ────────────
    def run_generation():
        incomplete_log = []
        
        for idx, row in enumerate(csv_rows, start=1):
            out_img = image_for_generating.copy()
            draw    = ImageDraw.Draw(out_img)
            row_incomplete = False

            for r in rectangles:
                col      = r['col_var'].get()
                raw_text = row.get(col, "")
                if not raw_text.strip():
                    row_incomplete = True

                if score_toggle_var.get() and col == score_col_var.get():
                    raw_text = get_grade_label(raw_text)

                coords          = canvas.coords(r['rect_id'])
                x1, y1, x2, y2 = [c / scale for c in coords]
                max_w = x2 - x1
                try:
                    max_font = int(r['maxfont_var'].get())
                except ValueError:
                    max_font = 36
                disp_text, font = prepare_text(raw_text, r['font_var'].get(), max_w, max_font)
                draw.text(((x1+x2)/2, (y1+y2)/2), disp_text,
                          font=font, fill=r['color_var'].get(), anchor="mm")

            marker   = "x" if row_incomplete else ""
            filename = f"{prefix}{marker}{idx}.{ext}"
            save_kwargs = {'quality': 95} if fmt == "JPG" else {}

            if gender_toggle_var.get():
                gender_val = row.get(gender_col_var.get(), "").strip()
                if gender_val == male_val_var.get().strip():
                    subfolder = Path(out_dir) / "رجال"
                elif gender_val == female_val_var.get().strip():
                    subfolder = Path(out_dir) / "نساء"
                else:
                    subfolder = Path(out_dir) / "لم يتم التحديد"
                subfolder.mkdir(exist_ok=True)
                save_path = subfolder / filename
            else:
                save_path = Path(out_dir) / filename

            out_img.save(str(save_path), **save_kwargs)

            if row_incomplete:
                incomplete_log.append(f"Row {idx}: missing data in some columns")

            window.after(0, lambda i=idx: progress_var.set(f"{i} / {len(csv_rows)}"))

        # ── cleanup after loop finishes ────────────────
        if incomplete_log:
            log_path = Path(out_dir) / f"{prefix}incomplete_rows.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(incomplete_log))
            window.after(0, lambda: messagebox.showinfo("Done",
                f"Generated {len(csv_rows)} images.\n"
                f"{len(incomplete_log)} had missing data, see incomplete_rows.txt"))
        else:
            window.after(0, lambda: messagebox.showinfo("Done",
                f"All {len(csv_rows)} images generated successfully!"))

        window.after(0, lambda: status_var.set("Idle"))
        status_label.config(fg="red")
        window.after(0, lambda: progress_var.set(f" {len(csv_rows)} / {len(csv_rows)}"))
        progress_label.config(fg="red")
        window.after(0, lambda: generatebutton.config(state=tk.NORMAL))
        window.after(0, lambda: score_chkbutton.config(state=tk.NORMAL))
        window.after(0, lambda: gender_chkbutton.config(state=tk.NORMAL))
        window.after(0, lambda: createbutton.config(state=tk.NORMAL))
        window.after(0, lambda: removebutton.config(state=tk.NORMAL))
        window.after(0, lambda: previewbutton.config(state=tk.NORMAL))
        window.after(0, lambda: gender_col_menu.config(state=tk.NORMAL))
        window.after(0, lambda: male_entry.config(state=tk.NORMAL))
        window.after(0, lambda: female_entry.config(state=tk.NORMAL))
        window.after(0, lambda: score_col_menu.config(state=tk.NORMAL))
        window.after(0, lambda: filename_entry.config(state=tk.NORMAL))
        window.after(0, lambda: format_menu.config(state=tk.NORMAL))
        window.after(0, lambda: selectimg_button.config(state=tk.NORMAL))
        window.after(0, lambda: selectcsv_button.config(state=tk.NORMAL))
        for r in rectangles:
            window.after(0, lambda r=r: r['col_menu'].config(state=tk.NORMAL))
            window.after(0, lambda r=r: r['font_btn'].config(state=tk.NORMAL))
            window.after(0, lambda r=r: r['color_btn'].config(state=tk.NORMAL))
            window.after(0, lambda r=r: r['fontsize_entry'].config(state=tk.NORMAL))
            window.after(0, lambda r=r: r['width_entry'].config(state=tk.NORMAL))
            window.after(0, lambda r=r: r['height_entry'].config(state=tk.NORMAL))
        window.after(0, lambda: set_drag_locked(False))
        

    thread = threading.Thread(target=run_generation, daemon=True)
    thread.start()

def _refresh_scroll(event=None):
    settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))

# ══════════════════════════════════════════════════════════════════════════════
# UI layout
# ══════════════════════════════════════════════════════════════════════════════
window = tk.Tk()
window.title("CSV + Image Combiner")
window.resizable(True, True)
# ── top bar ────────────────────────────────────────────────────────────────────
top_bar = tk.Frame(window)
top_bar.pack(fill=tk.X, padx=6, pady=4)

selectcsv_button = tk.Button(top_bar, text="1 · Select CSV",   command=csv_file_selection)
selectcsv_button.pack(side=tk.LEFT, padx=2)
csv_label = tk.Label(top_bar, text="No CSV loaded", anchor="w")
csv_label.pack(side=tk.LEFT, padx=4)

selectimg_button = tk.Button(top_bar, text="2 · Select Image", command=image_file_selection)
selectimg_button.pack(side=tk.LEFT, padx=2)
img_label = tk.Label(top_bar, text="No image loaded", anchor="w")
img_label.pack(side=tk.LEFT, padx=4)

# ── rectangle controls ─────────────────────────────────────────────────────────
rect_bar = tk.Frame(window)
rect_bar.pack(fill=tk.X, padx=6, pady=2)

createbutton  = tk.Button(rect_bar, text="+ Add Rectangle",    command=create_rectangle, state=tk.DISABLED)
createbutton.pack(side=tk.LEFT, padx=2)
removebutton  = tk.Button(rect_bar, text="− Remove Last",       command=remove_rectangle, state=tk.DISABLED)
removebutton.pack(side=tk.LEFT, padx=2)
previewbutton = tk.Button(rect_bar, text="👁 Preview (row 1)", command=preview,           state=tk.DISABLED)
previewbutton.pack(side=tk.LEFT, padx=2)
preview_label = tk.Label(rect_bar, text="")
preview_label.pack(side=tk.LEFT, padx=8)

# ── special features bar ───────────────────────────────────────────────────────
features_bar = tk.Frame(window, relief=tk.GROOVE, bd=1)
features_bar.pack(fill=tk.X, padx=6, pady=4)

# gender feature
gender_toggle_var = tk.BooleanVar(value=False)
gender_chkbutton = tk.Checkbutton(features_bar, text="Split output",
               variable=gender_toggle_var,
               state=tk.DISABLED,
               command=toggle_gender_settings)
gender_chkbutton.pack(side=tk.LEFT, padx=4, pady=4)

gender_settings_frame = tk.Frame(features_bar)
# packed/unpacked by toggle_gender_settings()

gender_col_var = tk.StringVar(value="")
tk.Label(gender_settings_frame, text="Gender column:").pack(side=tk.LEFT)
gender_col_menu = tk.OptionMenu(gender_settings_frame, gender_col_var, "")
gender_col_menu.config(width=10)
gender_col_menu.pack(side=tk.LEFT, padx=2)

male_val_var = tk.StringVar(value="رجال")
tk.Label(gender_settings_frame, text="Male value:").pack(side=tk.LEFT, padx=(8, 0))
male_entry = tk.Entry(gender_settings_frame, textvariable=male_val_var, width=8)
male_entry.pack(side=tk.LEFT, padx=2)

female_val_var = tk.StringVar(value="نساء")
tk.Label(gender_settings_frame, text="Female value:").pack(side=tk.LEFT, padx=(8, 0))
female_entry = tk.Entry(gender_settings_frame, textvariable=female_val_var, width=8)
female_entry.pack(side=tk.LEFT, padx=2)

# score feature
score_toggle_var = tk.BooleanVar(value=False)
score_chkbutton = tk.Checkbutton(features_bar, text="Convert score",
               variable=score_toggle_var,
               state=tk.DISABLED,
               command=toggle_score_settings)
score_chkbutton.pack(side=tk.LEFT, padx=4, pady=4)

score_settings_frame = tk.Frame(features_bar)
# packed/unpacked by toggle_score_settings()

score_col_var = tk.StringVar(value="")
tk.Label(score_settings_frame, text="Score column:").pack(side=tk.LEFT)
score_col_menu = tk.OptionMenu(score_settings_frame, score_col_var, "")
score_col_menu.config(width=10)
score_col_menu.pack(side=tk.LEFT, padx=2)

tk.Label(score_settings_frame,
         text=" أكثر من 80% = ممتاز"
         " | أكثر من 60% = جيد جداً"
         " | أكثر من 40% = جيد"
         " | أقل من 40% = مقبول",
         fg="gray").pack(side=tk.LEFT, padx=6)

# ── bottom bar ─────────────────────────────────────────────────────────────────
bottom_bar = tk.Frame(window)
bottom_bar.pack(fill=tk.X, padx=6, pady=6, side=tk.BOTTOM)

generatebutton = tk.Button(bottom_bar, text="⚡  Generate All Images",
          command=generate, bg="#4a90d9", fg="white")
generatebutton.pack(side=tk.RIGHT, padx=4)
tk.Label(bottom_bar).pack(side=tk.RIGHT, padx=6)

progress_var = tk.StringVar(value="Select A CSV File First!")
progress_label = tk.Label(bottom_bar, textvariable=progress_var, fg="red")
progress_label.pack(side=tk.RIGHT)
tk.Label(bottom_bar, text="Progress:", bg="silver").pack(side=tk.RIGHT)
tk.Label(bottom_bar).pack(side=tk.RIGHT, padx=6)

status_var = tk.StringVar(value="Idle")
status_label = tk.Label(bottom_bar, textvariable=status_var, fg="red")
status_label.pack(side=tk.RIGHT)
tk.Label(bottom_bar, text="Status:", bg="silver").pack(side=tk.RIGHT)

tk.Label(bottom_bar, text="Filename prefix:").pack(side=tk.LEFT)
prefix_var = tk.StringVar(value="")
filename_entry = tk.Entry(bottom_bar, textvariable=prefix_var, width=12)
filename_entry.pack(side=tk.LEFT, padx=2)

tk.Label(bottom_bar, text="  Format:").pack(side=tk.LEFT)
format_var = tk.StringVar(value="PNG")
format_menu = tk.OptionMenu(bottom_bar, format_var, "PNG", "WEBP")
format_menu.pack(side=tk.LEFT, padx=2)
# ── main area ─────────────────────────────────────────────────────────────────
main_area = tk.Frame(window)
main_area.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

canvas = tk.Canvas(main_area, bg="#aaaaaa", width=700, height=450)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

settings_frame = tk.Frame(main_area, width=230, relief=tk.SUNKEN, bd=1)
settings_frame.pack(side=tk.RIGHT, fill=tk.Y)
settings_frame.pack_propagate(False)

tk.Label(settings_frame, text="Rectangle Settings", font=("", 9, "bold")).pack(pady=(4, 0))

settings_canvas = tk.Canvas(settings_frame, width=220, highlightthickness=0)
settings_scroll = tk.Scrollbar(settings_frame, orient="vertical", command=settings_canvas.yview)
settings_canvas.configure(yscrollcommand=settings_scroll.set)
settings_scroll.pack(side=tk.RIGHT, fill=tk.Y)
settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

settings_inner = tk.Frame(settings_canvas)
settings_canvas.create_window((0, 0), window=settings_inner, anchor="nw")
settings_inner.bind("<Configure>", _refresh_scroll)

window.mainloop()