import os
import queue
import threading
import argparse
import io
import re
import datetime
import json
import contextlib
import customtkinter as ctk
from tkinter import filedialog, messagebox
import unicodedata
from urllib.parse import urlparse, parse_qs, unquote

ctk.set_appearance_mode("dark")  # "light", "dark", "system"
ctk.set_default_color_theme("blue")  # "blue", "dark-blue", "green"

_IMPORT_ERROR: str = ""
try:
    import main as _core
except ImportError as _e:
    _IMPORT_ERROR = str(_e)
    _core = None  # type: ignore


_RICH_RE = re.compile(r"\[/?[a-zA-Z0-9_ #:=,\.\(\)]+\]")


def strip_rich(text: str) -> str:
    return _RICH_RE.sub("", text)


class _QueueIO(io.TextIOBase):
    """File-like object viết vào một Queue (dùng cho Rich Console)."""

    def __init__(self, q: queue.Queue):
        super().__init__()
        self._q = q

    def write(self, text: str) -> int:
        cleaned = strip_rich(text)
        if cleaned.strip():
            self._q.put(("log", cleaned.rstrip()))
        return len(text)

    def flush(self):
        pass


class _StopWorker(Exception):
    pass


_ACCENT = "#1f6aa5"
_SUCCESS = "#2ecc71"
_ERROR = "#e74c3c"
_WARNING = "#f39c12"
_LOG_BG = "#1a1a2e"
_LOG_FG = "#e0e0e0"

