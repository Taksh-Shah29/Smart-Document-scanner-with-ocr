import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2, pytesseract, shutil, os
from scanner import detect_document, perspective_transform, enhance_document, extract_text_and_confidence, export_multipage_pdf
from ai_classifier import classify_document, make_suggested_filename

# Find Tesseract automatically on Windows. You can replace this path if needed.
_tesseract_candidates = [
    shutil.which("tesseract"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for _candidate in _tesseract_candidates:
    if _candidate and os.path.isfile(_candidate):
        pytesseract.pytesseract.tesseract_cmd = _candidate
        break

class ScannerApp:
    def __init__(self,root):
        self.root=root; root.title("Scanify Pro"); root.geometry("1280x820")
        self.original=self.processed=None; self.corners=None; self.drag=None
        self.pages=[]; self.refs={}; self.camera=None
        self.mode=tk.StringVar(value="Magic Color"); self.lang=tk.StringVar(value="eng")
        self.psm=tk.StringVar(value="4"); self.status=tk.StringVar(value="Open an image or capture from webcam.")
        bar=ttk.Frame(root,padding=8); bar.pack(fill="x")
        for label,fn in [("Open Image",self.open_image),("Webcam Capture",self.webcam),
                         ("Auto Detect",self.auto_detect),("Apply Corners",self.apply_corners),
                         ("Enhance",self.enhance),("Extract OCR",self.ocr),
                         ("Handwriting OCR",self.handwriting_ocr),
                         ("Add PDF Page",self.add_page),("Export Multi-page PDF",self.export_pdf),
                         ("Save Image",self.save_image),("Detect Document Type",self.ai_classify)]:
            ttk.Button(bar,text=label,command=fn).pack(side="left",padx=2)
        opts=ttk.Frame(root,padding=(8,0,8,8)); opts.pack(fill="x")
        ttk.Label(opts,text="Image filter").pack(side="left")
        ttk.Combobox(opts,textvariable=self.mode,values=["Original","Magic Color","Grayscale","Black & White","High Contrast","Sharpen","Shadow Removal"],state="readonly",width=14).pack(side="left",padx=4)
        ttk.Label(opts,text="OCR language").pack(side="left",padx=(12,3))
        ttk.Entry(opts,textvariable=self.lang,width=8).pack(side="left")
        ttk.Label(opts,text="PSM").pack(side="left",padx=(12,3))
        ttk.Combobox(opts,textvariable=self.psm,values=["3","4","6","11"],state="readonly",width=4).pack(side="left")
        panes=ttk.Panedwindow(root,orient="horizontal"); panes.pack(fill="both",expand=True,padx=8,pady=5)
        lf=ttk.LabelFrame(panes,text="Original — drag yellow corner handles",padding=5)
        rf=ttk.LabelFrame(panes,text="Processed result",padding=5); panes.add(lf,weight=1); panes.add(rf,weight=1)
        self.left=tk.Canvas(lf,bg="#222831",highlightthickness=0,cursor="crosshair"); self.left.pack(fill="both",expand=True)
        self.right=tk.Canvas(rf,bg="#222831",highlightthickness=0); self.right.pack(fill="both",expand=True)
        self.left.bind("<Button-1>",self.corner_click); self.left.bind("<B1-Motion>",self.corner_drag)
        self.left.bind("<ButtonRelease-1>",lambda e:setattr(self,"drag",None))
        self.left.bind("<Configure>",lambda e:self.draw_left()); self.right.bind("<Configure>",lambda e:self.draw_right())
        lower=ttk.Panedwindow(root,orient="horizontal"); lower.pack(fill="x",padx=8,pady=5)
        tf=ttk.LabelFrame(lower,text="OCR text (editable)",padding=4); pf=ttk.LabelFrame(lower,text="PDF page queue",padding=4)
        lower.add(tf,weight=3); lower.add(pf,weight=1)
        self.text=tk.Text(tf,height=7,wrap="word"); self.text.pack(fill="both",expand=True)
        self.ai_result=tk.StringVar(value="Document type: Not classified")
        ttk.Label(tf,textvariable=self.ai_result,foreground="#087f6b").pack(anchor="w",pady=(4,0))
        self.page_list=tk.Listbox(pf,height=6); self.page_list.pack(fill="both",expand=True)
        ttk.Button(pf,text="Remove selected",command=self.remove_page).pack(fill="x")
        ttk.Label(root,textvariable=self.status,relief="sunken",padding=5).pack(fill="x")
        root.protocol("WM_DELETE_WINDOW",self.close)

    def open_image(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.tif *.tiff")])
        if p:
            img=cv2.imread(p)
            if img is None: messagebox.showerror("Error","Cannot read image."); return
            self.set_image(img)

    def set_image(self,img):
        self.original=img.copy(); self.processed=None; self.corners=detect_document(img)
        self.text.delete("1.0","end"); self.draw_left(); self.draw_right()
        self.status.set("Page boundary detected — drag yellow handles." if self.corners is not None else
                        "No boundary detected. Use Auto Detect or click near page corners to create handles.")

    def geometry(self,img,canvas):
        h,w=img.shape[:2]; cw=max(canvas.winfo_width(),100); ch=max(canvas.winfo_height(),100)
        s=min((cw-24)/w,(ch-24)/h); return s,(cw-w*s)/2,(ch-h*s)/2

    def draw_left(self):
        c=self.left; c.delete("all")
        if self.original is None: c.create_text(15,15,anchor="nw",fill="white",text="Open image"); return
        s,x,y=self.geometry(self.original,c); h,w=self.original.shape[:2]
        im=Image.fromarray(cv2.cvtColor(self.original,cv2.COLOR_BGR2RGB)).resize((int(w*s),int(h*s)))
        self.refs["left"]=ImageTk.PhotoImage(im); c.create_image(x,y,image=self.refs["left"],anchor="nw")
        if self.corners is not None:
            pts=[(x+p[0]*s,y+p[1]*s) for p in self.corners]
            c.create_polygon(*[v for pt in pts for v in pt],outline="#00e5a8",fill="",width=3)
            for i,(px,py) in enumerate(pts):
                c.create_oval(px-8,py-8,px+8,py+8,fill="#ffcc33",outline="black",width=2)
                c.create_text(px+12,py-12,text=str(i+1),fill="white")
        self.left_geo=(s,x,y)

    def draw_right(self):
        c=self.right; c.delete("all")
        if self.processed is None: c.create_text(15,15,anchor="nw",fill="white",text="Processed scan appears here"); return
        s,x,y=self.geometry(self.processed,c); h,w=self.processed.shape[:2]
        im=Image.fromarray(cv2.cvtColor(self.processed,cv2.COLOR_BGR2RGB)).resize((int(w*s),int(h*s)))
        self.refs["right"]=ImageTk.PhotoImage(im); c.create_image(x,y,image=self.refs["right"],anchor="nw")

    def canvas_point(self,event):
        s,x,y=self.left_geo; h,w=self.original.shape[:2]
        return [min(max((event.x-x)/s,0),w-1),min(max((event.y-y)/s,0),h-1)]

    def corner_click(self,e):
        if self.original is None:return
        if self.corners is None:
            h,w=self.original.shape[:2]
            self.corners=[[0,0],[w-1,0],[w-1,h-1],[0,h-1]]
        s,x,y=self.left_geo; shown=[(x+p[0]*s,y+p[1]*s) for p in self.corners]
        ds=[(e.x-px)**2+(e.y-py)**2 for px,py in shown]; idx=int(min(range(4),key=lambda i:ds[i]))
        if ds[idx]<35**2:
            self.drag=idx; self.corners[idx]=self.canvas_point(e); self.draw_left()

    def corner_drag(self,e):
        if self.drag is not None:
            self.corners[self.drag]=self.canvas_point(e); self.draw_left()

    def auto_detect(self):
        if self.original is None:return
        self.corners=detect_document(self.original); self.draw_left()
        self.status.set("Corners detected." if self.corners is not None else "Detection failed; click near a corner handle to initialize full-image corners.")

    def apply_corners(self):
        if self.original is None or self.corners is None:
            messagebox.showinfo("Corners","Open image and detect/create corners first."); return
        self.processed=enhance_document(perspective_transform(self.original,self.corners),self.mode.get())
        self.draw_right(); self.status.set("Perspective correction applied.")

    def enhance(self):
        if self.original is None:return
        source=perspective_transform(self.original,self.corners) if self.corners is not None else self.original
        self.processed=enhance_document(source,self.mode.get()); self.draw_right()
        self.status.set("Side-by-side comparison updated.")

    def ocr(self):
        if self.processed is None:self.enhance()
        if self.processed is None:return
        try:
            text,conf=extract_text_and_confidence(self.processed,self.lang.get().strip() or "eng",int(self.psm.get()))
            self.text.delete("1.0","end"); self.text.insert("1.0",text)
            self.status.set(f"OCR complete — mean word confidence {conf}% (indicative, not accuracy).")
            self.ai_classify()
        except pytesseract.TesseractNotFoundError:
            messagebox.showerror("Tesseract missing","Install Tesseract OCR separately; see README.")
        except Exception as ex:messagebox.showerror("OCR error",str(ex))

    def handwriting_ocr(self):
        if self.processed is None:
            self.enhance()
        if self.processed is None:
            return
        try:
            from handwriting_ocr import extract_handwriting
            self.status.set("Loading English handwriting OCR model; first use downloads it locally.")
            self.root.update_idletasks()
            text = extract_handwriting(self.processed)
            self.text.delete("1.0", "end")
            self.text.insert("1.0", text)
            self.status.set("Handwriting OCR complete — review the result for mistakes.")
            if text.strip():
                self.ai_classify()
        except Exception as ex:
            messagebox.showerror("Handwriting OCR", str(ex))

    def ai_classify(self):
        """Classify the current OCR text locally; no cloud/API connection is required."""
        content = self.text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("AI classification", "Extract OCR text first, or enter text in the OCR editor.")
            return
        result = classify_document(content)
        self.ai_result.set(
            f"Document type: {result['label']}  |  Confidence: {result['confidence']}%  |  {result['reason']}"
        )
        self.status.set(f"Document classified as {result['label']}. Review the suggestion before using it.")
        messagebox.showinfo(
            "Scanify Pro — Document type",
            f"Predicted type: {result['label']}\nConfidence: {result['confidence']}%\n"
            f"Suggested filename: {make_suggested_filename(result['label'])}\n\n"
            f"Reason: {result['reason']}\n\n"
            "This is an offline, keyword-based AI-assisted prediction. Please verify the result."
        )

    def webcam(self):
        cap=cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release(); messagebox.showerror("Webcam","Cannot access default camera."); return
        win=tk.Toplevel(self.root); win.title("Webcam capture")
        label=ttk.Label(win); label.pack()
        state={"photo":None,"frame":None,"running":True}
        def update():
            if not state["running"]:return
            ok,frame=cap.read()
            if ok:
                state["frame"]=frame
                im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)); im.thumbnail((760,520))
                state["photo"]=ImageTk.PhotoImage(im); label.configure(image=state["photo"])
            win.after(30,update)
        def capture():
            if state["frame"] is not None:self.set_image(state["frame"])
            stop()
        def stop():
            state["running"]=False; cap.release()
            if win.winfo_exists():win.destroy()
        ttk.Button(win,text="Capture photo",command=capture).pack(side="left",padx=8,pady=8)
        ttk.Button(win,text="Close camera",command=stop).pack(side="left",padx=8,pady=8)
        win.protocol("WM_DELETE_WINDOW",stop); update()

    def add_page(self):
        if self.processed is None:self.enhance()
        if self.processed is None:return
        self.pages.append(self.processed.copy()); self.page_list.insert("end",f"Page {len(self.pages)}")
        self.status.set(f"Queued {len(self.pages)} page(s). Open next image to continue.")

    def remove_page(self):
        sel=self.page_list.curselection()
        if not sel:return
        self.pages.pop(sel[0]); self.page_list.delete(0,"end")
        for i in range(len(self.pages)):self.page_list.insert("end",f"Page {i+1}")

    def export_pdf(self):
        if not self.pages:messagebox.showinfo("PDF","Add at least one processed page."); return
        p=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")])
        if p:
            try:export_multipage_pdf(self.pages,p); self.status.set(f"Exported {len(self.pages)} pages to PDF.")
            except Exception as ex:messagebox.showerror("PDF error",str(ex))

    def save_image(self):
        if self.processed is None:messagebox.showinfo("Image","Enhance a page first."); return
        p=filedialog.asksaveasfilename(defaultextension=".jpg",filetypes=[("JPEG","*.jpg"),("PNG","*.png")])
        if p:cv2.imwrite(p,self.processed); self.status.set("Image saved.")

    def close(self):
        self.root.destroy()

def show_splash(root):
    """Display a short branded loading screen before opening the scanner."""
    root.withdraw()
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#101827")
    width, height = 520, 300
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f"{width}x{height}+{(sw-width)//2}+{(sh-height)//2}")

    panel = tk.Frame(splash, bg="#101827", padx=34, pady=28)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text="SCANIFY", bg="#101827", fg="#ffffff",
             font=("Segoe UI", 30, "bold")).pack(pady=(25, 0))
    tk.Label(panel, text="PRO", bg="#101827", fg="#21d4a5",
             font=("Segoe UI", 17, "bold")).pack()
    tk.Label(panel, text="Smart Document Scanner",
             bg="#101827", fg="#aab7c8",
             font=("Segoe UI", 11)).pack(pady=(8, 24))
    progress = ttk.Progressbar(panel, mode="indeterminate", length=330)
    progress.pack(pady=8)
    progress.start(12)
    tk.Label(panel, text="Preparing your workspace...",
             bg="#101827", fg="#8292a8",
             font=("Segoe UI", 9)).pack(pady=(10, 0))

    def launch():
        progress.stop()
        splash.destroy()
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass
        root.deiconify()
        ScannerApp(root)

    splash.after(1900, launch)


if __name__=="__main__":
    root=tk.Tk()
    show_splash(root)
    root.mainloop()
