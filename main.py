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
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.text import Text
from rich import box
from rich.style import Style
from rich.live import Live
from rich.status import Status

# Initialize Rich console
console = Console()

def check_ffmpeg():
    """Kiểm tra FFmpeg đã cài đặt chưa"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(Panel(
            "[bold red]LỖI:[/bold red] Không tìm thấy FFmpeg!\n\n"
            "[yellow]Vui lòng cài đặt FFmpeg:[/yellow]\n"
            "   • Windows: https://www.gyan.dev/ffmpeg/builds/\n"
            "   • Thêm vào PATH hoặc đặt trong thư mục script",
            title="[bold red]FFmpeg Not Found[/bold red]",
            border_style="red"
        ))
        sys.exit(1)


def check_gpu():
    """Kiểm tra GPU và CUDA"""
    try:
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_count = torch.cuda.device_count()
            console.print(f"[bold green]GPU được phát hiện:[/bold green] [cyan]{gpu_name}[/cyan] [yellow](x{gpu_count})[/yellow]")
            return True
        else:
            console.print("[yellow]Không tìm thấy GPU, sẽ dùng CPU (chậm hơn)[/yellow]")
            return False
    except Exception as e:
        console.print(f"[yellow]Lỗi kiểm tra GPU:[/yellow] [red]{e}[/red]")
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
    console.print("\n[bold cyan]Đang tải video từ m3u8...[/bold cyan]")
    try:
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
                        except:
                            pass
            except:
                pass
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        # Sử dụng Rich Progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="cyan", finished_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Đang tải video...", total=100)
            
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    
                    line = line.strip()
                    
                    if line.startswith("out_time_ms="):
                        try:
                            time_ms = int(line.split("=")[1])
                            current_time = time_ms / 1_000_000
                            
                            if current_time > last_time:
                                last_time = current_time
                                
                                if duration_found and duration > 0:
                                    percent = (current_time / duration) * 100
                                    progress.update(task, completed=percent, description=f"Đang tải video ({int(current_time)}s / {int(duration)}s)")
                                elif duration_found:
                                    progress.update(task, description=f"Đã phát hiện video ({int(duration)}s)")
                        except:
                            pass
            except KeyboardInterrupt:
                progress.stop()
                raise
        
        return_code = process.wait()
        stderr_thread.join(timeout=1)
        
        if return_code != 0:
            stderr_output = process.stderr.read() if process.stderr else ""
            raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr_output)
        
        console.print(f"[bold green]✓ Tải video thành công[/bold green]")
        return output_path
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Đã hủy tải video bởi người dùng[/yellow]")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                console.print("[dim]Đã xóa file tạm[/dim]")
            except:
                pass
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        console.print(Panel(
            f"[bold red]LỖI:[/bold red] Không thể tải video từ URL\n"
            f"[dim]{m3u8_url}[/dim]\n\n"
            f"[yellow]Gợi ý:[/yellow] Kiểm tra URL m3u8 và kết nối internet"
            + (f"\n\n[red]Chi tiết:[/red] {str(e.stderr)[:200]}" if hasattr(e, 'stderr') and e.stderr else ""),
            title="[bold red]Download Error[/bold red]",
            border_style="red"
        ))
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]❌ LỖI:[/bold red] [red]{str(e)}[/red]")
        sys.exit(1)


def extract_audio(video_path: str, audio_path: str = "audio.wav") -> str:
    console.print("\n[bold magenta]Đang tách audio...[/bold magenta]")
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
            console.print("   [yellow]Timeout khi lấy duration, sẽ hiển thị tiến độ theo thời gian[/yellow]")
            duration = 0
        except Exception as e:
            console.print(f"   [yellow]Lỗi nhỏ khi probe:[/yellow] [red]{e}[/red]")
            duration = 0
        
        # Extract audio with progress
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", "-progress", "pipe:1", audio_path
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True, bufsize=1)
        
        last_time = 0
        
        # Sử dụng Rich Progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold magenta]{task.description}"),
            BarColumn(complete_style="magenta", finished_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Đang tách audio...", total=100)
            
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    
                    line = line.strip()
                    
                    if line.startswith("out_time_ms="):
                        try:
                            time_ms = int(line.split("=")[1])
                            current_time = time_ms / 1_000_000
                            
                            if current_time > last_time:
                                last_time = current_time
                                
                                if duration > 0:
                                    percent = (current_time / duration) * 100
                                    progress.update(task, completed=percent, description=f"Đang tách audio ({int(current_time)}s / {int(duration)}s)")
                                else:
                                    progress.update(task, description=f"Đang tách audio ({int(current_time)}s)")
                        except:
                            pass
            except KeyboardInterrupt:
                progress.stop()
                raise
        
        return_code = process.wait(timeout=300)
        
        if return_code != 0:
            try:
                stderr = process.stderr.read()
            except:
                stderr = ""
            raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr)
        
        console.print(f"[bold green]✓ Tách audio thành công[/bold green]")
        return audio_path
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Đã hủy tách audio bởi người dùng[/yellow]")
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                console.print("[dim]Đã xóa file tạm[/dim]")
            except:
                pass
        sys.exit(0)
    except subprocess.TimeoutExpired:
        console.print(Panel(
            "[bold red]LỖI:[/bold red] Timeout khi tách audio (quá 5 phút)",
            title="[bold red]Timeout Error[/bold red]",
            border_style="red"
        ))
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(Panel(
            "[bold red]LỖI:[/bold red] Không thể tách audio từ video\n\n"
            "[yellow]Gợi ý:[/yellow] Kiểm tra file video có lỗi không",
            title="[bold red]Audio Extraction Error[/bold red]",
            border_style="red"
        ))
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]❌ LỖI:[/bold red] [red]{str(e)}[/red]")
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





def display_menu():
    """Hiển thị menu chính với Rich styling"""
    console = Console()
    
    # ASCII Art Logo với gradient màu
    logo = Text()
    logo_text = r"""
