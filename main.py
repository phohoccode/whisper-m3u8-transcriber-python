import os
import subprocess
import argparse
import whisper
import datetime
from typing import Optional
import sys
import threading
import time
import torch
import json
from typing import List

def check_ffmpeg():
    """Kiểm tra FFmpeg đã cài đặt chưa"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ LỖI: Không tìm thấy FFmpeg!")
        print("📥 Vui lòng cài đặt FFmpeg:")
        print("   - Windows: https://www.gyan.dev/ffmpeg/builds/")
        print("   - Thêm vào PATH hoặc đặt trong thư mục script")
        sys.exit(1)


def check_gpu():
    """Kiểm tra GPU và CUDA"""
    try:
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_count = torch.cuda.device_count()
            print(f"✅ GPU được phát hiện: {gpu_name} (x{gpu_count})")
            return True
        else:
            print("⚠️  Không tìm thấy GPU, sẽ dùng CPU (chậm hơn)")
            return False
    except Exception as e:
        print(f"⚠️  Lỗi kiểm tra GPU: {e}")
        return False


def _get_config_path() -> str:
    """Return path to config file in user home directory."""
    home = os.path.expanduser("~")
    return os.path.join(home, ".whisper_m3u8_transcriber_config.json")


def load_recent_paths() -> List[str]:
    """Load recent paths from config file. Returns list (may be empty)."""
    cfg = _get_config_path()
    try:
        if os.path.exists(cfg):
            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
                paths = data.get("recent_paths", [])
                # keep only strings and existing ones are optional
                return [p for p in paths if isinstance(p, str)]
    except Exception:
        pass
    return []


def save_recent_paths(paths: List[str]) -> None:
    """Save recent paths list to config file."""
    cfg = _get_config_path()
    try:
        data = {"recent_paths": paths}
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_recent_path(path: str, max_entries: int = 10) -> None:
    """Add a path to recent list (move to front), cap to max_entries."""
    try:
        path = os.path.abspath(path)
        paths = load_recent_paths()
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        # remove duplicates and cap
        seen = []
        out = []
        for p in paths:
            if p not in seen:
                seen.append(p)
                out.append(p)
            if len(out) >= max_entries:
                break
        save_recent_paths(out)
    except Exception:
        pass


def validate_url(url: str) -> bool:
    """Kiểm tra URL hợp lệ"""
    return url.startswith(("http://", "https://")) and ".m3u8" in url.lower()

def download_from_m3u8(m3u8_url: str, output_path: str = "video.mp4") -> str:
    print("⬇️  Đang tải video từ m3u8...")
    try:
        # Bỏ qua probe - chỉ tải trực tiếp (probe thường bị hang với m3u8 từ xa)
        # Thay vào đó, ta sẽ lấy duration từ output của tải xuống
        print("   Bắt đầu tải...")
        
        # Now download with progress - bỏ -progress để tránh hang
        cmd = [
            "ffmpeg", "-y",
            "-i", m3u8_url,
            "-c", "copy",
            "-progress", "pipe:1",
            output_path
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        last_time = 0
        duration = 0
        duration_found = False
        spinner = Spinner("   Đang tải...")
        spinner.start()
        
        # Thread để đọc stderr và tìm duration
        def read_stderr():
            nonlocal duration, duration_found
            try:
                for line in process.stderr:
                    if "Duration:" in line and not duration_found:
                        try:
                            time_str = line.split("Duration:")[1].split(",")[0].strip()
                            h, m, s = time_str.split(":")
                            duration = int(h) * 3600 + int(m) * 60 + float(s)
                            duration_found = True
                            spinner.stop()
                            print(f"   Độ dài video: {int(duration)}s")
                            spinner.start()
                        except:
                            pass
            except:
                pass
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                
                # Parse progress output: out_time_ms=123456
                if line.startswith("out_time_ms="):
                    try:
                        time_ms = int(line.split("=")[1])
                        current_time = time_ms / 1_000_000  # Convert to seconds
                        
                        if current_time > last_time and duration_found:
                            last_time = current_time
                            spinner.stop()
                            if duration > 0:
                                # Show progress bar with %
                                print_progress(int(current_time), int(duration), prefix='Tải video')
                            else:
                                # Just show time if duration unknown
                                mins = int(current_time // 60)
                                secs = current_time % 60
                                print(f"\r⬇️  Tải video: {mins:02d}:{secs:06.3f}", end='', flush=True)
                            spinner.start()
                    except:
                        pass
        finally:
            spinner.stop()
        
        return_code = process.wait()
        stderr_thread.join(timeout=1)
        
        if return_code != 0:
            stderr_output = process.stderr.read() if process.stderr else ""
            raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr_output)
        
        print(f"✅ Tải video thành công")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"\n❌ LỖI: Không thể tải video từ URL: {m3u8_url}")
        print(f"💡 Gợi ý: Kiểm tra URL m3u8 và kết nối internet")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Chi tiết: {str(e.stderr)[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ LỖI: {str(e)}")
        sys.exit(1)


def extract_audio(video_path: str, audio_path: str = "audio.wav") -> str:
    print("🎧  Đang tách audio...")
    try:
        # Get duration từ video info
        probe_cmd = [
            "ffmpeg", "-i", video_path,
            "-f", "null", "-"
        ]
        
        duration = 0
        try:
            # Timeout 10 giây cho probe
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            output = probe_result.stderr if probe_result.stderr else ""
            for line in output.split('\n'):
                if "Duration:" in line:
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = time_str.split(":")
                    duration = int(h) * 3600 + int(m) * 60 + float(s)
                    break
        except subprocess.TimeoutExpired:
            print("   ⚠️  Timeout khi lấy duration, sẽ hiển thị tiến độ theo thời gian")
            duration = 0
        except Exception as e:
            print(f"   ⚠️  Lỗi nhỏ khi probe: {e}")
            duration = 0
        
        # Extract audio with progress
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", "-progress", "pipe:1", audio_path
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True, bufsize=1)
        
        spinner = Spinner("   Tách audio...")
        spinner.start()
        
        last_time = 0
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                
                # Parse progress output: out_time_ms=123456
                if line.startswith("out_time_ms="):
                    try:
                        time_ms = int(line.split("=")[1])
                        current_time = time_ms / 1_000_000  # Convert to seconds
                        
                        if current_time > last_time:
                            last_time = current_time
                            spinner.stop()
                            
                            if duration > 0:
                                print_progress(int(current_time), int(duration), prefix='Tách audio')
                            else:
                                mins = int(current_time // 60)
                                secs = current_time % 60
                                print(f"\r🎧  Tách audio: {mins:02d}:{secs:06.3f}", end='', flush=True)
                            
                            spinner.start()
                    except:
                        pass
        finally:
            spinner.stop()
        
        return_code = process.wait(timeout=300)  # 5 min timeout
        
        if return_code != 0:
            try:
                stderr = process.stderr.read()
            except:
                stderr = ""
            raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr)
        
        print(f"✅ Tách audio thành công")
        return audio_path
    except subprocess.TimeoutExpired:
        print(f"\n❌ LỖI: Timeout khi tách audio (quá 5 phút)")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ LỖI: Không thể tách audio từ video")
        print(f"💡 Gợi ý: Kiểm tra file video có lỗi không")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ LỖI: {str(e)}")
        sys.exit(1)


def _format_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


def result_to_vtt(result: dict) -> str:
    if isinstance(result.get("vtt"), str):
        return result["vtt"]

    segments = result.get("segments") or []
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp(seg.get("start", 0.0))
        end = _format_timestamp(seg.get("end", 0.0))
        text = seg.get("text", "").strip()
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def print_progress(current: int, total: int, prefix: str = '', bar_length: int = 40) -> None:
    """In-place progress bar for console.

    Args:
        current: current completed count
        total: total count
        prefix: optional prefix message
        bar_length: length of progress bar in characters
    """
    if total <= 0:
        return
    percent = float(current) / float(total)
    filled = int(bar_length * percent)
    # use ASCII-safe characters to avoid encoding issues on Windows consoles
    bar = '=' * filled + '-' * (bar_length - filled)
    # \r to overwrite the same line
    try:
        print(f"\r{prefix} |{bar}| {current}/{total} ({percent*100:5.1f}%)", end='', flush=True)
    except UnicodeEncodeError:
        # fallback without special formatting
        print(f"\r{prefix} [{current}/{total}] {percent*100:5.1f}%", end='', flush=True)
    if current >= total:
        print()


class Spinner:
    """Simple spinner to show activity for long-running subprocesses."""
    def __init__(self, message: str = ''):
        self._running = False
        self._thread = None
        self.message = message

    def _spin(self):
        chars = ['|', '/', '-', '\\']
        idx = 0
        while self._running:
            print(f"\r{self.message} {chars[idx % len(chars)]}", end='', flush=True)
            idx += 1
            time.sleep(0.12)
        # clear line after stop
        print('\r' + ' ' * (len(self.message) + 4) + '\r', end='', flush=True)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join()


def transcribe_audio(audio_path: str, model_name: str = "small", lang: Optional[str] = None, task: str = "transcribe", use_gpu: bool = True) -> dict:
    print("🧠  Đang nhận dạng giọng nói bằng Whisper...")
    try:
        # Xác định device
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        print(f"   📱 Dùng: {device.upper()}")
        
        # Load model với device
        model = whisper.load_model(model_name, device=device)
        
        kwargs = {"task": task, "verbose": True}
        if lang:
            kwargs["language"] = lang
        
        result = model.transcribe(audio_path, **kwargs)
        return result
    except Exception as e:
        print(f"\n❌ LỖI: Không thể nhận dạng giọng nói")
        print(f"Chi tiết: {e}")
        sys.exit(1)


def save_subtitles(result: dict, output_vtt: str = "subtitle.vtt") -> None:
    print("💾  Đang lưu phụ đề...")
    vtt_text = result_to_vtt(result)
    with open(output_vtt, "w", encoding="utf-8") as f:
        f.write(vtt_text)
    print(f"✅  Đã tạo xong: {output_vtt}")


def extract_thumbnails(video_path: str, output_dir: str, interval: int = 5, thumb_width: int = 160, thumb_height: int = 90, cols: int = 10, image_format: str = "webp") -> dict:
    """
    Tạo sprite sheet từ video - tất cả thumbnails trong 1 ảnh duy nhất
    
    Args:
        video_path: Đường dẫn đến file video
        output_dir: Thư mục lưu sprite sheet
        interval: Khoảng thời gian giữa các thumbnail (giây)
        thumb_width: Chiều rộng mỗi thumbnail
        thumb_height: Chiều cao mỗi thumbnail
        cols: Số cột trong sprite sheet
        image_format: Định dạng ảnh ('webp' hoặc 'jpg')
    
    Returns:
        Dict chứa thông tin sprite sheet và timestamps
    """
    print(f"🖼️  Đang tạo sprite sheet (mỗi {interval}s, định dạng: {image_format.upper()})...")
    
    # Tạo thư mục thumbnails
    thumb_dir = os.path.join(output_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    
    try:
        # Lấy độ dài video
        probe_cmd = [
            "ffmpeg", "-i", video_path,
            "-f", "null", "-"
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        # Parse duration từ stderr
        duration = 0
        output = result.stderr if result.stderr else ""
        for line in output.split('\n'):
            if "Duration:" in line:
                time_str = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = time_str.split(":")
                duration = int(h) * 3600 + int(m) * 60 + float(s)
                break
        
        if duration == 0:
            print("⚠️  Không thể xác định độ dài video")
            return {}
        
        print(f"📊  Độ dài video: {int(duration)}s")
        
        # Tính số thumbnails cần tạo
        timestamps = list(range(0, int(duration), interval))
        thumb_count = len(timestamps)
        
        if thumb_count == 0:
            print("⚠️  Không có thumbnail nào để tạo")
            return {}
        
        print(f"📊  Số thumbnails: {thumb_count}")
        
        # Tạo các thumbnail riêng lẻ trước (tạm thời)
        temp_thumbs = []
        temp_dir = os.path.join(thumb_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Show progress while extracting individual thumbnails
        print(f"📊  Tạo {thumb_count} thumbnails... (mỗi {interval}s)")
        print_progress(0, thumb_count, prefix='Tạo thumbnails')

        for i, timestamp in enumerate(timestamps):
            thumb_filename = f"thumb{i:04d}.jpg"
            thumb_path = os.path.join(temp_dir, thumb_filename)

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={thumb_width}:{thumb_height}",
                "-q:v", "2",
                thumb_path
            ]

            subprocess.run(cmd, capture_output=True, check=True)
            temp_thumbs.append(thumb_path)
            # Update console progress
            print_progress(i + 1, thumb_count, prefix='Tạo thumbnails')

        print(f"✅  Đã tạo {len(temp_thumbs)} thumbnails tạm")
        
        # Tạo sprite sheet từ các thumbnails
        rows = (thumb_count + cols - 1) // cols  # Làm tròn lên
        sprite_width = cols * thumb_width
        sprite_height = rows * thumb_height
        sprite_filename = f"sprite.{image_format}"
        sprite_path = os.path.join(thumb_dir, sprite_filename)
        
        # Sử dụng FFmpeg để tạo sprite sheet với tile filter (tối ưu cho video dài)
        # Tile filter xếp các ảnh vào lưới một cách hiệu quả hơn xstack
        cmd = [
            "ffmpeg", "-y",
            "-i", os.path.join(temp_dir, "thumb%04d.jpg"),
            "-vf", f"tile={cols}x{rows}:margin=0:padding=0",
        ]
        
        # Tùy chọn encoding tùy theo định dạng
        if image_format.lower() == "webp":
            cmd.extend(["-quality", "90"])  # WebP quality (0-100)
        else:
            cmd.extend(["-q:v", "2"])  # JPEG quality (2-31, thấp hơn = tốt hơn)
        
        cmd.append(sprite_path)
        
        # Run sprite creation with a spinner to indicate activity (can take time)
        spinner = Spinner(f"🎨  Ghép sprite sheet ({sprite_width}x{sprite_height})...")
        spinner.start()
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        finally:
            spinner.stop()

        print(f"✅  Đã tạo sprite sheet: {sprite_filename}")
        
        # Xóa các thumbnails tạm
        print("🧹  Đang xóa thumbnails tạm...")
        for thumb in temp_thumbs:
            if os.path.exists(thumb):
                os.remove(thumb)
        
        # Xóa thư mục temp
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        
        # Tạo thông tin sprite sheet
        sprite_info = {
            "sprite_path": sprite_path,
            "sprite_filename": sprite_filename,
            "relative_path": f"thumbnails/{sprite_filename}",
            "timestamps": timestamps,
            "thumb_width": thumb_width,
            "thumb_height": thumb_height,
            "cols": cols,
            "rows": rows,
            "total_thumbs": thumb_count
        }
        
        print(f"✅  Sprite sheet: {cols} cột x {rows} hàng = {thumb_count} thumbnails")
        
        return sprite_info
        
    except subprocess.CalledProcessError as e:
        print(f"❌ LỖI: Không thể tạo sprite sheet")
        print(f"Chi tiết: {e}")
        return {}


def create_thumbnail_vtt(sprite_info: dict, output_vtt: str, interval: int = 5, cdn_url: str = None) -> None:
    """
    Tạo file VTT cho sprite sheet thumbnails
    
    Args:
        sprite_info: Dict chứa thông tin sprite sheet
        output_vtt: Đường dẫn file VTT đầu ra
        interval: Khoảng thời gian giữa các thumbnail (giây)
        cdn_url: URL CDN cho sprite sheet (nếu có), ví dụ: https://cdn.example.com/thumbs/sprite.jpg
                 Nếu None, sẽ dùng đường dẫn tương đối
    """
    print("💾  Đang tạo file VTT cho sprite sheet...")
    
    if not sprite_info:
        print("⚠️  Không có thông tin sprite sheet")
        return
    
    lines = ["WEBVTT", ""]
    
    timestamps = sprite_info["timestamps"]
    thumb_width = sprite_info["thumb_width"]
    thumb_height = sprite_info["thumb_height"]
    cols = sprite_info["cols"]
    
    # URL cho sprite sheet
    if cdn_url:
        sprite_url = cdn_url
    else:
        sprite_url = sprite_info["relative_path"]
    
    for i, timestamp in enumerate(timestamps):
        start_time = timestamp
        end_time = start_time + interval
        
        # Format thời gian: MM:SS.mmm (phút:giây.mili)
        start_mins = int(start_time // 60)
        start_secs = start_time % 60
        start_str = f"{start_mins:02d}:{start_secs:06.3f}"
        
        end_mins = int(end_time // 60)
        end_secs = end_time % 60
        end_str = f"{end_mins:02d}:{end_secs:06.3f}"
        
        # Tính vị trí của thumbnail trong sprite sheet
        row = i // cols
        col = i % cols
        x = col * thumb_width
        y = row * thumb_height
        
        # Format: URL#xywh=x,y,width,height
        xywh = f"#xywh={x},{y},{thumb_width},{thumb_height}"
        
        lines.append(f"{start_str} --> {end_str}")
        lines.append(f"{sprite_url}{xywh}")
        lines.append("")
    
    with open(output_vtt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅  Đã tạo file VTT sprite sheet: {output_vtt}")
    print(f"ℹ️   Sprite URL: {sprite_url}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Tải video từ m3u8, tách audio và nhận dạng giọng nói bằng Whisper")
    parser.add_argument("--m3u8", help="URL đến playlist m3u8 (nếu bỏ qua, bạn sẽ được nhắc)")
    parser.add_argument("-l", "--language", help="Mã ngôn ngữ để truyền cho Whisper (ví dụ: 'vi', 'en'). Nếu bỏ qua, bạn sẽ được nhắc.")
    parser.add_argument("-m", "--model", default="small", help="Mô hình Whisper để sử dụng (mặc định: small)")
    parser.add_argument("-o", "--output-prefix", default="movie", help="Tiền tố tên tệp đầu ra (mặc định: movie)")
    parser.add_argument("-d", "--output-dir", help="Đường dẫn thư mục đầu ra (nếu bỏ qua, bạn sẽ được nhắc)")
    parser.add_argument("-g", "--group-name", help="(Tùy chọn) Tên thư mục mới để nhóm các file. Nếu bỏ qua, sẽ hỏi người dùng.")
    parser.add_argument("--save-video", action="store_true", help="Lưu file video (mặc định: lưu tất cả nếu không chỉ định)")
    parser.add_argument("--save-audio", action="store_true", help="Lưu file audio (mặc định: lưu tất cả nếu không chỉ định)")
    parser.add_argument("--save-vtt", action="store_true", help="Lưu file VTT phụ đề (mặc định: lưu tất cả nếu không chỉ định)")
    parser.add_argument("--create-thumbnails", action="store_true", help="Tạo sprite sheet thumbnails và VTT")
    parser.add_argument("--thumbnail-interval", type=int, default=5, help="Khoảng thời gian giữa các thumbnail (giây, mặc định: 5)")
    parser.add_argument("--thumb-width", type=int, default=160, help="Chiều rộng mỗi thumbnail (px, mặc định: 160)")
    parser.add_argument("--thumb-height", type=int, default=90, help="Chiều cao mỗi thumbnail (px, mặc định: 90)")
    parser.add_argument("--thumb-cols", type=int, default=10, help="Số cột trong sprite sheet (mặc định: 10)")
    parser.add_argument("--thumb-format", choices=["webp", "jpg"], default="webp", help="Định dạng ảnh sprite sheet (mặc định: webp)")
    parser.add_argument("--cdn-url", help="URL CDN cho sprite sheet (ví dụ: https://cdn.example.com/thumbs/sprite.webp)")
    parser.add_argument("--no-gpu", action="store_true", help="Bắt buộc dùng CPU thay vì GPU")
    args = parser.parse_args()

    # Kiểm tra FFmpeg
    check_ffmpeg()
    
    # Kiểm tra GPU
    use_gpu = not args.no_gpu
    check_gpu()

    # Nhập và validate URL
    m3u8_link = args.m3u8
    while True:
        if not m3u8_link:
            m3u8_link = input("🔗 Nhập link .m3u8: ").strip()
        
        if validate_url(m3u8_link):
            break
        else:
            print("❌ URL không hợp lệ! URL phải:")
            print("   - Bắt đầu bằng http:// hoặc https://")
            print("   - Chứa đuôi .m3u8")
            print("   Ví dụ: https://example.com/video/index.m3u8\n")
            m3u8_link = None

    # Chọn thư mục lưu trữ
    output_dir = args.output_dir
    if not output_dir:
        recent = load_recent_paths()
        print("\n📂 Chọn nơi lưu trữ:")
        print("1. Thư mục hiện tại")
        if recent:
            print("2. Chọn từ các đường dẫn đã dùng trước (gợi ý)")
            print("3. Nhập đường dẫn tùy chỉnh")
            dir_choice = input("👉 Chọn (1-3): ").strip()
        else:
            print("2. Nhập đường dẫn tùy chỉnh")
            dir_choice = input("👉 Chọn (1-2): ").strip()

        if dir_choice == "1":
            output_dir = os.getcwd()
            print(f"✅ Sẽ lưu vào thư mục hiện tại: {output_dir}")
            add_recent_path(output_dir)

        elif dir_choice == "2" and recent:
            # show recent list
            print("\n📁 Đường dẫn đã dùng trước:")
            for i, p in enumerate(recent, start=1):
                print(f"  {i}. {p}")
            print(f"  {len(recent)+1}. Nhập đường dẫn mới")
            sel = input(f"👉 Chọn (1-{len(recent)+1}): ").strip()
            try:
                idx = int(sel)
                if 1 <= idx <= len(recent):
                    output_dir = recent[idx-1]
                    print(f"✅ Chọn: {output_dir}")
                    # Ensure exists or ask to create
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                    except Exception:
                        print("⚠️  Không thể tạo hoặc truy cập thư mục đã chọn")
                    add_recent_path(output_dir)
                else:
                    # fallthrough to custom input
                    output_dir = None
            except ValueError:
                output_dir = None

        else:
            # custom path input (either choice 2 when no recent, or explicit 3, or fallback)
            while True:
                output_dir = input("💾 Nhập đường dẫn thư mục (ví dụ: E:\\Videos\\Subtitles): ").strip()
                # Xóa dấu ngoặc kép nếu user copy-paste từ Windows Explorer
                output_dir = output_dir.strip('"').strip("'")
                # Tạo thư mục nếu chưa tồn tại
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"✅ Sẽ lưu vào: {output_dir}")
                    add_recent_path(output_dir)
                    break
                except Exception as e:
                    print(f"❌ Đường dẫn không hợp lệ: {e}")
                    print("Vui lòng nhập lại!\n")
    else:
        # Tạo thư mục nếu được truyền qua CLI
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"✅ Sẽ lưu vào: {output_dir}")
            add_recent_path(output_dir)
        except Exception as e:
            print(f"❌ Không thể tạo thư mục đầu ra đã truyền: {e}")
            print("Sẽ dùng thư mục hiện tại thay thế.")
            output_dir = os.getcwd()
            add_recent_path(output_dir)

    # --- Tùy chọn nhóm 3 file vào thư mục con mới ---
    group_name = args.group_name
    group_dir = None
    # Nếu chưa truyền --group-name, hỏi người dùng
    if not group_name:
        choose_group = input("\n📦 Bạn có muốn nhóm 3 file (video/audio/vtt) vào thư mục mới không? (y/N): ").strip().lower()
        if choose_group == "y":
            group_name = input("📛 Nhập tên thư mục nhóm (để trống sẽ dùng tên theo thời điểm): ").strip()
            # loại bỏ dấu ngoặc kép nếu copy-paste
            group_name = group_name.strip('"').strip("'")
            if not group_name:
                group_name = f"group_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if group_name:
        try:
            group_dir = os.path.join(output_dir, group_name)
            os.makedirs(group_dir, exist_ok=True)
            print(f"✅ Sẽ lưu các file vào: {group_dir}")
        except Exception as e:
            print(f"❌ Không thể tạo thư mục nhóm: {e}")
            print("Sẽ lưu vào thư mục đầu ra chính.")
            group_dir = None

    # base_dir là nơi thực tế các file sẽ được ghi
    base_dir = group_dir if group_dir else output_dir

    # --- Tùy chọn chọn file cần lưu ---
    # Kiểm tra xem người dùng đã truyền CLI flags không
    has_save_flags = args.save_video or args.save_audio or args.save_vtt
    
    if has_save_flags:
        # Nếu có CLI flags, sử dụng chúng
        save_video = args.save_video
        save_audio = args.save_audio
        save_vtt = args.save_vtt
    else:
        # Nếu không có, hỏi người dùng qua menu
        print("\n" + "="*50)
        print("💾 CHỌN FILE CẦN LƯU")
        print("="*50)
        print("1. Video + Audio + VTT (lưu tất cả)")
        print("2. Chỉ Video")
        print("3. Chỉ Audio")
        print("4. Chỉ VTT (Phụ đề)")
        print("5. Video + Audio")
        print("6. Video + VTT")
        print("7. Audio + VTT")
        print("="*50)
        
        choice = input("👉 Nhập lựa chọn (1-7): ").strip()
        
        save_video = False
        save_audio = False
        save_vtt = False
        
        if choice == "1":
            save_video = save_audio = save_vtt = True
        elif choice == "2":
            save_video = True
        elif choice == "3":
            save_audio = True
        elif choice == "4":
            save_vtt = True
        elif choice == "5":
            save_video = save_audio = True
        elif choice == "6":
            save_video = save_vtt = True
        elif choice == "7":
            save_audio = save_vtt = True
        else:
            print("⚠️  Lựa chọn không hợp lệ, sẽ lưu tất cả file")
            save_video = save_audio = save_vtt = True
        
        # Hiển thị lựa chọn
        files_to_save = []
        if save_video:
            files_to_save.append("Video")
        if save_audio:
            files_to_save.append("Audio")
        if save_vtt:
            files_to_save.append("VTT (Phụ đề)")
        
        if files_to_save:
            print(f"✅ Sẽ lưu: {', '.join(files_to_save)}")
        else:
            print("⚠️  Không có file nào được chọn để lưu!")
            print("    (Video và Audio vẫn sẽ được tải về để xử lý, sau đó sẽ bị xóa)")


    # --- Tùy chọn tạo thumbnails ---
    create_thumbnails = args.create_thumbnails
    thumbnail_interval = args.thumbnail_interval
    thumb_width = args.thumb_width
    thumb_height = args.thumb_height
    thumb_cols = args.thumb_cols
    thumb_format = args.thumb_format
    cdn_url = args.cdn_url
    
    if not create_thumbnails:
        create_thumb_choice = input("\n🖼️  Bạn có muốn tạo sprite sheet thumbnails từ video không? (y/N): ").strip().lower()
        if create_thumb_choice == "y":
            create_thumbnails = True
            
            # Hỏi khoảng thời gian
            interval_input = input(f"⏱️  Nhập khoảng thời gian giữa các thumbnail (giây, mặc định {thumbnail_interval}): ").strip()
            if interval_input.isdigit() and int(interval_input) > 0:
                thumbnail_interval = int(interval_input)
            
            # Hỏi kích thước thumbnail
            print(f"\nℹ️  Kích thước mặc định: {thumb_width}x{thumb_height}px")
            size_input = input("📐 Thay đổi kích thước? (Nhấn Enter để giữ mặc định hoặc nhập 'w,h' ví dụ: 160,90): ").strip()
            if size_input and "," in size_input:
                try:
                    w, h = size_input.split(",")
                    thumb_width = int(w.strip())
                    thumb_height = int(h.strip())
                    print(f"✅ Đã đặt kích thước: {thumb_width}x{thumb_height}px")
                except:
                    print(f"⚠️  Định dạng không hợp lệ, giữ mặc định {thumb_width}x{thumb_height}px")
            
            # Hỏi số cột
            cols_input = input(f"📊 Số cột trong sprite sheet (mặc định {thumb_cols}): ").strip()
            if cols_input.isdigit() and int(cols_input) > 0:
                thumb_cols = int(cols_input)
            
            # Hỏi định dạng ảnh
            print(f"\n🎨 Chọn định dạng ảnh:")
            print(f"  1. WebP (nhẹ hơn, chất lượng tốt - khuyến nghị)")
            print(f"  2. JPG (tương thích rộng)")
            format_choice = input(f"👉 Chọn (1-2, mặc định 1): ").strip()
            if format_choice == "2":
                thumb_format = "jpg"
            else:
                thumb_format = "webp"
            
            # Hỏi CDN URL (tùy chọn)
            cdn_input = input(f"🌐 URL CDN cho sprite sheet (Nhấn Enter để bỏ qua): ").strip()
            if cdn_input:
                cdn_url = cdn_input
            
            print(f"✅ Sẽ tạo sprite sheet: {thumb_cols} cột, {thumb_width}x{thumb_height}px, {thumb_format.upper()}, mỗi {thumbnail_interval}s")
            if cdn_url:
                print(f"✅ Sử dụng CDN URL: {cdn_url}")

    # Menu chọn ngôn ngữ (giữ nguyên như cũ)
    language = args.language
    if not language:
        print("\n" + "="*50)
        print("🌍  CHỌN NGÔN NGỮ NHẬN DẠNG")
        print("="*50)
        languages = [
            ("1", "🇻🇳 Tiếng Việt", "vi"),
            ("2", "🇺🇸 Tiếng Anh", "en"),
            ("3", "🇯🇵 Tiếng Nhật", "ja"),
            ("4", "🇰🇷 Tiếng Hàn", "ko"),
            ("5", "🇨🇳 Tiếng Trung", "zh"),
            ("6", "🇹🇭 Tiếng Thái", "th"),
            ("7", "🇮🇩 Tiếng Indonesia", "id"),
            ("8", "🤖 Tự động nhận diện", "auto"),
            ("0", "➕ Nhập mã khác", "custom"),
        ]
        
        for num, name, _ in languages:
            print(f"  {num}. {name}")
        print("="*50)
        
        choice = input("👉 Nhập lựa chọn của bạn: ").strip()
        
        selected = next((lang for lang in languages if lang[0] == choice), None)
        
        if selected:
            if selected[2] == "custom":
                language = input("💬 Nhập mã ngôn ngữ (ví dụ: fr, de, es): ").strip() or None
                if language:
                    print(f"✅ Đã chọn ngôn ngữ: {language}")
            elif selected[2] == "auto":
                language = None
                print("✅ Sẽ tự động nhận diện ngôn ngữ")
            else:
                language = selected[2]
                print(f"✅ Đã chọn: {selected[1]}")
        else:
            print("⚠️  Lựa chọn không hợp lệ, sẽ dùng auto-detect")
            language = None

    print("\n" + "="*50)
    print("🚀 BẮT ĐẦU XỬ LÝ")
    print("="*50)
    print("ℹ️  Lưu ý: Video và Audio sẽ được tải về để xử lý")
    print("    Các file không được chọn sẽ tự động xóa sau khi hoàn tất")
    print("="*50 + "\n")

    # Tạo đường dẫn file đầy đủ (ghi vào base_dir - có thể là thư mục nhóm mới)
    video_path = os.path.join(base_dir, "video.mp4")
    audio_path = os.path.join(base_dir, "audio.wav")
    vtt_path = os.path.join(base_dir, f"{args.output_prefix}_{language or 'auto'}.vtt")
    thumbnail_vtt_path = os.path.join(base_dir, "thumbnails.vtt")

    # Xử lý
    video = download_from_m3u8(m3u8_link, video_path)
    audio = extract_audio(video, audio_path)
    result = transcribe_audio(audio, model_name=args.model, lang=language, use_gpu=use_gpu)
    
    # Lưu các file theo lựa chọn của người dùng
    if save_vtt:
        save_subtitles(result, vtt_path)
    
    # Tạo sprite sheet thumbnails nếu được yêu cầu
    sprite_info = {}
    if create_thumbnails:
        sprite_info = extract_thumbnails(video_path, base_dir, thumbnail_interval, thumb_width, thumb_height, thumb_cols, thumb_format)
        if sprite_info:
            create_thumbnail_vtt(sprite_info, thumbnail_vtt_path, thumbnail_interval, cdn_url)
    
    # Dọn dẹp các file không cần thiết
    print("\n🧹 Đang dọn dẹp...")
    
    # Xóa file video nếu người dùng không muốn lưu
    if not save_video and os.path.exists(video_path):
        os.remove(video_path)
        print("   ❌ Đã xóa file video tạm")
    
    # Xóa file audio nếu người dùng không muốn lưu
    if not save_audio and os.path.exists(audio_path):
        os.remove(audio_path)
        print("   ❌ Đã xóa file audio tạm")
    
    print(f"\n{'='*50}")
    print(f"✅ HOÀN TẤT!")
    print(f"📁 Thư mục: {base_dir}")
    
    # Hiển thị file đã lưu
    files_saved = []
    if save_video and os.path.exists(video_path):
        files_saved.append(f"📹 Video: video.mp4")
    if save_audio and os.path.exists(audio_path):
        files_saved.append(f"🎵 Audio: audio.wav")
    if save_vtt and os.path.exists(vtt_path):
        files_saved.append(f"📝 Phụ đề: {os.path.basename(vtt_path)}")
    if sprite_info and os.path.exists(thumbnail_vtt_path):
        sprite_file = sprite_info.get("sprite_filename", "sprite.jpg")
        thumb_count = sprite_info.get("total_thumbs", 0)
        files_saved.append(f"🖼️  Sprite sheet: {sprite_file} ({thumb_count} thumbnails) + thumbnails.vtt")
    
    for file_info in files_saved:
        print(file_info)
    
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()