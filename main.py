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

def main() -> None:
    parser = argparse.ArgumentParser(description="Tải video từ m3u8, tách audio và nhận dạng giọng nói bằng Whisper")
    parser.add_argument("--m3u8", help="URL đến playlist m3u8 (nếu bỏ qua, bạn sẽ được nhắc)")
    parser.add_argument("-l", "--language", help="Mã ngôn ngữ để truyền cho Whisper (ví dụ: 'vi', 'en'). Nếu bỏ qua, bạn sẽ được nhắc.")
    parser.add_argument("-m", "--model", default="small", help="Mô hình Whisper để sử dụng (mặc định: small)")
    parser.add_argument("-o", "--output-prefix", default="movie", help="Tiền tố tên tệp đầu ra (mặc định: movie)")
    parser.add_argument("-d", "--output-dir", help="Đường dẫn thư mục đầu ra (nếu bỏ qua, bạn sẽ được nhắc)")  # ← MỚI
    parser.add_argument("-g", "--group-name", help="(Tùy chọn) Tên thư mục mới để nhóm 3 file (video/audio/vtt). Nếu bỏ qua, sẽ hỏi người dùng.")
    parser.add_argument("--save-video", action="store_true", help="Lưu file video (mặc định: lưu tất cả nếu không chỉ định)")
    parser.add_argument("--save-audio", action="store_true", help="Lưu file audio (mặc định: lưu tất cả nếu không chỉ định)")
    parser.add_argument("--save-vtt", action="store_true", help="Lưu file VTT phụ đề (mặc định: lưu tất cả nếu không chỉ định)")
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
        print(f"✅ Sẽ lưu: {', '.join(files_to_save)}")

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
    print("="*50 + "\n")

    # Tạo đường dẫn file đầy đủ (ghi vào base_dir - có thể là thư mục nhóm mới)
    video_path = os.path.join(base_dir, "video.mp4")
    audio_path = os.path.join(base_dir, "audio.wav")
    vtt_path = os.path.join(base_dir, f"{args.output_prefix}_{language or 'auto'}.vtt")

    # Xử lý
    video = download_from_m3u8(m3u8_link, video_path)
    audio = extract_audio(video, audio_path)
    result = transcribe_audio(audio, model_name=args.model, lang=language)
    
    # Lưu các file theo lựa chọn của người dùng
    if save_vtt:
        save_subtitles(result, vtt_path)
    
    # Xóa file video nếu người dùng không muốn lưu
    if not save_video and os.path.exists(video_path):
        os.remove(video_path)
    
    # Xóa file audio nếu người dùng không muốn lưu
    if not save_audio and os.path.exists(audio_path):
        os.remove(audio_path)
    
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
    
    for file_info in files_saved:
        print(file_info)
    
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()