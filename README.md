# Whisper m3u8 Transcriber

Công cụ tải video từ URL m3u8, tách âm thanh và nhận dạng giọng nói bằng OpenAI Whisper. Script hỗ trợ lưu lựa chọn file, nhóm kết quả vào thư mục mới, và hỗ trợ đa ngôn ngữ.

## 📋 Mục lục

1. [Tính năng](#tính-năng)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Cài đặt](#cài-đặt)
4. [Cách sử dụng](#cách-sử-dụng)
5. [Các tuỳ chọn dòng lệnh](#các-tuỳ-chọn-dòng-lệnh)
6. [Sprite Sheet Thumbnails](#sprite-sheet-thumbnails)
7. [Ví dụ sử dụng](#ví-dụ-sử-dụng)

---

## ✨ Tính năng

- ✅ Tải video từ URL m3u8
- ✅ Tách âm thanh từ video (WAV 16kHz mono)
- ✅ Nhận dạng giọng nói bằng Whisper (hỗ trợ 99+ ngôn ngữ)
- ✅ Xuất phụ đề VTT
- ✅ **Chọn lựa file cần lưu**: Video, Audio, VTT hoặc bất kỳ tổ hợp nào
- ✅ **Nhóm file vào thư mục mới**: Tự động hoặc đặt tên tuỳ chỉnh
- ✅ Hỗ trợ menu tương tác: chọn ngôn ngữ, chọn mô hình Whisper
- ✅ Tự động nhận diện ngôn ngữ
- ✅ **🆕 Tạo Sprite Sheet Thumbnails**: Tạo hình ảnh sprite sheet từ video, hỗ trợ WebP và JPG
- ✅ **🆕 VTT cho Sprite Sheet**: Tự động tạo file VTT kèm tọa độ sprite (xywh)

---

## 🖥️ Yêu cầu hệ thống

### Phần cứng

- CPU: 2+ cores (khuyến khích 4+)
- RAM: 4GB tối thiểu (8GB+ cho mô hình lớn)
- Disk: 10GB+ cho mô hình Whisper

### Phần mềm

- **Python 3.8+**
- **FFmpeg** (để xử lý video/audio)

---

## 📥 Cài đặt

### Bước 1: Cài đặt Python

Tải từ [python.org](https://www.python.org/downloads/). Chọn Python 3.8 trở lên và **nhớ tick "Add Python to PATH"** khi cài đặt.

### Bước 2: Cài đặt FFmpeg

#### Windows:

1. Tải FFmpeg từ [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (chọn **Full** release)
2. Giải nén vào thư mục (ví dụ: `C:\ffmpeg`)
3. Thêm vào PATH:

   - Mở "Edit environment variables for your account"
   - Tìm PATH, click "Edit"
   - Click "New" và thêm `C:\ffmpeg\bin`
   - Nhấn OK

4. Kiểm tra cài đặt:
   ```powershell
   ffmpeg -version
   ```

#### macOS (sử dụng Homebrew):

```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian):

```bash
sudo apt-get install ffmpeg
```

### Bước 3: Cài đặt Dependencies Python

Mở PowerShell/Terminal trong thư mục dự án và chạy:

```powershell
pip install openai-whisper
```

> Nếu bạn muốn sử dụng GPU (NVIDIA CUDA) để tăng tốc độ xử lý:
>
> ```powershell
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
> ```

---

## 🚀 Cách sử dụng

### Cách chạy đơn giản nhất (Menu tương tác)

```powershell
python .\main.py
```

Script sẽ hỏi bạn:

1. URL m3u8 hoặc đường dẫn file
2. Thư mục lưu trữ (hiện tại hoặc tuỳ chỉnh)
3. Có nhóm file vào thư mục con mới không (nhập tên thư mục)
4. **Chọn file nào cần lưu**: Video, Audio, VTT hoặc tất cả
5. Chọn ngôn ngữ nhận dạng (Việt, Anh, Nhật, Hàn, Trung, Thái, v.v.)

---

## ⚙️ Các tuỳ chọn dòng lệnh

| Tuỳ chọn               | Mô tả                              | Ví dụ                                                        |
| ---------------------- | ---------------------------------- | ------------------------------------------------------------ |
| `--m3u8`               | URL m3u8 hoặc đường dẫn file       | `--m3u8 "https://example.com/video.m3u8"`                    |
| `--output-dir`         | Thư mục lưu trữ                    | `--output-dir "E:\Videos"`                                   |
| `--group-name`         | Tên thư mục nhóm file (tuỳ chọn)   | `--group-name "bai_hoc_1"`                                   |
| `--language`           | Mã ngôn ngữ (ISO 639-1)            | `--language "vi"` (Việt), `--language "en"` (Anh)            |
| `--model`              | Mô hình Whisper                    | `--model "tiny"`, `"base"`, `"small"`, `"medium"`, `"large"` |
| `--output-prefix`      | Tiền tố tên file                   | `--output-prefix "movie"` → `movie_vi.vtt`                   |
| `--save-video`         | Lưu file video                     | Không có value, chỉ cần thêm flag                            |
| `--save-audio`         | Lưu file audio (WAV)               | Không có value, chỉ cần thêm flag                            |
| `--save-vtt`           | Lưu file phụ đề (VTT)              | Không có value, chỉ cần thêm flag                            |
| `--create-thumbnails`  | Tạo sprite sheet thumbnails        | Không có value, chỉ cần thêm flag                            |
| `--thumbnail-interval` | Khoảng cách giữa thumbnails (giây) | `--thumbnail-interval 5` (mặc định: 5)                       |
| `--thumb-width`        | Chiều rộng mỗi thumbnail (px)      | `--thumb-width 160` (mặc định: 160)                          |
| `--thumb-height`       | Chiều cao mỗi thumbnail (px)       | `--thumb-height 90` (mặc định: 90)                           |
| `--thumb-cols`         | Số cột trong sprite sheet          | `--thumb-cols 10` (mặc định: 10)                             |
| `--thumb-format`       | Định dạng ảnh sprite sheet         | `--thumb-format "webp"` hoặc `"jpg"` (mặc định: webp)        |
| `--cdn-url`            | URL CDN cho sprite sheet           | `--cdn-url "https://cdn.example.com/sprite.webp"`            |
| `--no-gpu`             | Bắt buộc dùng CPU thay vì GPU      | Không có value, chỉ cần thêm flag                            |

**Ghi chú**: Nếu bạn cung cấp các flag `--save-*`, script sẽ **chỉ lưu những file bạn chỉ định**. Nếu không cung cấp, script sẽ hỏi qua menu.

---

## �️ Sprite Sheet Thumbnails

Script có thể tự động tạo **sprite sheet thumbnails** từ video - đây là một hình ảnh duy nhất chứa nhiều ảnh nhỏ được xếp thành lưới. Rất hữu ích cho phát triển các ứng dụng video player.

### Tính năng Sprite Sheet

- 📸 Tạo thumbnails từ các khung hình của video
- 🎨 Hỗ trợ định dạng **WebP** (nhẹ, chất lượng tốt) hoặc **JPG** (tương thích rộng)
- 🔗 Tạo file **VTT** kèm theo với tọa độ xywh để sử dụng trong video player
- ⚙️ Tùy chỉnh hoàn toàn: khoảng cách, kích thước, số cột
- 🌐 Hỗ trợ URL CDN

### Cách sử dụng

#### Qua menu tương tác

```powershell
python .\main.py
```

Khi chạy, script sẽ hỏi:

```
🖼️  Bạn có muốn tạo sprite sheet thumbnails từ video không? (y/N): y
⏱️  Nhập khoảng thời gian giữa các thumbnail (giây, mặc định 5): 3
📐 Thay đổi kích thước? (Nhấn Enter để giữ mặc định hoặc nhập 'w,h' ví dụ: 160,90):
📊 Số cột trong sprite sheet (mặc định 10): 8
🎨 Chọn định dạng ảnh:
  1. WebP (nhẹ hơn, chất lượng tốt - khuyến nghị)
  2. JPG (tương thích rộng)
👉 Chọn (1-2, mặc định 1): 1
🌐 URL CDN cho sprite sheet (Nhấn Enter để bỏ qua):
```

#### Qua CLI

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --create-thumbnails `
  --thumbnail-interval 5 `
  --thumb-cols 10 `
  --thumb-format "webp"
```

### Kết quả

Sau khi hoàn tất, bạn sẽ có:

```
output-dir\
└── group-name\
    ├── video.mp4 (nếu chọn lưu)
    ├── audio.wav (nếu chọn lưu)
    ├── movie_vi.vtt (phụ đề)
    ├── thumbnails.vtt (VTT cho sprite sheet)
    └── thumbnails\
        └── sprite.webp (hoặc sprite.jpg)
```

### File VTT cho Sprite Sheet

File `thumbnails.vtt` tự động sinh ra với tọa độ xywh:

```vtt
WEBVTT

00:00:00.000 --> 00:00:05.000
thumbnails/sprite.webp#xywh=0,0,160,90

00:00:05.000 --> 00:00:10.000
thumbnails/sprite.webp#xywh=160,0,160,90

00:00:10.000 --> 00:00:15.000
thumbnails/sprite.webp#xywh=320,0,160,90
```

Bạn có thể dùng file này với các video player hỗ trợ CORS, hoặc tùy chỉnh CDN URL:

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --create-thumbnails `
  --cdn-url "https://cdn.example.com/sprites/sprite.webp"
```

### Gợi ý

- **WebP**: Dung lượng nhỏ hơn ~40% so với JPG, phù hợp cho web modern
- **JPG**: Tương thích rộng, phù hợp cho các trình duyệt cũ
- **Khoảng cách nhỏ hơn** (ví dụ: 2-3s): Nhiều thumbnails nhưng chi tiết cao
- **Khoảng cách lớn hơn** (ví dụ: 10s+): Ít thumbnails nhưng file nhẹ hơn

---

## �📌 Ví dụ sử dụng

### Ví dụ 1: Lưu tất cả file với tên thư mục tuỳ chỉnh

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\MyVideos" `
  --group-name "lesson_1" `
  --language "vi" `
  --model "small"
```

**Kết quả**:

```
E:\MyVideos\
└── lesson_1\
    ├── video.mp4
    ├── audio.wav
    └── movie_vi.vtt
```

---

### Ví dụ 2: Chỉ lưu phụ đề (không video/audio)

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\Subtitles" `
  --group-name "vietnamese_subs" `
  --save-vtt `
  --language "vi"
```

**Kết quả**:

```
E:\Subtitles\
└── vietnamese_subs\
    └── movie_vi.vtt
```

---

### Ví dụ 3: Lưu video + audio, tự động nhóm với timestamp

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --save-video `
  --save-audio `
  --language "en"
```

**Kết quả** (thư mục mặc định với tên timestamp):

```
<current-dir>\
└── group_20251027_153045\
    ├── video.mp4
    └── audio.wav
```

---

### Ví dụ 4: Menu tương tác (không CLI flags)

```powershell
python .\main.py
```

Script sẽ hỏi từng bước:

```
🔗 Nhập link .m3u8: https://example.com/stream.m3u8
📂 Chọn nơi lưu trữ:
1. Thư mục hiện tại
2. Nhập đường dẫn tùy chỉnh
👉 Chọn (1-2): 1

📦 Bạn có muốn nhóm 3 file (video/audio/vtt) vào thư mục mới không? (y/N): y
📛 Nhập tên thư mục nhóm (để trống sẽ dùng tên theo thời điểm): my_video

💾 CHỌN FILE CẦN LƯU
==================================================
1. Video + Audio + VTT (lưu tất cả)
2. Chỉ Video
3. Chỉ Audio
4. Chỉ VTT (Phụ đề)
5. Video + Audio
6. Video + VTT
7. Audio + VTT
==================================================
👉 Nhập lựa chọn (1-7): 1

🖼️  Bạn có muốn tạo sprite sheet thumbnails từ video không? (y/N): y
⏱️  Nhập khoảng thời gian giữa các thumbnail (giây, mặc định 5): 5
📐 Thay đổi kích thước? (Nhấn Enter để giữ mặc định hoặc nhập 'w,h' ví dụ: 160,90):
📊 Số cột trong sprite sheet (mặc định 10): 10
🎨 Chọn định dạng ảnh:
  1. WebP (nhẹ hơn, chất lượng tốt - khuyến nghị)
  2. JPG (tương thích rộng)
👉 Chọn (1-2, mặc định 1): 1
🌐 URL CDN cho sprite sheet (Nhấn Enter để bỏ qua):

🌍  CHỌN NGÔN NGỮ NHẬN DẠNG
==================================================
  1. 🇻🇳 Tiếng Việt
  2. 🇺🇸 Tiếng Anh
  3. 🇯🇵 Tiếng Nhật
  4. 🇰🇷 Tiếng Hàn
  5. 🇨🇳 Tiếng Trung
  6. 🇹🇭 Tiếng Thái
  7. 🇮🇩 Tiếng Indonesia
  8. 🤖 Tự động nhận diện
  0. ➕ Nhập mã khác
==================================================
👉 Nhập lựa chọn của bạn: 1
```

---

### Ví dụ 5: Tạo sprite sheet với URL CDN

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\Videos" `
  --group-name "video_with_sprites" `
  --save-video `
  --save-audio `
  --save-vtt `
  --create-thumbnails `
  --thumbnail-interval 3 `
  --thumb-cols 8 `
  --thumb-format "webp" `
  --cdn-url "https://cdn.example.com/videos/video_with_sprites/sprites/sprite.webp" `
  --language "vi"
```

**Kết quả**:

```
E:\Videos\
└── video_with_sprites\
    ├── video.mp4
    ├── audio.wav
    ├── movie_vi.vtt (phụ đề)
    ├── thumbnails.vtt (tham chiếu CDN: https://cdn.example.com/videos/video_with_sprites/sprites/sprite.webp)
    └── thumbnails\
        └── sprite.webp
```

---

### Ví dụ 6: Chỉ tạo sprite sheets (không lưu video/audio)

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\Sprites" `
  --group-name "video_sprites" `
  --create-thumbnails `
  --thumbnail-interval 10 `
  --thumb-width 120 `
  --thumb-height 68 `
  --thumb-cols 12 `
  --thumb-format "jpg"
```

**Kết quả** (chỉ giữ thumbnails):

```
E:\Sprites\
└── video_sprites\
    ├── thumbnails.vtt
    └── thumbnails\
        └── sprite.jpg
```

---

## 💡 Mẹo sử dụng

### 1. Tăng tốc độ xử lý

- Sử dụng mô hình nhỏ hơn: `--model "tiny"` (nhanh nhất, chất lượng thấp)
- Hoặc `--model "base"` (cân bằng tốc độ/chất lượng)

### 2. Tiết kiệm dung lượng

- Chỉ lưu VTT nếu bạn chỉ cần phụ đề: `--save-vtt`

### 3. Xử lý hàng loạt

Tạo file batch (`process.bat`):

```batch
@echo off
python .\main.py --m3u8 "URL_1" --group-name "video_1" --language "vi"
python .\main.py --m3u8 "URL_2" --group-name "video_2" --language "vi"
python .\main.py --m3u8 "URL_3" --group-name "video_3" --language "vi"
```

Chạy:

```powershell
.\process.bat
```

---

## 🆘 Xử lý sự cố

| Vấn đề                      | Giải pháp                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| `ffmpeg: command not found` | FFmpeg chưa được cài đặt hoặc thêm vào PATH. Xem lại [bước cài FFmpeg](#bước-2-cài-đặt-ffmpeg) |
| `No module named 'whisper'` | Chạy `pip install openai-whisper`                                                              |
| Xử lý chậm                  | Sử dụng mô hình nhỏ: `--model "tiny"` hoặc cài CUDA                                            |
| URL không hợp lệ            | Đảm bảo URL kết thúc bằng `.m3u8` và bắt đầu bằng `http://` hoặc `https://`                    |
| Không đủ dung lượng ổ cứng  | Tính năng `--save-vtt` chỉ lưu phụ đề (~1-5MB) thay vì video (GB)                              |

---

## 📝 Cấu trúc kết quả

Sau khi chạy, bạn sẽ có:

```
output-dir\
└── group-name\                    # Tuỳ chọn, tự động tạo nếu chọn
    ├── video.mp4                  # Nếu --save-video (tuỳ chọn)
    ├── audio.wav                  # Nếu --save-audio (tuỳ chọn)
    └── movie_<lang>.vtt           # Nếu --save-vtt (tuỳ chọn)
```

---

## 🔗 Các tài liệu liên quan

- [OpenAI Whisper](https://github.com/openai/whisper)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)

---

## 📄 License

Dự án này sử dụng OpenAI Whisper (Apache 2.0) và FFmpeg (LGPL).

**Lần cập nhật cuối**: 12 tháng 11 năm 2025