██╗      ██████╗ ██╗  ██╗ ██████╗ ██╗  ██╗ ██████╗  ██████╗ ██████╗ ██████╗ ██████╗ ███████╗
╚██╗     ██╔══██╗██║  ██║██╔═══██╗██║  ██║██╔═══██╗██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝
 ╚██╗    ██████╔╝███████║██║   ██║███████║██║   ██║██║     ██║     ██║   ██║██║  ██║█████╗  
 ██╔╝    ██╔═══╝ ██╔══██║██║   ██║██╔══██║██║   ██║██║     ██║     ██║   ██║██║  ██║██╔══╝  
██╔╝     ██║     ██║  ██║╚██████╔╝██║  ██║╚██████╔╝╚██████╗╚██████╗╚██████╔╝██████╔╝███████╗
╚═╝      ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
    """


    
    # Tạo gradient từ cyan sang magenta
    lines = logo_text.strip().split('\n')
    for i, line in enumerate(lines):
        # Tạo màu gradient từ cyan -> blue -> magenta
        color_progress = i / (len(lines) - 1)
        if color_progress < 0.5:
            color = f"rgb({int(0 + color_progress * 2 * 100)},{int(255 - color_progress * 2 * 100)},{255})"
        else:
            progress = (color_progress - 0.5) * 2
            color = f"rgb({int(100 + progress * 155)},{int(155 - progress * 155)},{255})"
        logo.append(line + "\n", style=color)
    
    console.print(logo)
    
    # Subtitle
    subtitle = Text("WHISPER M3U8 TRANSCRIBER BY PHOHOCCODE", style="bold bright_white")
    console.print(Panel(subtitle, box=box.DOUBLE, border_style="bright_cyan"))
    
    console.print()

def transcribe_audio(audio_path: str, model_name: str = "small", lang: Optional[str] = None, task: str = "transcribe", use_gpu: bool = True) -> dict:
    console.print("\n[bold blue]Đang nhận dạng giọng nói bằng Whisper...[/bold blue]")
    try:
        # Xác định device
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        device_color = "green" if device == "cuda" else "yellow"
        console.print(f"   [bold]Dùng:[/bold] [{device_color}]{device.upper()}[/{device_color}]")
        
        # Load model với device
        model = whisper.load_model(model_name, device=device)
        
        # Cấu hình transcribe với các tham số tối ưu
        kwargs = {
            "task": task,
            "verbose": True,
            "fp16": device == "cuda",  # Sử dụng FP16 nếu có GPU
            "condition_on_previous_text": True,  # Cải thiện độ chính xác
            "temperature": 0,  # Giảm randomness, tăng độ chính xác
            "compression_ratio_threshold": 2.4,  # Phát hiện lỗi tốt hơn
            "logprob_threshold": -1.0,  # Lọc kết quả không chắc chắn
            "no_speech_threshold": 0.6,  # Tăng ngưỡng để lọc nhạc/noise
        }
        
        # Nếu chỉ định ngôn ngữ, bắt buộc sử dụng ngôn ngữ đó
        if lang:
            kwargs["language"] = lang
            console.print(f"   [cyan]Ngôn ngữ:[/cyan] [yellow]{lang}[/yellow]")
        else:
            console.print(f"   [yellow]Tự động nhận diện ngôn ngữ[/yellow]")
        
        result = model.transcribe(audio_path, **kwargs)
        
        # Kiểm tra nếu kết quả có vấn đề
        if result.get("language") == "music" or not result.get("text", "").strip():
            console.print("\n[yellow]⚠ Cảnh báo: Whisper phát hiện chủ yếu là nhạc/noise![/yellow]")
            if lang is None:
                console.print("   [yellow]💡 Gợi ý: Hãy chỉ định rõ ngôn ngữ để cải thiện kết quả[/yellow]")
        else:
            console.print(f"\n[bold green]✓ Nhận dạng hoàn tất[/bold green] [dim]({len(result.get('segments', []))} đoạn)[/dim]")
        
        return result
    except KeyboardInterrupt:
        console.print("\n[yellow]Đã hủy nhận dạng giọng nói bởi người dùng[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(Panel(
            f"[bold red]LỖI:[/bold red] Không thể nhận dạng giọng nói\n\n"
            f"[red]Chi tiết:[/red] {e}",
            title="[bold red]Transcription Error[/bold red]",
            border_style="red"
        ))
        sys.exit(1)


def save_subtitles(result: dict, output_vtt: str = "subtitle.vtt") -> None:
    with console.status("[bold yellow]Đang lưu phụ đề...", spinner="dots"):
        vtt_text = result_to_vtt(result)
        with open(output_vtt, "w", encoding="utf-8") as f:
            f.write(vtt_text)
    console.print(f"[bold green]✓ Đã lưu phụ đề:[/bold green] [cyan]{output_vtt}[/cyan]")


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
    console.print(f"\n[bold cyan]Đang tạo sprite sheet[/bold cyan] [dim](mỗi {interval}s, định dạng: {image_format.upper()})[/dim]")
    
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
            console.print("[yellow]Không thể xác định độ dài video[/yellow]")
            return {}
        
        console.print(f"[green]Độ dài video:[/green] [yellow]{int(duration)}s[/yellow]")
        
        # Tính số thumbnails cần tạo
        timestamps = list(range(0, int(duration), interval))
        thumb_count = len(timestamps)
        
        if thumb_count == 0:
            console.print("[yellow]Không có thumbnail nào để tạo[/yellow]")
            return {}
        
        console.print(f"[green]Số thumbnails:[/green] [yellow]{thumb_count}[/yellow]")
        
        # Tạo các thumbnail riêng lẻ trước (tạm thời)
        temp_thumbs = []
        temp_dir = os.path.join(thumb_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Sử dụng Rich Progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(complete_style="cyan", finished_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Tạo thumbnails (mỗi {interval}s)", total=thumb_count)
            
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
                progress.update(task, advance=1)
        
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
        
        # Sử dụng Rich Status cho sprite creation
        with console.status(f"[bold cyan]Đang ghép sprite sheet ({sprite_width}x{sprite_height})...", spinner="dots"):
            subprocess.run(cmd, capture_output=True, check=True)

        console.print(f"[bold green]✓ Đã tạo sprite sheet:[/bold green] [cyan]{sprite_filename}[/cyan]")
        
        # Xóa các thumbnails tạm
        console.print("[dim]Đang xóa thumbnails tạm...[/dim]")
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
        
        console.print(f"[green]Sprite sheet:[/green] [yellow]{cols} cột x {rows} hàng = {thumb_count} thumbnails[/yellow]")
        
        return sprite_info
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Đã hủy tạo sprite sheet bởi người dùng[/yellow]")
        # Cleanup temp files
        console.print("[dim]Đang dọn dẹp...[/dim]")
        for thumb in temp_thumbs:
            if os.path.exists(thumb):
                try:
                    os.remove(thumb)
                except:
                    pass
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass
        return {}
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]LỖI:[/bold red] [red]Không thể tạo sprite sheet[/red]")
        console.print(f"[red]Chi tiết: {e}[/red]")
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
    if not sprite_info:
        console.print("[yellow]⚠ Không có thông tin sprite sheet[/yellow]")
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
    
    with console.status("[bold yellow]Đang lưu file VTT...", spinner="dots"):
        with open(output_vtt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    console.print(f"[bold green]✓ Đã tạo file VTT sprite sheet:[/bold green] [cyan]{output_vtt}[/cyan]")
    console.print(f"   [blue]Sprite URL:[/blue] [dim]{sprite_url}[/dim]")

def main() -> None:
    try:
        display_menu()
        _main()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Bạn đã thoát chương trình[/bold yellow]")
        sys.exit(0)

def _main() -> None:
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
            m3u8_link = console.input("[bold cyan]Nhập link .m3u8:[/bold cyan] ").strip()
        
        if validate_url(m3u8_link):
            break
        else:
            console.print(Panel(
                "[bold red]URL không hợp lệ![/bold red]\n\n"
                "URL phải:\n"
                "   • Bắt đầu bằng [cyan]http://[/cyan] hoặc [cyan]https://[/cyan]\n"
                "   • Chứa đuôi [cyan].m3u8[/cyan]\n\n"
                "[yellow]Ví dụ:[/yellow] [dim]https://example.com/video/index.m3u8[/dim]",
                title="[bold red]Invalid URL[/bold red]",
                border_style="red"
            ))
            m3u8_link = None

    # Chọn thư mục lưu trữ
    output_dir = args.output_dir
    if not output_dir:
        recent = load_recent_paths()
        console.print("\n[bold cyan]Chọn nơi lưu trữ:[/bold cyan]")
        console.print("[yellow]1.[/yellow] Thư mục hiện tại")
        if recent:
            console.print("[yellow]2.[/yellow] Chọn từ các đường dẫn đã dùng trước (gợi ý)")
            console.print("[yellow]3.[/yellow] Nhập đường dẫn tùy chỉnh")
            dir_choice = console.input("[bold green]Chọn (1-3):[/bold green] ").strip()
        else:
            console.print("[yellow]2.[/yellow] Nhập đường dẫn tùy chỉnh")
            dir_choice = console.input("[bold green]Chọn (1-2):[/bold green] ").strip()

        if dir_choice == "1":
            output_dir = os.getcwd()
            console.print(f"[green]Sẽ lưu vào thư mục hiện tại:[/green] [cyan]{output_dir}[/cyan]")
            add_recent_path(output_dir)

        elif dir_choice == "2" and recent:
            # show recent list
            table = Table(title="[bold cyan]Đường dẫn đã dùng trước[/bold cyan]", box=box.ROUNDED)
            table.add_column("#", style="yellow", justify="center")
            table.add_column("Đường dẫn", style="cyan")
            
            for i, p in enumerate(recent, start=1):
                table.add_row(str(i), p)
            table.add_row(str(len(recent)+1), "[yellow]Nhập đường dẫn mới[/yellow]")
            
            console.print(table)
            sel = console.input(f"[bold green]Chọn (1-{len(recent)+1}):[/bold green] ").strip()
            try:
                idx = int(sel)
                if 1 <= idx <= len(recent):
                    output_dir = recent[idx-1]
                    console.print(f"[green]Chọn:[/green] [cyan]{output_dir}[/cyan]")
                    # Ensure exists or ask to create
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                    except Exception:
                        console.print("[yellow]Không thể tạo hoặc truy cập thư mục đã chọn[/yellow]")
                    add_recent_path(output_dir)
                elif idx == len(recent) + 1:
                    # User wants to enter custom path
                    output_dir = None
                else:
                    # Invalid choice, use current directory
                    output_dir = os.getcwd()
                    console.print(f"[yellow]Lựa chọn không hợp lệ, dùng thư mục hiện tại:[/yellow] [cyan]{output_dir}[/cyan]")
                    add_recent_path(output_dir)
            except ValueError:
                # Invalid input, use current directory
                output_dir = os.getcwd()
                console.print(f"[yellow]Lựa chọn không hợp lệ, dùng thư mục hiện tại:[/yellow] [cyan]{output_dir}[/cyan]")
                add_recent_path(output_dir)

        # If output_dir is still None, ask for custom path
        if output_dir is None:
            # custom path input (either choice 2 when no recent, or explicit 3, or fallback)
            while True:
                output_dir = console.input("[bold cyan]Nhập đường dẫn thư mục[/bold cyan] [dim](ví dụ: E:\\Videos\\Subtitles)[/dim]: ").strip()
                # Xóa dấu ngoặc kép nếu user copy-paste từ Windows Explorer
                output_dir = output_dir.strip('"').strip("'")
                # Tạo thư mục nếu chưa tồn tại
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    console.print(f"[green]Sẽ lưu vào:[/green] [cyan]{output_dir}[/cyan]")
                    add_recent_path(output_dir)
                    break
                except Exception as e:
                    console.print(f"[red]Đường dẫn không hợp lệ:[/red] {e}")
                    console.print("[yellow]Vui lòng nhập lại![/yellow]\n")
    else:
        # Tạo thư mục nếu được truyền qua CLI
        try:
            os.makedirs(output_dir, exist_ok=True)
            console.print(f"[green]Sẽ lưu vào:[/green] [cyan]{output_dir}[/cyan]")
            add_recent_path(output_dir)
        except Exception as e:
            console.print(f"[red]Không thể tạo thư mục đầu ra đã truyền:[/red] {e}")
            console.print("[yellow]Sẽ dùng thư mục hiện tại thay thế.[/yellow]")
            output_dir = os.getcwd()
            add_recent_path(output_dir)

    # --- Tùy chọn nhóm 3 file vào thư mục con mới ---
    group_name = args.group_name
    group_dir = None
    # Nếu chưa truyền --group-name, hỏi người dùng
    if not group_name:
        choose_group = console.input("\n[bold cyan]Bạn có muốn nhóm 3 file (video/audio/vtt) vào thư mục mới không?[/bold cyan] [dim](y/N)[/dim]: ").strip().lower()
        if choose_group == "y":
            group_name = console.input("[bold cyan]Nhập tên thư mục nhóm[/bold cyan] [dim](để trống sẽ dùng tên theo thời điểm)[/dim]: ").strip()
            # loại bỏ dấu ngoặc kép nếu copy-paste
            group_name = group_name.strip('"').strip("'")
            if not group_name:
                group_name = f"group_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if group_name:
        try:
            group_dir = os.path.join(output_dir, group_name)
            os.makedirs(group_dir, exist_ok=True)
            console.print(f"[green]Sẽ lưu các file vào:[/green] [cyan]{group_dir}[/cyan]")
        except Exception as e:
            console.print(f"[red]Không thể tạo thư mục nhóm:[/red] {e}")
            console.print("[yellow]Sẽ lưu vào thư mục đầu ra chính.[/yellow]")
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
        table = Table(title="[bold cyan]CHỌN FILE CẦN LƯU[/bold cyan]", box=box.DOUBLE)
        table.add_column("#", style="yellow", justify="center")
        table.add_column("Tùy chọn", style="green")
        
        table.add_row("1", "Video + Audio + VTT (lưu tất cả)")
        table.add_row("2", "Chỉ Video")
        table.add_row("3", "Chỉ Audio")
        table.add_row("4", "Chỉ VTT (Phụ đề)")
        table.add_row("5", "Video + Audio")
        table.add_row("6", "Video + VTT")
        table.add_row("7", "Audio + VTT")
        
        console.print("\n", table)
        choice = console.input("[bold green]Nhập lựa chọn (1-7):[/bold green] ").strip()
        
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
            console.print("[yellow]Lựa chọn không hợp lệ, sẽ lưu tất cả file[/yellow]")
            save_video = save_audio = save_vtt = True
        
        # Hiển thị lựa chọn
        files_to_save = []
        if save_video:
            files_to_save.append("[cyan]Video[/cyan]")
        if save_audio:
            files_to_save.append("[magenta]Audio[/magenta]")
        if save_vtt:
            files_to_save.append("[yellow]VTT (Phụ đề)[/yellow]")
        
        if files_to_save:
            console.print(f"[green]Sẽ lưu:[/green] {', '.join(files_to_save)}")
        else:
            console.print("[yellow]Không có file nào được chọn để lưu![/yellow]")
            console.print("[dim]    (Video và Audio vẫn sẽ được tải về để xử lý, sau đó sẽ bị xóa)[/dim]")


    # --- Tùy chọn tạo thumbnails ---
    create_thumbnails = args.create_thumbnails
    thumbnail_interval = args.thumbnail_interval
    thumb_width = args.thumb_width
    thumb_height = args.thumb_height
    thumb_cols = args.thumb_cols
    thumb_format = args.thumb_format
    cdn_url = args.cdn_url
    
    if not create_thumbnails:
        create_thumb_choice = console.input("\n[bold cyan]Bạn có muốn tạo sprite sheet thumbnails từ video không?[/bold cyan] [dim](y/N)[/dim]: ").strip().lower()
        if create_thumb_choice == "y":
            create_thumbnails = True
            
            # Hỏi khoảng thời gian
            interval_input = console.input(f"[cyan]Nhập khoảng thời gian giữa các thumbnail[/cyan] [dim](giây, mặc định {thumbnail_interval})[/dim]: ").strip()
            if interval_input.isdigit() and int(interval_input) > 0:
                thumbnail_interval = int(interval_input)
            
            # Hỏi kích thước thumbnail
            console.print(f"\n[blue]Kích thước mặc định:[/blue] [yellow]{thumb_width}x{thumb_height}px[/yellow]")
            size_input = console.input("[cyan]Thay đổi kích thước?[/cyan] [dim](Nhấn Enter để giữ mặc định hoặc nhập 'w,h' ví dụ: 160,90)[/dim]: ").strip()
            if size_input and "," in size_input:
                try:
                    w, h = size_input.split(",")
                    thumb_width = int(w.strip())
                    thumb_height = int(h.strip())
                    console.print(f"[green]Đã đặt kích thước:[/green] [yellow]{thumb_width}x{thumb_height}px[/yellow]")
                except:
                    console.print(f"[yellow]Định dạng không hợp lệ, giữ mặc định {thumb_width}x{thumb_height}px[/yellow]")
            
            # Hỏi số cột
            cols_input = console.input(f"[cyan]Số cột trong sprite sheet[/cyan] [dim](mặc định {thumb_cols})[/dim]: ").strip()
            if cols_input.isdigit() and int(cols_input) > 0:
                thumb_cols = int(cols_input)
            
            # Hỏi định dạng ảnh
            console.print(f"\n[bold cyan]Chọn định dạng ảnh:[/bold cyan]")
            console.print(f"  [yellow]1.[/yellow] WebP [dim](nhẹ hơn, chất lượng tốt - khuyến nghị)[/dim]")
            console.print(f"  [yellow]2.[/yellow] JPG [dim](tương thích rộng)[/dim]")
            format_choice = console.input(f"[bold green]Chọn (1-2, mặc định 1):[/bold green] ").strip()
            if format_choice == "2":
                thumb_format = "jpg"
            else:
                thumb_format = "webp"
            
            # Hỏi CDN URL (tùy chọn)
            cdn_input = console.input(f"[cyan]URL CDN cho sprite sheet[/cyan] [dim](Nhấn Enter để bỏ qua)[/dim]: ").strip()
            if cdn_input:
                cdn_url = cdn_input
            
            console.print(f"[green]Sẽ tạo sprite sheet:[/green] [yellow]{thumb_cols} cột, {thumb_width}x{thumb_height}px, {thumb_format.upper()}, mỗi {thumbnail_interval}s[/yellow]")
            if cdn_url:
                console.print(f"[green]Sử dụng CDN URL:[/green] [cyan]{cdn_url}[/cyan]")

    # Menu chọn ngôn ngữ với Rich Table
    language = args.language
    if not language:
        table = Table(title="[bold cyan]CHỌN NGÔN NGỮ NHẬN DẠNG[/bold cyan]", box=box.DOUBLE_EDGE, show_lines=False)
        table.add_column("#", style="yellow", justify="center", width=4)
        table.add_column("Ngôn ngữ", style="green", width=25)
        table.add_column("Mã", style="cyan", justify="center", width=6)
        
        languages = [
            ("1", "Tiếng Việt", "vi"),
            ("2", "Tiếng Anh", "en"),
            ("3", "Tiếng Nhật", "ja"),
            ("4", "Tiếng Hàn", "ko"),
            ("5", "Tiếng Trung", "zh"),
            ("6", "Tiếng Thái", "th"),
            ("7", "Tiếng Indonesia", "id"),
            ("8", "Tự động nhận diện", "auto"),
            ("0", "Nhập mã khác", "custom"),
        ]
        
        for num, name, code in languages:
            table.add_row(num, name, code if code not in ["auto", "custom"] else "")
        
        console.print("\n", table)
        choice = console.input("[bold green]Nhập lựa chọn của bạn:[/bold green] ").strip()
        
        selected = next((lang for lang in languages if lang[0] == choice), None)
        
        if selected:
            if selected[2] == "custom":
                language = console.input("[cyan]Nhập mã ngôn ngữ[/cyan] [dim](ví dụ: fr, de, es)[/dim]: ").strip() or None
                if language:
                    console.print(f"[green]Đã chọn ngôn ngữ:[/green] [yellow]{language}[/yellow]")
            elif selected[2] == "auto":
                language = None
                console.print("[green]Sẽ tự động nhận diện ngôn ngữ[/green]")
            else:
                language = selected[2]
                console.print(f"[green]Đã chọn:[/green] [cyan]{selected[1]}[/cyan]")
        else:
            console.print("[yellow]Lựa chọn không hợp lệ, sẽ dùng auto-detect[/yellow]")
            language = None

    console.print(Panel(
        "[bold green]BẮT ĐẦU XỬ LÝ[/bold green]\n\n"
        "[blue]Lưu ý:[/blue]\n"
        "   • Video và Audio sẽ được tải về để xử lý\n"
        "   • Các file không được chọn sẽ tự động xóa sau khi hoàn tất",
        title="[bold cyan]Processing Started[/bold cyan]",
        border_style="cyan"
    ))

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
    if (not save_video and os.path.exists(video_path)) or (not save_audio and os.path.exists(audio_path)):
        console.print("\n[bold yellow]Đang dọn dẹp...[/bold yellow]")
        
        if not save_video and os.path.exists(video_path):
            os.remove(video_path)
            console.print("   [dim]🗑 Đã xóa file video tạm[/dim]")
        
        if not save_audio and os.path.exists(audio_path):
            os.remove(audio_path)
            console.print("   [dim]🗑 Đã xóa file audio tạm[/dim]")
    
    # Tạo bảng tổng kết kết quả
    table = Table(title="[bold green]✓ HOÀN TẤT![/bold green]", box=box.DOUBLE, show_header=True)
    table.add_column("Loại", style="cyan", justify="center", width=20)
    table.add_column("Tên file", style="yellow", width=40)
    table.add_column("Trạng thái", style="green", justify="center", width=10)
    
    if save_video and os.path.exists(video_path):
        table.add_row("Video", "video.mp4", "✓")
    if save_audio and os.path.exists(audio_path):
        table.add_row("Audio", "audio.wav", "✓")
    if save_vtt and os.path.exists(vtt_path):
        table.add_row("Phụ đề", os.path.basename(vtt_path), "✓")
    if sprite_info and os.path.exists(thumbnail_vtt_path):
        sprite_file = sprite_info.get("sprite_filename", "sprite.jpg")
        thumb_count = sprite_info.get("total_thumbs", 0)
        table.add_row("Sprite Sheet", f"{sprite_file} ({thumb_count} thumbs)", "✓")
        table.add_row("Thumbnail VTT", "thumbnails.vtt", "✓")
    
    console.print("\n")
    console.print(Panel(
        table,
        title=f"[bold cyan]Thư mục: {base_dir}[/bold cyan]",
        border_style="green",
        padding=(1, 2)
    ))
    console.print("")

if __name__ == "__main__":
    main()