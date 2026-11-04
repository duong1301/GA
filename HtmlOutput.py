"""Module dựng báo cáo HTML cho thuật toán xếp thời khoá biểu bằng GA.

HtmlOutput chỉ sinh chuỗi: nhận nhiễm sắc thể tốt nhất (Schedule) và lịch sử
các thế hệ do Trace.get_history() trả về, rồi dựng MỘT trang HTML tự chứa gồm
  - khối đầu trang: quy mô bài toán + độ phù hợp (fitness) của lời giải,
  - chú thích 3 ràng buộc cứng P/G/N và ràng buộc mềm B,
  - dữ liệu đầu vào (giảng viên / lớp học phần / phòng học + lưới giờ bận),
  - thời khoá biểu cuối cùng theo phòng học và theo giảng viên,
  - biểu đồ fitness qua các thế hệ và lưới thế hệ bấm-để-xem-lịch.

CSS (PAGE_STYLE) và JavaScript (PAGE_SCRIPT) được nhúng thẳng vào trang nên
báo cáo xem được ngoại tuyến; riêng lưới thế hệ còn dựng sẵn phía máy chủ để
trang vẫn có lịch khi trình duyệt không chạy JavaScript.
"""

import html
import json
import math
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace

from model.AlgorithmParameters import FIELDS, format_value, normalize, summary
from model.Constant import Constant
from model.Criteria import Criteria
from model.Reservation import Reservation