_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
_LANGUAGES = ["auto", "vi", "en", "ja", "ko", "zh", "th", "id", "custom"]
_THUMB_FORMATS = ["webp", "jpg"]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Whisper M3U8 Transcriber - GUI")
        self.geometry("980x780")
        self.resizable(True, True)
        self.minsize(800, 640)

        # Queue trao đổi giữa worker thread và UI thread
        self._q: queue.Queue = queue.Queue()

        # Worker thread hiện tại (nếu có)
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self._current_args = None

        # Cờ import lỗi
        self._core_ok = _core is not None

        self._build_ui()
        self._init_core()

        # Bắt đầu vòng lặp poll queue
        self._poll_queue()

    def _init_core(self):
        if not self._core_ok:
            self.log(f"[LỖI IMPORT] {_IMPORT_ERROR}", "error")
            self.log(
                "Kiểm tra xem main.py có cùng thư mục và đã cài đủ thư viện chưa.",
                "warning",
            )
            self.set_status("Lỗi import – Xem log", color=_ERROR)
            return

        # Kiểm tra FFmpeg
        try:
            import subprocess

            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            self.log("✓ FFmpeg đã được cài đặt.", "success")
        except Exception:
            messagebox.showerror(
                "Thiếu FFmpeg",
                "Không tìm thấy FFmpeg!\n\nVui lòng cài FFmpeg và thêm vào PATH:\n"
                "  Windows: https://www.gyan.dev/ffmpeg/builds/\n"
                "  Linux/macOS: sudo apt install ffmpeg  hoặc  brew install ffmpeg",
            )
            self.log(
                "[LỖI] FFmpeg không tìm thấy – hãy cài đặt trước khi chạy.", "error"
            )
            self.set_status("Thiếu FFmpeg", color=_ERROR)
            return

        # Kiểm tra GPU
        try:
            import torch

            if torch.cuda.is_available():
                gpu = torch.cuda.get_device_name(0)
                self.log(f"✓ GPU phát hiện: {gpu}", "success")
                self._gpu_label.configure(text=f"GPU: {gpu}", text_color=_SUCCESS)
            else:
                self.log("Không tìm thấy GPU – sẽ dùng CPU (chậm hơn).", "warning")
                self._gpu_label.configure(
                    text="Chế độ CPU (không có GPU)", text_color=_WARNING
                )
        except Exception as e:
            self.log(f"Lỗi kiểm tra GPU: {e}", "warning")
            self._gpu_label.configure(text="Không xác định GPU", text_color=_WARNING)

        self.set_status("Sẵn sàng")

    def _build_ui(self):
        # ── Header ──────────────────────────────────────
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color=("#1a3a5c", "#0d1b2a"))
        hdr.pack(fill="x", pady=(0, 0))

        ctk.CTkLabel(
            hdr,
            text="🎬  Whisper M3U8 Transcriber",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        self._gpu_label = ctk.CTkLabel(
            hdr,
            text="Đang kiểm tra GPU…",
            font=ctk.CTkFont(size=12),
            text_color=_WARNING,
        )
        self._gpu_label.pack(side="right", padx=20)

        # ── Nội dung chính ──────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=1)

        # Tab chế độ
        self._tabview = ctk.CTkTabview(body, anchor="nw")
        self._tabview.grid(row=0, column=0, sticky="nsew")
        self._tabview.add("📂  Chế độ Batch")

        self._build_batch_tab(self._tabview.tab("📂  Chế độ Batch"))

        # Khu vực Log + Progress
        log_frame = ctk.CTkFrame(body)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        # Thanh điều khiển log
        ctrl = ctk.CTkFrame(log_frame, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))

        ctk.CTkLabel(
            ctrl, text="📋 Log tiến trình", font=ctk.CTkFont(weight="bold")
        ).pack(side="left")

        # Nút Stop
        self._btn_stop = ctk.CTkButton(
            ctrl,
            text="⏹  Dừng",
            width=90,
            fg_color=_ERROR,
            hover_color="#c0392b",
            command=self._stop_worker,
            state="disabled",
        )
        self._btn_stop.pack(side="right", padx=(4, 0))

        # Nút Clear log
        ctk.CTkButton(
            ctrl,
            text="🗑  Xóa log",
            width=90,
            fg_color="#555",
            hover_color="#666",
            command=self._clear_log,
        ).pack(side="right")

        # Textbox log
        self._log_box = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=_LOG_BG,
            text_color=_LOG_FG,
            wrap="word",
            state="disabled",
        )
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 4))

        # Progress + Status bar
        bot = ctk.CTkFrame(log_frame, fg_color="transparent")
        bot.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))
        bot.columnconfigure(0, weight=1)

        self._progress = ctk.CTkProgressBar(bot, height=14, corner_radius=6)
        self._progress.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._progress.set(0)

        self._status_label = ctk.CTkLabel(
            bot,
            text="Đang khởi tạo…",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#aaa",
        )
        self._status_label.grid(row=1, column=0, sticky="w")

    def _build_batch_tab(self, parent):
        parent.columnconfigure(1, weight=1)

        r = 0

        # Chọn file JSON
        ctk.CTkLabel(parent, text="File JSON:").grid(
            row=r, column=0, sticky="w", padx=8, pady=(10, 2)
        )
        self._b_json = ctk.CTkEntry(
            parent, placeholder_text="Chọn file .json chứa danh sách URL…"
        )
        self._b_json.grid(row=r, column=1, sticky="ew", padx=8, pady=(10, 2))
        ctk.CTkButton(
            parent, text="Browse JSON", width=100, command=self._browse_json_file
        ).grid(row=r, column=2, padx=(0, 8), pady=(10, 2))
        r += 1
        ctk.CTkLabel(
            parent,
            text="File JSON chứa danh sách các URL .m3u8 cần xử lý",
            text_color="white",
            font=ctk.CTkFont(size=10),
        ).grid(row=r, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4))
        r += 1

        # ── Tạo JSON từ danh sách link m3u8 ─────────────────
        json_tools = ctk.CTkFrame(parent, fg_color="transparent")
        json_tools.grid(row=r, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 4))

        ctk.CTkButton(
            json_tools,
            text="➕ Tạo JSON từ danh sách link",
            width=220,
            fg_color="#2b7a78",
            hover_color="#205f5d",
            command=self._open_create_json_dialog,
        ).pack(side="left")

        ctk.CTkLabel(
            json_tools,
            text="Dán nhiều link .m3u8, app sẽ tự tạo file input.json",
            text_color="#aaa",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=10)

        r += 1

        # ── Checkpoint info ──────────────────────────────
        self._b_ckpt_label = ctk.CTkLabel(
            parent, text="", font=ctk.CTkFont(size=11), text_color="#aaa"
        )
        self._b_ckpt_label.grid(
            row=r, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 2)
        )

        self._btn_clear_ckpt = ctk.CTkButton(
            parent,
            text="Xóa Checkpoint",
            width=120,
            fg_color="#555",
            hover_color="#666",
            command=self._clear_checkpoint_ui,
        )
        self._btn_clear_ckpt.grid(row=r, column=2, padx=(0, 8), pady=(0, 2))
        r += 1

        # Model Whisper
        ctk.CTkLabel(parent, text="Model Whisper:").grid(
            row=r, column=0, sticky="w", padx=8, pady=2
        )
        self._b_model = ctk.CTkOptionMenu(parent, values=_WHISPER_MODELS)
        self._b_model.set("small")
        self._b_model.grid(row=r, column=1, sticky="w", padx=8, pady=2)
        r += 1
        ctk.CTkLabel(
            parent,
            text="tiny: nhanh, chất lượng thấp | large: chất lượng cao, tốc độ chậm",
            text_color="white",
            font=ctk.CTkFont(size=10),
        ).grid(row=r, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4))
        r += 1

        # Ngôn ngữ
        ctk.CTkLabel(parent, text="Ngôn ngữ:").grid(
            row=r, column=0, sticky="w", padx=8, pady=2
        )
        b_lang_row = ctk.CTkFrame(parent, fg_color="transparent")
        b_lang_row.grid(row=r, column=1, columnspan=2, sticky="ew", padx=8, pady=2)
        self._b_lang = ctk.CTkOptionMenu(
            b_lang_row, values=_LANGUAGES, command=self._on_batch_lang_change
        )
        self._b_lang.set("vi")
        self._b_lang.pack(side="left")
        self._b_custom_lang = ctk.CTkEntry(
            b_lang_row, placeholder_text="Mã ngôn ngữ (ví dụ: fr)", width=160
        )
        self._b_custom_lang.pack(side="left", padx=(8, 0))
        self._b_custom_lang.configure(state="disabled")
        r += 1
        ctk.CTkLabel(
            parent,
            text="auto: tự nhận dạng | chọn ngôn ngữ cụ thể để tăng độ chính xác",
            text_color="white",
            font=ctk.CTkFont(size=10),
        ).grid(row=r, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4))
        r += 1

        # Checkboxes
        cb_frame = ctk.CTkFrame(parent)
        cb_frame.grid(row=r, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(cb_frame, text="Lưu file:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=(8, 16)
        )
        self._b_save_video = ctk.CTkCheckBox(cb_frame, text="Video")
        self._b_save_video.pack(side="left", padx=6)
        self._b_save_audio = ctk.CTkCheckBox(cb_frame, text="Audio")
        self._b_save_audio.pack(side="left", padx=6)
        self._b_save_vtt = ctk.CTkCheckBox(cb_frame, text="Phụ đề VTT")
        self._b_save_vtt.pack(side="left", padx=6)
        self._b_save_vtt.select()

        self._b_create_thumbs = ctk.CTkCheckBox(
            cb_frame, text="Tạo Thumbnails", command=self._toggle_thumbs_batch
        )
        self._b_create_thumbs.pack(side="left", padx=6)
        r += 1

        # Tùy chọn Thumbnail (batch)
        self._b_thumb_frame = ctk.CTkFrame(parent)
        self._b_thumb_frame.grid(
            row=r, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 4)
        )
        self._b_thumb_frame.grid_remove()

        btf = self._b_thumb_frame
        btf.columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(btf, text="Interval (s):").grid(
            row=0, column=0, padx=(8, 4), pady=4, sticky="w"
        )
        self._b_t_interval = ctk.CTkEntry(btf, width=70)
        self._b_t_interval.insert(0, "5")
        self._b_t_interval.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(btf, text="Rộng (px):").grid(
            row=0, column=2, padx=(12, 4), pady=4, sticky="w"
        )
        self._b_t_width = ctk.CTkEntry(btf, width=70)
        self._b_t_width.insert(0, "160")
        self._b_t_width.grid(row=0, column=3, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(btf, text="Cao (px):").grid(
            row=0, column=4, padx=(12, 4), pady=4, sticky="w"
        )
        self._b_t_height = ctk.CTkEntry(btf, width=70)
        self._b_t_height.insert(0, "90")
        self._b_t_height.grid(row=0, column=5, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(btf, text="Số cột:").grid(
            row=1, column=0, padx=(8, 4), pady=4, sticky="w"
        )
        self._b_t_cols = ctk.CTkEntry(btf, width=70)
        self._b_t_cols.insert(0, "10")
        self._b_t_cols.grid(row=1, column=1, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(btf, text="Định dạng:").grid(
            row=1, column=2, padx=(12, 4), pady=4, sticky="w"
        )
        self._b_t_fmt = ctk.CTkOptionMenu(btf, values=_THUMB_FORMATS, width=80)
        self._b_t_fmt.set("webp")
        self._b_t_fmt.grid(row=1, column=3, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(btf, text="CDN URL:").grid(
            row=1, column=4, padx=(12, 4), pady=4, sticky="w"
        )
        self._b_t_cdn = ctk.CTkEntry(
            btf, placeholder_text="https://cdn.example.com/ (tùy chọn)"
        )
        self._b_t_cdn.grid(row=1, column=5, padx=(4, 8), pady=4, sticky="ew")
        r += 1

        # Nút Start
        self._btn_start_batch = ctk.CTkButton(
            parent,
            text="▶  CHẠY BATCH",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=_ACCENT,
            hover_color="#174e80",
            height=40,
            command=self.start_batch,
        )
        self._btn_start_batch.grid(
            row=r, column=0, columnspan=3, padx=8, pady=(8, 12), sticky="ew"
        )

        # Cập nhật thông tin checkpoint khi mở tab
        self._refresh_checkpoint_label()

    def start_batch(self):
        if not self._assert_core_ok():
            return

        json_path = self._b_json.get().strip()
        if not json_path:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn file JSON")
            return
        if not os.path.exists(json_path):
            messagebox.showwarning(
                "Không tìm thấy file", f"File không tồn tại:\n{json_path}"
            )
            return

        lang = self._resolve_lang(self._b_lang, self._b_custom_lang)
        args = self._build_args(
            model=self._b_model.get(),
            language=lang,
            save_video=self._b_save_video.get(),
            save_audio=self._b_save_audio.get(),
            save_vtt=self._b_save_vtt.get(),
            create_thumbnails=bool(self._b_create_thumbs.get()),
            thumb_frame=self._b_thumb_frame,
            t_interval=self._b_t_interval,
            t_width=self._b_t_width,
            t_height=self._b_t_height,
            t_cols=self._b_t_cols,
            t_fmt=self._b_t_fmt,
            t_cdn=self._b_t_cdn,
        )

        self._current_args = args
        self._start_worker(self._run_batch_worker, json_path, args)

    def _run_batch_worker(self, json_path: str, args):
        try:
            self._q.put(("log", f"[Batch] Đọc file JSON: {json_path}"))

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            root_path = data.get("root_path", "")
            items = data.get("items", [])

            if not items:
                self._q.put(("error", "File JSON không có items nào!"))
                return

            total = len(items)
            self._q.put(("log", f"Tìm thấy {total} items trong file JSON."))

            # Kiểm tra checkpoint
            checkpoint = _core.load_checkpoint()
            start_index = 0
            if checkpoint.get("json_path") == os.path.abspath(json_path):
                last_index = checkpoint.get("last_index", 0)
                if 0 < last_index < total:
                    time_saved = datetime.datetime.fromtimestamp(
                        checkpoint.get("timestamp", 0)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    self._q.put(
                        (
                            "log",
                            f"► Tìm thấy checkpoint: đã xử lý {last_index}/{total} items (lưu lúc {time_saved})",
                        )
                    )
                    self._q.put(("log", f"  Tiếp tục từ item #{last_index + 1}"))
                    start_index = last_index

            for i in range(start_index, total):
                if self._stop_event.is_set():
                    _core.save_checkpoint(os.path.abspath(json_path), i, total)
                    self._q.put(("log", f"  Đã lưu checkpoint tại item #{i + 1}"))
                    raise _StopWorker()

                item = items[i]
                slug = item.get("slug", "")
                m3u8_url = item.get("m3u8_url", "")
                folder_nm = item.get("folder_name", slug)

                self._q.put(("log", f"\n── Item {i+1}/{total}: {slug} ──"))
                self._q.put(("progress", (i / total) * 0.95))

                if not m3u8_url or not _core.validate_url(m3u8_url):
                    self._q.put(("log", f"  [BỎ QUA] URL không hợp lệ: {m3u8_url}"))
                    _core.save_checkpoint(os.path.abspath(json_path), i + 1, total)
                    continue

                try:
                    if root_path:
                        output_base = os.path.join(root_path, slug)
                    else:
                        output_base = slug
                    group_dir = os.path.join(output_base, folder_nm)
                    os.makedirs(group_dir, exist_ok=True)

                    _core.process_single_item(
                        m3u8_url=m3u8_url,
                        output_dir=group_dir,
                        args=args,
                        item_number=i + 1,
                        total_items=total,
                    )
                    _core.save_checkpoint(os.path.abspath(json_path), i + 1, total)
                    self._q.put(("log", f"  ✓ Hoàn thành item #{i+1}"))

                except _StopWorker:
                    raise
                except SystemExit as e:
                    self._q.put(
                        (
                            "log",
                            f"  [LỖI] Item #{i+1} bị thoát (code={e.code}) – bỏ qua.",
                        )
                    )
                    _core.save_checkpoint(os.path.abspath(json_path), i + 1, total)
                except Exception as e:
                    cancel_cls = getattr(_core, "UserCancelled", None)

                    if self._stop_event.is_set() or (
                        cancel_cls is not None and isinstance(e, cancel_cls)
                    ):
                        _core.save_checkpoint(os.path.abspath(json_path), i, total)
                        self._q.put(("log", f"  Đã lưu checkpoint tại item #{i + 1}"))
                        raise _StopWorker()

                    self._q.put(("log", f"  [LỖI] Item #{i+1}: {e} – bỏ qua."))
                    _core.save_checkpoint(os.path.abspath(json_path), i + 1, total)

            _core.clear_checkpoint()
            self._q.put(("progress", 1.0))
            self._q.put(("done", f"✓ Hoàn thành tất cả {total} items!"))

        except _StopWorker:
            self._q.put(("cancelled", "⏹ Đã dừng theo yêu cầu. Checkpoint đã lưu."))
        except json.JSONDecodeError as e:
            self._q.put(("error", f"File JSON không hợp lệ: {e}"))
        except SystemExit as e:
            self._q.put(("error", f"Tiến trình bị thoát (code={e.code}) – xem log."))
        except Exception as e:
            self._q.put(("error", f"Lỗi: {e}"))

    def _start_worker(self, target, *args):
        """Khởi chạy worker trong thread riêng, redirect Rich console + stdout/stderr."""
        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showwarning(
                "Đang chạy", "Có tiến trình đang chạy. Hãy dừng lại trước."
            )
            return

        self._stop_event.clear()
        self.set_status("Đang chạy…", color=_WARNING)
        self._set_running(True)
        self._progress.set(0)

        q_io = _QueueIO(self._q)

        def wrapped():
            old_console = None

            try:
                if _core is not None:
                    from rich.console import Console

                    old_console = _core.console
                    _core.console = Console(
                        file=q_io,
                        highlight=False,
                        markup=True,
                        width=120,
                        force_terminal=False,
                    )

                # Bắt cả print(), tqdm, Whisper verbose, warning...
                with contextlib.redirect_stdout(q_io), contextlib.redirect_stderr(q_io):
                    target(*args)

            except Exception as e:
                self._q.put(("error", f"Lỗi worker: {e}"))

            finally:
                if _core is not None and old_console is not None:
                    try:
                        _core.console = old_console
                    except Exception:
                        pass

        self._worker_thread = threading.Thread(target=wrapped, daemon=True)
        self._worker_thread.start()

    def _stop_worker(self):
        self._stop_event.set()
        self.set_status("Đang dừng…", color=_WARNING)
        self.log("⏹ Đang gửi tín hiệu dừng, vui lòng chờ vài giây…", "warning")

        # Kill process ffmpeg đang chạy nếu có
        try:
            args = getattr(self, "_current_args", None)
            process = (
                getattr(args, "_active_process", None) if args is not None else None
            )

            if process is not None and process.poll() is None:
                self.log("⏹ Đang dừng tiến trình ffmpeg...", "warning")
                process.terminate()

                try:
                    process.wait(timeout=3)
                except Exception:
                    self.log("⏹ ffmpeg chưa dừng, đang kill cưỡng bức...", "warning")
                    process.kill()

        except Exception as e:
            self.log(f"Lỗi khi dừng process: {e}", "error")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "progress":
                    self.set_progress(float(payload))
                elif kind == "done":
                    self.log(payload, "success")
                    self.set_status("Hoàn thành ✓", color=_SUCCESS)
                    self._set_running(False)
                    self._refresh_checkpoint_label()
                elif kind == "error":
                    self.log(payload, "error")
                    self.set_status("Lỗi – xem log", color=_ERROR)
                    self._set_running(False)
                elif kind == "cancelled":
                    self.log(payload, "warning")
                    self.set_status("Đã dừng", color=_WARNING)
                    self._set_running(False)
                    self._refresh_checkpoint_label()
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def log(self, msg: str, level: str = "normal"):
        self._log_box.configure(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = f"[{ts}] "
        line = prefix + str(msg) + "\n"
        self._log_box.insert("end", line)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def set_status(self, msg: str, color: str = "#aaa"):
        self._status_label.configure(text=msg, text_color=color)

    def set_progress(self, value: float):
        self._progress.set(max(0.0, min(1.0, value)))

    def _set_running(self, running: bool):
        state_start = "disabled" if running else "normal"
        state_stop = "normal" if running else "disabled"
        self._btn_start_batch.configure(state=state_start)
        self._btn_stop.configure(state=state_stop)

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _browse_json_file(self):
        f = filedialog.askopenfilename(
            title="Chọn file JSON", filetypes=[("JSON files", "*.json"), ("All", "*.*")]
        )
        if f:
            self._b_json.delete(0, "end")
            self._b_json.insert(0, f)
            self._refresh_checkpoint_label()

    def _open_create_json_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("Tạo JSON từ danh sách link .m3u8")
        win.geometry("860x680")
        win.minsize(760, 580)
        win.transient(self)
        win.grab_set()

        win.columnconfigure(0, weight=1)
        win.rowconfigure(5, weight=1)
        title = ctk.CTkLabel(
            win,
            text="Tạo file JSON Batch từ danh sách link .m3u8",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        root_frame = ctk.CTkFrame(win)
        root_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=6)
        root_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(root_frame, text="Thư mục root_path:").grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )

        root_entry = ctk.CTkEntry(root_frame, placeholder_text="Ví dụ: D:/phoflix-data")
        root_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        default_root = ""
        try:
            default_root = self._d_outdir.get().strip()
        except Exception:
            default_root = ""

        root_entry.insert(0, default_root or "D:/phoflix-data")

        def browse_root():
            d = filedialog.askdirectory(title="Chọn thư mục root_path", parent=win)
            if d:
                root_entry.delete(0, "end")
                root_entry.insert(0, d)

        ctk.CTkButton(root_frame, text="Browse", width=90, command=browse_root).grid(
            row=0, column=2, padx=10, pady=8
        )

        opt_frame = ctk.CTkFrame(win)
        opt_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=6)
        opt_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(opt_frame, text="Slug prefix nếu dòng không có tên tập:").grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )

        slug_prefix_entry = ctk.CTkEntry(opt_frame, placeholder_text="video")
        slug_prefix_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        slug_prefix_entry.insert(0, "video")

        out_frame = ctk.CTkFrame(win)
        out_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=6)
        out_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(out_frame, text="Lưu JSON tại:").grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )

        json_out_entry = ctk.CTkEntry(out_frame)
        json_out_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        default_json_path = os.path.abspath("input_generated.json")
        json_out_entry.insert(0, default_json_path)

        def browse_json_save():
            f = filedialog.asksaveasfilename(
                title="Lưu file JSON",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                parent=win,
            )
            if f:
                json_out_entry.delete(0, "end")
                json_out_entry.insert(0, f)

        ctk.CTkButton(
            out_frame, text="Browse", width=90, command=browse_json_save
        ).grid(row=0, column=2, padx=10, pady=8)

        hint = ctk.CTkLabel(
            win,
            text=(
                "Dán mỗi link một dòng. Hỗ trợ: "
                "Tập 01|https://.../index.m3u8 hoặc link .m3u8 trực tiếp."
            ),
            text_color="#aaa",
            font=ctk.CTkFont(size=12),
        )
        hint.grid(row=4, column=0, sticky="w", padx=16, pady=(8, 2))

        links_box = ctk.CTkTextbox(
            win, font=ctk.CTkFont(family="Consolas", size=12), wrap="word"
        )
        links_box.grid(row=5, column=0, sticky="nsew", padx=16, pady=8)

        links_box.insert(
            "1.0",
            "Tập 01|https://s2.phim1280.tv/20240310/QPdCAUah/index.m3u8\n"
            "Tập 02|https://s2.phim1280.tv/20240310/Gc4Ycfp/index.m3u8\n"
            "Tập 03|https://s2.phim1280.tv/20240310/g8xR3bUd/index.m3u8\n",
        )

        def slugify(value: str) -> str:
            value = value.strip().lower()

            # Bỏ dấu tiếng Việt: "Tập 01" -> "tap 01"
            value = unicodedata.normalize("NFKD", value)
            value = "".join(ch for ch in value if not unicodedata.combining(ch))

            value = re.sub(r"[^a-z0-9_-]+", "-", value)
            value = re.sub(r"-+", "-", value).strip("-")

            return value or "video"

        def extract_real_m3u8_url(raw_url: str) -> str:
            raw_url = raw_url.strip()

            # Trường hợp:
            # https://player.phimapi.com/player/?url=https://s2.phim1280.tv/.../index.m3u8
            try:
                parsed = urlparse(raw_url)
                query = parse_qs(parsed.query)

                if "url" in query and query["url"]:
                    real_url = unquote(query["url"][0]).strip()
                    if ".m3u8" in real_url.lower():
                        return real_url
            except Exception:
                pass

            # Trường hợp link trực tiếp hoặc dòng có lẫn text
            match = re.search(
                r"https?://[^\s\"'<>|]+?\.m3u8(?:\?[^\s\"'<>|]*)?",
                raw_url,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(0).strip()

            return ""

        def extract_m3u8_items(raw_text: str) -> list[dict]:
            parsed_items = []
            seen = set()

            for line in raw_text.splitlines():
                line = line.strip()
                if not line:
                    continue

                label = ""
                url_part = line

                # Dạng chuẩn:
                # Tập 01|https://.../index.m3u8
                if "|" in line:
                    left, right = line.split("|", 1)
                    label = left.strip()
                    url_part = right.strip()

                m3u8_url = extract_real_m3u8_url(url_part)

                if not m3u8_url:
                    continue

                if m3u8_url in seen:
                    continue

                seen.add(m3u8_url)

                parsed_items.append({"label": label, "m3u8_url": m3u8_url})

            return parsed_items

        def create_json_file():
            raw_text = links_box.get("1.0", "end").strip()
            parsed_items = extract_m3u8_items(raw_text)

            if not parsed_items:
                messagebox.showwarning(
                    "Không có link",
                    "Không tìm thấy link .m3u8 hợp lệ trong nội dung đã dán.",
                    parent=win,
                )
                return

            root_path = root_entry.get().strip()
            slug_prefix = slugify(slug_prefix_entry.get().strip() or "video")
            json_out = json_out_entry.get().strip()

            if not root_path:
                messagebox.showwarning(
                    "Thiếu root_path",
                    "Vui lòng nhập hoặc chọn thư mục root_path.",
                    parent=win,
                )
                return

            if not json_out:
                messagebox.showwarning(
                    "Thiếu đường dẫn JSON",
                    "Vui lòng chọn nơi lưu file JSON.",
                    parent=win,
                )
                return

            items = []

            for idx, item in enumerate(parsed_items, start=1):
                label = item.get("label", "").strip()
                m3u8_url = item["m3u8_url"]

                if label:
                    slug = slugify(label)
                else:
                    slug = f"{slug_prefix}-{idx:03d}"

                items.append({"slug": slug, "m3u8_url": m3u8_url})

            data = {"root_path": root_path, "items": items}

            try:
                out_dir = os.path.dirname(os.path.abspath(json_out))
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)

                with open(json_out, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Tự điền file JSON vừa tạo vào ô Batch
                self._b_json.delete(0, "end")
                self._b_json.insert(0, json_out)
                self._refresh_checkpoint_label()

                self.log(f"✓ Đã tạo file JSON: {json_out}", "success")
                self.log(f"✓ Số item: {len(items)}", "success")

                messagebox.showinfo(
                    "Tạo JSON thành công",
                    f"Đã tạo file JSON với {len(items)} item:\n{json_out}",
                    parent=win,
                )

                win.destroy()

            except Exception as e:
                messagebox.showerror("Lỗi tạo JSON", str(e), parent=win)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.grid(row=6, column=0, sticky="ew", padx=16, pady=(6, 14))

        ctk.CTkButton(
            btn_frame,
            text="✅ Tạo JSON và chọn file này",
            fg_color=_SUCCESS,
            hover_color="#239b56",
            height=38,
            command=create_json_file,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame,
            text="Hủy",
            fg_color="#555",
            hover_color="#666",
            height=38,
            command=win.destroy,
        ).pack(side="right")

        win.after(100, win.lift)

    def _on_batch_lang_change(self, value: str):
        self._b_custom_lang.configure(
            state="normal" if value == "custom" else "disabled"
        )

    def _toggle_thumbs_batch(self):
        if self._b_create_thumbs.get():
            self._b_thumb_frame.grid()
        else:
            self._b_thumb_frame.grid_remove()

    def _refresh_checkpoint_label(self):
        if not self._core_ok:
            return
        try:
            ckpt = _core.load_checkpoint()
            if ckpt and ckpt.get("json_path"):
                last = ckpt.get("last_index", 0)
                total = ckpt.get("total", 0)
                ts = datetime.datetime.fromtimestamp(ckpt.get("timestamp", 0)).strftime(
                    "%H:%M %d/%m/%Y"
                )
                self._b_ckpt_label.configure(
                    text=f"Checkpoint: {last}/{total} items – lưu lúc {ts}",
                    text_color=_WARNING,
                )
            else:
                self._b_ckpt_label.configure(
                    text="Không có checkpoint", text_color="#aaa"
                )
        except Exception:
            pass

    def _clear_checkpoint_ui(self):
        if not self._core_ok:
            return
        if messagebox.askyesno(
            "Xóa checkpoint", "Bạn có chắc muốn xóa checkpoint không?"
        ):
            _core.clear_checkpoint()
            self._refresh_checkpoint_label()
            self.log("✓ Đã xóa checkpoint.", "success")

    def _assert_core_ok(self) -> bool:
        if not self._core_ok:
            messagebox.showerror(
                "Lỗi import", f"Không thể import main.py:\n{_IMPORT_ERROR}"
            )
            return False
        return True

    @staticmethod
    def _safe_int(entry_widget, default: int) -> int:
        try:
            v = int(entry_widget.get().strip())
            return v if v > 0 else default
        except Exception:
            return default

    def _resolve_lang(self, option_menu, custom_entry) -> str | None:
        v = option_menu.get()
        if v == "auto":
            return None
        if v == "custom":
            c = custom_entry.get().strip()
            return c if c else None
        return v

    def _build_args(
        self,
        model,
        language,
        save_video,
        save_audio,
        save_vtt,
        create_thumbnails,
        thumb_frame,
        t_interval,
        t_width,
        t_height,
        t_cols,
        t_fmt,
        t_cdn,
    ) -> argparse.Namespace:
        cdn_val = t_cdn.get().strip() or None

        return argparse.Namespace(
            model=model,
            language=language,
            output_prefix="movie",
            save_video=bool(save_video),
            save_audio=bool(save_audio),
            save_vtt=bool(save_vtt),
            no_gpu=False,
            create_thumbnails=create_thumbnails,
            thumbnail_interval=self._safe_int(t_interval, 5),
            thumb_width=self._safe_int(t_width, 160),
            thumb_height=self._safe_int(t_height, 90),
            thumb_cols=self._safe_int(t_cols, 10),
            thumb_format=t_fmt.get(),
            cdn_url=cdn_val,
            gui_queue=self._q,
            stop_event=self._stop_event,
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
