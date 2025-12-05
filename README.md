# Whisper m3u8 Transcriber

Công cụ tải video từ URL m3u8, tách âm thanh và nhận dạng giọng nói bằng OpenAI Whisper với giao diện Rich console đẹp mắt. Script hỗ trợ lưu lựa chọn file, nhóm kết quả vào thư mục mới, và hỗ trợ đa ngôn ngữ.

## Mục lục

1. [Tính năng](#tính-năng)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Cài đặt](#cài-đặt)
4. [Cách sử dụng](#cách-sử-dụng)
5. [Các tuỳ chọn dòng lệnh](#các-tuỳ-chọn-dòng-lệnh)
6. [Sprite Sheet Thumbnails](#sprite-sheet-thumbnails)
7. [Ví dụ sử dụng](#ví-dụ-sử-dụng)
8. [Mẹo sử dụng](#mẹo-sử-dụng)
9. [Xử lý sự cố](#xử-lý-sự-cố)
10. [Cấu trúc kết quả](#cấu-trúc-kết-quả)
11. [Các tài liệu liên quan](#các-tài-liệu-liên-quan)
12. [Tính năng Rich Console](#tính-năng-rich-console)
13. [License](#license)
14. [Changelog](#changelog)

---

## Tính năng

- Tải video từ URL m3u8
- Tách âm thanh từ video (WAV 16kHz mono)
- Nhận dạng giọng nói bằng Whisper (hỗ trợ 99+ ngôn ngữ)
- Xuất phụ đề VTT
- **2 Chế độ xử lý**:
  - **Direct Mode**: Nhập link m3u8 trực tiếp (xử lý 1 video)
  - **Batch Mode**: Xử lý nhiều video từ file JSON với checkpoint tự động
- **Checkpoint System**: Tự động lưu tiến trình khi xử lý batch, tiếp tục từ nơi đã dừng
  - File checkpoint: `.whisper_m3u8_transcriber_checkpoint.json` (trong thư mục hiện tại)
  - Menu quản lý: Xem thông tin và xóa checkpoint
  - Hỗ trợ KeyboardInterrupt (Ctrl+C) an toàn
- **Recent Paths**: Tự động lưu các đường dẫn đã dùng
  - File config: `.whisper_m3u8_transcriber_config.json` (trong thư mục hiện tại)
  - Hiển thị gợi ý khi chọn thư mục lưu trữ
  - Tự động thêm path mới vào đầu danh sách
- **Chọn lựa file cần lưu**: Video, Audio, VTT, Thumbnails hoặc bất kỳ tổ hợp nào (8 options)
- **Nhóm file vào thư mục mới**: Tự động hoặc đặt tên tuỳ chỉnh
- **Giao diện Rich Console**: Progress bars, status indicators, bảng đẹp với màu sắc gradient
- Hỗ trợ menu tương tác: chọn ngôn ngữ, chọn mô hình Whisper
- Tự động nhận diện ngôn ngữ (hoặc chỉ định cụ thể)
- **Tạo Sprite Sheet Thumbnails**: Tạo hình ảnh sprite sheet từ video, hỗ trợ WebP và JPG
- **VTT cho Sprite Sheet**: Tự động tạo file VTT kèm tọa độ sprite (xywh)
- **Tối ưu Whisper**: Các tham số tối ưu để cải thiện độ chính xác và xử lý âm thanh có nhạc nền
- **Tối ưu xử lý**: Bỏ qua bước transcription khi không cần thiết (chỉ lưu video/audio/thumbnails)

---

## Yêu cầu hệ thống

### Phần cứng

- CPU: 2+ cores (khuyến khích 4+)
- RAM: 4GB tối thiểu (8GB+ cho mô hình lớn)
- GPU: NVIDIA GPU với CUDA (tùy chọn, để tăng tốc xử lý)
- Disk: 10GB+ cho mô hình Whisper

### Phần mềm

- **Python 3.8+**
- **FFmpeg** (để xử lý video/audio)

---

## Cài đặt

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
pip install openai-whisper rich
```

**Thư viện cần thiết:**

- `openai-whisper`: Mô hình nhận dạng giọng nói
- `rich`: Thư viện console UI với progress bars, tables, panels

> Nếu bạn muốn sử dụng GPU (NVIDIA CUDA) để tăng tốc độ xử lý:
>
> ```powershell
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
> ```

---

## Cách sử dụng

### Cách chạy đơn giản nhất (Menu tương tác)

```powershell
python .\main.py
```

Script sẽ hiển thị logo ASCII art với gradient màu sắc và menu chính:

```
1. Nhập link trực tiếp (Direct Mode)
2. Xử lý theo file JSON (Batch Mode)
3. Quản lý checkpoint (xem/xóa checkpoint đã lưu)
4. Hướng dẫn sử dụng (hiển thị help chi tiết)
```

#### Chế độ Direct (xử lý 1 video)

1. Chọn chế độ `1` từ menu chính
2. Nhập URL m3u8
3. Chọn thư mục lưu trữ:
   - Thư mục hiện tại
   - Chọn từ lịch sử đã dùng (lưu trong `.whisper_m3u8_transcriber_config.json`)
   - Nhập đường dẫn tùy chỉnh
4. Có nhóm file vào thư mục con mới không (nhập tên thư mục hoặc để trống dùng timestamp)
5. **Chọn file nào cần lưu** (8 tùy chọn):
   - 1: Video + Audio + VTT (lưu tất cả)
   - 2: Chỉ Video
   - 3: Chỉ Audio
   - 4: Chỉ VTT (Phụ đề)
   - 5: Video + Audio
   - 6: Video + VTT
   - 7: Audio + VTT
   - 8: Chỉ Thumbnails (không lưu video/audio)
6. Có tạo sprite sheet thumbnails không (y/n)
   - Nếu có: hỏi interval, kích thước, số cột, định dạng (webp/jpg), CDN URL
7. Chọn ngôn ngữ nhận dạng (chỉ khi cần transcription - option 1,4,6,7):
   - 1-7: Ngôn ngữ phổ biến (vi, en, ja, ko, zh, th, id)
   - 8: Tự động nhận diện
   - 0: Nhập mã khác

#### Chế độ Batch (xử lý nhiều video)

1. Chọn chế độ `2` từ menu chính
2. Nhập đường dẫn file JSON (ví dụ: `input.json` hoặc `input_example.txt`)
3. Hệ thống tự động kiểm tra checkpoint:
   - Nếu có checkpoint với cùng file JSON, hỏi có muốn tiếp tục không
   - Hiển thị tiến độ đã xử lý (ví dụ: 5/10 items) và thời gian lưu cuối
4. **Chọn file nào cần lưu** (8 tùy chọn - giống Direct Mode)
5. **Chọn ngôn ngữ** (chỉ khi cần transcription)
6. **Cấu hình thumbnails** (nếu muốn)
7. Chọn chạy đến item thứ mấy (Enter để chạy hết, hoặc nhập số để dừng sớm)
8. Xử lý tự động từng item theo thứ tự
9. Sau mỗi item thành công, checkpoint được lưu tự động

**Cấu trúc file JSON:**

```json
{
  "root_path": "E:\\Videos\\Subtitles",
  "items": [
    {
      "slug": "video-001",
      "m3u8_url": "https://example.com/stream1.m3u8",
      "folder_name": "video-phần-1"
    },
    {
      "slug": "video-002",
      "m3u8_url": "https://example.com/stream2.m3u8",
      "folder_name": "video-phần-2"
    }
  ]
}
```

- `root_path`: Thư mục gốc (ví dụ: `E:\Videos\Subtitles`)
- `slug`: Tên thư mục con (sẽ ghép với root_path)
- `m3u8_url`: URL của video m3u8
- `folder_name`: Tên thư mục nhóm file (tương đương --group-name)

**Đường dẫn cuối cùng:** `{root_path}\{slug}\{folder_name}\`

**Ví dụ:** `E:\Videos\Subtitles\video-001\video-phần-1\`

**Checkpoint System:**

- Tự động lưu tiến trình sau mỗi item thành công vào file `.whisper_m3u8_transcriber_checkpoint.json` (trong thư mục hiện tại)
- Khi bị gián đoạn (Ctrl+C), checkpoint được lưu lại ngay lập tức
- Lần chạy tiếp theo với cùng file JSON sẽ hỏi có muốn tiếp tục không
- Có thể chọn bắt đầu lại từ đầu hoặc tiếp tục từ item cuối cùng
- Menu chính có option "Quản lý checkpoint" để xem và xóa checkpoint

**Giao diện Rich Console bao gồm:**

- Progress bars với spinner và thời gian thực cho download, extract, transcribe
- Tables đẹp với border styles cho menu lựa chọn
- Panels màu sắc cho thông báo lỗi và cảnh báo
- Status indicators với animation
- Gradient colors cho text và ASCII art

---

## Các tuỳ chọn dòng lệnh

| Tuỳ chọn               | Mô tả                              | Ví dụ                                                        |
| ---------------------- | ---------------------------------- | ------------------------------------------------------------ |
| `--mode`               | Chế độ xử lý                       | `--mode "direct"` hoặc `--mode "batch"`                      |
| `--json`               | Đường dẫn file JSON (batch mode)   | `--json "input.json"`                                        |
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

## Sprite Sheet Thumbnails

Script có thể tự động tạo **sprite sheet thumbnails** từ video - đây là một hình ảnh duy nhất chứa nhiều ảnh nhỏ được xếp thành lưới. Rất hữu ích cho phát triển các ứng dụng video player.

### Tính năng Sprite Sheet

- Tạo thumbnails từ các khung hình của video với FFmpeg
- Hỗ trợ định dạng **WebP** (nhẹ, chất lượng tốt) hoặc **JPG** (tương thích rộng)
- Tạo file **VTT** kèm theo với tọa độ xywh để sử dụng trong video player
- Tùy chỉnh hoàn toàn: khoảng cách, kích thước, số cột
- Hỗ trợ URL CDN cho sprite sheet
- Progress bar hiển thị tiến trình tạo thumbnails
- Tự động dọn dẹp file tạm

### Cách sử dụng

#### Qua menu tương tác

```powershell
python .\main.py
```

Khi chạy, script sẽ hỏi:

```text
Bạn có muốn tạo sprite sheet thumbnails từ video không? (y/N): y
Nhập khoảng thời gian giữa các thumbnail (giây, mặc định 5): 3
Thay đổi kích thước? (Nhấn Enter để giữ mặc định hoặc nhập 'w,h' ví dụ: 160,90):
Số cột trong sprite sheet (mặc định 10): 8
Chọn định dạng ảnh:
  1. WebP (nhẹ hơn, chất lượng tốt - khuyến nghị)
  2. JPG (tương thích rộng)
Chọn (1-2, mặc định 1): 1
URL CDN cho sprite sheet (Nhấn Enter để bỏ qua):
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

**Batch Mode:**

```powershell
python .\main.py `
  --mode batch `
  --json "input.json" `
  --language "vi" `
  --save-video --save-vtt `
  --create-thumbnails
```

### Kết quả

Sau khi hoàn tất, bạn sẽ có:

**Direct Mode:**

```text
output-dir/
└── group-name/
    ├── video.mp4 (nếu chọn lưu)
    ├── audio.wav (nếu chọn lưu)
    ├── movie_vi.vtt (phụ đề)
    ├── thumbnails.vtt (VTT cho sprite sheet)
    └── thumbnails/
        └── sprite.webp (hoặc sprite.jpg)
```

**Batch Mode:**

```text
E:\Videos\Subtitles\
├── video-001\
│   └── video-phần-1\
│       ├── video.mp4
│       ├── movie_vi.vtt
│       └── thumbnails/
│           └── sprite.webp
├── video-002\
│   └── video-phần-2\
│       ├── video.mp4
│       ├── movie_vi.vtt
│       └── thumbnails/
│           └── sprite.webp
└── video-003\
    └── video-phần-3\
        ├── video.mp4
        ├── movie_vi.vtt
        └── thumbnails/
            └── sprite.webp
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

### Gợi ý tối ưu

**Định dạng ảnh:**

- **WebP**: Dung lượng nhỏ hơn ~40% so với JPG, chất lượng tốt, phù hợp cho web modern
- **JPG**: Tương thích rộng, phù hợp cho các trình duyệt cũ

**Khoảng cách thumbnails:**

- **2-3 giây**: Nhiều thumbnails, chi tiết cao, file sprite lớn hơn
- **5 giây**: Cân bằng giữa chi tiết và dung lượng (khuyến nghị)
- **10 giây trở lên**: Ít thumbnails, file nhẹ, phù hợp video dài

**Kích thước và cột:**

- **160x90px, 10 cột**: Chuẩn cho video 16:9, sprite width = 1600px
- **120x68px, 12 cột**: Thumbnail nhỏ hơn, nhiều cột, sprite compact hơn

---

## Ví dụ sử dụng

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

```text
E:/MyVideos/
└── lesson_1/
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

```text
E:/Subtitles/
└── vietnamese_subs/
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

```text
<current-dir>/
└── group_20251027_153045/
    ├── video.mp4
    └── audio.wav
```

---

### Ví dụ 4: Menu tương tác (không CLI flags)

```powershell
python .\main.py
```

Script sẽ hỏi từng bước:

```text
Nhập link .m3u8: https://example.com/stream.m3u8

Chọn nơi lưu trữ:
1. Thư mục hiện tại
2. Chọn từ các đường dẫn đã dùng trước (gợi ý)
3. Nhập đường dẫn tùy chỉnh
Chọn (1-3): 1

Bạn có muốn nhóm 3 file (video/audio/vtt) vào thư mục mới không? (y/N): y
Nhập tên thư mục nhóm (để trống sẽ dùng tên theo thời điểm): my_video

CHỌN FILE CẦN LƯU
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ # ┃ Tùy chọn                                           ┃
┣━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 1 ┃ Video + Audio + VTT (lưu tất cả)                   ┃
┃ 2 ┃ Video                                              ┃
┃ 3 ┃ Audio                                              ┃
┃ 4 ┃ VTT (Phụ đề)                                       ┃
┃ 5 ┃ Video + Audio                                      ┃
┃ 6 ┃ Video + VTT                                        ┃
┃ 7 ┃ Audio + VTT                                        ┃
┃ 8 ┃ Thumbnails (ảnh thumbnail + sprite sheet)          ┃
┗━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
Nhập lựa chọn (1-8, mặc định 1): 1

Bạn có muốn tạo sprite sheet thumbnails từ video không? (y/N): y
Nhập khoảng thời gian giữa các thumbnail (giây, mặc định 5): 5
Thay đổi kích thước? (Nhấn Enter để giữ mặc định hoặc nhập 'w,h' ví dụ: 160,90):
Số cột trong sprite sheet (mặc định 10): 10
Chọn định dạng ảnh:
  1. WebP (nhẹ hơn, chất lượng tốt - khuyến nghị)
  2. JPG (tương thích rộng)
Chọn (1-2, mặc định 1): 1
URL CDN cho sprite sheet (Nhấn Enter để bỏ qua):

CHỌN NGÔN NGỮ NHẬN DẠNG (Chỉ hiển thị khi cần transcription)
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓
┃ # ┃ Ngôn ngữ                ┃ Mã   ┃
┣━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━┫
┃ 1 ┃ Tiếng Việt              ┃ vi   ┃
┃ 2 ┃ Tiếng Anh               ┃ en   ┃
┃ 3 ┃ Tiếng Nhật              ┃ ja   ┃
┃ 4 ┃ Tiếng Hàn               ┃ ko   ┃
┃ 5 ┃ Tiếng Trung             ┃ zh   ┃
┃ 6 ┃ Tiếng Thái              ┃ th   ┃
┃ 7 ┃ Tiếng Indonesia         ┃ id   ┃
┃ 8 ┃ Tự động nhận diện       ┃      ┃
┃ 0 ┃ Nhập mã khác            ┃      ┃
┗━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━┛
Nhập lựa chọn của bạn (mặc định 1): 1
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

```text
E:/Videos/
└── video_with_sprites/
    ├── video.mp4
    ├── audio.wav
    ├── movie_vi.vtt (phụ đề)
    ├── thumbnails.vtt (tham chiếu CDN: https://cdn.example.com/videos/video_with_sprites/sprites/sprite.webp)
    └── thumbnails/
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

```text
E:/Sprites/
└── video_sprites/
    ├── thumbnails.vtt
    └── thumbnails/
        └── sprite.jpg
```

---

## Mẹo sử dụng

### 1. Tăng tốc độ xử lý

- Sử dụng GPU nếu có: Script tự động phát hiện CUDA
- Sử dụng mô hình nhỏ hơn: `--model "tiny"` (nhanh nhất, chất lượng thấp)
- Hoặc `--model "base"` (cân bằng tốc độ/chất lượng)
- Model `small` là khuyến nghị cho độ chính xác tốt

### 2. Cải thiện độ chính xác transcription

- Luôn chỉ định ngôn ngữ: `--language "vi"` thay vì để auto-detect
- Các tham số tối ưu đã được cấu hình sẵn:
  - `temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`: Fallback temperatures để giảm lặp
  - `condition_on_previous_text=False`: Tắt để tránh lặp lại context
  - `no_speech_threshold=0.6`: Lọc nhạc/noise tốt hơn
  - `compression_ratio_threshold=2.4`: Phát hiện lỗi tốt hơn
  - `logprob_threshold=-1.0`: Lọc kết quả không chắc chắn
  - `best_of=5`: Lấy kết quả tốt nhất trong 5 lần decode
  - `initial_prompt`: Tự động thêm prompt theo ngôn ngữ để cải thiện độ chính xác

### 3. Tiết kiệm dung lượng và thời gian

- Chỉ lưu VTT nếu bạn chỉ cần phụ đề: `--save-vtt`
- Chỉ lưu Video nếu không cần transcription: `--save-video` (bỏ qua bước nhận dạng giọng nói)
- Chỉ tạo thumbnails mà không cần transcription: chọn option 8 trong menu
- Sử dụng WebP cho sprite sheet (nhẹ hơn JPG ~40%)

### 4. Xử lý hàng loạt

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

## Xử lý sự cố

| Vấn đề                        | Giải pháp                                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| `ffmpeg: command not found`   | FFmpeg chưa được cài đặt hoặc thêm vào PATH. Xem lại [bước cài FFmpeg](#bước-2-cài-đặt-ffmpeg) |
| `No module named 'whisper'`   | Chạy `pip install openai-whisper`                                                              |
| `No module named 'rich'`      | Chạy `pip install rich`                                                                        |
| `No module named 'torch'`     | Chạy `pip install torch` hoặc cài CUDA version cho GPU                                         |
| Xử lý chậm                    | Sử dụng mô hình nhỏ: `--model "tiny"` hoặc cài CUDA để dùng GPU                                |
| URL không hợp lệ              | Đảm bảo URL chứa `.m3u8` và bắt đầu bằng `http://` hoặc `https://`                             |
| Whisper chỉ nhận dạng "Music" | Chỉ định rõ ngôn ngữ: `--language "vi"` thay vì để auto-detect                                 |
| Kết quả bị lặp lại            | Script đã tối ưu với `condition_on_previous_text=False` và `best_of=5`                         |
| Progress bar không hiển thị   | Console không hỗ trợ ANSI colors, script vẫn chạy bình thường                                  |
| Không đủ dung lượng ổ cứng    | Chọn option 4 (chỉ lưu VTT) hoặc option 8 (chỉ thumbnails)                                     |
| Checkpoint không tìm thấy     | Checkpoint lưu ở `.whisper_m3u8_transcriber_checkpoint.json` (thư mục hiện tại)                |
| Recent paths không lưu        | Config lưu ở `.whisper_m3u8_transcriber_config.json` (thư mục hiện tại)                        |

---

## Cấu trúc kết quả

Sau khi chạy, bạn sẽ có:

### Cấu trúc file output

```text
output-dir/
└── group-name/                    # Tuỳ chọn, tự động tạo nếu chọn
    ├── video.mp4                  # Nếu chọn lưu video
    ├── audio.wav                  # Nếu chọn lưu audio
    ├── movie_<lang>.vtt           # Nếu chọn lưu VTT (phụ đề)
    ├── thumbnails.vtt             # VTT cho sprite sheet (nếu tạo thumbnails)
    └── thumbnails/                # Thư mục thumbnails
        ├── sprite.webp            # Hoặc sprite.jpg tùy chọn định dạng
        └── sprite_info.txt        # File thông tin chi tiết về sprite
```

### File config và checkpoint

```text
./ (Thư mục hiện tại)
├── .whisper_m3u8_transcriber_config.json      # Lưu recent paths
└── .whisper_m3u8_transcriber_checkpoint.json  # Lưu checkpoint batch mode
```

**File config (recent paths):**

```json
{
  "recent_paths": [
    "E:\\Videos\\Subtitles",
    "D:\\Projects\\videos",
    "C:\\Users\\username\\Desktop"
  ]
}
```

**File checkpoint:**

```json
{
  "json_path": "E:\\Projects\\input.json",
  "last_index": 5,
  "total": 10,
  "timestamp": 1733404123.45
}
```

**Bảng tổng kết khi hoàn tất:**

Script sẽ hiển thị bảng kết quả với Rich formatting:

```text
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃               ┃                                        ┃            ┃
┃     Loại      ┃               Tên file                 ┃ Trạng thái ┃
┃               ┃                                        ┃            ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│     Video     │ video.mp4                              │     ✓      │
│     Audio     │ audio.wav                              │     ✓      │
│    Phụ đề     │ movie_vi.vtt                           │     ✓      │
│ Sprite Sheet  │ sprite.webp (120 thumbs)               │     ✓      │
│ Thumbnail VTT │ thumbnails.vtt                         │     ✓      │
└───────────────┴────────────────────────────────────────┴────────────┘
```

---

## Các tài liệu liên quan

- [OpenAI Whisper](https://github.com/openai/whisper) - Mô hình nhận dạng giọng nói
- [Rich Library](https://rich.readthedocs.io/) - Python library cho rich text và beautiful formatting
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html) - Công cụ xử lý video/audio
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes) - Mã ngôn ngữ chuẩn

---

## Tính năng Rich Console

### Progress Bars

- Spinner animation với các frames xoay
- Progress bar với màu sắc (cyan, magenta, green)
- Hiển thị phần trăm hoàn thành
- Thời gian đã chạy (TimeElapsed)
- Số lượng hoàn thành/tổng số (cho thumbnails)

### Tables

- Border styles: ROUNDED, DOUBLE, DOUBLE_EDGE
- Columns với fixed width cho alignment tốt
- Color coding: yellow cho số, green cho options, cyan cho values

### Panels

- Error panels với border đỏ
- Warning panels với border vàng
- Info panels với border cyan/green
- Styled text với bold, dim, colors

### Status Indicators

- Checkmark (✓) cho success
- Warning symbol (⚠) cho cảnh báo
- Spinning dots animation cho processing
- Real-time updates cho download/extract/transcribe

---

## License

Dự án này sử dụng:

- OpenAI Whisper (Apache 2.0)
- FFmpeg (LGPL)
- Rich (MIT License)

---

**Lần cập nhật cuối**: 05 tháng 12 năm 2025 (v1.2.0)

---

## Changelog

### v1.2.0 (05/12/2025)

- **[Feature]** Thêm Recent Paths: Lưu và gợi ý các đường dẫn đã dùng
  - File config: `.whisper_m3u8_transcriber_config.json` (lưu trong thư mục hiện tại)
  - Hỗ trợ chọn nhanh từ lịch sử hoặc nhập mới
- **[Feature]** Menu quản lý checkpoint: Xem thông tin và xóa checkpoint
  - Option 3 trong menu chính
  - Hiển thị tiến độ, file JSON, thời gian lưu
- **[Feature]** Hướng dẫn sử dụng tích hợp: Option 4 trong menu chính
  - Hiển thị full hướng dẫn với Rich formatting
  - Tables, Panels với border styles đẹp mắt
- **[Feature]** Option 8: Chỉ tạo thumbnails mà không cần transcription
- **[Feature]** Batch Mode: Hỏi chạy đến item thứ mấy (cho phép dừng sớm)
- **[Improvement]** Tối ưu Whisper parameters:
  - `temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`: Fallback để giảm lặp
  - `condition_on_previous_text=False`: Tắt để tránh lặp context
  - `best_of=5`: Lấy kết quả tốt nhất
  - `initial_prompt`: Tự động theo ngôn ngữ
- **[Improvement]** Cải thiện xử lý KeyboardInterrupt:
  - Cleanup temp files an toàn
  - Lưu checkpoint ngay khi Ctrl+C
- **[Improvement]** Tối ưu logic: Chỉ tách audio và transcription khi cần
- **[Fix]** Sửa lỗi UnboundLocalError khi KeyboardInterrupt trong thumbnails
- **[UI]** Cải thiện consistency với default values cho tất cả prompts

### v1.0.0 (03/12/2025)

- Release đầu tiên với đầy đủ tính năng
- Hỗ trợ tải video từ m3u8
- Nhận dạng giọng nói bằng Whisper
- Tạo sprite sheet thumbnails
- Giao diện Rich Console với progress bars
- Checkpoint system cho batch mode