class HtmlOutput:
    """Lớp tĩnh dựng báo cáo; mọi hàm chỉ đọc lời giải, không biến đổi nó."""

    # Kích thước lưới MỘT bảng lịch, đã tính cả hàng/cột tiêu đề:
    #   ROOM_COLUMN_NUMBER = DAYS_NUM + 1 = 5 + 1 = 6
    #       -> 1 cột nhãn "Tiết" + 5 ngày T2..T6
    #   ROOM_ROW_NUMBER    = DAY_HOURS + 1 = 13 + 1 = 14
    #       -> 1 hàng tiêu đề + 13 offset của một ngày (0..12)
    # Bảng vì thế dùng periodId = offset + 1 (chạy 1..13), khác với Reservation
    # và Professor.BusySlots vốn lưu offset 0-based.
    ROOM_COLUMN_NUMBER = Constant.DAYS_NUM + 1
    ROOM_ROW_NUMBER = Constant.DAY_HOURS + 1
    # Màu huy hiệu tiêu chí: xanh = đạt, đỏ = vi phạm ràng buộc cứng.
    COLOR1 = "#047857"
    COLOR2 = "#b91c1c"
    # Ký hiệu viết tắt của 3 tiêu chí kiểm tra ràng buộc:
    #   P = Phòng học   G = Giảng viên   N = Nghỉ trưa
    # Thứ tự P-G-N trùng đúng thứ tự của Criteria.weights, nên cờ tiêu chí i của
    # lớp thứ k nằm tại Schedule._criteria[k * 3 + i] (len(weights) = 3).
    # Các hàm duyệt lớp vì vậy tăng con trỏ ci thêm len(CRITERIAS) = 3 mỗi lớp.
    CRITERIAS = ('P', 'G', 'N')
    # Ba chuỗi mô tả dưới đây đồng chỉ số với CRITERIAS: phần tử i là nhãn/mô tả
    # của tiêu chí CRITERIAS[i], dùng cho chú thích và tooltip của huy hiệu.
    CRITERIA_LABELS = (
        "Phòng không trùng lịch",
        "Giảng viên không trùng lịch",
        "Không xếp giờ vào khung nghỉ trưa 12h-13h",
    )
    OK_DESCR = (
        "Phòng học không bị trùng lịch",
        "Giảng viên không bị trùng lịch dạy",
        "Lớp không rơi vào khung nghỉ trưa 12h-13h",
    )
    FAIL_DESCR = (
        "Phòng học bị trùng lịch",
        "Giảng viên bị trùng lịch dạy",
        "Lớp bị xếp vào khung nghỉ trưa 12h-13h",
    )

    # Ký hiệu + nhãn của RÀNG BUỘC MỀM tối ưu lịch giảng dạy.
    # B là ràng buộc mềm duy nhất được cài đặt: lớp bị xếp vào khung giờ bận của
    # chính giảng viên được giao, phạt Criteria.busyPenalty = 0.2 điểm và chỉ tính
    # MỘT LẦN cho mỗi lớp (dù dính mấy tiết bận). Nhẹ hơn vi phạm cứng (1.0 điểm).
    SOFT_CRITERIAS = ('B',)
    SOFT_LABELS = ("Tránh khung giờ bận của giảng viên",)
    # Chuỗi 14 nhãn cho 14 hàng bảng, index = periodId (offset 0-based + 1):
    #   PERIODS[0] = "" (hàng tiêu đề), PERIODS[7] = "Nghỉ trưa"
    #   (vì offset nghỉ trưa LUNCH_PERIOD = 6 -> periodId 7).
    PERIODS = ("",) + tuple(
        "Nghỉ trưa" if offset == Constant.LUNCH_PERIOD
        else f"Tiết {Constant.periodNumber(offset)}"
        for offset in range(Constant.DAY_HOURS)
    )
    # Mỗi tiết dài 50 phút và các tiết trong cùng buổi LIỀN NHAU:
    #   Tiết 1: 7:00-7:50, Tiết 2: 7:50-8:40, ... (không có khoảng nghỉ 10 phút)
    # Khung nghỉ trưa là khoảng giữa buổi sáng và buổi chiều.
    # Khung giờ của từng hàng, cùng quy ước index với PERIODS:
    # PERIOD_TIMES[periodId] tra thẳng theo số hàng (periodId = offset + 1).
    PERIOD_TIMES = ("",) + tuple(
        Constant.lunchRange()
        if offset == Constant.LUNCH_PERIOD
        else Constant.periodTimeRange(offset)
        for offset in range(Constant.DAY_HOURS)
    )
    # Nhãn ngày theo day index 0-based của bài toán (T2 = ngày 0); bảng lịch hiển
    # thị theo dayId = ngày + 1 nên vòng lặp cột chạy 1..ROOM_COLUMN_NUMBER-1.
    WEEK_DAYS = ("T2", "T3", "T4", "T5", "T6")
    WEEK_DAY_NAMES = ("Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu")

    # Toàn bộ CSS của báo cáo, nhúng thẳng vào trang để xem được ngoại tuyến.
    # Ba bộ biến --ok/--bad/--soft tương ứng đạt / vi phạm cứng / vi phạm mềm.
    PAGE_STYLE = """<style>
        :root {
            color-scheme: light;
            --bg: #eef2f7;
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --border: #e2e8f0;
            --text: #0f172a;
            --muted: #64748b;
            --brand: #1d4ed8;
            --ok: #047857;
            --ok-bg: #ecfdf5;
            --ok-border: #a7f3d0;
            --bad: #b91c1c;
            --bad-bg: #fef2f2;
            --bad-border: #fecaca;
            /* Ràng buộc mềm vi phạm: màu cam, phân biệt với đỏ của ràng buộc cứng */
            --soft: #c2410c;
            --soft-bg: #fff7ed;
            --soft-border: #fed7aa;
            --soft-fill: #ffedd5;
            --amber-bg: #fffbeb;
            --shadow-lg: 0 24px 60px -32px rgba(15, 23, 42, .45);
            --shadow-sm: 0 10px 30px -22px rgba(15, 23, 42, .4);
        }

        * { box-sizing: border-box; }

        html { -webkit-text-size-adjust: 100%; font-size: 22.4px; }

        body {
            margin: 0;
            min-height: 100vh;
            color: var(--text);
            background:
                radial-gradient(1100px 560px at 8% -8%, #dbeafe 0%, rgba(219, 234, 254, 0) 60%),
                radial-gradient(900px 500px at 100% 0%, #ede9fe 0%, rgba(237, 233, 254, 0) 55%),
                var(--bg);
            font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
            font-size: 21px;
            line-height: 1.55;
        }

        .page {
            width: min(1440px, 100%);
            margin: 0 auto;
            padding: 40px 28px 56px;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 36px 38px 32px;
            color: #fff;
            border-radius: 26px;
            background: linear-gradient(130deg, #0f172a 0%, #172554 52%, #1d4ed8 100%);
            box-shadow: var(--shadow-lg);
        }

        .hero::before,
        .hero::after {
            content: "";
            position: absolute;
            border-radius: 50%;
            pointer-events: none;
        }

        .hero::before {
            width: 420px;
            height: 420px;
            right: -120px;
            top: -210px;
            background: radial-gradient(circle, rgba(96, 165, 250, .45), transparent 68%);
        }

        .hero::after {
            width: 340px;
            height: 340px;
            right: 140px;
            bottom: -240px;
            background: radial-gradient(circle, rgba(167, 139, 250, .38), transparent 70%);
        }

        .hero-content { position: relative; z-index: 1; }

        .hero-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 24px;
        }

        .hero-actions {
            flex: 0 0 auto;
            display: flex;
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
            min-width: 170px;
            max-width: 280px;
        }

        .rerun-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 11px 16px;
            border: 1px solid rgba(255, 255, 255, .38);
            border-radius: 14px;
            background: #fff;
            color: #1e3a8a;
            font: inherit;
            font-size: .88rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 8px 24px rgba(15, 23, 42, .18);
            transition: background .15s ease, transform .15s ease, opacity .15s ease;
        }

        .rerun-button:focus-visible {
            outline: 3px solid rgba(191, 219, 254, .9);
            outline-offset: 3px;
        }

        .rerun-button:disabled {
            cursor: wait;
            opacity: .72;
            transform: none;
        }

        .eyebrow {
            margin: 0 0 10px;
            font-size: .78rem;
            font-weight: 700;
            letter-spacing: .16em;
            text-transform: uppercase;
            color: #bfdbfe;
        }

        .hero h1 {
            margin: 0;
            font-size: clamp(1.8rem, 3vw, 2.6rem);
            line-height: 1.1;
            letter-spacing: -.02em;
        }

        .subtitle {
            margin: 12px 0 0;
            color: #dbeafe;
            max-width: 720px;
        }

        .score {
            flex: 0 0 auto;
            min-width: 150px;
            padding: 14px 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, .22);
            border-radius: 18px;
            background: rgba(255, 255, 255, .1);
            backdrop-filter: blur(6px);
        }

        .score-value {
            display: block;
            font-size: 1.9rem;
            font-weight: 700;
            letter-spacing: -.02em;
        }

        .score-label {
            display: block;
            margin-top: 2px;
            font-size: .72rem;
            font-weight: 600;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: #bfdbfe;
        }

        .score.perfect .score-value { color: #86efac; }

        .stats {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 26px 0 0;
            padding: 0;
            list-style: none;
            position: relative;
            z-index: 1;
        }

        .stat {
            display: flex;
            align-items: baseline;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 999px;
            background: rgba(255, 255, 255, .12);
            border: 1px solid rgba(255, 255, 255, .16);
        }

        .stat strong { font-size: 1rem; }

        .stat span {
            font-size: .78rem;
            color: #dbeafe;
        }

        .legend {
            position: sticky;
            top: 0;
            z-index: 30;
            margin: 22px 0 0;
            padding: 18px 22px;
            background: rgba(255, 255, 255, .96);
            border: 1px solid rgba(226, 232, 240, .9);
            border-radius: 18px;
            box-shadow: var(--shadow-sm);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }

        .legend-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px 18px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }

        .legend h2 {
            margin: 0;
            font-size: .83rem;
            letter-spacing: .1em;
            text-transform: uppercase;
            color: var(--muted);
        }

        .legend-items {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .legend-item {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 6px 11px 6px 7px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface-soft);
            font-size: .82rem;
        }

        .legend-note {
            margin: 0;
            font-size: .78rem;
            color: var(--muted);
        }

        .legend-ok { color: var(--ok); font-weight: 700; }
        .legend-bad { color: var(--bad); font-weight: 700; }
        .legend-soft { color: var(--soft); font-weight: 700; }

        .crit {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 19px;
            height: 19px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: #f1f5f9;
            color: #475569;
            font-size: .68rem;
            font-weight: 800;
            line-height: 1;
            letter-spacing: 0;
        }

        .crit.ok {
            color: var(--ok);
            background: var(--ok-bg);
            border-color: var(--ok-border);
        }

        .crit.bad {
            color: var(--bad);
            background: var(--bad-bg);
            border-color: var(--bad-border);
        }

        /* --- Ràng buộc mềm (soft constraints) --- */
        .legend-subhead {
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px dashed var(--border);
        }

        .legend-subhead h3 {
            margin: 0 0 4px;
            font-size: .78rem;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: var(--muted);
        }

        .legend-item--soft {
            align-items: flex-start;
            border-style: dashed;
        }

        .crit--soft {
            color: var(--soft);
            background: var(--soft-bg);
            border-color: var(--soft-border);
        }

        .soft-body {
            display: inline-flex;
            flex-direction: column;
            gap: 2px;
            line-height: 1.35;
        }

        .soft-value {
            font-size: .72rem;
            color: var(--muted);
        }

        /* --- Lưới chọn lịch bận (weekly grid) --- */
        .busy-grid-section {
            margin-top: 14px;
        }

        .busy-grid-block {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface-soft);
            padding: 12px 14px;
            margin-bottom: 14px;
        }

        .busy-grid-title {
            font-size: .82rem;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text, #0f172a);
        }

        .busy-grid {
            /* Chỉ là khung đóng gói các hàng lưới. Mỗi .busy-row đã tự
               xây lưới cột đầy đủ (display: grid), nên .busy-grid không
               nên cũng là grid container — nếu không các hàng sẽ bị lồng
               lưới và dồn vào một cột duy nhất, không hiển thị dạng lưới.
               overflow-x: trên màn hẹp mỗi cột vẫn tối thiểu 34px, lưới
               trượt ngang thay vì co chữ chồng lên nhau. */
            display: block;
            overflow-x: auto;
            padding-bottom: 2px;
        }

        .busy-row {
            display: grid;
            grid-template-columns: 34px repeat(12, minmax(34px, 1fr));
            gap: 4px;
            align-items: center;
            width: max-content;
            min-width: 100%;
        }

        .busy-corner,
        .busy-rowlabel,
        .busy-col {
            font-size: .68rem;
            color: var(--muted);
            text-align: center;
            align-self: center;
        }

        .busy-corner {
            font-weight: 700;
        }

        /* Cột của lưới chọn giờ bận ghi số tiết và giờ bắt đầu, hai hàng xếp
           dọc trong ô hẹp, để ô được chọn khớp tuyệt đối với dòng bảng lịch. */
        .busy-col {
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 0;
            gap: 1px;
            line-height: 1.1;
        }

        .busy-col-name {
            font-weight: 700;
        }

        .busy-col-time {
            font-size: .55rem;
            white-space: nowrap;
        }

        .busy-rowlabel {
            font-weight: 700;
            font-size: .72rem;
        }

        .busy-cell {
            height: 22px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: #fff;
            cursor: pointer;
            padding: 0;
            position: relative;
        }

        .busy-cell .busy-dot {
            display: block;
            width: 100%;
            height: 100%;
            border-radius: 6px;
            background: #e2e8f0;
        }

        .busy-cell.is-busy {
            border-color: var(--soft);
            background: var(--soft-fill); /* cam nhạt: khung GV bận, không phải vi phạm cứng */
            border-width: 2px;
            cursor: pointer;
        }

        .busy-cell.is-busy .busy-dot {
            background: var(--soft);
        }

        .busy-cell[aria-pressed="true"] {
            border-color: var(--soft);
            background: var(--soft-fill);
            border-width: 2px;
        }

        .busy-cell[aria-pressed="true"] .busy-dot {
            background: var(--soft);
        }

        .rooms {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 24px;
            margin-top: 26px;
        }

        .room {
            min-width: 0;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 22px;
            box-shadow: var(--shadow-sm);
            overflow: hidden;
        }

        .room-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            flex-wrap: wrap;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(180deg, #fff, #f8fafc);
        }

        .room-kicker {
            display: block;
            font-size: .7rem;
            font-weight: 700;
            letter-spacing: .14em;
            text-transform: uppercase;
            color: var(--brand);
        }

        .room-head h2 {
            margin: 2px 0 0;
            font-size: 1.3rem;
            letter-spacing: -.01em;
        }

        .room-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface-soft);
            font-size: .8rem;
            font-weight: 600;
            color: #334155;
        }

        .badge::before {
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--brand);
        }

        .badge.badge-muted::before { background: #94a3b8; }

        .table-wrap { overflow-x: auto; }

        .scroll-hint {
            display: none;
            margin: 0;
            padding: 10px 18px 0;
            color: var(--muted);
            font-size: .74rem;
        }

        @media (max-width: 1020px) {
            .scroll-hint { display: block; }
        }

        table.schedule {
            width: 100%;
            min-width: 960px;
            border-collapse: collapse;
            table-layout: fixed;
            font-size: .9rem;
        }

        .schedule thead th {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            background: #f8fafc;
            color: #334155;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-align: center;
            text-transform: uppercase;
        }

        .schedule thead th + th { border-left: 1px solid var(--border); }

        .schedule thead .corner {
            width: 132px;
            text-align: left;
            color: var(--muted);
        }

        .schedule thead .day {
            display: block;
            color: var(--text);
            font-size: .9rem;
            letter-spacing: .02em;
        }

        .schedule thead .day-name {
            display: block;
            margin-top: 1px;
            color: var(--muted);
            font-size: .66rem;
            font-weight: 600;
            letter-spacing: .02em;
            text-transform: none;
        }

        .schedule tbody th,
        .schedule tbody td {
            border-bottom: 1px solid var(--border);
            border-left: 1px solid var(--border);
            vertical-align: top;
        }

        .schedule tbody tr:last-child th,
        .schedule tbody tr:last-child td { border-bottom: 0; }

        .schedule tbody th:first-child,
        .schedule tbody td:first-child { border-left: 0; }

        .schedule tbody th.period {
            width: 132px;
            padding: 12px 14px;
            background: #fbfdff;
            font-weight: 600;
            text-align: left;
            white-space: nowrap;
        }

        .period-name {
            display: block;
            color: var(--text);
            font-size: .88rem;
        }

        .period-time {
            display: block;
            margin-top: 1px;
            color: var(--muted);
            font-size: .72rem;
            font-weight: 500;
        }

        .schedule td.slot { padding: 10px 12px; }
        .schedule td.empty { background: #fff; }

        /* Ô trống nhưng giảng viên bận (không dạy được) — sọc cam,
           thống nhất với màu của ràng buộc mềm (đỏ chỉ dành cho ràng buộc cứng) */
        .schedule td.empty.busy {
            background: repeating-linear-gradient(
                135deg, var(--soft-bg), var(--soft-bg) 7px,
                var(--soft-fill) 7px, var(--soft-fill) 14px);
        }

        .schedule tbody tr:nth-child(even) td.empty:not(.busy) { background: #fbfcfe; }

        /* Hàng khung giờ nghỉ trưa 12h-13h */
        .schedule tbody tr.lunch > .period .period-name {
            color: var(--muted);
            font-style: italic;
        }

        .schedule tbody tr.lunch > td.empty {
            background: repeating-linear-gradient(
                135deg, #f8fafc, #f8fafc 9px, #eef2f7 9px, #eef2f7 18px);
        }

        .schedule td.filled {
            background: #fff;
            transition: background .15s ease;
        }

        .schedule td.filled.conflict {
            background: #fffafa;
        }

        /* Lớp bị xếp vào khung giờ giảng viên bận (vi phạm ràng buộc MỀM):
           nền cam nhạt + viền trong cam, tách biệt hoàn toàn với đỏ của ràng buộc cứng */
        .schedule td.filled.busy-soft {
            background: var(--soft-bg);
            box-shadow: inset 0 0 0 2px var(--soft-border);
        }

        .course {
            color: var(--text);
            font-size: .95rem;
            font-weight: 700;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }

        .prof {
            margin-top: 2px;
            color: var(--muted);
            font-size: .8rem;
            overflow-wrap: anywhere;
        }

        .tags {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 7px;
        }

        .tag {
            display: inline-flex;
            align-items: center;
            padding: 2px 7px;
            border-radius: 999px;
            font-size: .67rem;
            font-weight: 600;
            line-height: 1.5;
        }

        .tag-duration {
            color: #475569;
            background: #f1f5f9;
            border: 1px solid var(--border);
        }

        .tag-room {
            color: #6d28d9;
            background: #f5f3ff;
            border: 1px solid #ddd6fe;
        }

        .prof-item > summary {
            cursor: pointer;
            list-style: none;
        }

        .prof-item > summary::-webkit-details-marker {
            display: none;
        }

        .prof-item > summary::marker {
            content: "";
        }

        .prof-item > summary::after {
            content: "▾";
            color: var(--muted);
            font-size: .9rem;
        }

        .prof-item[open] > summary::after {
            content: "▴";
        }

        .crits {
            display: flex;
            gap: 4px;
            margin-top: 8px;
        }

        .slot-stack {
            display: flex;
            flex-direction: column;
        }

        .course-card { min-width: 0; }

        .course-card + .course-card {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px dashed var(--border);
        }

        .course-card.continued .course { font-size: .87rem; }
        .course-card.continued .prof { font-size: .76rem; }
        .course-card.continued .tags { margin-top: 4px; }
        .course-card.continued .crits { margin-top: 5px; }

        .slot-warning {
            display: inline-flex;
            align-items: center;
            align-self: flex-start;
            gap: 5px;
            margin-bottom: 7px;
            padding: 2px 7px;
            border: 1px solid var(--bad-border);
            border-radius: 999px;
            background: var(--bad-bg);
            color: var(--bad);
            font-size: .66rem;
            font-weight: 700;
            line-height: 1.4;
        }

        .slot-warning::before {
            content: "!";
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--bad);
            color: #fff;
            font-size: .6rem;
            line-height: 1;
        }

        /* Nhãn vi phạm ràng buộc mềm (xếp vào khung giảng viên bận) */
        .slot-warning--soft {
            border-color: var(--soft-border);
            background: var(--soft-fill);
            color: var(--soft);
        }

        .slot-warning--soft::before {
            content: "B";
            background: var(--soft);
            font-size: .55rem;
            font-weight: 800;
        }

        .badge.badge--busy {
            color: var(--soft);
            background: var(--soft-bg);
            border-color: var(--soft-border);
        }

        .badge.badge--busy::before { background: var(--soft); }

        .tag-continued {
            color: #92400e;
            background: var(--amber-bg);
            border: 1px solid #fde68a;
        }

        .result-section {
            margin-top: 28px;
        }

        .section-head {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 12px 24px;
            flex-wrap: wrap;
            padding: 0 4px;
        }

        .section-kicker {
            margin: 0 0 4px;
            font-size: .7rem;
            font-weight: 800;
            letter-spacing: .14em;
            text-transform: uppercase;
            color: var(--brand);
        }

        .section-head h2 {
            margin: 0;
            font-size: 1.22rem;
            letter-spacing: -.01em;
        }

        .section-note {
            margin: 0;
            color: var(--muted);
            font-size: .78rem;
        }

        .result-section .rooms {
            margin-top: 16px;
        }

        .result-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            width: fit-content;
            margin-top: 18px;
            padding: 6px;
            background: var(--surface-soft);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 14px;
        }

        .result-tab {
            appearance: none;
            border: 0;
            background: transparent;
            padding: 9px 18px;
            border-radius: 10px;
            font: inherit;
            font-size: .82rem;
            font-weight: 700;
            color: var(--muted);
            cursor: pointer;
            transition: background .15s ease, color .15s ease,
                        box-shadow .15s ease;
        }

        .result-tab[aria-selected="true"] {
            background: var(--surface);
            color: var(--brand);
            box-shadow: var(--shadow-sm);
        }

        .result-tab:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        .result-panel {
            margin-top: 16px;
        }

        .result-panel .rooms {
            margin-top: 0;
        }

        .result-panel[hidden] {
            display: none;
        }

        .tab-note {
            margin: 0 4px 12px;
            color: var(--muted);
            font-size: .78rem;
        }

        .input-section {
            margin-top: 28px;
            overflow: hidden;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 22px;
            box-shadow: var(--shadow-sm);
        }

        .input-summary {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px 24px;
            flex-wrap: wrap;
            padding: 20px 24px;
            cursor: pointer;
            list-style: none;
        }

        .input-summary::-webkit-details-marker { display: none; }
        .input-summary::marker { content: ""; }

        .input-summary::after {
            content: "▾";
            margin-left: 2px;
            color: var(--muted);
            font-size: .9rem;
            transition: transform .15s ease;
        }

        .input-section[open] .input-summary {
            border-bottom: 1px solid var(--border);
        }

        .input-section[open] .input-summary::after {
            transform: rotate(180deg);
        }

        .input-summary h2,
        .settings-heading h2 {
            margin: 0;
            font-size: 1.22rem;
            letter-spacing: -.01em;
        }

        .input-summary-meta {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .input-summary-note {
            margin: 0;
            color: var(--muted);
            font-size: .78rem;
        }

        .input-body {
            padding: 0 18px 20px;
        }

        .settings-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 18px 28px;
            flex-wrap: wrap;
            padding: 20px 24px;
        }

        .settings-heading {
            min-width: 0;
        }

        .settings-summary-note {
            margin: 6px 0 0;
            color: var(--muted);
            font-size: .78rem;
            line-height: 1.5;
        }

        .settings-header-actions {
            display: flex;
            flex: 0 0 auto;
            flex-direction: column;
            align-items: flex-end;
            gap: 6px;
        }

        .rerun-button--header {
            border-color: #1d4ed8;
            background: #1d4ed8;
            color: #fff;
            box-shadow: 0 8px 18px rgba(29, 78, 216, .18);
        }

        .settings-details {
            border-top: 1px solid var(--border);
        }

        .settings-toggle {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 13px 24px;
            background: #f8fafc;
            color: #475569;
            font-size: .78rem;
            font-weight: 700;
            cursor: pointer;
            list-style: none;
        }

        .settings-toggle::-webkit-details-marker { display: none; }
        .settings-toggle::marker { content: ""; }

        .settings-toggle::after {
            content: "▾";
            color: var(--muted);
            font-size: .9rem;
            transition: transform .15s ease;
        }

        .settings-details[open] .settings-toggle {
            border-bottom: 1px solid var(--border);
        }

        .settings-details[open] .settings-toggle::after {
            transform: rotate(180deg);
        }

        .settings-body {
            padding: 18px 24px 22px;
        }

        .settings-note {
            margin: 0 0 16px;
            color: var(--muted);
            font-size: .84rem;
            line-height: 1.55;
        }

        .settings-note strong {
            color: #334155;
        }

        .settings-form {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
        }

        .setting-field {
            display: flex;
            flex-direction: column;
            gap: 7px;
            min-width: 0;
            padding: 14px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: #f8fafc;
        }

        .setting-label {
            color: #0f172a;
            font-size: .82rem;
            font-weight: 700;
            line-height: 1.35;
        }

        .setting-control {
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
        }

        .setting-control input {
            width: 100%;
            min-width: 0;
            padding: 8px 10px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            background: #fff;
            color: #0f172a;
            font: inherit;
            font-size: .9rem;
        }

        .setting-control input:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, .15);
        }

        .setting-unit {
            flex: 0 0 auto;
            color: var(--muted);
            font-size: .72rem;
            white-space: nowrap;
        }

        .setting-help {
            color: var(--muted);
            font-size: .7rem;
            line-height: 1.4;
        }

        .settings-status {
            max-width: 340px;
            margin: 0;
            min-height: 1.1em;
            color: var(--muted);
            font-size: .75rem;
            line-height: 1.4;
            overflow-wrap: anywhere;
            text-align: right;
        }

        .settings-status.error {
            color: #b91c1c;
        }

        .input-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin-top: 16px;
        }

        .input-card {
            min-width: 0;
            overflow: hidden;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 18px;
            box-shadow: var(--shadow-sm);
        }

        .input-card--wide {
            grid-column: 1 / -1;
        }

        .input-card-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
        }

        .input-card-head h3 {
            margin: 0;
            font-size: .92rem;
        }

        .input-card-head .badge {
            padding: 4px 10px;
            font-size: .72rem;
        }

        .input-table-wrap {
            overflow-x: auto;
        }

        .input-table {
            width: 100%;
            border-collapse: collapse;
            font-size: .8rem;
        }

        .input-table th,
        .input-table td {
            padding: 9px 14px;
            text-align: left;
            vertical-align: top;
            border-top: 1px solid var(--border);
        }

        .input-table thead th {
            border-top: 0;
            background: var(--surface-soft);
            color: var(--muted);
            font-size: .68rem;
            letter-spacing: .045em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .input-table tfoot td {
            border-top: 2px solid var(--border);
            background: var(--surface-soft);
            font-weight: 600;
        }

        .input-table .num {
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }

        .history-section {
            margin-top: 28px;
            overflow: hidden;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 22px;
            box-shadow: var(--shadow-sm);
        }

        .history-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px 20px;
            flex-wrap: wrap;
            padding: 22px 24px 12px;
        }

        .history-head h2 {
            margin: 0;
            font-size: 1.22rem;
            letter-spacing: -.01em;
        }

        .history-intro {
            margin: 0;
            padding: 0 24px 16px;
            color: var(--muted);
            font-size: .78rem;
        }

        .history-scroll-hint {
            display: none;
            margin: 0;
            padding: 0 16px 12px;
            color: var(--muted);
            font-size: .72rem;
        }

        .chart-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            padding: 0 24px 8px;
            color: var(--muted);
            font-size: .72rem;
        }

        .chart-legend span {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .chart-legend span::before {
            content: "";
            width: 16px;
            height: 3px;
            border-radius: 999px;
            background: var(--brand);
        }

        .chart-legend .chart-key-final::before {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--brand);
            box-shadow: 0 0 0 2px #fff, 0 0 0 3px var(--brand);
        }

        .chart-legend .chart-key-best::before {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--ok);
            box-shadow: 0 0 0 2px #fff, 0 0 0 3px var(--ok);
        }

        .fitness-chart-wrap {
            padding: 0 18px 4px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        .fitness-chart {
            display: block;
            width: 100%;
            min-width: 720px;
            height: auto;
            overflow: visible;
        }

        .fitness-chart text { font-family: inherit; }

        .chart-grid {
            stroke: #e2e8f0;
            stroke-width: 1;
        }

        .chart-grid-v { stroke: #eef2f7; }

        .chart-axis-label {
            fill: #64748b;
            font-size: 16.8px;
            font-variant-numeric: tabular-nums;
        }

        .chart-area { fill: url(#fitness-area); }

        .chart-line {
            fill: none;
            stroke: var(--brand);
            stroke-width: 2.5;
            stroke-linecap: round;
            stroke-linejoin: round;
        }

        .chart-dot {
            fill: #fff;
            stroke: var(--brand);
            stroke-width: 1.5;
        }

        .chart-final-dot {
            fill: var(--brand);
            stroke: #fff;
            stroke-width: 2;
        }

        .chart-best-dot {
            fill: var(--ok);
            stroke: #fff;
            stroke-width: 2;
        }

        .chart-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
            padding: 14px 24px 20px;
        }

        .chart-stat {
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface-soft);
        }

        .chart-stat span {
            display: block;
            color: var(--muted);
            font-size: .66rem;
            font-weight: 700;
            letter-spacing: .06em;
            text-transform: uppercase;
        }

        .chart-stat strong {
            display: block;
            margin-top: 2px;
            color: var(--text);
            font-size: 1.05rem;
            font-variant-numeric: tabular-nums;
        }

        .chart-stat small {
            display: block;
            margin-top: 1px;
            color: var(--muted);
            font-size: .68rem;
        }

        .chart-stat.is-max strong { color: var(--ok); }
        .chart-stat.is-final strong { color: var(--brand); }

        .count-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            min-width: 48px;
            padding: 3px 8px;
            border: 1px solid transparent;
            border-radius: 999px;
            font-size: .7rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }

        .count-pill strong { font-weight: 800; }

        .count-pill.ok {
            color: var(--ok);
            background: var(--ok-bg);
            border-color: var(--ok-border);
        }

        .count-pill.bad {
            color: var(--bad);
            background: var(--bad-bg);
            border-color: var(--bad-border);
        }

        .steps-section {
            margin-top: 28px;
        }

        /* Lưới nhiều hàng nên cuộn bên trong khung, không đẩy trang dài. */
        .step-grid-wrap {
            max-height: var(--step-grid-height, 430px);
            overflow: auto;
            overscroll-behavior: contain;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
            margin-top: 16px;
            padding: 2px 2px 6px;
            border-radius: 14px;
            background: var(--surface-soft);
            border: 1px solid var(--border);
        }

        .step-grid-wrap::-webkit-scrollbar { width: 10px; height: 10px; }

        .step-grid-wrap::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border: 3px solid transparent;
            border-radius: 999px;
            background-clip: content-box;
        }

        .step-grid-wrap::-webkit-scrollbar-track { background: transparent; }

        /* Lưới các thế hệ: mỗi hàng 10 ô, mỗi ô là một thế hệ. */
        .step-grid {
            display: grid;
            grid-template-columns: repeat(10, minmax(0, 1fr));
            gap: 8px;
            min-width: 840px;
        }

        .step-cell {
            display: flex;
            flex-direction: column;
            gap: 3px;
            padding: 9px 9px 8px;
            text-align: left;
            font: inherit;
            cursor: pointer;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 12px;
            box-shadow: var(--shadow-sm);
            transition: border-color .15s ease, box-shadow .15s ease,
                        transform .15s ease, background .15s ease;
        }

        .step-cell:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        .cell-gen {
            font-size: .64rem;
            font-weight: 700;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: var(--muted);
        }

        .cell-fit {
            font-size: .98rem;
            font-weight: 800;
            color: var(--text);
            font-variant-numeric: tabular-nums;
            line-height: 1.1;
        }

        .cell-fit.is-perfect { color: var(--ok); }

        .cell-vio {
            font-size: .7rem;
            color: var(--muted);
            font-variant-numeric: tabular-nums;
        }

        .cell-vio.has-violation { color: var(--bad); font-weight: 700; }

        .cell-crits {
            display: flex;
            flex-wrap: wrap;
            gap: 3px;
        }

        .cell-crit {
            padding: 1px 4px;
            border: 1px solid transparent;
            border-radius: 6px;
            font-size: .62rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }

        .cell-crit.ok {
            color: var(--ok);
            background: var(--ok-bg);
            border-color: var(--ok-border);
        }

        .cell-crit.bad {
            color: var(--bad);
            background: var(--bad-bg);
            border-color: var(--bad-border);
        }

        .step-cell.is-perfect {
            background: linear-gradient(180deg, #fff, var(--ok-bg));
            border-color: var(--ok-border);
        }

        .step-cell.is-best {
            border-color: #fcd34d;
            box-shadow: inset 0 0 0 1px #fcd34d, var(--shadow-sm);
        }

        .step-cell[aria-selected="true"] {
            background: #eff6ff;
            border-color: var(--brand);
            box-shadow: 0 0 0 2px rgba(29, 78, 216, .2), var(--shadow-sm);
            transform: translateY(-1px);
        }

        .step-cell.is-perfect[aria-selected="true"] {
            background: linear-gradient(180deg, #eff6ff, var(--ok-bg));
            border-color: var(--brand);
        }

        .step-panel {
            overflow: hidden;
            margin-top: 14px;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 16px;
            box-shadow: var(--shadow-sm);
        }

        .step-panel[hidden] { display: none; }

        .step-panel-head {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px 14px;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            background: #f8fbff;
        }

        .step-panel-title {
            display: flex;
            flex: 1 1 220px;
            flex-direction: column;
            min-width: 150px;
            line-height: 1.3;
        }

        .step-panel-kicker {
            font-size: .66rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: var(--brand);
        }

        .step-panel-title h3 {
            margin: 2px 0 0;
            font-size: 1rem;
            color: var(--text);
        }

        .step-panel-meta {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px 12px;
            color: var(--muted);
            font-size: .76rem;
            font-variant-numeric: tabular-nums;
        }

        .step-panel-fit { color: var(--brand); font-weight: 700; }

        .step-panel-vio { color: var(--muted); }

        .step-panel-vio.has-violation { color: var(--bad); font-weight: 700; }

        .step-panel-body { padding: 16px 18px 18px; }

        .step-panel .rooms {
            gap: 16px;
            margin-top: 0;
        }

        .step-panel .room {
            border-radius: 16px;
            box-shadow: none;
        }

        .step-panel .room-head { padding: 14px 18px; }

        .step-panel .room-head h2 { font-size: 1.1rem; }

        .empty-state {
            margin-top: 26px;
            padding: 60px 24px;
            text-align: center;
            color: var(--muted);
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 22px;
        }

        .footer {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 28px;
            padding: 0 4px;
            color: var(--muted);
            font-size: .76rem;
        }

        .footer strong { color: #334155; }

        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }

        @media (max-width: 720px) {
            .page { padding: 20px 12px 36px; }
            .hero { padding: 26px 22px 24px; border-radius: 20px; }
            .hero-row { flex-direction: column; }
            .hero-actions { width: 100%; max-width: none; }
            .score { width: 100%; }
            .room-head { padding: 16px 18px; align-items: flex-start; }
            .room-badges { width: 100%; }
            .legend {
                top: 0;
                padding: 10px 12px;
                border-radius: 14px;
            }
            .legend-head { margin-bottom: 6px; gap: 4px 12px; }
            .legend h2 { font-size: .72rem; }
            .legend-note { font-size: .68rem; }
            .legend-items {
                flex-wrap: nowrap;
                overflow-x: auto;
                padding-bottom: 2px;
                scrollbar-width: none;
                -webkit-overflow-scrolling: touch;
            }
            .legend-items::-webkit-scrollbar { display: none; }
            .legend-item {
                flex: 0 0 auto;
                padding: 4px 8px 4px 5px;
                font-size: .74rem;
            }
            .section-head { align-items: flex-start; }
            .history-head { padding: 18px 16px 10px; }
            .history-intro { padding: 0 16px 14px; }
            .history-scroll-hint { display: block; }
            .chart-legend { padding: 0 16px 8px; }
            .fitness-chart-wrap { padding: 0 10px 2px; }
            .chart-stats { padding: 12px 16px 16px; }
            .step-panel-head { padding: 13px 14px; gap: 8px 10px; }
            .step-panel-meta { width: 100%; }
            .step-panel-body { padding: 12px; }
            .step-panel .rooms { gap: 12px; }
            .step-panel .room-head { padding: 12px 14px; }
            .input-summary { padding: 16px 14px; }
            .input-summary h2,
            .settings-heading h2 { font-size: 1.08rem; }
            .input-body { padding: 0 12px 16px; }
            .settings-header { padding: 16px 14px; }
            .settings-header-actions { width: 100%; align-items: stretch; }
            .settings-header-actions .rerun-button { width: 100%; }
            .settings-status { text-align: left; }
            .settings-toggle { padding: 12px 14px; }
            .settings-body { padding: 16px 12px; }
            .input-grid { grid-template-columns: 1fr; }
            .settings-grid { grid-template-columns: 1fr; }
        }

        @media print {
            body {
                background: #fff;
                font-size: 15.4px;
            }

            .page {
                max-width: none;
                padding: 0;
            }

            .hero {
                color: #0f172a;
                background: #fff;
                border: 1px solid #cbd5e1;
                box-shadow: none;
            }

            .hero::before,
            .hero::after { display: none; }

            .eyebrow,
            .subtitle,
            .score-label,
            .stat span { color: #475569; }

            .score,
            .stat {
                border-color: #cbd5e1;
                background: #f8fafc;
            }

            .score.perfect .score-value,
            .score-value { color: #0f172a; }

            .legend {
                position: static;
                box-shadow: none;
            }

            .rerun-button { display: none; }

            .result-section { margin-top: 18px; }
            .result-section .rooms { margin-top: 12px; }
            .input-section,
            .history-section,
            .steps-section { display: none; }

            .rooms { gap: 14px; }

            .room {
                box-shadow: none;
                break-inside: avoid;
            }

            .table-wrap { overflow: visible; }
            table.schedule { min-width: 0; }
        }

        @media (prefers-reduced-motion: reduce) {
            * { transition: none !important; }
        }
    </style>"""

    PAGE_SCRIPT = """<script>
        (() => {
            const form = document.getElementById("ga-parameters");
            const buttons = Array.from(document.querySelectorAll("[data-rerun]"));
            const statuses = Array.from(
                document.querySelectorAll("[data-rerun-status]")
            );
            if (!buttons.length || !statuses.length) return;

            const setStatus = (message, isError = false) => {
                statuses.forEach(status => {
                    status.textContent = message;
                    status.classList.toggle("error", isError);
                });
            };

            const setBusy = busy => {
                buttons.forEach(button => {
                    button.disabled = busy;
                });
            };

            const isFile = window.location.protocol === "file:";
            if (isFile) {
                setStatus("Mở báo cáo qua ConsoleApp.py để dùng nút này.", true);
            }

            const readParameters = () => {
                if (!form) return {};
                if (!form.checkValidity()) {
                    const details = form.closest("details");
                    if (details) details.open = true;
                    form.reportValidity();
                    throw new Error("Vui lòng kiểm tra lại thông số.");
                }
                const parameters = {};
                form.querySelectorAll("input[name]").forEach(input => {
                    const value = Number(input.value);
                    if (!Number.isFinite(value)) {
                        throw new Error(
                            "Giá trị của " + input.name + " không hợp lệ."
                        );
                    }
                    parameters[input.name] = value;
                });
                return parameters;
            };

            const rerun = async () => {
                if (isFile) {
                    setStatus(
                        "Hãy chạy ConsoleApp.py để mở báo cáo qua máy chủ cục bộ rồi thử lại.",
                        true
                    );
                    return;
                }

                let parameters;
                try {
                    parameters = readParameters();
                } catch (error) {
                    setStatus(error.message, true);
                    return;
                }

                setBusy(true);
                setStatus("Đang chạy thuật toán mới…");
                const request = { parameters };
                // Chi gui khoa "busy" khi trang co luoi chon gio ban: danh sach
                // rong co nghia la da bo het, khong phai la "khong thay doi".
                if (window.collectBusy) {
                    request.busy = window.collectBusy();
                }
                try {
                    const response = await fetch("/rerun", {
                        method: "POST",
                        headers: {
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify(request),
                        cache: "no-store",
                    });
                    let data = {};
                    try {
                        data = await response.json();
                    } catch (error) {
                        // Giữ thông báo mặc định nếu máy chủ không trả JSON.
                    }
                    if (!response.ok) {
                        throw new Error(data.error || ("HTTP " + response.status));
                    }
                    setStatus("Hoàn tất. Đang tải lại báo cáo…");
                    window.location.reload();
                } catch (error) {
                    const message = error instanceof TypeError
                        ? "Không kết nối được máy chủ. Hãy chạy ConsoleApp.py rồi mở lại trang."
                        : error.message;
                    setStatus("Không chạy được: " + message, true);
                    setBusy(false);
                }
            };

            buttons.forEach(button => button.addEventListener("click", rerun));
            if (form) {
                form.addEventListener("submit", event => {
                    event.preventDefault();
                    rerun();
                });
            }
        })();

        // --- Chọn lịch bận (lưới tuần): click ô để bật/tắt khung giờ bận ---
        (() => {
            const grids = Array.from(document.querySelectorAll(".busy-grid"));
            if (!grids.length) return;

            const collectBusy = () => {
                const byProf = {};
                grids.forEach(gridEl => {
                    const profId = gridEl.getAttribute("data-prof");
                    const slots = [];
                    gridEl.querySelectorAll(".busy-row").forEach(rowEl => {
                        const dayAttr = rowEl.getAttribute("data-day");
                        if (dayAttr === null) return;
                        const dayNum = Number(dayAttr);
                        if (!Number.isInteger(dayNum)) return;
                        rowEl.querySelectorAll(".busy-cell").forEach(cellEl => {
                            const time = Number(cellEl.getAttribute("data-time"));
                            const busy = cellEl.classList.contains("is-busy");
                            if (busy) slots.push({ day: dayNum, start: time, end: time });
                        });
                    });
                    // Ghi cả giảng viên không còn ô bận nào (blocks = []) để máy
                    // chủ phân biệt "đã bỏ hết" với "trang này không có lưới".
                    const byDay = {};
                    slots.forEach(s => {
                        const arr = byDay[s.day] || [];
                        arr.push(s);
                        byDay[s.day] = arr;
                    });
                    const blocks = [];
                    Object.keys(byDay).forEach(d => {
                        const arr = (byDay[d] || []).sort((a, b) => a.start - b.start);
                        let start = arr[0].start;
                        let end = arr[0].end;
                        for (let i = 1; i < arr.length; i++) {
                            if (arr[i].start === end + 1) { end = arr[i].end; }
                            else {
                                blocks.push({ day: Number(d), start: start, end: end });
                                start = arr[i].start; end = arr[i].end;
                            }
                        }
                        blocks.push({ day: Number(d), start: start, end: end });
                    });
                    byProf[profId] = blocks;
                });
                return byProf;
            };

            grids.forEach(gridEl => {
                gridEl.addEventListener("click", event => {
                    const cell = event.target.closest(".busy-cell");
                    if (!cell) return;
                    const profId = cell.getAttribute("data-prof");
                    const day = Number(cell.getAttribute("data-day"));
                    const time = Number(cell.getAttribute("data-time"));
                    document.querySelectorAll(`.busy-grid[data-prof="${profId}"]`).forEach(g => {
                        const c = g.querySelector(`[data-day="${day}"][data-time="${time}"]`);
                        if (!c) return;
                        const willBe = !c.classList.contains("is-busy");
                        c.classList.toggle("is-busy", willBe);
                        c.setAttribute("aria-pressed", String(willBe));
                    });
                });
            });

            window.collectBusy = collectBusy;
        })();

        // Chuyển tab giữa các nhóm tab (lịch theo phòng/giảng viên, dữ liệu đầu vào)
        (() => {
            const tabLists = Array.from(
                document.querySelectorAll('[role="tablist"]')
            );
            tabLists.forEach(list => {
                const tabs = Array.from(list.querySelectorAll(".result-tab"));
                if (!tabs.length) return;

                const select = active => {
                    tabs.forEach(tab => {
                        const selected = tab === active;
                        tab.setAttribute("aria-selected", String(selected));
                        tab.tabIndex = selected ? 0 : -1;
                        const panel = document.getElementById(
                            tab.getAttribute("aria-controls")
                        );
                        if (panel) panel.hidden = !selected;
                    });
                };

                tabs.forEach((tab, index) => {
                    tab.addEventListener("click", () => select(tab));
                    tab.addEventListener("keydown", event => {
                        const steps = { ArrowLeft: -1, ArrowRight: 1 };
                        if (!(event.key in steps)) return;
                        event.preventDefault();
                        const next = tabs[
                            (index + steps[event.key] + tabs.length) % tabs.length
                        ];
                        next.focus();
                        select(next);
                    });
                });
            });
        })();
        // Thời khóa biểu của từng thế hệ: bấm một ô trong lưới để xem ở dưới.
        // Đây là bản dựng phía trình duyệt của getScheduleTable + generateTimeTable,
        // đọc payload do getStepsData sinh ra (id="step-data").
        (() => {
            const source = document.getElementById("step-data");
            const grid = document.getElementById("step-grid");
            const panel = document.getElementById("step-panel");
            const panelBody = document.getElementById("step-panel-body");
            if (!source || !grid || !panel || !panelBody) return;

            let data;
            try {
                data = JSON.parse(source.textContent);
            } catch (error) {
                // Giữ nguyên thời khóa biểu đã dựng sẵn phía máy chủ.
                return;
            }

            const letters = data.letters;
            const cells = Array.from(grid.querySelectorAll(".step-cell"));

            const esc = value => String(value).replace(
                /[&<>"]/g,
                character => ({
                    "&": "&amp;",
                    "<": "&lt;",
                    ">": "&gt;",
                    '"': "&quot;",
                })[character]
            );

            const setText = (id, value) => {
                const element = document.getElementById(id);
                if (element) element.textContent = value;
            };

            // Số ô mỗi hàng của lưới thế hệ (CSS khai báo 10 cột), dùng cho phím lên/xuống.
            const columns = () => {
                const value = getComputedStyle(grid).gridTemplateColumns;
                const count = value ? value.split(" ").length : 0;
                return count > 0 ? count : 10;
            };

            // Khung giờ bận của từng giảng viên (ràng buộc mềm, màu cam).
            // Tra theo ID giảng viên — cùng khoá với model, không dùng tên hiển
            // thị vì hai giảng viên trùng tên sẽ dính khung bận của nhau.
            const busyKeys = new Set();
            Object.keys(data.busy || {}).forEach(profId => {
                data.busy[profId].forEach(slot =>
                    busyKeys.add(profId + "|" + slot[0] + "|" + slot[1]));
            });
            // Khoá lưu theo (ngày, OFFSET 0-based); bảng lịch tra theo periodId nên
            // phải trừ 1: periodId = offset + 1, ví dụ offset nghỉ trưa 6 là hàng 7.
            const isBusySlot = (profId, day, periodId) =>
                profId !== null && profId !== undefined &&
                busyKeys.has(profId + "|" + day + "|" + (periodId - 1));
            const profNameOf = profId =>
                (data.profNames || {})[profId] || "—";

            // Số tiết của một offset (0-based), cùng quy ước với periodNumber:
            // sáng offset 0..5 = tiết 1..6, chiều offset 7..12 = tiết 7..12
            // (offset 6 là nghỉ trưa nên không bao giờ được vẽ ở đây).
            const periodNumber = offset =>
                (offset < data.lunch ? offset + 1 : offset);

            const periodTime = (offset, which) => {
                const parts = ((data.periods[offset] || ["", ""])[1]).split("–");
                return which === "start"
                    ? parts[0].trim()
                    : parts[parts.length - 1].trim();
            };

            // Gộp các offset bận thành dải liền mạch trong cùng buổi;
            // khung nghỉ trưa bị loại nên sáng và chiều không bao giờ liền dải.
            const busyRuns = (offsets) => {
                const sorted = [...new Set(offsets)]
                    .filter(offset => offset !== data.lunch)
                    .sort((a, b) => a - b);
                const runs = [];
                sorted.forEach(offset => {
                    const last = runs[runs.length - 1];
                    if (last && offset === last[last.length - 1] + 1) {
                        last.push(offset);
                    } else {
                        runs.push([offset]);
                    }
                });
                return runs;
            };

            const busyLabel = runs => {
                if (!runs.length) return "tiết bận";
                return "tiết " + runs.map(run => {
                    const first = periodNumber(run[0]);
                    const last = periodNumber(run[run.length - 1]);
                    return first === last ? String(first) : first + "-" + last;
                }).join(", ");
            };

            const busyTimes = runs => runs.map(run =>
                periodTime(run[0], "start") + "-" +
                periodTime(run[run.length - 1], "end")
            ).join(", ");

            // period_ids là periodId 1-based -> trừ 1 về offset rồi tách dải bận,
            // giống getBusyChip phía Python (mức phạt mềm B = 0.2 điểm/lớp).
            const busyChip = (periodIds) => {
                const runs = busyRuns(periodIds.map(periodId => periodId - 1));
                return '<div class="slot-warning slot-warning--soft" title="' +
                    esc("Ràng buộc mềm: lớp rơi vào khung giờ giảng viên bận" +
                        (runs.length ? " (" + busyTimes(runs) + ")" : "")) +
                    '">GV bận · ' + esc(busyLabel(runs)) + "</div>";
            };

            // Huy hiệu P/G/N của một lớp học ở thế hệ đang xem.
            // bits = bước "b" trong payload: chuỗi 0/1, mỗi lớp 3 ký tự theo thứ tự
            // P, G, N; offset = indexLop * letters.length = indexLop * 3 nên cờ của
            // tiêu chí i lấy tại bits.charAt(offset + i) — cùng cách đánh chỉ số với
            // criterias[ci + i] phía Python. letters.length = len(Criteria.weights).
            const criteriaBadges = (bits, offset, busy) => {
                let html = '<div class="crits">';
                for (let i = 0; i < letters.length; i++) {
                    const passed = bits.charAt(offset + i) === "1";
                    const state = passed ? "Đạt" : "Vi phạm";
                    const description = (passed ? data.ok : data.fail)[i];
                    html += '<span class="crit ' + (passed ? "ok" : "bad") +
                        '" title="' + esc(state + ": " + description) +
                        '" aria-label="' +
                        esc(letters[i] + " - " + state + ": " + description) +
                        '">' + letters[i] + "</span>";
                }
                if (busy) {
                    html += '<span class="crit crit--soft" title="' +
                        esc("Vi phạm ràng buộc mềm: lớp rơi vào khung giờ bận") +
                        '" aria-label="' +
                        esc("B - Vi phạm ràng buộc mềm: lớp rơi vào khung giờ bận") +
                        '">B</span>';
                }
                return html + "</div>";
            };

            // Thẻ nội dung một ô: tên môn, tên GV, nhãn số tiết/"Tiếp tiết", rồi huy hiệu.
            // offset là vị trí bộ cờ 3 ký tự của lớp trong step.b (indexLop * 3).
            const courseCard = (courseClass, profId, bits, offset, continued, busy) => {
                let html = '<div class="course">' + esc(courseClass.course) +
                    '</div><div class="prof">' + esc(profNameOf(profId)) + "</div>";
                if (continued) {
                    html += '<div class="tags">' +
                        '<span class="tag tag-continued">Tiếp tiết</span></div>';
                } else if (courseClass.dur > 1) {
                    html += '<div class="tags"><span class="tag tag-duration">' +
                        courseClass.dur + " tiết</span></div>";
                }
                return html + criteriaBadges(bits, offset, busy);
            };

            // Sắp các lớp học vào ô (phòng, ngày, tiết) như phần dựng bảng.
            // step.s[index] = [room, day, time] với cả ba đều 0-based (đúng như mã
            // nhiễm sắc thể); bước sang quy ước bảng phải cộng 1 ở chiều ngày và giờ:
            //   key      = roomId | (day + 1)      -> cột 1..cols-1 (cols = DAYS_NUM+1 = 6)
            //   startPeriod = time + 1             -> hàng 1..rows-1 (rows = DAY_HOURS+1 = 14)
            // roomId vẫn giữ 0-based vì bảng phòng được duyệt theo index cấu hình.
            const collectSlots = step => {
                const slots = new Map();
                step.s.forEach((slot, index) => {
                    const courseClass = data.classes[index];
                    if (!slot || !courseClass) return;
                    const key = slot[0] + "|" + (slot[1] + 1);
                    const startPeriod = slot[2] + 1;
                    // giảng viên được gán ở thế hệ này (ID, đổi theo thế hệ)
                    const profId = step.v ? step.v[index] : courseClass.prof;
                    // Các tiết của lớp rơi vào khung bận của giảng viên được giao.
                    // periodId tăng dần theo offset trong lớp, dừng ở hàng rows-1 = 13.
                    const busyPeriods = [];
                    for (let offset = 0; offset < courseClass.dur; offset++) {
                        const periodId = startPeriod + offset;
                        if (periodId >= data.rows) break;
                        if (isBusySlot(profId, slot[1], periodId)) {
                            busyPeriods.push(periodId);
                        }
                    }
                    for (let offset = 0; offset < courseClass.dur; offset++) {
                        const periodId = startPeriod + offset;
                        if (periodId >= data.rows) break;
                        const bucket = slots.get(key) || {};
                        const list = bucket[periodId] || [];
                        list.push({
                            start: startPeriod,
                            course: courseClass,
                            prof: profId,
                            bits: step.b,
                            // vị trí bộ cờ P/G/N của lớp này trong chuỗi "b": 3 ký tự/lớp
                            offset: index * letters.length,
                            busy: busyPeriods.indexOf(periodId) >= 0,
                            busyPeriods: busyPeriods,
                        });
                        bucket[periodId] = list;
                        slots.set(key, bucket);
                    }
                });

                return { slots };
            };

            // Số tiết liền kề chỉ do một lớp chiếm, không vượt qua bảng hay ô nghỉ trưa.
            // Bản sao phía trình duyệt của HtmlOutput.mergeSpan: dải chỉ mở khi ô kế
            // tiếp có đúng MỘT lớp (length === 1, tức không trùng phòng), không chạm
            // hàng nghỉ trưa lunchPeriod = data.lunch + 1 = 7, không quá dur tiết của
            // lớp và không quá hàng cuối data.rows - 1 = 13.
            const mergeSpan = (entry, periodId, bucket, lunchPeriod) => {
                if (periodId === lunchPeriod) return 1;
                const last = Math.min(
                    entry.start + entry.course.dur - 1, data.rows - 1);
                let span = 1;
                while (periodId + span <= last) {
                    const nextPeriod = periodId + span;
                    if (nextPeriod === lunchPeriod) break;
                    if ((bucket[nextPeriod] || []).length !== 1) break;
                    span += 1;
                }
                return span;
            };

            // Bảng một phòng ở thế hệ đang xem: hàng = periodId 1..rows-1 (1..13),
            // cột = dayId 1..cols-1 (1..5); cols = DAYS_NUM + 1 = 6 vì cột 0 là nhãn tiết.
            // covered[day] ghi các hàng đã bị ô rowspan ở trên nuốt nên không xuất lại.
            const roomTable = (roomId, slots) => {
                const roomName = data.rooms[roomId];
                // nghỉ trưa: offset 6 -> hàng 7 của bảng
                const lunchPeriod = data.lunch + 1;
                const covered = [];
                for (let day = 1; day < data.cols; day++) {
                    covered[day] = new Set();
                }
                let rows = "";

                // hàng 1..13 tương ứng offset 0..12; hàng 7 là nghỉ trưa
                for (let periodId = 1; periodId < data.rows; periodId++) {
                    let cellsHtml = "";
                    for (let dayId = 1; dayId < data.cols; dayId++) {
                        if (covered[dayId].has(periodId)) continue;
                        const bucket = slots.get(roomId + "|" + dayId) || {};
                        const entries = bucket[periodId] || [];
                        if (!entries.length) {
                            cellsHtml += '<td class="slot empty"></td>';
                            continue;
                        }

                        if (entries.length === 1) {
                            const entry = entries[0];
                            const span = mergeSpan(
                                entry, periodId, bucket, lunchPeriod);
                            // chỉ liệt kê tiết bận nằm trong dải vừa gộp của ô này
                            const busyPeriods = (entry.busyPeriods || []).filter(
                                period => period >= periodId &&
                                    period < periodId + span
                            );
                            const soft = busyPeriods.length > 0;
                            // true = ô đầu tiên của lớp; ô sau chỉ ghi nhãn "Tiếp tiết"
                            const first = entry.start === periodId;
                            cellsHtml += '<td class="slot filled' +
                                (soft ? " busy-soft" : "") + '"' +
                                (span > 1 ? ' rowspan="' + span + '"' : "") +
                                ">" +
                                (soft ? busyChip(busyPeriods) : "") +
                                '<div class="course-card' +
                                (first ? "" : " continued") + '">' +
                                courseCard(
                                    entry.course, entry.prof, entry.bits,
                                    entry.offset, !first, soft
                                ) +
                                "</div></td>";
                            for (let period = periodId; period < periodId + span; period++) {
                                // các hàng đã hiển thị trong ô rowspan: bỏ khi gặp lại
                                covered[dayId].add(period);
                            }
                            continue;
                        }

                        // Nhiều lớp trong cùng ô = trùng phòng (vi phạm P): không gộp
                        // rowspan, xếp chồng tất cả trong một slot-stack.
                        let cards = "";
                        let stackBusy = false;
                        if (entries.length > 1) {
                            cards += '<div class="slot-warning">Trùng phòng</div>';
                        }
                        entries.forEach(entry => {
                            const first = entry.start === periodId;
                            if (entry.busy) stackBusy = true;
                            cards += (entry.busy ? busyChip([periodId]) : "") +
                                '<div class="course-card' +
                                (first ? "" : " continued") + '">' +
                                courseCard(
                                    entry.course, entry.prof, entry.bits,
                                    entry.offset, !first, entry.busy
                                ) +
                                "</div>";
                        });
                        cellsHtml += '<td class="slot filled conflict' +
                            (stackBusy ? " busy-soft" : "") + '">' +
                            '<div class="slot-stack">' + cards + "</div></td>";
                    }

                    // periodId - 1 trả về offset 0-based; offset 6 là ô nghỉ trưa
                    const period = data.periods[periodId - 1] || ["", ""];
                    rows += "<tr" +
                        (periodId - 1 === data.lunch ? ' class="lunch"' : "") +
                        ">" +
                        '<th class="period" scope="row">' +
                        '<span class="period-name">' + esc(period[0]) + "</span>" +
                        '<span class="period-time">' + esc(period[1]) + "</span></th>" +
                        cellsHtml + "</tr>";
                }

                const dayHeaders = data.days.map(day =>
                    '<th scope="col"><span class="day">' + esc(day[0]) + "</span>" +
                    '<span class="day-name">' + esc(day[1]) + "</span></th>"
                ).join("");

                return (
                    '<section class="room"><div class="room-head">' +
                    '<div class="room-title"><span class="room-kicker">Phòng học</span>' +
                    "<h2>" + esc(roomName) + "</h2></div></div>" +
                    '<p class="scroll-hint">Vuốt ngang để xem đủ các ngày ' +
                    '<span aria-hidden="true">→</span></p>' +
                    '<div class="table-wrap"><table class="schedule">' +
                    '<caption class="sr-only">Thời khóa biểu phòng ' +
                    esc(roomName) + "</caption>" +
                    "<thead><tr>" +
                    '<th class="corner" scope="col">Tiết / Ngày</th>' +
                    dayHeaders +
                    "</tr></thead><tbody>" + rows + "</tbody></table>" +
                    "</div></section>"
                );
            };

            // Bảng thông số của thế hệ đang chọn ở đầu khung lịch.
            // step.n[i] = số lớp ĐẠT tiêu chí i, step.total = tổng số lớp, nên
            // số vi phạm của tiêu chí i là total - n[i]; tổng ba tiêu chí là
            // "x vi phạm". step.f là fitness đã chuẩn hoá trong [0, 1].
            const updateHead = step => {
                const percent = Math.max(0, Math.min(1, step.f)) * 100;
                const violations = step.n.reduce(
                    (sum, count) => sum + (step.total - count), 0
                );

                setText("step-panel-generation", "Thế hệ " + step.g);
                setText("step-panel-fitness",
                    "Fitness " + step.f.toFixed(6) + " · " + percent.toFixed(1) + "%");

                const pills = document.getElementById("step-panel-pills");
                if (pills) {
                    pills.innerHTML = letters.map((letter, index) => {
                        const count = step.n[index];
                        const passed = count === step.total;
                        return '<span class="count-pill ' +
                            (passed ? "ok" : "bad") + '" title="' + letter + ": " +
                            count + "/" + step.total + ' lớp đạt"><strong>' +
                            letter + "</strong> " + count + "/" + step.total + "</span>";
                    }).join("");
                }

                const violation = document.getElementById("step-panel-violations");
                if (violation) {
                    violation.textContent = violations + " vi phạm";
                    violation.classList.toggle("has-violation", violations > 0);
                }

                setText("step-panel-elapsed", step.t.toFixed(1) + "s");
                setText("step-panel-population",
                    step.p + " cá thể · không cải thiện " + step.z);
            };

            // Chọn thế hệ thứ index: dựng lại bảng phòng học từ step.s + step.b.
            const select = (index, focus) => {
                const step = data.steps[index];
                if (!step) return;

                cells.forEach((cell, cellIndex) => {
                    const active = cellIndex === index;
                    cell.setAttribute("aria-selected", String(active));
                    cell.tabIndex = active ? 0 : -1;
                });
                panel.setAttribute("aria-labelledby", cells[index].id);
                updateHead(step);

                const collected = collectSlots(step);
                panelBody.innerHTML = '<div class="rooms">' +
                    data.rooms.map((room, roomId) =>
                        roomTable(roomId, collected.slots)
                    ).join("") +
                    "</div>";
                panel.hidden = false;
                if (focus) cells[index].focus();
            };

            cells.forEach((cell, index) => {
                cell.addEventListener("click", () => select(index, false));
            });

            // Phím điều hướng lưới thế hệ: trái/phải đổi 1 ô, lên/xuống nhảy đúng
            // một hàng (số ô mỗi hàng = columns(), mặc định 10 theo CSS).
            grid.addEventListener("keydown", event => {
                const activeIndex = cells.findIndex(
                    cell => cell.getAttribute("aria-selected") === "true"
                );
                let next = activeIndex < 0 ? 0 : activeIndex;

                if (event.key === "Home") next = 0;
                else if (event.key === "End") next = cells.length - 1;
                else if (event.key === "ArrowLeft") next -= 1;
                else if (event.key === "ArrowRight") next += 1;
                else if (event.key === "ArrowUp") next -= columns();
                else if (event.key === "ArrowDown") next += columns();
                else return;

                event.preventDefault();
                next = Math.max(0, Math.min(cells.length - 1, next));
                select(next, true);
            });

            // Mặc định chọn thế hệ cuối cùng (kết quả cuối).
            select(cells.length - 1, false);
        })();
    </script>"""

    @staticmethod
    def getCriteriaBadges(criterias, ci, busy=False):
        """Dãy huy hiệu P/G/N (và B nếu dính ràng buộc mềm) của MỘT lớp học phần.

        criterias là mảng cờ của nhiễm sắc thể (Schedule.criteria), còn ci là con
        trỏ tới bộ 3 cờ của lớp đang xét: ci = k * 3 với k là số thứ tự của lớp
        trong solution.classes. Cờ tiêu chí i đọc tại criterias[ci + i], thứ tự
        i = 0,1,2 trùng thứ tự Criteria.weights nên letter/OK_DESCR/FAIL_DESCR
        tra theo cùng chỉ số i là đúng cặp.
        Cờ False = vi phạm ràng buộc cứng, mất trọn Criteria.hardPenalty = 1.0
        điểm của tiêu chí đó; huy hiệu B chỉ để hiển thị, mức phạt thật là
        Criteria.busyPenalty = 0.2 điểm và chỉ tính một lần cho mỗi lớp.
        """
        sb = ['<div class="crits">']
        for i, letter in enumerate(HtmlOutput.CRITERIAS):
            passed = bool(criterias[ci + i])
            description = HtmlOutput.OK_DESCR[i] if passed else HtmlOutput.FAIL_DESCR[i]
            state = "Đạt" if passed else "Vi phạm"
            sb.append('<span class="crit ')
            sb.append("ok" if passed else "bad")
            sb.append('" title="')
            sb.append(html.escape(f"{state}: {description}"))
            sb.append('" aria-label="')
            sb.append(html.escape(f"{letter} - {state}: {description}"))
            sb.append('">')
            sb.append(letter)
            sb.append('</span>')

        if busy:
            description = (
                "Vi phạm ràng buộc mềm: có tiết rơi vào khung giờ giảng viên bận "
                "(phạt ×{:g} điểm, nhẹ hơn ràng buộc cứng ×{:g} điểm)".format(
                    Criteria.busyPenalty, Criteria.hardPenalty)
            )
            sb.append('<span class="crit crit--soft" title="')
            sb.append(html.escape(description))
            sb.append('" aria-label="')
            sb.append(html.escape("B - " + description))
            sb.append('">B</span>')

        sb.append('</div>')
        return "".join(sb)

    @staticmethod
    def getCourseClass(cc, criterias, ci, professor=None, busy=False):
        """Nội dung HTML của một ô lịch ở tiết ĐẦU của lớp: môn, GV, số tiết, huy hiệu.

        ci là con trỏ cờ k * 3 của chính lớp này (do generateTimeTable truyền
        xuống) nên ô đầu và các ô "tiếp tiết" hiển thị cùng bộ P/G/N.
        """
        professor_name = professor.Name if professor is not None else "—"
        sb = [
            '<div class="course">', html.escape(cc.Course.Name), '</div>',
            '<div class="prof">', html.escape(professor_name), '</div>',
        ]

        if cc.Duration > 1:
            sb.append('<div class="tags">')
            sb.append(f'<span class="tag tag-duration">{cc.Duration} tiết</span>')
            sb.append('</div>')

        sb.append(HtmlOutput.getCriteriaBadges(criterias, ci, busy=busy))
        return "".join(sb)

    @staticmethod
    def getContinuedClass(cc, criterias, ci, professor=None):
        """Bản rút gọn cho các tiết sau của lớp nhiều tiết, gắn nhãn 'Tiếp tiết'.

        Bình thường mergeSpan gộp các tiết liền nhau vào ô đầu bằng rowspan nên
        bản này chỉ hiện khi chuỗi bị chặn (trùng phòng, chạm ô nghỉ trưa, chạm
        hàng cuối bảng 13). Bộ cờ P/G/N vẫn lấy từ cùng ci của lớp.
        """
        return "".join([
            '<div class="course">', html.escape(cc.Course.Name), '</div>',
            '<div class="prof">', html.escape(professor.Name if professor is not None else "—"), '</div>',
            '<div class="tags"><span class="tag tag-continued">Tiếp tiết</span></div>',
            HtmlOutput.getCriteriaBadges(criterias, ci),
        ])

    @staticmethod
    def generateTimeTable(solution):
        """Dựng bảng tra entries_by_slot[(roomId, dayId)][periodId] cho lời giải.

        solution.classes lưu mã nhiễm sắc thể: lớp -> hashCode của ô (ngày, giờ,
        phòng). Reservation.parse đổi mã đó về toạ độ 0-based, còn bảng lịch dùng
        chỉ số 1-based nên phải cộng thêm 1:
          dayId     = reservation.Day + 1   -> cột 1..5 (cột 0 là nhãn "Tiết")
          startPeriod = reservation.Time + 1 -> hàng 1..13 (hàng 0 là tiêu đề)
        roomId giữ nguyên 0-based vì phòng được duyệt theo index cấu hình.
        Một lớp Duration tiết được ghi vào Duration hàng liên tiếp kể từ
        startPeriod, dừng khi periodId >= ROOM_ROW_NUMBER (= 14) tức không vượt
        quá hàng 13. Lớp trùng phòng KHÔNG bị loại: nhiều entry cùng nằm trong
        một list và getScheduleTable sẽ xếp chồng chúng lên nhau.
        ci chạy theo lớp, mỗi lớp cách nhau len(CRITERIAS) = 3 cờ (P, G, N).
        """
        ci = 0

        entries_by_slot = defaultdict(lambda: defaultdict(list))
        getCourseClass = HtmlOutput.getCourseClass
        getContinuedClass = HtmlOutput.getContinuedClass

        for cc, reservation_index in solution.classes.items():
            reservation = Reservation.parse(reservation_index)

            # toạ độ của ô thời gian - không gian
            # Day/Time là 0-based -> cộng 1 thành cột/ngày và dòng của bảng
            dayId = reservation.Day + 1
            startPeriod = reservation.Time + 1
            roomId = reservation.Room
            duration = cc.Duration
            professor = solution.professors.get(cc) if hasattr(solution, "professors") else None
            # busyPeriods trả về periodId 1-based, dùng riêng cho ràng buộc mềm B
            busy_periods = HtmlOutput.busyPeriods(
                professor, reservation.Day, startPeriod, duration)

            entry = {
                "start": startPeriod,
                "duration": duration,
                "busy_periods": busy_periods,
                "html": getCourseClass(
                    cc, solution.criteria, ci, professor,
                    busy=bool(busy_periods)),
                "continued": getContinuedClass(cc, solution.criteria, ci, professor),
            }

            for offset in range(duration):
                # offset 0..duration-1 tính từ tiết đầu; periodId vẫn là 1-based
                periodId = startPeriod + offset
                if periodId >= HtmlOutput.ROOM_ROW_NUMBER:
                    break
                entries_by_slot[(roomId, dayId)][periodId].append(entry)

            # chuyển sang bộ cờ của lớp kế tiếp: mỗi lớp chiếm 3 ô (P, G, N)
            ci += len(HtmlOutput.CRITERIAS)

        return entries_by_slot

    @staticmethod
    def busyPeriods(professor, day, startPeriod, duration):
        """Danh sách tiết của một lớp trùng khung giờ bận của giảng viên được giao.

        Đây chính là nguồn đếm vi phạm ràng buộc mềm B. Kết quả trả về theo
        periodId 1-based (khớp số hàng của bảng lịch), còn professor.BusySlots
        lưu (ngày, offset) với offset 0-based, nên phép tra phải lùi một:
            offset = startPeriod - 1 + offset_in_class
        Bắt đầu từ offset = 0 đến duration - 1; ngày ở đây vẫn là ngày 0-based.
        """
        if professor is None or not professor.BusySlots:
            return []
        return [
            startPeriod + offset
            for offset in range(duration)
            # startPeriod - 1: đổi periodId (1-based) về offset (0-based) để so BusySlots
            if (day, startPeriod - 1 + offset) in professor.BusySlots
        ]

    @staticmethod
    def splitBusyRuns(offsets):
        """Chia các chỉ số offset (0-based) thành từng dải liên tiếp trong một buổi.

        Khung nghỉ trưa bị loại và không được nối liền với hai buổi bên cạnh,
        nhờ vậy mỗi dải tương ứng đúng một khoảng giờ đồng nhất.
        Hai offset cùng dải khi offset sau = offset trước + 1; vì offset 6
        (nghỉ trưa) bị loại nên dải sáng (0..5) và dải chiều (7..12) không bao
        giờ dính nhau dù 6 + 1 = 7 liền kề về chỉ số.
        """
        runs = []
        for offset in sorted({offset for offset in offsets}):
            if offset == Constant.LUNCH_PERIOD:
                continue
            if runs and offset == runs[-1][-1] + 1:
                runs[-1].append(offset)
            else:
                runs.append([offset])
        return runs

    @staticmethod
    def formatBusyRuns(runs):
        """Nhãn gọn 'tiết 2-3, 7' từ các dải offset, khớp số tiết của bảng lịch.

        Số tiết lấy theo Constant.periodNumber(offset): sáng offset 0..5 thành
        tiết 1..6, chiều offset 7..12 thành tiết 7..12 (không đếm ô nghỉ trưa).
        """
        parts = []
        for run in runs:
            first = Constant.periodNumber(run[0])
            last = Constant.periodNumber(run[-1])
            parts.append(str(first) if first == last else f"{first}-{last}")
        if not parts:
            return "tiết bận"
        return "tiết " + ", ".join(parts)

    @staticmethod
    def formatBusyRunTimes(runs):
        """Khung giờ của từng dải bận, VD '9:50–11:40, 13:00–13:50'.

        start = periodStart(offset đầu dải); end = periodStart(offset cuối dải)
        + PERIOD_MINUTES (50 phút). Các tiết trong buổi liền nhau nên chỉ cần
        hai mốc này là phủ kín dải; dải không vắt qua nghỉ trưa (xem splitBusyRuns).
        """
        parts = []
        for run in runs:
            start = Constant.periodStart(run[0])
            end = Constant.periodStart(run[-1]) + Constant.PERIOD_MINUTES
            parts.append("{}–{}".format(
                Constant.formatHM(start), Constant.formatHM(end)))
        return ", ".join(parts)

    @staticmethod
    def getBusyChip(period_ids):
        """Nhãn cam báo một lớp bị xếp vào khung bận của giảng viên (ràng buộc mềm).

        period_ids là periodId 1-based nên phải trừ 1 để về offset 0-based trước
        khi tách dải; số điểm trừ khi tính fitness là busyPenalty = 0.2 cho mỗi
        lớp bị bận, nhỏ hơn hardPenalty = 1.0 của một vi phạm P/G/N.
        """
        runs = HtmlOutput.splitBusyRuns(period_id - 1 for period_id in period_ids)
        label = HtmlOutput.formatBusyRuns(runs)
        times = HtmlOutput.formatBusyRunTimes(runs)
        title = (
            "Ràng buộc mềm: lớp rơi vào khung giờ giảng viên bận"
            + (f" ({times})" if times else "")
            + ". Phạt ×{:g} điểm, nhẹ hơn vi phạm ràng buộc cứng (×{:g} điểm)."
            .format(Criteria.busyPenalty, Criteria.hardPenalty)
        )
        return (
            '<div class="slot-warning slot-warning--soft" title="{}">'
            'GV bận · {}</div>'.format(html.escape(title), html.escape(label))
        )

    @staticmethod
    def getHtmlCell(content, busy=False, soft=False, title="", rowspan=None):
        """Một ô <td> của bảng lịch: rỗng, rỗng-kèm-tô-bận, hoặc có nội dung.

        content = None -> ô trống; nếu ô đó rơi vào khung bận của giảng viên thì
        thêm lớp "busy" (tô mờ) cùng title ghi số tiết. content có nội dung -> ô
        "filled", và soft=True thêm "busy-soft" (cam) báo vi phạm ràng buộc mềm B.
        rowspan chỉ được ghi khi lớn hơn 1, tức ô gộp nhiều tiết liên tiếp.
        """
        span = f' rowspan="{rowspan}"' if rowspan and rowspan > 1 else ""
        if content is None:
            if not busy:
                return '<td class="slot empty"></td>'
            return '<td class="slot empty busy"{} title="{}"></td>'.format(
                span, html.escape(title))

        cls = "slot filled" + (" busy-soft" if soft else "")
        return f'<td class="{cls}"{span}>{content}</td>'

    @staticmethod
    def mergeSpan(entry, periodId, day_entries, lunchPeriod):
        """Số hàng liên tiếp mà MỘT lớp độc chiếm, dùng làm giá trị rowspan.

        Điều kiện mở rộng dải (duyệt periodId + span tới hết lớp):
          - ô kế tiếp chỉ có đúng một lớp: len(day_entries[nextPeriod]) == 1;
            nếu có 2 lớp trở lên nghĩa là trùng phòng -> không gộp, để xếp chồng;
          - dải không chạm ô nghỉ trưa lunchPeriod = LUNCH_PERIOD + 1 = 7;
          - dải không quá số tiết của lớp: last = entry["start"] + duration - 1;
          - dải không quá hàng cuối bảng: ROOM_ROW_NUMBER - 1 = 13.
        Tiết nghỉ trưa luôn trả 1 (không bao giờ bị gộp vào lớp nào).
        """
        if periodId == lunchPeriod:
            return 1
        # giới hạn dưới của dải: tiết cuối của lớp, hoặc hàng 13 của bảng
        last = min(entry["start"] + entry["duration"] - 1,
                   HtmlOutput.ROOM_ROW_NUMBER - 1)
        span = 1
        while periodId + span <= last:
            nextPeriod = periodId + span
            if nextPeriod == lunchPeriod:
                break
            if len(day_entries.get(nextPeriod, ())) != 1:
                # ô kế tiếp có 0 hoặc >= 2 lớp: hoặc hết lớp, hoặc trùng lịch -> dừng
                break
            span += 1
        return span

    @staticmethod
    def getScheduleTable(key, entries_by_slot,
                         overlap_label="Trùng phòng", caption="",
                         busy_slots=None):
        """Dựng một bảng lịch 13 hàng x 5 ngày cho MỘT dòng dữ liệu (phòng hoặc GV).

        key là roomId (bảng phòng học) hoặc profId (bảng giảng viên); ô tương ứng
        lấy từ entries_by_slot[(key, dayId)][periodId]. Quy ước chỉ số của bảng:
          periodId = offset 0-based + 1, chạy 1..ROOM_ROW_NUMBER-1 = 1..13
          dayId    = ngày 0-based + 1,    chạy 1..ROOM_COLUMN_NUMBER-1 = 1..5
          hàng nghỉ trưa là periodId = LUNCH_PERIOD + 1 = 7
        busy_slots là tập (ngày, offset) 0-based của giảng viên, chỉ dùng để tô ô
        trống; vì bảng đếm 1-based nên phải trừ 1 ở cả hai chiều khi tra cứu.
        Các tiết liền nhau cùng một lớp được gộp thành một ô rowspan nhờ mergeSpan,
        còn ô có nhiều lớp (trùng lịch) KHÔNG gộp mà xếp chồng trong slot-stack.
        """
        rows = []
        busy_slots = busy_slots or set()
        # các hàng đã bị một ô rowspan "nuốt" ở ngày đó, cần bỏ khi gặp lại
        covered = {dayId: set() for dayId in range(1, HtmlOutput.ROOM_COLUMN_NUMBER)}
        lunchPeriod = Constant.LUNCH_PERIOD + 1  # ô nghỉ trưa nằm ở hàng 7

        # hàng 1..13 (hàng 0 là tiêu đề), cột 1..5 (cột 0 là nhãn tiết)
        for periodId in range(1, HtmlOutput.ROOM_ROW_NUMBER):
            cells = []
            for dayId in range(1, HtmlOutput.ROOM_COLUMN_NUMBER):
                if periodId in covered[dayId]:
                    continue
                day_entries = entries_by_slot.get((key, dayId), {})
                slot_entries = day_entries.get(periodId, [])
                if not slot_entries:
                    # ô trống: quay về offset 0-based để so với BusySlots của giảng viên
                    offset = periodId - 1
                    is_busy = (dayId - 1, offset) in busy_slots
                    cells.append(HtmlOutput.getHtmlCell(
                        None, busy=is_busy,
                        title="Giảng viên bận · tiết {} ({})".format(
                            Constant.periodNumber(offset),
                            Constant.periodTimeRange(offset, sep="-"))))
                    continue

                if len(slot_entries) == 1:
                    entry = slot_entries[0]
                    span = HtmlOutput.mergeSpan(
                        entry, periodId, day_entries, lunchPeriod)
                    # chỉ đếm tiết bận nằm trong đúng dải vừa gộp [periodId, periodId+span)
                    busy_periods = [
                        period for period in (entry.get("busy_periods") or ())
                        if periodId <= period < periodId + span
                    ]
                    chip = (HtmlOutput.getBusyChip(busy_periods)
                            if busy_periods else "")
                    if entry["start"] == periodId:
                        card = f'<div class="course-card">{entry["html"]}</div>'
                    else:
                        card = (f'<div class="course-card continued">'
                                f'{entry["continued"]}</div>')
                    cells.append(HtmlOutput.getHtmlCell(
                        chip + card, soft=bool(busy_periods), rowspan=span))
                    # đánh dấu span-1 hàng kế tiếp đã hiển thị xong trong ô này
                    covered[dayId].update(range(periodId, periodId + span))
                    continue

                # Trùng phòng: xếp chồng mọi lớp đang diễn ra trong cùng ô.
                cards = []
                if len(slot_entries) > 1:
                    cards.append(f'<div class="slot-warning">{overlap_label}</div>')
                any_busy = False
                for entry in slot_entries:
                    is_busy = periodId in set(entry.get("busy_periods") or ())
                    any_busy = any_busy or is_busy
                    chip = HtmlOutput.getBusyChip([periodId]) if is_busy else ""
                    if entry["start"] == periodId:
                        cards.append(
                            chip + f'<div class="course-card">{entry["html"]}</div>'
                        )
                    else:
                        cards.append(
                            chip + f'<div class="course-card continued">'
                            f'{entry["continued"]}</div>'
                        )
                content = f'<div class="slot-stack">{"".join(cards)}</div>'
                cells.append(
                    '<td class="slot filled conflict{}">{}</td>'.format(
                        " busy-soft" if any_busy else "", content)
                )

            # hàng 7 = periodId - 1 == LUNCH_PERIOD (offset 6) -> dán nhãn nghỉ trưa
            is_lunch = periodId - 1 == Constant.LUNCH_PERIOD
            rows.append(
                '<tr{}>'.format(' class="lunch"' if is_lunch else '')
                + f'<th class="period" scope="row">'
                f'<span class="period-name">{HtmlOutput.PERIODS[periodId]}</span>'
                f'<span class="period-time">{HtmlOutput.PERIOD_TIMES[periodId]}</span>'
                '</th>'
                + "".join(cells)
                + '</tr>'
            )

        day_headers = "".join(
            f'<th scope="col"><span class="day">{day}</span>'
            f'<span class="day-name">{name}</span></th>'
            for day, name in zip(HtmlOutput.WEEK_DAYS, HtmlOutput.WEEK_DAY_NAMES)
        )

        return (
            '<table class="schedule">'
            f'<caption class="sr-only">{html.escape(caption)}</caption>'
            '<thead><tr>'
            '<th class="corner" scope="col">Tiết / Ngày</th>'
            f'{day_headers}'
            '</tr></thead>'
            '<tbody>'
            + "".join(rows) +
            '</tbody>'
            '</table>'
        )

    @staticmethod
    def getRoomTable(room, roomId, entries_by_slot):
        """Bảng thời khóa biểu của MỘT phòng học (kèm khung và tiêu đề phòng).

        roomId là key 0-based trong entries_by_slot của generateTimeTable; ô
        "trùng" ở đây là hai lớp cùng phòng cùng tiết -> vi phạm ràng buộc P.
        """
        table = HtmlOutput.getScheduleTable(
            roomId,
            entries_by_slot,
            overlap_label="Trùng phòng",
            caption=f"Thời khóa biểu phòng {room.Name}",
        )
        return (
            '<section class="room">'
            '<div class="room-head">'
            '<div class="room-title">'
            '<span class="room-kicker">Phòng học</span>'
            f'<h2>{html.escape(room.Name)}</h2>'
            '</div>'
            '</div>'
            '<p class="scroll-hint">Vuốt ngang để xem đủ các ngày '
            '<span aria-hidden="true">→</span></p>'
            '<div class="table-wrap">'
            f'{table}'
            '</div>'
            '</section>'
        )

    @staticmethod
    def generateProfessorTimeTable(solution):
        """Dựng entries_by_slot[(profId, dayId)][periodId] theo góc nhìn giảng viên.

        Cùng phép đổi trục với generateTimeTable: dayId = reservation.Day + 1 và
        startPeriod = reservation.Time + 1 (bảng 1-based, mã nhiễm sắc thể 0-based).
        Khác biệt: key là ID giảng viên được GA gán cho lớp (thay vì phòng), mỗi ô
        ghi tên môn + phòng, và lớp của cùng một GV trùng nhau sẽ xếp chồng với nhãn
        "Trùng lịch giảng viên" (vi phạm ràng buộc G).
        busy_classes đếm số LỚP của GV có ít nhất một tiết rơi vào khung bận của
        chính họ (ràng buộc mềm B, phạt 0.2 điểm/lớp ở fitness) — mỗi lớp chỉ bị
        đếm một lần dù trùng mấy tiết.
        """
        entries_by_slot = defaultdict(lambda: defaultdict(list))
        busy_classes = defaultdict(int)   # profId -> số lớp dính khung bận

        for cc, reservation_index in solution.classes.items():
            reservation = Reservation.parse(reservation_index)

            # Day/Time 0-based trong mã -> cộng 1 thành cột/dòng của bảng
            dayId = reservation.Day + 1
            startPeriod = reservation.Time + 1
            professor = solution.professors.get(cc) if hasattr(solution, "professors") else None
            profId = professor.Id if professor is not None else None
            duration = cc.Duration
            busy_periods = HtmlOutput.busyPeriods(
                professor, reservation.Day, startPeriod, duration)
            if busy_periods:
                # một lớp chỉ bị tính một lần cho ràng buộc mềm B
                busy_classes[profId] += 1

            room = solution.configuration.getRoomById(reservation.Room)
            room_name = room.Name if room is not None else f"Phòng {reservation.Room}"

            entry = {
                "start": startPeriod,
                "duration": duration,
                "busy_periods": busy_periods,
                "html": (
                    '<div class="course">'
                    + html.escape(cc.Course.Name)
                    + '</div>'
                    '<div class="tags">'
                    f'<span class="tag tag-room">{html.escape(room_name)}</span>'
                    '</div>'
                ),
                "continued": (
                    '<div class="course">'
                    + html.escape(cc.Course.Name)
                    + '</div>'
                    '<div class="tags">'
                    '<span class="tag tag-continued">Tiếp tiết</span>'
                    '</div>'
                ),
            }

            for offset in range(duration):
                # dải tiết 1-based của lớp, cắt ở hàng 13 (ROOM_ROW_NUMBER - 1)
                periodId = startPeriod + offset
                if periodId >= HtmlOutput.ROOM_ROW_NUMBER:
                    break
                entries_by_slot[(profId, dayId)][periodId].append(entry)

        return entries_by_slot, busy_classes

    @staticmethod
    def getProfessorTable(professor, profId, entries_by_slot,
                          total_hours, number_of_courses, busy_classes=0):
        """Bảng thời khóa biểu của một giảng viên, kèm badge tổng kết tuần.

        Bảng dùng chung getScheduleTable nhưng với busy_slots = professor.BusySlots
        (tập (ngày, offset) 0-based) để tô mờ những ô trống nằm trong giờ bận;
        total_hours là tổng Duration các lớp được giao, number_of_courses là số
        môn khác nhau, busy_classes là số lớp dính ràng buộc mềm B.
        """
        table = HtmlOutput.getScheduleTable(
            profId,
            entries_by_slot,
            overlap_label="Trùng lịch giảng viên",
            caption=f"Lịch giảng dạy của {professor.Name}",
            busy_slots=professor.BusySlots,
        )
        busy_badge = (
            '<span class="badge badge--busy" '
            'title="Lớp bị xếp vào khung giờ giảng viên bận (ràng buộc mềm)">'
            f'{busy_classes} lớp dính bận</span>'
            if busy_classes else ""
        )
        return (
            '<details class="room prof-item" open>'
            '<summary class="room-head">'
            '<div class="room-title">'
            '<span class="room-kicker">Giảng viên</span>'
            f'<h2>{html.escape(professor.Name)}</h2>'
            '</div>'
            '<div class="room-badges">'
            f'<span class="badge">{total_hours} tiết/tuần</span>'
            f'<span class="badge">{number_of_courses} môn</span>'
            f'{busy_badge}'
            '</div>'
            '</summary>'
            '<p class="scroll-hint">Vuốt ngang để xem đủ các ngày '
            '<span aria-hidden="true">→</span></p>'
            '<div class="table-wrap">'
            f'{table}'
            '</div>'
            '</details>'
        )

    @staticmethod
    def getProfessorSections(solution):
        """Chuỗi các bảng lịch của từng giảng viên cho tab "Theo giảng viên".

        Số tiết/tuần của một GV = tổng Duration các lớp được GA gán cho họ;
        số môn = số tên môn khác nhau. Giảng viên không nhận lớp nào bị bỏ qua.
        """
        configuration = solution.configuration
        entries_by_slot, busy_classes = HtmlOutput.generateProfessorTimeTable(solution)
        if not entries_by_slot:
            return (
                '<div class="empty-state">'
                'Chưa có lớp học nào được xếp lịch.'
                '</div>'
            )

        # tổng số tiết và số môn của từng giảng viên trong tuần
        hours = defaultdict(int)
        courses = defaultdict(set)
        professors_map = solution.professors if hasattr(solution, "professors") else {}
        for cc in solution.classes:
            professor = professors_map.get(cc)
            if professor is None:
                continue
            profId = professor.Id
            hours[profId] += cc.Duration
            courses[profId].add(cc.Course.Name)

        sections = []
        for professor in sorted(
            configuration._professors.values(), key=lambda item: item.Id
        ):
            profId = professor.Id
            if profId not in hours:
                # giảng viên không có lớp nào được xếp lịch
                continue
            sections.append(
                HtmlOutput.getProfessorTable(
                    professor,
                    profId,
                    entries_by_slot,
                    hours[profId],
                    len(courses[profId]),
                    busy_classes.get(profId, 0),
                )
            )
        return "".join(sections)

    @staticmethod
    def getRoomSections(solution):
        """Toàn bộ các bảng phòng học của một lời giải, xếp theo roomId 0..nr-1.

        Duyệt đủ numberOfRooms phòng nên phòng trống vẫn xuất hiện, giúp người
        xem thấy rõ phòng nào chưa được dùng.
        """
        configuration = solution.configuration
        nr = configuration.numberOfRooms

        entries_by_slot = HtmlOutput.generateTimeTable(solution)
        if not entries_by_slot:
            return (
                '<div class="empty-state">'
                'Chưa có lớp học nào được xếp lịch.'
                '</div>'
            )

        sections = []
        for roomId in range(nr):
            room = configuration.getRoomById(roomId)
            if room is not None:
                sections.append(
                    HtmlOutput.getRoomTable(room, roomId, entries_by_slot)
                )
        return "".join(sections)

    @staticmethod
    def _snapshotSolution(entry):
        """Bọc một bản ghi lịch sử thành "lời giải" đủ trường để tái dùng hàm vẽ.

        Các bản ghi của Trace lưu đúng classes / professors / criteria /
        configuration / fitness của thế hệ đó, nên chỉ cần SimpleNamespace là
        generateTimeTable và getRoomSections chạy được như với Schedule thật.
        """
        return SimpleNamespace(
            configuration=entry["configuration"],
            classes=entry["classes"],
            professors=entry.get("professors", {}),
            criteria=entry["criteria"],
            fitness=entry["fitness"],
        )

    @staticmethod
    def _criteriaCounts(entry):
        """Đếm số lớp ĐẠT từng tiêu chí P/G/N trong một bản ghi lịch sử.

        Mảng cờ lưu class-major, 3 cờ mỗi lớp theo thứ tự P, G, N, nên cờ tiêu
        chí i của lớp j nằm tại criteria[j * step + i] với step = 3.
        total = len(criteria) // 3 = số lớp của bài toán; counts[i] đếm số lớp có
        cờ True, vì vậy số vi phạm của tiêu chí i là total - counts[i].
        Trace đã tính sẵn counts/total thì dùng trực tiếp, không đếm lại.
        """
        criteria = entry.get("criteria")
        step = len(HtmlOutput.CRITERIAS)
        total = entry.get("total")
        if total is None:
            total = len(criteria) // step if criteria is not None else 0
        total = int(total)

        counts = entry.get("counts")
        if counts is None:
            if criteria is None:
                counts = tuple(0 for _ in range(step))
            else:
                counts = tuple(
                    sum(1 for j in range(total) if criteria[j * step + i])
                    for i in range(step)
                )
        return tuple(int(count) for count in counts), total

    @staticmethod
    def getStepsData(history):
        """Dữ liệu gọn của từng thế hệ nhúng vào trang (khối <script id="step-data">).

        Trình duyệt dùng mảng này để tự dựng thời khóa biểu của thế hệ được
        bấm, nhờ đó file HTML chỉ nặng vài trăm KB thay vì hàng chục MB.

        payload lưu theo quy ước 0-based của model (Room/Day/Time và BusySlots),
        JavaScript sẽ tự cộng 1 khi vẽ bảng — xem collectSlots trong PAGE_SCRIPT.
        """
        if not history:
            return ""

        # Thứ tự lớp học lấy theo bản ghi đầu tiên; các bản ghi sau được
        # dời về đúng vị trí này (tiêu chí lại được lưu theo thứ tự của nó).
        order = list((history[0].get("classes") or {}).keys())
        position = {course_class: index
                    for index, course_class in enumerate(order)}
        first_professors = history[0].get("professors") or {}
        # Lop hoc gan voi ID giang vien (khong phai ten) de moi lien kiet trong
        # trinh duyet deu tra theo khoa ID nhu model.
        classes = [
            {
                "course": course_class.Course.Name,
                "prof": (first_professors[course_class].Id
                         if first_professors.get(course_class) is not None else None),
                "dur": int(course_class.Duration),
            }
            for course_class in order
        ]

        configuration = history[0].get("configuration")
        rooms = []
        busy_by_professor = {}
        professor_names = {}
        if configuration is not None:
            for room_id in range(configuration.numberOfRooms):
                room = configuration.getRoomById(room_id)
                rooms.append(room.Name if room is not None else "Phòng {}".format(room_id))
            # khung bận của từng giảng viên, để trình duyệt tô ô vi phạm ràng buộc mềm
            for professor in configuration._professors.values():
                professor_names[professor.Id] = professor.Name
                if professor.BusySlots:
                    busy_by_professor[professor.Id] = sorted(
                        [int(day), int(period)]
                        for day, period in professor.BusySlots
                    )

        # step_size = 3 cờ / lớp theo đúng thứ tự Criteria.weights (P, G, N)
        step_size = len(HtmlOutput.CRITERIAS)
        steps = []
        for entry in history:
            counts, total = HtmlOutput._criteriaCounts(entry)
            entry_classes = entry.get("classes") or {}
            criteria = entry.get("criteria")

            # "b": chuỗi cờ 0/1 nối liền, mỗi lớp 3 ký tự, xếp theo thứ tự "order".
            # index là vị trí của lớp trong bản ghi đang xét, target là vị trí trong
            # order; cờ của tiêu chí offset đọc tại criteria[index * step_size + offset].
            flags = ["0" * step_size for _ in order]
            for index, course_class in enumerate(entry_classes):
                target = position.get(course_class)
                if target is None or criteria is None:
                    continue
                flags[target] = "".join(
                    "1" if criteria[index * step_size + offset] else "0"
                    for offset in range(step_size)
                    if index * step_size + offset < len(criteria)
                )

            # "s": vị trí xếp của từng lớp [phòng, ngày, giờ] — GIỮ NGUYÊN 0-based
            # như mã nhiễm sắc thể; JavaScript cộng 1 khi tra hàng/cột của bảng.
            slots = [None] * len(order)
            for course_class, reservation_index in entry_classes.items():
                target = position.get(course_class)
                if target is None:
                    continue
                reservation = Reservation.parse(reservation_index)
                slots[target] = [int(reservation.Room),
                                 int(reservation.Day),
                                 int(reservation.Time)]

            # ID giảng viên được gán cho từng lớp ở thế hệ này (đổi theo thế hệ)
            entry_professors = entry.get("professors") or {}
            prof_ids = [
                (entry_professors[course_class].Id
                 if entry_professors.get(course_class) is not None else None)
                for course_class in order
            ]

            # một bước trong lưới thế hệ: g=thế hệ, f=fitness, t=số giây chạy,
            # n=số lớp đạt từng tiêu chí P/G/N, total=tổng số lớp, p=dân số,
            # z=số thế hệ liên tiếp không cải thiện, b=chuỗi cờ, s=vị trí xếp lớp,
            # v=ID giảng viên được gán cho từng lớp ở thế hệ này
            steps.append({
                "g": int(entry.get("generation", len(steps) + 1)),
                "f": float(entry.get("fitness", 0.0)),
                "t": round(float(entry.get("elapsed", 0.0) or 0.0), 2),
                "n": [int(count) for count in counts],
                "total": int(total),
                "p": int(entry.get("populationSize", 0) or 0),
                "z": int(entry.get("bestNotEnhance", 0) or 0),
                "b": "".join(flags),
                "s": slots,
                "v": prof_ids,
            })

        # "phần cứng" của lưới mà JavaScript cần để dựng lại bảng lịch:
        #   periods[i] ứng với hàng i+1 (PERIODS/PERIOD_TIMES đã chèn phần tử rỗng
        #   ở index 0 nên tra theo periodId trực tiếp)
        #   lunch = LUNCH_PERIOD = 6 là OFFSET 0-based của ô nghỉ trưa; hàng trong
        #           bảng là lunch + 1 = 7
        #   rows  = ROOM_ROW_NUMBER    = 14 -> vòng hàng chạy 1..13
        #   cols  = ROOM_COLUMN_NUMBER = 6  -> vòng cột chạy 1..5
        #   busy[profId] = danh sách [ngày, offset] 0-based của giảng viên
        payload = {
            "letters": list(HtmlOutput.CRITERIAS),
            "ok": list(HtmlOutput.OK_DESCR),
            "fail": list(HtmlOutput.FAIL_DESCR),
            "days": [list(day) for day in
                     zip(HtmlOutput.WEEK_DAYS, HtmlOutput.WEEK_DAY_NAMES)],
            "periods": [[HtmlOutput.PERIODS[index], HtmlOutput.PERIOD_TIMES[index]]
                        for index in range(1, HtmlOutput.ROOM_ROW_NUMBER)],
            "lunch": Constant.LUNCH_PERIOD,
            "rows": HtmlOutput.ROOM_ROW_NUMBER,
            "cols": HtmlOutput.ROOM_COLUMN_NUMBER,
            "rooms": rooms,
            "profNames": professor_names,
            "busy": busy_by_professor,
            "classes": classes,
            "steps": steps,
        }
        document = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        return ('<script type="application/json" id="step-data">'
                + document.replace("</", "<\\/")
                + "</script>\n")

    @staticmethod
    def getFitnessChart(history):
        """Biểu đồ SVG nội tuyến: fitness của cá thể tốt nhất qua từng thế hệ.

        Fitness của một nhiễm sắc thể = (điểm cứng − phạt mềm) / (3 × số lớp),
        trong đó điểm cứng là tổng 3 cờ P/G/N mỗi lớp (mỗi cờ False bị trừ
        hardPenalty = 1.0) và phạt mềm = 0.2 cho mỗi lớp dính khung bận; vì thế
        1.0 là lịch hoàn hảo và giá trị luôn nằm trong [0, 1] (values kẹp clamp).
        Trục dọc chỉ vẽ quanh dải dữ liệu thực tế để nhìn rõ biến động nhỏ.
        """
        if not history:
            return ""

        count = len(history)
        values = [
            max(0.0, min(1.0, float(entry.get("fitness", 0.0))))
            for entry in history
        ]
        generations = [
            entry.get("generation", index + 1)
            for index, entry in enumerate(history)
        ]

        # Thu gọn trục dọc quanh dải fitness thực tế để thấy rõ biến động.
        # padding = max(0.005, 15% độ rộng dải); dải quá hẹp (< 0.05) thì mở
        # thành ±0.025 quanh giữa, cuối cùng làm tròn xuống/lên 2 chữ số.
        data_min = min(values)
        data_max = max(values)
        padding = max(0.005, (data_max - data_min) * 0.15)
        axis_min = max(0.0, data_min - padding)
        axis_max = min(1.0, data_max + padding)
        if axis_max - axis_min < 0.05:
            center = (axis_min + axis_max) / 2
            axis_min = max(0.0, center - 0.025)
            axis_max = min(1.0, center + 0.025)
        axis_min = math.floor(axis_min * 100) / 100
        axis_max = math.ceil(axis_max * 100) / 100
        if axis_max <= axis_min:
            axis_min = max(0.0, axis_min - 0.01)
            axis_max = min(1.0, axis_max + 0.01)
        axis_span = axis_max - axis_min
        # số thập phân của nhãn trục: dải càng hẹp càng cần nhiều chữ số
        axis_decimals = 2 if axis_span < 0.02 else (1 if axis_span < 0.5 else 0)

        # hệ quy chiếu SVG: vùng vẽ rộng plot_width, cao plot_height bên trong
        # lề left/right/top/bottom; baseline là cạnh dưới của vùng vẽ
        width, height = 1000, 340
        left, right, top, bottom = 58, 22, 28, 52
        plot_width = width - left - right
        plot_height = height - top - bottom
        baseline = top + plot_height

        def x_for(index):
            """Hoành độ của điểm thứ index: chia đều plot_width cho count-1 khoảng."""
            if count <= 1:
                return left + plot_width / 2
            return left + (index / (count - 1)) * plot_width

        def y_for(value):
            """Trục tung đảo chiều: axis_max ở cạnh trên (top), axis_min ở baseline.

            y = top + (axis_max - value) / axis_span * plot_height
            """
            return top + (axis_max - value) / axis_span * plot_height

        points = [
            (x_for(index), y_for(value))
            for index, value in enumerate(values)
        ]
        line_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        # vùng tô đậm dưới đường: xuống baseline ở điểm đầu và điểm cuối rồi đóng
        area_path = (
            f"M {points[0][0]:.2f} {baseline:.2f} "
            + " ".join(f"L {x:.2f} {y:.2f}" for x, y in points)
            + f" L {points[-1][0]:.2f} {baseline:.2f} Z"
        )

        # 5 đường ngang chia đều trục dọc: giá trị mỗi đường = axis_min +
        # axis_span * step / 4 (step = 0..4); nhãn hiển thị theo phần trăm
        grid = []
        for step in range(5):
            value = axis_min + axis_span * step / 4
            y = y_for(value)
            label = f"{value * 100:.{axis_decimals}f}%"
            grid.append(
                f'<line class="chart-grid" x1="{left}" y1="{y:.2f}" '
                f'x2="{left + plot_width}" y2="{y:.2f}"/>'
            )
            grid.append(
                f'<text class="chart-axis-label" x="{left - 10}" '
                f'y="{y + 4:.2f}" text-anchor="end">{label}</text>'
            )

        # 5 mốc dọc ở các vị trí 0%, 25%, 50%, 75%, 100% của dải thế hệ
        tick_indexes = sorted({
            0,
            round((count - 1) * .25),
            round((count - 1) * .5),
            round((count - 1) * .75),
            count - 1,
        })
        for index in tick_indexes:
            x = x_for(index)
            if 0 < index < count - 1:
                grid.append(
                    f'<line class="chart-grid chart-grid-v" x1="{x:.2f}" '
                    f'y1="{top}" x2="{x:.2f}" y2="{baseline}"/>'
                )
            generation = html.escape(str(generations[index]))
            grid.append(
                f'<text class="chart-axis-label" x="{x:.2f}" '
                f'y="{baseline + 22}" text-anchor="middle">'
                f'Thế hệ {generation}</text>'
            )

        # chỉ chấm điểm từng thế hệ khi mật độ vừa phải (2..160 điểm), tránh nhiễu
        dots = ""
        if 1 < count <= 160:
            dots = "".join(
                f'<circle class="chart-dot" cx="{x:.2f}" cy="{y:.2f}" r="2.4">'
                f'<title>Thế hệ {html.escape(str(generations[index]))} · '
                f'Fitness {values[index]:.4f}</title></circle>'
                for index, (x, y) in enumerate(points)
            )

        # fitness cao nhất có thể không nằm ở thế hệ cuối (GA giữ cá thể tốt nhất),
        # nên đánh dấu riêng khi nó khác thế hệ cuối
        best_index = max(range(count), key=lambda index: values[index])
        best_dot = ""
        if best_index != count - 1:
            best_x, best_y = points[best_index]
            best_dot = (
                f'<circle class="chart-best-dot" cx="{best_x:.2f}" '
                f'cy="{best_y:.2f}" r="4.5"><title>Cao nhất — Thế hệ '
                f'{html.escape(str(generations[best_index]))} · '
                f'Fitness {values[best_index]:.4f}</title></circle>'
            )

        final_x, final_y = points[-1]
        final_generation = html.escape(str(generations[-1]))
        final_value = values[-1]
        final_dot = (
            f'<circle class="chart-final-dot" cx="{final_x:.2f}" '
            f'cy="{final_y:.2f}" r="5"><title>Kết quả cuối — Thế hệ '
            f'{final_generation} · Fitness {final_value:.4f}</title></circle>'
        )

        final_generation_label = html.escape(str(generations[-1]))
        best_generation_label = html.escape(str(generations[best_index]))
        first_generation_label = html.escape(str(generations[0]))

        max_class = "chart-stat is-max"
        final_class = "chart-stat is-final"
        # ba thẻ tóm tắt: fitness đầu / cao nhất / cuối, đều nhân 100 thành phần trăm
        stats_html = (
            '<div class="chart-stats">'
            '<div class="chart-stat">'
            '<span>Bắt đầu</span>'
            f'<strong>{values[0] * 100:.1f}%</strong>'
            f'<small>Thế hệ {first_generation_label}</small>'
            '</div>'
            f'<div class="{max_class}">'
            '<span>Cao nhất</span>'
            f'<strong>{values[best_index] * 100:.1f}%</strong>'
            f'<small>Thế hệ {best_generation_label}</small>'
            '</div>'
            f'<div class="{final_class}">'
            '<span>Cuối cùng</span>'
            f'<strong>{final_value * 100:.1f}%</strong>'
            f'<small>Thế hệ {final_generation_label}</small>'
            '</div>'
            '</div>'
        )

        best_legend = (
            '<span class="chart-key-best">Cao nhất</span>'
            if best_index != count - 1 else
            ""
        )
        chart_legend = (
            '<div class="chart-legend">'
            '<span>Fitness</span>'
            '<span class="chart-key-final">Kết quả cuối</span>'
            f'{best_legend}'
            '</div>'
        )

        return (
            f'{chart_legend}'
            '<div class="fitness-chart-wrap">'
            f'<svg class="fitness-chart" viewBox="0 0 {width} {height}" '
            'role="img" aria-labelledby="fitness-chart-title '
            'fitness-chart-desc">'
            '<title id="fitness-chart-title">Biểu đồ fitness qua các thế hệ</title>'
            f'<desc id="fitness-chart-desc">Fitness từ '
            f'{values[0] * 100:.1f}% đến {final_value * 100:.1f}% qua '
            f'{count} thế hệ; cao nhất {values[best_index] * 100:.1f}%.</desc>'
            '<defs>'
            '<linearGradient id="fitness-area" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#3b82f6" stop-opacity=".24"/>'
            '<stop offset="100%" stop-color="#3b82f6" stop-opacity=".02"/>'
            '</linearGradient>'
            '</defs>'
            f'{"".join(grid)}'
            f'<path class="chart-area" d="{area_path}"/>'
            f'<polyline class="chart-line" points="{line_points}"/>'
            f'{dots}{best_dot}{final_dot}'
            '</svg>'
            '</div>'
            f'{stats_html}'
        )

    @staticmethod
    def getHistorySection(history):
        """Khối "Đánh giá": tiêu đề + phần dẫn + biểu đồ fitness của getFitnessChart."""
        if not history:
            return ""

        return (
            '<section class="history-section" aria-labelledby="history-title">'
            '<div class="history-head">'
            '<div>'
            '<p class="section-kicker">Đánh giá</p>'
            '<h2 id="history-title">Fitness qua các thế hệ</h2>'
            '</div>'
            f'<span class="badge badge-muted">{len(history)} thế hệ</span>'
            '</div>'
            '<p class="history-intro">'
            'Biểu đồ thể hiện fitness của thế hệ tốt nhất sau mỗi bước. '
            'Trục dọc được thu gọn theo dải fitness thực tế để thấy rõ '
            'biến động; trục ngang là thế hệ, đường càng cao càng tốt.'
            '</p>'
            '<p class="history-scroll-hint">'
            'Vuốt ngang để xem đủ biểu đồ '
            '<span aria-hidden="true">→</span>'
            '</p>'
            f'{HtmlOutput.getFitnessChart(history)}'
            '</section>'
        )

    @staticmethod
    def getStepViolations(entry):
        """Số vi phạm của một thế hệ: vi phạm_i = tổng số lớp - số lớp đạt tiêu chí i.

        Tổng vi phạm = vi phạm P + vi phạm G + vi phạm N; mỗi vi phạm cứng làm
        fitness mất 1/(3 x số lớp) điểm (hardPenalty = 1.0 chia cho tổng điểm tối đa).
        """
        counts, total = HtmlOutput._criteriaCounts(entry)
        violations = [total - count for count in counts]
        return violations, sum(violations), total

    @staticmethod
    def getStepHeadHtml(entry, index):
        """Tiêu đề động của khung lịch thế hệ (fitness, số lớp đạt P/G/N, vi phạm...).

        percent = clamp(fitness, 0..1) * 100 vì fitness đã được chuẩn hoá trên
        tổng điểm tối đa 3 x số lớp; pill chuyển sang màu đỏ khi count < total.
        """
        counts, total = HtmlOutput._criteriaCounts(entry)
        violations = [total - count for count in counts]
        violation_total = sum(violations)
        fitness = float(entry.get("fitness", 0.0))
        percent = max(0.0, min(1.0, fitness)) * 100
        generation = entry.get("generation", index + 1)
        elapsed = float(entry.get("elapsed", 0.0) or 0.0)
        population = int(entry.get("populationSize", 0) or 0)
        stagnation = int(entry.get("bestNotEnhance", 0) or 0)

        pills = "".join(
            '<span class="count-pill {state}" title="{letter}: {count}/{total} lớp đạt">'
            "<strong>{letter}</strong> {count}/{total}</span>".format(
                state="ok" if count == total else "bad",
                letter=letter, count=count, total=total,
            )
            for letter, count in zip(HtmlOutput.CRITERIAS, counts)
        )

        return (
            '<div class="step-panel-head">'
            '<div class="step-panel-title">'
            '<span class="step-panel-kicker">Thời khóa biểu của thế hệ</span>'
            '<h3 id="step-panel-generation">Thế hệ {generation}</h3>'
            "</div>"
            '<div class="step-panel-meta">'
            '<span class="step-panel-fit" id="step-panel-fitness">'
            "Fitness {fitness:.6f} · {percent:.1f}%</span>"
            '<span class="step-panel-pills" id="step-panel-pills">{pills}</span>'
            '<span class="step-panel-vio{vio_class}" id="step-panel-violations">'
            "{violation_total} vi phạm</span>"
            '<span id="step-panel-elapsed">{elapsed:.1f}s</span>'
            '<span id="step-panel-population">{population} cá thể · '
            "không cải thiện {stagnation}</span>"
            "</div>"
            "</div>"
        ).format(
            generation=generation,
            fitness=fitness,
            percent=percent,
            pills=pills,
            violation_total=violation_total,
            vio_class=" has-violation" if violation_total else "",
            elapsed=elapsed,
            population=population,
            stagnation=stagnation,
        )

    @staticmethod
    def getStepsSection(history):
        """Lưới các thế hệ: mỗi ô một bước tiến hoá, bấm ô để xem lịch của bước đó.

        Ô nền xanh (is-perfect) là ô có tổng vi phạm P/G/N bằng 0; ô viền vàng
        (is-best) là ô có fitness cao nhất — có thể khác thế hệ cuối.
        Khung lịch dựng sẵn bằng thế hệ cuối để trang vẫn xem được khi JavaScript
        không chạy, rồi mới được trình duyệt vẽ lại theo dữ liệu nhúng.
        """
        if not history:
            return ""

        # thế hệ có fitness cao nhất trong toàn bộ lịch sử (không chắc là thế hệ cuối)
        best_index = max(
            range(len(history)),
            key=lambda index: float(history[index].get("fitness", 0.0)),
        )

        cells = []
        for index, entry in enumerate(history):
            violations, violation_total, total = HtmlOutput.getStepViolations(entry)
            fitness = float(entry.get("fitness", 0.0))
            # fitness nằm trong [0, 1] (điểm/chuẩn hoá); kẹp lại rồi đổi ra phần trăm
            percent = max(0.0, min(1.0, fitness)) * 100
            generation = entry.get("generation", index + 1)
            elapsed = float(entry.get("elapsed", 0.0) or 0.0)
            population = int(entry.get("populationSize", 0) or 0)
            stagnation = int(entry.get("bestNotEnhance", 0) or 0)

            # is-perfect = không còn vi phạm cứng nào; is-best = fitness cao nhất
            perfect = " is-perfect" if violation_total == 0 else ""
            best = " is-best" if index == best_index else ""
            selected = index == len(history) - 1

            crit_html = "".join(
                '<span class="cell-crit {state}">{letter}{violation}</span>'.format(
                    state="ok" if violation == 0 else "bad",
                    letter=letter, violation=violation,
                )
                for letter, violation in zip(HtmlOutput.CRITERIAS, violations)
            )
            title = (
                "Thế hệ {generation} · Fitness {fitness:.6f} ({percent:.1f}%) · "
                "Vi phạm: {detail} (tổng {total_violations}) · "
                "Đạt {achieved} · "
                "{elapsed:.1f}s · {population} cá thể · "
                "không cải thiện {stagnation}"
            ).format(
                generation=generation,
                fitness=fitness,
                percent=percent,
                detail=", ".join(
                    "{} {}".format(letter, violation)
                    for letter, violation in zip(HtmlOutput.CRITERIAS, violations)
                ),
                total_violations=violation_total,
                achieved=" · ".join(
                    "{} {}/{}".format(letter, total - violation, total)
                    for letter, violation in zip(HtmlOutput.CRITERIAS, violations)
                ),
                elapsed=elapsed,
                population=population,
                stagnation=stagnation,
            )

            cells.append((
                '<button class="step-cell{perfect}{best}" type="button" '
                'role="tab" id="step-tab-{index}" aria-controls="step-panel" '
                'aria-selected="{selected}" tabindex="{tabindex}" '
                'data-step="{index}" title="{title}">'
                '<span class="cell-gen">Thế hệ {generation}</span>'
                '<span class="cell-fit{fit_class}">{percent:.1f}%</span>'
                '<span class="cell-vio{vio_class}">Vi phạm {total_violations}</span>'
                '<span class="cell-crits">{crit_html}</span>'
                "</button>"
            ).format(
                perfect=perfect,
                best=best,
                index=index,
                selected="true" if selected else "false",
                tabindex="0" if selected else "-1",
                title=html.escape(title, quote=True),
                generation=generation,
                fit_class=" is-perfect" if violation_total == 0 else "",
                percent=percent,
                vio_class=" has-violation" if violation_total else "",
                total_violations=violation_total,
                crit_html=crit_html,
            ))

        # Khung hiển thị khởi tạo sẵn bằng thế hệ cuối cùng để trang vẫn
        # có lịch khi JavaScript không chạy.
        last_index = len(history) - 1
        snapshot = HtmlOutput._snapshotSolution(history[last_index])
        rooms = HtmlOutput.getRoomSections(snapshot)
        head = HtmlOutput.getStepHeadHtml(history[last_index], last_index)

        note = ("Bấm một ô để xem thời khóa biểu của thế hệ đó; "
                "ô nền xanh là thế hệ không có vi phạm, viền vàng là thế hệ "
                "tốt nhất. Di chuyển bằng phím mũi tên.")

        panel = (
            '<div class="step-panel" id="step-panel" role="tabpanel" '
            'aria-labelledby="step-tab-{last_index}">'
            "{head}"
            '<div class="step-panel-body" id="step-panel-body">'
            '<div class="rooms">{rooms}</div>'
            "</div>"
            "</div>"
        ).format(last_index=last_index, head=head, rooms=rooms)

        # Các chuỗi dựng sẵn ở trên chỉ được nối với chuỗi runtime qua "+",
        # nhờ đó không một giá trị người dùng nào lọt vào dấu ngoặc nhọn {}.
        return (
            '<section class="steps-section" aria-labelledby="steps-title">'
            '<div class="section-head">'
            '<div>'
            '<p class="section-kicker">Diễn biến</p>'
            '<h2 id="steps-title">Thời khóa biểu qua các bước</h2>'
            "</div>"
            f'<p class="section-note">{len(history)} thế hệ · '
            "10 ô mỗi hàng · cuộn trong khung để xem đủ · "
            "bấm ô để xem lịch</p>"
            "</div>"
            '<p class="tab-note">' + note + "</p>"
            '<div class="step-grid-wrap">'
            '<div class="step-grid" id="step-grid" role="tablist" '
            'aria-label="Các thế hệ của thuật toán">'
            + "".join(cells) +
            "</div>"
            "</div>"
            + panel +
            "</section>"
        )

    @staticmethod
    def getInputTable(headers, rows, aligns=None, footer=None):
        """Dựng một bảng HTML nhỏ cho phần dữ liệu đầu vào."""
        if aligns is None:
            aligns = ["l"] * len(headers)

        def align_class(align):
            return ' class="num"' if align == "r" else ""

        def body_cells(values):
            return "".join(
                f'<td{align_class(aligns[i])}>{html.escape(str(value))}</td>'
                for i, value in enumerate(values)
            )

        head_cells = "".join(
            f'<th scope="col"{align_class(aligns[i])}>{html.escape(str(header))}</th>'
            for i, header in enumerate(headers)
        )
        body_rows = [f"<tr>{body_cells(row)}</tr>" for row in rows]
        foot_html = (
            f"<tfoot><tr>{body_cells(footer)}</tr></tfoot>"
            if footer is not None else ""
        )

        return (
            '<div class="input-table-wrap">'
            '<table class="input-table">'
            f'<thead><tr>{head_cells}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody>'
            f'{foot_html}'
            '</table>'
            '</div>'
        )

    @staticmethod
    def getInputCard(title, count, table_html, wide=False):
        """Tạo một thẻ chứa bảng dữ liệu đầu vào."""
        card_class = "input-card input-card--wide" if wide else "input-card"
        return (
            f'<article class="{card_class}">'
            '<div class="input-card-head">'
            f'<h3>{html.escape(title)}</h3>'
            f'<span class="badge badge-muted">{count}</span>'
            '</div>'
            f'{table_html}'
            '</article>'
        )

    @staticmethod
    def formatBusySlots(slots):
        """Định dạng các ô bận (day, offset) thành chuỗi khớp đúng bảng lịch.

        Số tiết lấy từ Constant.periodNumber nên buổi chiều (offset 7..12) hiện
        là tiết 7..12 chứ không phải 8..13, và mỗi ngày được gộp gọn thành một
        cụm. VD: {(0,1),(0,2),(0,7),(0,8),(0,9),(0,10)} -> 'T2 tiết 2-3, 7-10'.

        day và offset đều 0-based (đúng như Professor.BusySlots), vì thế nhãn ngày
        tra WEEK_DAYS[day] trực tiếp còn offset đi qua splitBusyRuns để tách dải.
        """
        offsets_by_day = {}
        for day, offset in slots:
            offsets_by_day.setdefault(day, []).append(offset)

        parts = []
        for day in sorted(offsets_by_day):
            runs = HtmlOutput.splitBusyRuns(offsets_by_day[day])
            if not runs:
                continue
            day_name = (HtmlOutput.WEEK_DAYS[day]
                        if 0 <= day < len(HtmlOutput.WEEK_DAYS)
                        else f"Ngày {day + 1}")
            parts.append("{} {}".format(day_name, HtmlOutput.formatBusyRuns(runs)))

        if not parts:
            return "—"
        return " · ".join(parts)

    @staticmethod
    def getSoftMetrics(solution):
        """Đếm số lớp vi phạm ràng buộc mềm B, dùng cho chú thích kết quả.

        Đây là bản mô phỏng lại phần phạt mềm của Schedule.calculateFitness:
        với mỗi lớp, chỉ cần MỘT tiết trùng khung bận của giảng viên được giao là
        lớp đó bị tính một lần (break), mức phạt busyPenalty = 0.2 điểm/lớp.
        Vòng lặp ở đây dùng offset 0-based của reservation.Time — cùng quy ước
        với isBusyAt(day, offset), khác với periodId 1-based của bảng lịch.
        """
        classes = getattr(solution, "classes", None) or {}
        professors = getattr(solution, "professors", None) or {}
        busy_violations = 0

        for cc, reservation_index in classes.items():
            prof = professors.get(cc)
            if prof is None:
                continue
            reservation = Reservation.parse(reservation_index)
            # day/time là 0-based: kiểm tra dur tiết liên tiếp kể từ time
            day, time, dur = reservation.Day, reservation.Time, cc.Duration
            if any(prof.isBusyAt(day, time + off) for off in range(dur)):
                busy_violations += 1

        return {'B': busy_violations}

    @staticmethod
    def getSoftLegendHtml(solution):
        """Dựng mục 'Ràng buộc mềm' hiển thị ký hiệu + trọng số + giá trị hiện tại.

        Mức phạt hiển thị lấy thẳng từ Criteria.busyPenalty (0.2) và so với
        Criteria.hardPenalty (1.0) để người đọc hiểu vì sao GA luôn sửa P/G/N trước.
        """
        metrics = HtmlOutput.getSoftMetrics(solution)
        classes = getattr(solution, "classes", None) or {}
        has_solution = bool(classes)

        # trọng số của từng ràng buộc mềm (để người dùng thấy mức phạt)
        weights = {'B': Criteria.busyPenalty}

        def fmt(letter):
            if not has_solution:
                return "—"
            value = metrics.get(letter, 0)
            return f"{value} lớp dính bận"

        items = "".join(
            '<li class="legend-item legend-item--soft">'
            f'<span class="crit crit--soft">{letter}</span>'
            '<span class="soft-body">'
            f'<span>{html.escape(label)}</span>'
            f'<span class="soft-value">phạt ×{weights[letter]:g} · {fmt(letter)}</span>'
            '</span></li>'
            for letter, label in zip(HtmlOutput.SOFT_CRITERIAS, HtmlOutput.SOFT_LABELS)
        )

        return (
            '<div class="legend-subhead">'
            '<h3>Ràng buộc mềm (tối ưu lịch giảng dạy)</h3>'
            '<p class="legend-note">Không bắt buộc đạt và <strong>luôn nhẹ hơn '
            'ràng buộc cứng</strong>: một vi phạm mềm phạt dưới '
            f'{Criteria.hardPenalty:g} điểm, trong khi một vi phạm cứng mất trọn '
            f'{Criteria.hardPenalty:g} điểm. Thuật toán vì thế sửa P/G/N trước, '
            'rồi mới tối ưu giờ rảnh của giảng viên. '
            'B = bận.</p>'
            '</div>'
            f'<ul class="legend-items">{items}</ul>'
        )

    @staticmethod
    def getBusyGridsHtml(configuration):
        """Dựng các lưới lịch bận (click để chọn/bật tắt ô bận) cho từng giảng viên.

        Lưới chỉ có 12 cột tiết vì offset nghỉ trưa (LUNCH_PERIOD = 6) bị loại khỏi
        `periods`; mỗi ô mang data-day / data-time là chỉ số 0-based đúng như
        Professor.BusySlots, nên thu gom phía JavaScript gửi về server không phải
        đổi hệ chỉ số.
        """
        profs = sorted(configuration._professors.values(), key=lambda item: item.Id)
        # 13 offset của một ngày, trừ ô nghỉ trưa -> 12 tiết dạy thực tế
        periods = [i for i in range(Constant.DAY_HOURS) if i != Constant.LUNCH_PERIOD]
        parts = []
        for prof in profs:
            is_busy = set(prof.BusySlots)
            head_cells = []
            for p in periods:
                head_cells.append(
                    '<span class="busy-col" data-period="{}" title="{}">'
                    '<span class="busy-col-name">{}</span>'
                    '<span class="busy-col-time">{}</span></span>'.format(
                        p,
                        html.escape("Tiết {} · {}".format(
                            Constant.periodNumber(p),
                            Constant.periodTimeRange(p, sep="-"))),
                        Constant.periodNumber(p),
                        # chỉ ghi giờ bắt đầu cho cột gọn không tràn hàng
                        html.escape(Constant.formatHM(Constant.periodStart(p)))))
            head_html = (
                '<div class="busy-row busy-row-head">'
                '<span class="busy-corner" title="Số tiết và giờ bắt đầu">Tiết'
                '</span>' + "".join(head_cells) + '</div>')

            rows_html = []
            for d in range(Constant.DAYS_NUM):
                cells = []
                for p in periods:
                    busy = (d, p) in is_busy
                    busy_cls = " is-busy" if busy else ""
                    cells.append(
                        '<button type="button" class="busy-cell{}" '
                        'data-prof="{pid}" data-day="{day}" data-time="{time}" '
                        'aria-pressed="{pressed}" title="{label}">'
                        '<span class="busy-dot"></span></button>'.format(
                            busy_cls, pid=prof.Id, day=d, time=p,
                            pressed="true" if busy else "false",
                            label=html.escape("{} · tiết {} · {}".format(
                                HtmlOutput.WEEK_DAYS[d],
                                Constant.periodNumber(p),
                                Constant.periodTimeRange(p, sep="-")))))
                rows_html.append(
                    '<div class="busy-row" data-day="{}"><span class="busy-rowlabel">{}</span>{}</div>'.format(
                        d, HtmlOutput.WEEK_DAYS[d], "".join(cells)))
            grid = (
                '<div class="busy-grid" data-prof="{}">'
                + head_html + "".join(rows_html) + '</div>').format(prof.Id)
            block = (
                '<div class="busy-grid-block" data-prof="{}">'
                '<div class="busy-grid-title">GV {} · {}</div>'
                + grid + '</div>').format(prof.Id, prof.Id, html.escape(prof.Name))
            parts.append(block)
        return "".join(parts)

    @staticmethod
    def getInputSection(solution):
        """Tab "Dữ liệu đầu vào": bảng giảng viên / lớp học phần / phòng học.

        Số tiết bận của mỗi giảng viên là len(BusySlots) — tập (ngày, offset)
        0-based mà người dùng chọn trên lưới busy-grid; chính các ô này tạo ra vi
        phạm ràng buộc mềm B khi GA xếp lớp của họ vào đó.
        """
        configuration = solution.configuration
        classes = list(configuration.courseClasses)

        professors = sorted(configuration._professors.values(), key=lambda item: item.Id)
        professor_rows = []
        for professor in professors:
            # hiển thị năng lực giảng dạy (các môn phụ trách) từ danh sách subjects
            courses = sorted(
                {
                    configuration.getCourseById(cid).Name
                    for cid in professor.Subjects
                    if configuration.getCourseById(cid) is not None
                },
                key=str.casefold,
            )
            # giảng viên tự chọn số tiết bận trong tuần
            busy_text = HtmlOutput.formatBusySlots(professor.BusySlots)
            professor_rows.append([
                professor.Id,
                professor.Name,
                ", ".join(courses) if courses else "—",
                len(professor.BusySlots),
                busy_text,
            ])

        class_rows = []
        for course_class in sorted(
            classes, key=lambda item: (item.Course.Id, item.Id)
        ):
            # giảng viên không còn cài sẵn: GA tự gán khi xếp lịch
            class_rows.append([
                course_class.Id,
                course_class.Course.Name,
                course_class.Duration,
            ])
        class_footer = ["", "Tổng cộng", sum(row[2] for row in class_rows)]

        # sức chứa một phòng: TEACHING_HOURS (12 tiết dạy/ngày, đã trừ nghỉ trưa)
        # x DAYS_NUM (5 ngày) = 60 giờ/tuần
        capacity = Constant.TEACHING_HOURS * Constant.DAYS_NUM
        rooms = sorted(configuration._rooms.values(), key=lambda item: item.Id)
        room_rows = [
            [room.Id, room.Name, f"{capacity} giờ"]
            for room in rooms
        ]

        professor_card = HtmlOutput.getInputCard(
            "Giảng viên",
            len(professor_rows),
            HtmlOutput.getInputTable(
                ["Mã", "Họ tên", "Môn học phụ trách", "Số tiết bận", "Lịch bận"],
                professor_rows,
                ["r", "l", "l", "c", "l"],
            ),
        )
        class_card = HtmlOutput.getInputCard(
            "Lớp học phần",
            len(class_rows),
            HtmlOutput.getInputTable(
                ["Mã lớp", "Môn học", "Số tiết/tuần"],
                class_rows,
                ["r", "l", "r"],
                footer=class_footer,
            ),
        )
        room_card = HtmlOutput.getInputCard(
            "Phòng học",
            len(room_rows),
            HtmlOutput.getInputTable(
                ["Mã", "Phòng học", "Sức chứa/tuần"],
                room_rows,
                ["r", "l", "r"],
            ),
        )

        summary_counts = (
            f"{len(professor_rows)} giảng viên · {len(class_rows)} lớp học phần · "
            f"{len(room_rows)} phòng"
        )

        return (
            '<details class="input-section" aria-labelledby="input-title">'
            '<summary class="input-summary">'
            '<div>'
            '<p class="section-kicker">Dữ liệu nguồn</p>'
            '<h2 id="input-title">Dữ liệu đầu vào</h2>'
            '</div>'
            '<div class="input-summary-meta">'
            f'<span class="input-summary-note">{summary_counts} · '
            'nhấn để mở hoặc thu gọn</span>'
            '</div>'
            '</summary>'
            '<div class="input-body">'
            '<div class="result-tabs" role="tablist" '
            'aria-label="Dữ liệu đầu vào">'
            '<button class="result-tab" type="button" role="tab" '
            'id="input-tab-professors" aria-controls="input-panel-professors" '
            'aria-selected="true">Giảng viên</button>'
            '<button class="result-tab" type="button" role="tab" '
            'id="input-tab-classes" aria-controls="input-panel-classes" '
            'aria-selected="false" tabindex="-1">Lớp học phần</button>'
            '<button class="result-tab" type="button" role="tab" '
            'id="input-tab-rooms" aria-controls="input-panel-rooms" '
            'aria-selected="false" tabindex="-1">Phòng học</button>'
            '</div>'
            '<div class="result-panel" role="tabpanel" '
            'id="input-panel-professors" aria-labelledby="input-tab-professors">'
            f'{professor_card}'
            '<div class="busy-grid-section">'
            f'{HtmlOutput.getBusyGridsHtml(configuration)}'
            '</div>'
            '</div>'
            '<div class="result-panel" role="tabpanel" '
            'id="input-panel-classes" aria-labelledby="input-tab-classes" hidden>'
            f'{class_card}'
            '</div>'
            '<div class="result-panel" role="tabpanel" '
            'id="input-panel-rooms" aria-labelledby="input-tab-rooms" hidden>'
            f'{room_card}'
            '</div>'
            '</div>'
            '</details>'
        )

    @staticmethod
    def getSettingsSection(parameters=None):
        """Khối điều khiển thông số GA: sinh input cho từng trường trong FIELDS.

        Giá trị hiển thị qua normalize() nên thiếu thông số vẫn có mặc định hợp lệ;
        mỗi input mang min/max/step để trình duyệt chặn giá trị ngoài khoảng.
        """
        values = normalize(parameters)
        fields = []
        for field in FIELDS:
            name = field["name"]
            field_id = "param-{}".format(name)
            help_id = "{}-help".format(field_id)
            input_mode = "decimal" if field["kind"] == "float" else "numeric"
            unit = ""
            if field["unit"]:
                unit = '<span class="setting-unit">{}</span>'.format(
                    html.escape(field["unit"])
                )
            fields.append(
                '<label class="setting-field" for="{}">'
                '<span class="setting-label">{}</span>'
                '<span class="setting-control">'
                '<input id="{}" name="{}" type="number" value="{}" '
                'min="{}" max="{}" step="{}" inputmode="{}" '
                'aria-describedby="{}" autocomplete="off" required>'
                '{}</span>'
                '<span class="setting-help" id="{}">{}</span>'
                '</label>'.format(
                    field_id,
                    html.escape(field["label"]),
                    field_id,
                    name,
                    format_value(values[name]),
                    format_value(field["min"]),
                    format_value(field["max"]),
                    format_value(field["step"]),
                    input_mode,
                    help_id,
                    unit,
                    help_id,
                    html.escape(field["help"]),
                )
            )

        return (
            '<section class="input-section settings-section" '
            'aria-labelledby="settings-title">'
            '<div class="settings-header">'
            '<div class="settings-heading">'
            '<p class="section-kicker">Điều khiển</p>'
            '<h2 id="settings-title">Thông số thuật toán</h2>'
            '<p class="settings-summary-note">{} · thay đổi áp dụng cho lần chạy mới</p>'
            '</div>'
            '<div class="settings-header-actions">'
            '<button class="rerun-button rerun-button--header" id="rerun-button" '
            'type="button" data-rerun '
            'title="Chạy thuật toán với thông số hiện tại">'
            '▶ Chạy</button>'
            '<p class="settings-status" id="settings-status" '
            'data-rerun-status role="status" aria-live="polite"></p>'
            '</div>'
            '</div>'
            '<details class="settings-details" open>'
            '<summary class="settings-toggle">Thông số chi tiết</summary>'
            '<div class="settings-body">'
            '<p class="settings-note">Điều chỉnh thông số cho lần chạy tới, '
            'sau đó bấm <strong>▶ Chạy</strong> ở phần đầu khối này.</p>'
            '<form id="ga-parameters" class="settings-form" autocomplete="off">'
            '<div class="settings-grid">{}</div>'
            '</form>'
            '</div>'
            '</details>'
            '</section>'
        ).format(summary(values), "".join(fields))

    @staticmethod
    def getResult(solution, history=None, parameters=None):
        """Điểm vào chính: dựng cả hai bộ bảng (phòng học, giảng viên) rồi xuất trang.

        solution là nhiễm sắc thể tốt nhất sau khi GA kết thúc, history là ảnh chụp
        từng thế hệ do Trace.get_history() trả về, parameters là thông số GA để
        hiển thị lại trong khối điều khiển.
        """
        room_sections = HtmlOutput.getRoomSections(solution)
        professor_sections = HtmlOutput.getProfessorSections(solution)
        return HtmlOutput.getDocument(
            solution,
            room_sections,
            professor_sections=professor_sections,
            history=history,
            parameters=parameters,
        )

    @staticmethod
    def getDocument(solution, room_sections, professor_sections="",
                    history=None, parameters=None):
        """Ghép mọi khối HTML thành một trang hoàn chỉnh, tự chứa CSS/JS.

        Trình tự khối: header (chỉ số + điểm fitness) -> thông số GA -> chú thích
        tiêu chí -> dữ liệu đầu vào -> thời khoá biểu cuối (tab phòng/giảng viên)
        -> biểu đồ fitness -> lưới thế hệ -> dữ liệu JSON + PAGE_SCRIPT.
        """
        configuration = solution.configuration
        # tổng số tiết cần xếp = tổng Duration của mọi lớp học phần
        total_hours = sum(cc.Duration for cc in configuration.courseClasses)

        stats = (
            (len(solution.classes), "lớp học"),
            (configuration.numberOfRooms, "phòng"),
            (configuration.numberOfProfessors, "giảng viên"),
            (total_hours, "tiết học"),
        )
        stats_html = "".join(
            f'<li class="stat"><strong>{value}</strong><span>{label}</span></li>'
            for value, label in stats
        )

        fitness = getattr(solution, "fitness", None)
        if fitness is None:
            score_html = ""
        else:
            # fitness đã chuẩn hoá trong [0, 1]: (điểm cứng - phạt mềm)/(3 x số lớp)
            # -> nhân 100 thành %; 100% nghĩa là không còn vi phạm cứng nào
            percent = max(0.0, min(1.0, float(fitness))) * 100
            perfect_class = " perfect" if percent >= 99.95 else ""
            score_html = (
                f'<div class="score{perfect_class}">'
                f'<span class="score-value">{percent:.1f}%</span>'
                '<span class="score-label">Độ phù hợp</span>'
                '</div>'
            )

        # chú thích 3 ràng buộc cứng: CRITERIAS và CRITERIA_LABELS đồng chỉ số i
        legend_items = "".join(
            f'<li class="legend-item"><span class="crit">{letter}</span>'
            f'<span>{html.escape(label)}</span></li>'
            for letter, label in zip(HtmlOutput.CRITERIAS, HtmlOutput.CRITERIA_LABELS)
        )
        soft_legend_html = HtmlOutput.getSoftLegendHtml(solution)

        generated_at = datetime.now().strftime("%H:%M · %d/%m/%Y")
        # dòng mô tả quy ước thời gian: 5 ngày x 12 tiết (6 sáng + 6 chiều),
        # mỗi tiết 50 phút liền nhau, sáng từ 7:00, chiều từ 13:00, nghỉ trưa 12-13h
        subtitle = (
            f"Kết quả xếp lịch cho {Constant.DAYS_NUM} ngày làm việc, "
            f"mỗi ngày 2 buổi × {Constant.TEACHING_HOURS // 2} tiết, "
            f"mỗi tiết {Constant.PERIOD_MINUTES} phút, các tiết trong buổi liền nhau "
            f"(sáng {Constant.formatHM(Constant.periodStart(0))}–"
            f"{Constant.formatHM(Constant.periodStart(Constant.LUNCH_PERIOD - 1) + Constant.PERIOD_MINUTES)}, "
            f"chiều {Constant.formatHM(Constant.periodStart(Constant.LUNCH_PERIOD + 1))}–"
            f"{Constant.formatHM(Constant.periodStart(Constant.DAY_HOURS - 1) + Constant.PERIOD_MINUTES)}). "
            f"Khung {Constant.lunchRange()} là giờ nghỉ trưa."
        )
        settings_html = HtmlOutput.getSettingsSection(parameters)
        input_html = HtmlOutput.getInputSection(solution)
        # hai khối diễn biến: biểu đồ fitness (SVG) và lưới thế hệ bấm-để-xem-lịch
        history_html = HtmlOutput.getHistorySection(history)
        steps_html = HtmlOutput.getStepsSection(history)
        # payload JSON gọn cho JavaScript, đặt cuối trang để không chặn hiển thị
        steps_data = HtmlOutput.getStepsData(history)

        return (
            '<!DOCTYPE html>\n'
            '<html lang="vi">\n'
            '<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>Thời khóa biểu tuần · GaSchedule</title>\n'
            + HtmlOutput.PAGE_STYLE + '\n'
            '</head>\n'
            '<body>\n'
            '<main class="page">\n'
            '<header class="hero">\n'
            '<div class="hero-content">\n'
            '<div class="hero-row">\n'
            '<div>\n'
            '<p class="eyebrow">GaSchedule · Kết quả lập thời khóa biểu</p>\n'
            '<h1>Thời khóa biểu tuần</h1>\n'
            f'<p class="subtitle">{subtitle}</p>\n'
            '</div>\n'
            '<div class="hero-actions">\n'
            f'{score_html}\n'
            '</div>\n'
            '</div>\n'
            f'<ul class="stats">{stats_html}</ul>\n'
            '</div>\n'
            '</header>\n'
            f'{settings_html}\n'
            '<section class="legend" aria-label="Chú thích tiêu chí">\n'
            '<div class="legend-head">\n'
            '<h2>Chú thích</h2>\n'
            '<p class="legend-note">'
            '<span class="legend-ok">Xanh</span> = đạt · '
            '<span class="legend-bad">Đỏ</span> = vi phạm ràng buộc cứng · '
            '<span class="legend-soft">Cam</span> = vi phạm ràng buộc mềm. '
            f'Mỗi vi phạm cứng mất trọn {Criteria.hardPenalty:g} điểm, còn ràng buộc '
            'mềm luôn phạt ít hơn nên thuật toán sửa P/G/N trước. '
            'Di chuột hoặc chạm vào ký hiệu để xem chi tiết. '
            'Các tiết liền nhau của cùng một lớp gộp thành một ô; lớp trùng phòng '
            'được xếp chồng trong cùng một ô.'
            '</p>\n'
            '</div>\n'
            f'<ul class="legend-items">{legend_items}</ul>\n'
            f'{soft_legend_html}\n'
            '</section>\n'
            f'{input_html}\n'
            '<section class="result-section" aria-labelledby="result-title">\n'
            '<div class="section-head">\n'
            '<div>\n'
            '<p class="section-kicker">Kết quả cuối</p>\n'
            '<h2 id="result-title">Thời khóa biểu cuối cùng</h2>\n'
            '</div>\n'
            '<p class="section-note">Lời giải tốt nhất sau khi thuật toán kết thúc; '
            'chuyển tab để xem theo phòng học hoặc theo giảng viên.</p>\n'
            '</div>\n'
            '<div class="result-tabs" role="tablist" '
            'aria-label="Kiểu hiển thị thời khóa biểu">\n'
            '<button class="result-tab" type="button" role="tab" '
            'id="tab-rooms" aria-controls="panel-rooms" '
            'aria-selected="true">Theo phòng học</button>\n'
            '<button class="result-tab" type="button" role="tab" '
            'id="tab-professors" aria-controls="panel-professors" '
            'aria-selected="false" tabindex="-1">Theo giảng viên</button>\n'
            '</div>\n'
            '<div class="result-panel" role="tabpanel" '
            'id="panel-rooms" aria-labelledby="tab-rooms">\n'
            '<div class="rooms">\n'
            f'{room_sections}\n'
            '</div>\n'
            '</div>\n'
            '<div class="result-panel" role="tabpanel" '
            'id="panel-professors" aria-labelledby="tab-professors" hidden>\n'
            '<p class="tab-note">Mỗi bảng là thời khóa biểu trong tuần của một '
            'giảng viên; bấm vào tên để thu gọn hoặc mở rộng.</p>\n'
            '<div class="rooms">\n'
            f'{professor_sections}\n'
            '</div>\n'
            '</div>\n'
            '</section>\n'
            f'{history_html}\n'
            f'{steps_html}\n'
            '<footer class="footer">\n'
            '<span>Được tạo bởi <strong>GASchedule.py</strong></span>\n'
            f'<span>Cập nhật lúc {generated_at}</span>\n'
            '</footer>\n'
            '</main>\n'
            f'{steps_data}\n'
            f'{HtmlOutput.PAGE_SCRIPT}\n'
            '</body>\n'
            '</html>\n'
        )
