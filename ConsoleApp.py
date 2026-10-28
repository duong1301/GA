import json
import pathlib
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit

# Ép mã hóa UTF-8 cho console, nếu không thì tiếng Việt sẽ lỗi trên Windows
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from model.AlgorithmParameters import ParameterError, normalize as normalize_parameters
from model.Configuration import Configuration
from algorithm.GeneticAlgorithm import GeneticAlgorithm
from HtmlOutput import HtmlOutput
from Trace import Trace as Tracer


def resolve_input_path(file_name):
    """Trả về đường dẫn tệp cấu hình, hỗ trợ cả đường dẫn tương đối và tuyệt đối."""
    candidate = pathlib.Path(file_name)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    return str(pathlib.Path.cwd() / file_name.lstrip("/\\"))


def report_path_for(file_name):
    """Tạo đường dẫn tệp HTML trong thư mục tạm, giữ tên tệp cấu hình."""
    name = pathlib.Path(file_name).name
    if name.lower().endswith(".json"):
        name = name[:-5] + ".htm"
    elif not name.lower().endswith((".htm", ".html")):
        name += ".htm"
    return pathlib.Path(tempfile.gettempdir()) / name


def write_report(report_path, html_result):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html_result, encoding="utf-8")


def run_schedule(file_name, parameters=None):
    """Chạy thuật toán và trả về (HTML, số giây, thông số đã áp dụng)."""
    start_time = int(round(time.time() * 1000))

    configuration = Configuration()
    configuration.parseFile(resolve_input_path(file_name))
    parameters = normalize_parameters(
        parameters,
        configuration.numberOfCourseClasses,
    )

    # In toàn bộ thông tin đầu vào trước khi chạy thuật toán
    Tracer.input(configuration, file_name)

    alg = GeneticAlgorithm(
        configuration,
        numberOfCrossoverPoints=parameters["numberOfCrossoverPoints"],
        mutationSize=parameters["mutationSize"],
        crossoverProbability=parameters["crossoverProbability"],
        mutationProbability=parameters["mutationProbability"],
        maxIterations=parameters["maxIterations"],
        maxStagnation=parameters["maxStagnation"],
        numberOfChromosomes=parameters["numberOfChromosomes"],
        replaceByGeneration=parameters["replaceByGeneration"],
        trackBest=parameters["trackBest"],
    )
    print("GaSchedule phiên bản 1.2.6. Lập thời khóa biểu bằng", alg, ".\n")
    print("Bản quyền (C) 2022 - 2024 Miller Cy Chan.\n")
    print(
        "Thông số: {} cá thể · {} thế hệ tối đa · dừng sau {} thế hệ "
        "· lai {}% · đột biến {}%.\n".format(
            parameters["numberOfChromosomes"],
            parameters["maxIterations"],
            parameters["maxStagnation"],
            parameters["crossoverProbability"],
            parameters["mutationProbability"],
        )
    )
    Tracer.reset()
    alg.run(minFitness=parameters["minFitness"])

    # In lịch giảng dạy của từng giảng viên theo lời giải tốt nhất
    Tracer.professors(alg.result)

    html_result = HtmlOutput.getResult(
        alg.result,
        history=Tracer.get_history(),
        parameters=parameters,
    )

    seconds = (int(round(time.time() * 1000)) - start_time) / 1000.0
    return html_result, seconds, parameters


