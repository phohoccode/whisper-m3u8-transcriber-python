import os
import subprocess
import argparse
import whisper
import datetime
from typing import Optional
import sys

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


def validate_url(url: str) -> bool:
    """Kiểm tra URL hợp lệ"""
    return url.startswith(("http://", "https://")) and ".m3u8" in url.lower()

def download_from_m3u8(m3u8_url: str, output_path: str = "video.mp4") -> str:
    print("⬇️  Đang tải video từ m3u8...")
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", m3u8_url,
            "-c", "copy",
            output_path
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"\n❌ LỖI: Không thể tải video từ URL: {m3u8_url}")
        print(f"Chi tiết lỗi: {e.stderr}")
        sys.exit(1)


def extract_audio(video_path: str, audio_path: str = "audio.wav") -> str:
    print("🎧  Đang tách audio...")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", audio_path
        ], check=True, capture_output=True)
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"\n❌ LỖI: Không thể tách audio từ video")
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


def transcribe_audio(audio_path: str, model_name: str = "small", lang: Optional[str] = None, task: str = "transcribe") -> dict:
    print("🧠  Đang nhận dạng giọng nói bằng Whisper...")
    try:
        model = whisper.load_model(model_name)
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
        
        print(f"✅  Đã tạo {len(temp_thumbs)} thumbnails tạm")
        
        # Tạo sprite sheet từ các thumbnails
        rows = (thumb_count + cols - 1) // cols  # Làm tròn lên
        sprite_width = cols * thumb_width
        sprite_height = rows * thumb_height
        sprite_filename = f"sprite.{image_format}"
        sprite_path = os.path.join(thumb_dir, sprite_filename)
        
        print(f"🎨  Đang ghép sprite sheet ({sprite_width}x{sprite_height})...")
        
        # Sử dụng FFmpeg để tạo sprite sheet
        # Tạo filter complex để sắp xếp các ảnh vào grid
        inputs = []
        for thumb in temp_thumbs:
            inputs.extend(["-i", thumb])
        
        # Tạo filter complex
        filter_parts = []
        for i in range(thumb_count):
            filter_parts.append(f"[{i}:v]")
        
        # xstack filter để sắp xếp theo grid
        xstack_inputs = "".join(filter_parts)
        
        # Tính layout cho xstack
        layout = []
        for i in range(thumb_count):
            row = i // cols
            col = i % cols
            x = col * thumb_width
            y = row * thumb_height
            layout.append(f"{x}_{y}")
        
        layout_str = "|".join(layout)
        
        filter_complex = f"{xstack_inputs}xstack=inputs={thumb_count}:layout={layout_str}:fill=black[out]"
        
        # Tùy chọn encoding tùy theo định dạng
        if image_format.lower() == "webp":
            encoding_options = ["-quality", "90"]  # WebP quality (0-100)
        else:
            encoding_options = ["-q:v", "2"]  # JPEG quality (2-31, thấp hơn = tốt hơn)
        
        cmd = inputs + [
            "-filter_complex", filter_complex,
            "-map", "[out]",
        ] + encoding_options + [sprite_path]
        
        subprocess.run(["ffmpeg", "-y"] + cmd, capture_output=True, check=True)
        
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
    args = parser.parse_args()

    # Kiểm tra FFmpeg
    check_ffmpeg()

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
        print("\n📂 Chọn nơi lưu trữ:")
        print("1. Thư mục hiện tại")
        print("2. Nhập đường dẫn tùy chỉnh")
        
        dir_choice = input("👉 Chọn (1-2): ").strip()
        
        if dir_choice == "2":
            while True:
                output_dir = input("💾 Nhập đường dẫn thư mục (ví dụ: E:\\Videos\\Subtitles): ").strip()
                # Xóa dấu ngoặc kép nếu user copy-paste từ Windows Explorer
                output_dir = output_dir.strip('"').strip("'")
                
                # Tạo thư mục nếu chưa tồn tại
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"✅ Sẽ lưu vào: {output_dir}")
                    break
                except Exception as e:
                    print(f"❌ Đường dẫn không hợp lệ: {e}")
                    print("Vui lòng nhập lại!\n")
        else:
            output_dir = os.getcwd()
            print(f"✅ Sẽ lưu vào thư mục hiện tại: {output_dir}")
    else:
        # Tạo thư mục nếu được truyền qua CLI
        os.makedirs(output_dir, exist_ok=True)
        print(f"✅ Sẽ lưu vào: {output_dir}")

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
    result = transcribe_audio(audio, model_name=args.model, lang=language)
    
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