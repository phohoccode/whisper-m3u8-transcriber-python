# Whisper m3u8 Transcriber

Công cụ tải video từ URL m3u8, tách âm thanh và nhận dạng giọng nói bằng OpenAI Whisper với giao diện Rich console đẹp mắt. Script hỗ trợ lưu lựa chọn file, nhóm kết quả vào thư mục mới, và hỗ trợ đa ngôn ngữ.

## Mục lục

1. [Tính năng](#tính-năng)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Cài đặt](#cài-đặt)
4. [Cách sử dụng](#cách-sử-dụng)
   - [Cách 1: Menu Tương tác](#-cách-1-sử-dụng-menu-tương-tác-khuyến-nghị-cho-người-mới)
   - [Cách 2: Giao diện GUI](#-cách-2-sử-dụng-giao-diện-gui-windows)
   - [Cách 3: Command Line (CLI)](#-cách-3-sử-dụng-command-line-interface-cli)
5. [Sprite Sheet Thumbnails](#sprite-sheet-thumbnails)
6. [Ví dụ sử dụng chi tiết](#ví-dụ-sử-dụng-chi-tiết)
7. [Mẹo sử dụng](#mẹo-sử-dụng)
8. [Xử lý sự cố](#xử-lý-sự-cố)
9. [Cấu trúc kết quả](#cấu-trúc-kết-quả)
10. [Các tài liệu liên quan](#các-tài-liệu-liên-quan)
11. [Tính năng Rich Console](#tính-năng-rich-console)
12. [License](#license)
13. [Changelog](#changelog)

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

Công cụ này hỗ trợ **2 cách sử dụng chính**:

1. **CLI Mode** - Sử dụng command line với các flags
2. **Interactive Menu Mode** - Menu tương tác dòng lệnh với giao diện đẹp
3. **GUI Mode** - Giao diện đồ họa (Windows)

---

## 📋 Cách 1: Sử dụng Menu Tương Tác (Khuyến nghị cho người mới)

### Chạy menu tương tác

```powershell
python .\main.py
```

Script sẽ hiển thị logo ASCII art với gradient màu sắc và menu chính:

```
╔═════════════════════════════════════════╗
║  WHISPER M3U8 TRANSCRIBER (v1.2.0)      ║
║  Tải video m3u8 → Nhận dạng giọng nói   ║
╚═════════════════════════════════════════╝

MENU CHÍNH:
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ # ┃ Tùy chọn                           ┃
┣━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 1 ┃ Nhập link trực tiếp (Direct Mode)  ┃
┃ 2 ┃ Xử lý theo file JSON (Batch Mode)  ┃
┃ 3 ┃ Quản lý checkpoint                 ┃
┃ 4 ┃ Hướng dẫn sử dụng                  ┃
┗━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Tùy chọn 1: Direct Mode (Xử lý 1 video)

**Quy trình chi tiết:**

1. **Nhập URL m3u8**

   ```
   Nhập link .m3u8: https://example.com/stream.m3u8
   ```

2. **Chọn nơi lưu trữ**

   ```
   Chọn nơi lưu trữ:
   1. Thư mục hiện tại (E:\Project\whisper-m3u8-transcriber)
   2. Chọn từ các đường dẫn đã dùng trước
   3. Nhập đường dẫn tùy chỉnh
   Chọn (1-3, mặc định 1):
   ```

   - **Option 1**: Lưu trong thư mục script đang chạy
   - **Option 2**: Hiển thị danh sách các thư mục đã dùng gần đây (lưu trong `.whisper_m3u8_transcriber_config.json`)
   - **Option 3**: Nhập đường dẫn tùy ý, ví dụ: `E:\MyVideos`

3. **Chọn nhóm file vào thư mục con**

   ```
   Bạn có muốn nhóm các file (video/audio/vtt) vào thư mục con không? (y/N): y
   Nhập tên thư mục nhóm (để trống sẽ dùng tên theo thời điểm): my_video
   ```

   - **Có (y)**: Tạo thư mục con để nhóm các file
   - **Không (n)**: Lưu trực tiếp vào output directory
   - Để trống → Script tự tạo tên theo timestamp: `group_20251205_143022/`

4. **Chọn file cần lưu** (8 tùy chọn)

   ```
   ┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ # ┃ Tùy chọn                                           ┃
   ┣━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
   ┃ 1 ┃ Video + Audio + VTT (lưu tất cả) ⭐ Khuyến nghị     ┃
   ┃ 2 ┃ Chỉ Video                                          ┃
   ┃ 3 ┃ Chỉ Audio (WAV)                                    ┃
   ┃ 4 ┃ Chỉ VTT (Phụ đề)                                   ┃
   ┃ 5 ┃ Video + Audio                                      ┃
   ┃ 6 ┃ Video + VTT                                        ┃
   ┃ 7 ┃ Audio + VTT                                        ┃
   ┃ 8 ┃ Thumbnails (sprite sheet mà không cần video/audio) ┃
   ┗━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
   Nhập lựa chọn (1-8, mặc định 1):
   ```

   - **1**: Lưu video (MP4) + audio (WAV) + phụ đề (VTT) - Dùng khi cần đầy đủ
   - **2**: Chỉ lưu video (bỏ qua transcription để tiết kiệm thời gian)
   - **3**: Chỉ lưu audio WAV (16kHz mono)
   - **4**: Chỉ lưu VTT (chỉ cần phụ đề)
   - **8**: Chỉ tạo sprite sheet thumbnails (không cần video/audio)

5. **Cấu hình Sprite Sheet Thumbnails** (nếu chọn option có thumbnails)

   ```
   Bạn có muốn tạo sprite sheet thumbnails từ video không? (y/N): y
   ```

   - **Khoảng cách** (Interval)

     ```
     Nhập khoảng thời gian giữa các thumbnail (giây, mặc định 5): 3
     ```

     - 2-3 giây: Chi tiết cao, file lớn
     - 5 giây: Cân bằng (khuyến nghị)
     - 10+ giây: Ít thumbnails, file nhẹ

   - **Kích thước** (Size)

     ```
     Thay đổi kích thước? (Nhấn Enter để giữ 160,90 hoặc nhập 'w,h' ví dụ: 160,90):
     ```

     - Để trống: Dùng mặc định 160x90px
     - Nhập: 120,68 hoặc 200,112

   - **Số cột** (Columns)

     ```
     Số cột trong sprite sheet (mặc định 10): 8
     ```

     - Ảnh được xếp thành lưới (cols × rows)
     - 10 cột: 1600px rộng (với thumbnail 160px)

   - **Định dạng ảnh** (Format)

     ```
     Chọn định dạng ảnh:
       1. WebP (nhẹ hơn 40%, khuyến nghị) ⭐
       2. JPG (tương thích rộng)
     Chọn (1-2, mặc định 1):
     ```

     - **WebP**: Nhẹ hơn, tối ưu cho web modern
     - **JPG**: Tương thích trình duyệt cũ

   - **CDN URL** (Tùy chọn)

     ```
     URL CDN cho sprite sheet (Nhấn Enter để bỏ qua):
     ```

     - Nhập: Dùng URL CDN trong VTT file
     - Để trống: Dùng đường dẫn tương đối

6. **Chọn ngôn ngữ** (chỉ hiển thị nếu chọn option có transcription)

   ```
   ┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓
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
   ┃ 0 ┃ Nhập mã ngôn ngữ khác   ┃      ┃
   ┗━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━┛
   Nhập lựa chọn (mặc định 1):
   ```

   - **1-7**: Chọn ngôn ngữ phổ biến
   - **8**: Để Whisper tự động phát hiện (chậm hơn, có thể sai)
   - **0**: Nhập mã ISO 639-1 khác (ví dụ: `ru`, `es`, `fr`)

7. **Xử lý bắt đầu**

   ```
   🔄 Đang tải video...
   [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45% | 00:15 < 00:20

   🎵 Đang tách âm thanh...
   ✓ Hoàn tất tách âm thanh

   🎤 Đang nhận dạng giọng nói (model: small)...
   [████████████████████████████████████████████████████] 100% | 00:32

   ✅ Xử lý hoàn tất!
   ```

### Tùy chọn 2: Batch Mode (Xử lý nhiều video)

**Cấu trúc file JSON:**

Tạo file `input.json`:

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
    },
    {
      "slug": "video-003",
      "m3u8_url": "https://example.com/stream3.m3u8",
      "folder_name": "video-phần-3"
    }
  ]
}
```

**Các field bắt buộc:**

- `root_path`: Thư mục gốc (ví dụ: `E:\Videos\Subtitles`)
- `items[]`: Mảng video cần xử lý
  - `slug`: Tên thư mục con
  - `m3u8_url`: URL m3u8 của video
  - `folder_name`: Tên thư mục nhóm file

**Đường dẫn cuối cùng**: `{root_path}\{slug}\{folder_name}\`

**Ví dụ**: `E:\Videos\Subtitles\video-001\video-phần-1\`

**Quy trình Batch Mode:**

1. **Chọn option 2** từ menu chính
2. **Nhập đường dẫn file JSON**

   ```
   Nhập đường dẫn file JSON: input.json
   ```

   - Tên file (nếu cùng thư mục): `input.json`
   - Đường dẫn đầy đủ: `D:\Projects\input.json`

3. **Kiểm tra Checkpoint** (nếu có)

   ```
   ⚠️  Tìm thấy checkpoint từ lần chạy trước
   File: input.json
   Đã xử lý: 5/10 items
   Lần cuối: 2025-12-05 14:30:23

   Bạn có muốn tiếp tục từ item #6 không? (y/N): y
   ```

   - **y**: Tiếp tục từ item đã dừng
   - **n**: Bắt đầu lại từ đầu

4. **Chọn file cần lưu, ngôn ngữ, thumbnails** (giống Direct Mode)

5. **Chọn xử lý đến item thứ mấy**

   ```
   Tổng cộng 10 items sẽ được xử lý
   Nhập số item cần xử lý (Enter để xử lý hết, hoặc nhập số, ví dụ: 5):
   ```

   - **Để trống**: Xử lý hết 10 items
   - **Nhập số**: Chỉ xử lý đến item thứ 5 (Items 0-4)

6. **Xử lý tự động**

   ```
   Đang xử lý 10 items...

   [1/10] 🎬 video-001 (video-phần-1)
   ✓ Hoàn tất

   [2/10] 🎬 video-002 (video-phần-2)
   ✓ Hoàn tất

   ...

   ✅ Xử lý batch hoàn tất! (10/10)
   ```

   - Sau mỗi item thành công, checkpoint được lưu tự động
   - Có thể nhấn Ctrl+C bất cứ lúc nào, checkpoint sẽ được giữ lại

### Tùy chọn 3: Quản lý Checkpoint

```
Checkpoint Management:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                 ┃
┃ 📁 File JSON: input.json                        ┃
┃ 📊 Tiến độ: 5/10 items                          ┃
┃ ⏱️  Thời gian: 2025-12-05 14:30:23              ┃
┃                                                 ┃
┃ [1] Xóa checkpoint                              ┃
┃ [2] Quay lại menu                               ┃
┃                                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Tùy chọn 4: Hướng dẫn sử dụng

Hiển thị full hướng dẫn với định dạng Rich Console đẹp mắt bao gồm các ví dụ, bảng, panels.

---

## 🖥️ Cách 2: Sử dụng Giao Diện GUI (Windows)

GUI cung cấp trải nghiệm người dùng thân thiện, không cần sử dụng dòng lệnh.

### Chạy ứng dụng GUI

```powershell
python .\main_gui.py
```

Cửa sổ ứng dụng sẽ mở ra với giao diện modern (CustomTkinter):

```
┌─────────────────────────────────────────────┐
│  Whisper M3U8 Transcriber - GUI             │
├─────────────────────────────────────────────┤
│                                             │
│  📋 INPUT SETTINGS                          │
│  ┌─────────────────────────────────────────┐
│  │ URL/Path: [________________]             │
│  │ Mode:     ○ Direct  ● Batch             │
│  │                                         │
│  │ [Browse] [Paste]                       │
│  └─────────────────────────────────────────┘
│                                             │
│  💾 OUTPUT SETTINGS                         │
│  ┌─────────────────────────────────────────┐
│  │ Output Dir: [______________]            │
│  │ Group Folder: [______________]          │
│  │ [Browse]                               │
│  └─────────────────────────────────────────┘
│                                             │
│  📁 FILE OPTIONS                            │
│  ┌─────────────────────────────────────────┐
│  │ ☑ Save Video      ☑ Save Audio         │
│  │ ☑ Save VTT        ☐ Create Thumbnails  │
│  └─────────────────────────────────────────┘
│                                             │
│  🎬 THUMBNAILS CONFIG                       │
│  ┌─────────────────────────────────────────┐
│  │ Interval: [5] seconds                  │
│  │ Size: [160] x [90] pixels              │
│  │ Cols: [10]  Format: [WebP ▼]           │
│  │ CDN URL: [______________]              │
│  └─────────────────────────────────────────┘
│                                             │
│  🌐 LANGUAGE & MODEL                        │
│  ┌─────────────────────────────────────────┐
│  │ Language: [Tiếng Việt ▼]               │
│  │ Model:    [small ▼]                    │
│  │ GPU: [Auto ▼]                          │
│  └─────────────────────────────────────────┘
│                                             │
│  [Start] [Stop] [Clear Checkpoint]         │
│                                             │
│  📊 STATUS & LOG                            │
│  ┌─────────────────────────────────────────┐
│  │ Status: Ready                           │
│  │ Progress: 45% [████░░░░░░] 00:15       │
│  │                                         │
│  │ Log Output:                             │
│  │ ✓ GPU detected: NVIDIA RTX 3060        │
│  │ 🔄 Downloading video...                 │
│  │ 🎵 Extracting audio...                  │
│  │ 🎤 Transcribing...                      │
│  └─────────────────────────────────────────┘
│                                             │
└─────────────────────────────────────────────┘
```

### Các bước sử dụng GUI chi tiết

#### 1. **INPUT SETTINGS - Nhập nguồn dữ liệu**

**Mode - Chế độ:**

- **Direct**: Xử lý một URL m3u8
- **Batch**: Xử lý file JSON với nhiều URL

**Input URL/Path:**

- **Direct Mode**: Nhập URL m3u8 hoặc dán từ clipboard
  ```
  https://example.com/stream.m3u8
  ```
- **Batch Mode**: Chọn file JSON
  - Click [Browse]: Chọn file `input.json`
  - Hoặc paste đường dẫn file

**Các nút hỗ trợ:**

- **[Browse]**: Mở file dialog để chọn
- **[Paste]**: Dán từ clipboard

#### 2. **OUTPUT SETTINGS - Cấu hình đầu ra**

**Output Directory - Thư mục lưu trữ:**

- Click [Browse] để chọn thư mục
- Hoặc nhập đường dẫn trực tiếp
- Ví dụ: `E:\Videos\Subtitles`

**Group Folder - Tên thư mục nhóm (tùy chọn):**

- Để trống: Script tự tạo tên theo timestamp (`group_20251205_143022`)
- Nhập tên: `my_video`, `lesson_1`, v.v.

#### 3. **FILE OPTIONS - Chọn file cần lưu**

Các checkbox để chọn file cần lưu:

- **☑ Save Video**: Lưu file video (MP4)
- **☑ Save Audio**: Lưu file audio (WAV 16kHz mono)
- **☑ Save VTT**: Lưu file phụ đề (VTT)
- **☐ Create Thumbnails**: Tạo sprite sheet thumbnails

**Ví dụ tổ hợp:**

- ☑☑☑☐: Video + Audio + VTT (đầy đủ)
- ☑☐☑☐: Video + VTT
- ☐☐☑☐: Chỉ VTT (tiết kiệm dung lượng)
- ☐☐☐☑: Chỉ Thumbnails

#### 4. **THUMBNAILS CONFIG - Cấu hình Sprite Sheet**

Chỉ hoạt động khi ☑ Create Thumbnails được chọn.

**Interval - Khoảng cách (giây):**

- Mặc định: 5
- Gợi ý: 2-3 (chi tiết), 5 (cân bằng), 10+ (ít thumbnails)

**Size - Kích thước (pixels):**

- Chiều rộng (Width): Mặc định 160px
- Chiều cao (Height): Mặc định 90px
- Ví dụ: 120x68, 160x90, 200x112

**Cols - Số cột trong sprite:**

- Mặc định: 10
- Ví dụ: 8, 10, 12 (ảnh xếp theo cột)

**Format - Định dạng ảnh:**

- **WebP** (khuyến nghị): Nhẹ ~40% so với JPG
- **JPG**: Tương thích rộng

**CDN URL - URL CDN (tùy chọn):**

- Để trống: Dùng đường dẫn tương đối
- Nhập: URL CDN đầy đủ
  ```
  https://cdn.example.com/videos/sprite.webp
  ```

#### 5. **LANGUAGE & MODEL - Chọn ngôn ngữ và mô hình**

**Language - Ngôn ngữ nhận dạng:**
Dropdown chứa danh sách ngôn ngữ:

- Tiếng Việt (vi)
- Tiếng Anh (en)
- Tiếng Nhật (ja)
- Tiếng Hàn (ko)
- Tiếng Trung (zh)
- Tiếng Thái (th)
- Tiếng Indonesia (id)
- Auto Detect (tự động - chậm hơn)

**Model - Mô hình Whisper:**

- **tiny**: Nhanh nhất, chất lượng thấp (~39MB)
- **base**: Nhanh, chất lượng trung bình (~140MB)
- **small**: Cân bằng ⭐ (khuyến nghị) (~466MB)
- **medium**: Chậm, chất lượng tốt (~1.5GB)
- **large**: Chậm nhất, chất lượng tốt nhất (~2.9GB)

**GPU - Tăng tốc:**

- **Auto**: Script tự phát hiện GPU
- **CPU**: Bắt buộc dùng CPU
- **CUDA**: Dùng NVIDIA GPU (nếu có)

#### 6. **Nút điều khiển**

- **[Start]**: Bắt đầu xử lý
  - Chuyển sang trạng thái "Processing"
  - Hiển thị progress bar
  - Lock các setting controls
- **[Stop]**: Dừng xử lý hiện tại
  - Chỉ hoạt động khi đang xử lý
  - Giữ lại checkpoint (batch mode)
- **[Clear Checkpoint]**: Xóa checkpoint
  - Xóa file `.whisper_m3u8_transcriber_checkpoint.json`
  - Hỏi confirm trước xóa

#### 7. **STATUS & LOG - Trạng thái và Nhật ký**

**Status Line:**

```
Status: Ready
Status: Validating inputs...
Status: GPU detected - NVIDIA RTX 3060
Status: Downloading video... (45%)
Status: Extracting audio...
Status: Transcribing with model small...
Status: Creating thumbnails...
Status: ✅ Processing completed successfully!
Status: ❌ Error occurred: ...
Status: ⏸️ Processing paused (Ctrl+C)
```

**Progress Bar:**

- Tiến trình hiện tại (0-100%)
- Thời gian đã dùng
- Thời gian còn lại (ước tính)

**Log Output:**

- Hiển thị thông báo chi tiết
- Cuộn tự động theo thông báo mới
- Các màu sắc khác nhau:
  - 🟢 Xanh lá: Thành công (✓)
  - 🔴 Đỏ: Lỗi (❌)
  - 🟡 Vàng: Cảnh báo (⚠️)
  - 🔵 Xanh dương: Thông tin (ℹ️)

### Ví dụ quy trình GUI

**Bước 1: Chọn mode**

```
Mode: ● Direct
```

**Bước 2: Nhập URL**

```
Input: https://example.com/stream.m3u8
```

**Bước 3: Chọn thư mục output**

```
Output Directory: E:\MyVideos
```

**Bước 4: Nhập tên thư mục nhóm**

```
Group Folder: lesson_1
```

**Bước 5: Chọn file cần lưu**

```
✓ Save Video
✓ Save Audio
✓ Save VTT
✓ Create Thumbnails
```

**Bước 6: Cấu hình thumbnails**

```
Interval: 5 seconds
Size: 160 x 90 pixels
Cols: 10
Format: WebP
CDN URL: [để trống]
```

**Bước 7: Chọn ngôn ngữ**

```
Language: Tiếng Việt
Model: small
GPU: Auto
```

**Bước 8: Click Start**

```
Status: GPU detected - NVIDIA RTX 3060
🔄 Downloading video... (23%)
✓ Downloaded 1.2GB
🎵 Extracting audio...
✓ Audio extracted: 250MB
🎤 Transcribing (model: small)...
✓ Transcription completed
🎨 Creating sprite sheet...
✓ Sprite sheet created (120 frames)

✅ Processing completed!
Output: E:\MyVideos\lesson_1\
```

---

---

## 💻 Cách 3: Sử dụng Command Line Interface (CLI)

CLI cho phép tự động hóa và chạy script mà không cần interactive menu.

### Cú pháp cơ bản

```powershell
python .\main_cli.py [options]
```

hoặc từ Python trực tiếp:

```powershell
python .\main.py --m3u8 "URL" --output-dir "PATH" [more options]
```

### Các tuỳ chọn CLI chi tiết

#### **Chế độ xử lý**

| Flag     | Mô tả                  | Giá trị               | Ví dụ                                      |
| -------- | ---------------------- | --------------------- | ------------------------------------------ |
| `--mode` | Chế độ xử lý           | `direct` hoặc `batch` | `--mode direct`                            |
| `--m3u8` | URL m3u8 (Direct Mode) | URL hoặc file         | `--m3u8 "https://example.com/stream.m3u8"` |
| `--json` | File JSON (Batch Mode) | File path             | `--json "input.json"`                      |

**Ví dụ Direct Mode:**

```powershell
python .\main.py --m3u8 "https://example.com/stream.m3u8"
```

**Ví dụ Batch Mode:**

```powershell
python .\main.py --mode batch --json "input.json"
```

#### **Cấu hình đầu ra**

| Flag              | Mô tả                   | Giá trị           | Ví dụ                      |
| ----------------- | ----------------------- | ----------------- | -------------------------- |
| `--output-dir`    | Thư mục lưu trữ         | Đường dẫn thư mục | `--output-dir "E:\Videos"` |
| `--group-name`    | Tên thư mục nhóm        | Tên thư mục       | `--group-name "lesson_1"`  |
| `--output-prefix` | Tiền tố tên file output | Tên               | `--output-prefix "movie"`  |

**Ví dụ:**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\MyVideos" `
  --group-name "bai_1"
```

**Kết quả**: `E:\MyVideos\bai_1\`

#### **Chọn file cần lưu**

| Flag           | Mô tả           | Giá trị                 |
| -------------- | --------------- | ----------------------- |
| `--save-video` | Lưu file video  | (flag, không cần value) |
| `--save-audio` | Lưu file audio  | (flag, không cần value) |
| `--save-vtt`   | Lưu file phụ đề | (flag, không cần value) |

**Ví dụ:**

```powershell
# Lưu tất cả
python .\main.py --m3u8 "..." --save-video --save-audio --save-vtt

# Chỉ lưu phụ đề
python .\main.py --m3u8 "..." --save-vtt

# Chỉ lưu video + audio
python .\main.py --m3u8 "..." --save-video --save-audio
```

**Ghi chú**: Nếu không chỉ định flag `--save-*`, script sẽ hỏi qua interactive menu.

#### **Ngôn ngữ và Mô hình**

| Flag         | Mô tả              | Giá trị                      | Ví dụ             |
| ------------ | ------------------ | ---------------------------- | ----------------- |
| `--language` | Ngôn ngữ nhận dạng | Mã ISO 639-1                 | `--language "vi"` |
| `--model`    | Mô hình Whisper    | tiny/base/small/medium/large | `--model "small"` |
| `--no-gpu`   | Bắt buộc dùng CPU  | (flag)                       | `--no-gpu`        |

**Mã ngôn ngữ phổ biến:**

- `vi` - Tiếng Việt ⭐
- `en` - Tiếng Anh
- `ja` - Tiếng Nhật
- `ko` - Tiếng Hàn
- `zh` - Tiếng Trung
- `th` - Tiếng Thái
- `id` - Tiếng Indonesia

**Mô hình Whisper (mặc định: small):**

- `tiny` - ~39MB, nhanh nhất, chất lượng thấp
- `base` - ~140MB, nhanh, chất lượng trung bình
- `small` - ~466MB, cân bằng ⭐ (khuyến nghị)
- `medium` - ~1.5GB, chậm, chất lượng tốt
- `large` - ~2.9GB, chậm nhất, chất lượng tốt nhất

**Ví dụ:**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --language "vi" `
  --model "small"

# Dùng CPU (không GPU)
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --language "en" `
  --no-gpu
```

#### **Cấu hình Sprite Sheet Thumbnails**

| Flag                   | Mô tả              | Giá trị       | Mặc định    |
| ---------------------- | ------------------ | ------------- | ----------- |
| `--create-thumbnails`  | Tạo sprite sheet   | (flag)        | Không tạo   |
| `--thumbnail-interval` | Khoảng cách (giây) | Số            | 5           |
| `--thumb-width`        | Chiều rộng (px)    | Số            | 160         |
| `--thumb-height`       | Chiều cao (px)     | Số            | 90          |
| `--thumb-cols`         | Số cột             | Số            | 10          |
| `--thumb-format`       | Định dạng ảnh      | webp hoặc jpg | webp        |
| `--cdn-url`            | URL CDN            | URL           | (tương đối) |

**Ví dụ 1: Sprite sheet mặc định**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --create-thumbnails
```

**Ví dụ 2: Sprite sheet tùy chỉnh**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --create-thumbnails `
  --thumbnail-interval 3 `
  --thumb-width 120 `
  --thumb-height 68 `
  --thumb-cols 12 `
  --thumb-format "jpg"
```

**Ví dụ 3: Với URL CDN**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --create-thumbnails `
  --thumb-format "webp" `
  --cdn-url "https://cdn.example.com/videos/sprite.webp"
```

### Ví dụ CLI chi tiết

#### **Ví dụ 1: Direct Mode - Lưu đầy đủ**

```powershell
python .\main.py `
  --mode direct `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\MyVideos" `
  --group-name "tutorial_01" `
  --language "vi" `
  --model "small" `
  --save-video `
  --save-audio `
  --save-vtt
```

**Kết quả:**

```
E:\MyVideos\tutorial_01\
├── video.mp4
├── audio.wav
└── movie_vi.vtt
```

#### **Ví dụ 2: Direct Mode - Chỉ phụ đề**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\Subtitles" `
  --save-vtt `
  --language "vi"
```

**Kết quả:**

```
E:\Subtitles\
└── movie_vi.vtt
```

#### **Ví dụ 3: Direct Mode - Video + Sprite Sheet**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\VideoPlayer" `
  --group-name "video_1" `
  --save-video `
  --save-vtt `
  --create-thumbnails `
  --thumbnail-interval 5 `
  --thumb-format "webp"
```

**Kết quả:**

```
E:\VideoPlayer\video_1\
├── video.mp4
├── movie_vi.vtt
├── thumbnails.vtt
└── thumbnails/
    └── sprite.webp
```

#### **Ví dụ 4: Batch Mode**

File `input.json`:

```json
{
  "root_path": "E:\\Videos\\Series",
  "items": [
    {
      "slug": "ep-01",
      "m3u8_url": "https://example.com/ep1.m3u8",
      "folder_name": "episode_01"
    },
    {
      "slug": "ep-02",
      "m3u8_url": "https://example.com/ep2.m3u8",
      "folder_name": "episode_02"
    }
  ]
}
```

**Chạy batch:**

```powershell
python .\main.py `
  --mode batch `
  --json "input.json" `
  --language "vi" `
  --model "small" `
  --save-video `
  --save-vtt
```

**Kết quả:**

```
E:\Videos\Series\
├── ep-01\
│   └── episode_01\
│       ├── video.mp4
│       └── movie_vi.vtt
└── ep-02\
    └── episode_02\
        ├── video.mp4
        └── movie_vi.vtt
```

#### **Ví dụ 5: Tối ưu cho tốc độ (GPU + Model nhỏ)**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\Fast" `
  --model "tiny" `
  --language "vi" `
  --save-vtt
```

**Ưu điểm:** Xử lý nhanh hơn ~5x so với large model

#### **Ví dụ 6: Tối ưu cho chất lượng**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\HighQuality" `
  --model "large" `
  --language "vi" `
  --save-vtt
```

**Ưu điểm:** Độ chính xác cao nhất, phù hợp tài liệu quan trọng

#### **Ví dụ 7: Lưu tất cả + Sprite sheet CDN**

```powershell
python .\main.py `
  --m3u8 "https://example.com/stream.m3u8" `
  --output-dir "E:\Complete" `
  --group-name "full_video" `
  --save-video `
  --save-audio `
  --save-vtt `
  --create-thumbnails `
  --thumbnail-interval 3 `
  --thumb-cols 8 `
  --thumb-format "webp" `
  --cdn-url "https://cdn.example.com/videos/full_video/sprite.webp" `
  --language "vi" `
  --model "medium"
```

**Kết quả:** File đầy đủ + sprite sheet tối ưu cho web

### Batch processing từ script

Tạo file `process.bat` để xử lý nhiều URL:

```batch
@echo off
REM Process multiple videos
python .\main.py --m3u8 "https://example.com/video1.m3u8" --group-name "video_1" --language "vi" --save-vtt
python .\main.py --m3u8 "https://example.com/video2.m3u8" --group-name "video_2" --language "vi" --save-vtt
python .\main.py --m3u8 "https://example.com/video3.m3u8" --group-name "video_3" --language "vi" --save-vtt
```

**Chạy:**

```powershell
.\process.bat
```

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

**Lần cập nhật cuối**: 29 tháng 4 năm 2026 (v1.3.0)

---

## Changelog

### v1.3.0 (29/04/2026)

- **[Documentation]** Cập nhật hướng dẫn sử dụng chi tiết cho tất cả 3 cách sử dụng:
  - **Menu Tương tác (Interactive Mode)**:
    - Chi tiết từng bước nhập dữ liệu
    - Giải thích chi tiết 8 tùy chọn lưu file
    - Quy trình cấu hình Sprite Sheet Thumbnails
    - Hướng dẫn chọn ngôn ngữ và mô hình
    - Ví dụ gợi ý dùng lặp lại
  - **Giao diện GUI (main_gui.py)**:
    - Trình bày chi tiết các phần UI
    - Hướng dẫn 7 bước sử dụng GUI
    - Screenshot ASCII art của giao diện
    - Giải thích từng control button
    - Status và Log output chi tiết
    - Ví dụ quy trình GUI đầy đủ
  - **Command Line Interface (CLI)**:
    - Bảng tham khảo flags cấu trúc theo chức năng
    - Giải thích chi tiết mỗi parameter
    - 7 ví dụ CLI thực tế:
      - Direct Mode lưu đầy đủ
      - Direct Mode chỉ phụ đề
      - Direct Mode với sprite sheet
      - Batch Mode xử lý
      - Tối ưu tốc độ
      - Tối ưu chất lượng
      - Lưu tất cả + sprite sheet CDN
    - Ví dụ batch processing từ .bat script
- **[Improvement]** Cấu trúc Mục lục mới phản ánh 3 cách sử dụng chính
- **[Content]** Thêm bảng tham khảo ngôn ngữ và mô hình Whisper với thông số
- **[Content]** Thêm ví dụ output structure chi tiết cho mỗi scenario

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