class ReportRequestHandler(BaseHTTPRequestHandler):
    """Phục vụ báo cáo HTML và nhận yêu cầu chạy lại từ nút trên trang."""

    server_version = "GaScheduleReport/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Không làm rối console bằng log truy cập của trình duyệt.
        return

    def _send_bytes(self, body, content_type, status=200, include_body=True):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.end_headers()
        if include_body and body:
            self.wfile.write(body)

    def _send_json(self, payload, status=200, include_body=True):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(
            body,
            "application/json; charset=utf-8",
            status=status,
            include_body=include_body,
        )

    def _serve_report(self, include_body=True):
        path = unquote(urlsplit(self.path).path)

        if path == "/favicon.ico":
            self._send_bytes(b"", "image/x-icon", status=204, include_body=False)
            return

        allowed_paths = {
            "/",
            "/index.html",
            "/report.htm",
            "/" + self.server.report_name,
        }
        if path not in allowed_paths:
            self._send_json(
                {"ok": False, "error": "Không tìm thấy trang."},
                status=404,
                include_body=include_body,
            )
            return

        body = self.server.html_result.encode("utf-8")
        self._send_bytes(
            body,
            "text/html; charset=utf-8",
            include_body=include_body,
        )

    def do_GET(self):
        self._serve_report(include_body=True)

    def do_HEAD(self):
        self._serve_report(include_body=False)

    def do_POST(self):
        path = unquote(urlsplit(self.path).path)
        if path != "/rerun":
            self._send_json(
                {"ok": False, "error": "Không tìm thấy thao tác."},
                status=404,
            )
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            self._send_json(
                {"ok": False, "error": "Độ dài dữ liệu không hợp lệ."},
                status=400,
            )
            return

        if content_length < 0:
            self._send_json(
                {"ok": False, "error": "Độ dài dữ liệu không hợp lệ."},
                status=400,
            )
            return

        if content_length > 65536:
            self.close_connection = True
            self._send_json(
                {"ok": False, "error": "Dữ liệu thông số quá lớn."},
                status=413,
            )
            return

        raw_body = self.rfile.read(content_length) if content_length else b""
        try:
            request_data = (
                json.loads(raw_body.decode("utf-8")) if raw_body else {}
            )
            if not isinstance(request_data, dict):
                raise ValueError
        except (UnicodeDecodeError, ValueError):
            self._send_json(
                {"ok": False, "error": "Dữ liệu thông số không hợp lệ."},
                status=400,
            )
            return

        requested = request_data.get("parameters", {})
        if requested is None:
            requested = {}
        if not isinstance(requested, dict):
            self._send_json(
                {"ok": False, "error": "Thông số thuật toán không hợp lệ."},
                status=400,
            )
            return

        server = self.server
        # Giữ các thông số hiện tại nếu trang cũ chỉ gửi một phần dữ liệu.
        parameters = dict(server.parameters)
        parameters.update(requested)

        if not server.rerun_lock.acquire(blocking=False):
            self._send_json(
                {"ok": False, "error": "Đang có một lần chạy lại khác, vui lòng đợi."},
                status=409,
            )
            return

        payload = None
        status = 200
        try:
            print("\nĐang chạy lại thuật toán...", flush=True)
            html_result, seconds, applied = run_schedule(
                server.file_name,
                parameters,
            )
            write_report(server.report_path, html_result)
            server.html_result = html_result
            server.parameters = applied
            print(
                "Đã cập nhật báo cáo tại {} trong {:.2f} giây.\n".format(
                    server.report_path, seconds
                ),
                flush=True,
            )
            payload = {
                "ok": True,
                "seconds": round(seconds, 2),
                "parameters": applied,
            }
        except ParameterError as exc:
            status = 400
            payload = {"ok": False, "error": str(exc)}
        except Exception as exc:
            traceback.print_exc()
            status = 500
            payload = {
                "ok": False,
                "error": str(exc) or exc.__class__.__name__,
            }
        finally:
            server.rerun_lock.release()

        self._send_json(payload, status=status)


class ReportServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, report_path, file_name, html_result,
                 parameters):
        super().__init__(server_address, ReportRequestHandler)
        self.report_path = pathlib.Path(report_path)
        self.report_name = self.report_path.name
        self.file_name = file_name
        self.html_result = html_result
        self.parameters = dict(parameters)
        self.rerun_lock = threading.Lock()


def serve_report(report_path, file_name, html_result, parameters):
    """Mở báo cáo qua localhost để nút Chạy lại có thể gọi lại thuật toán."""
    server = ReportServer(
        ("127.0.0.1", 0),
        report_path,
        file_name,
        html_result,
        parameters,
    )
    host, port = server.server_address[:2]
    url = "http://{}:{}/{}".format(host, port, quote(server.report_name, safe=""))

    print("Báo cáo đang chạy tại: {}".format(url))
    print("Nút 'Chạy lại' và phần 'Thông số thuật toán' dùng tệp cấu hình hiện tại.")
    print("Nhấn Ctrl+C để dừng máy chủ.\n")

    try:
        webbrowser.open(url)
    except Exception:
        traceback.print_exc()

    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()


def main(file_name, serve=True):
    html_result, seconds, parameters = run_schedule(file_name)
    report_path = report_path_for(file_name)
    write_report(report_path, html_result)

    print("\nHoàn thành trong {:.2f} giây.".format(seconds))
    print("Báo cáo: {}\n".format(report_path))

    if serve:
        serve_report(report_path, file_name, html_result, parameters)
        return

    print("Chế độ tĩnh: nút 'Chạy lại' cần ConsoleApp.py đang chạy.")
    try:
        webbrowser.open(report_path.as_uri())
    except Exception:
        traceback.print_exc()


def print_usage():
    print("Cách dùng: python ConsoleApp.py [tệp_cấu_hình.json] [--no-serve]")
    print("  --no-serve  chỉ tạo báo cáo HTML tĩnh, không mở máy chủ chạy lại.")
    print("  Thông số thuật toán có thể chỉnh trực tiếp trên báo cáo HTML.")


def parse_args(argv):
    serve = True
    positional = []
    for arg in argv:
        if arg in ("--no-serve", "--once"):
            serve = False
        elif arg in ("-h", "--help"):
            print_usage()
            raise SystemExit(0)
        elif arg.startswith("-"):
            raise SystemExit("Tham số không hợp lệ: {}".format(arg))
        else:
            positional.append(arg)

    if len(positional) > 1:
        raise SystemExit("Chỉ nhận một tệp cấu hình.")

    file_name = positional[0] if positional else "/GaSchedule.json"
    return file_name, serve


if __name__ == "__main__":
    file_name, serve = parse_args(sys.argv[1:])

    try:
        main(file_name, serve=serve)
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")
    except:
        traceback.print_exc()
