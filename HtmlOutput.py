import html
import math
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace

from model.Constant import Constant
from model.Reservation import Reservation


class HtmlOutput:
    ROOM_COLUMN_NUMBER = Constant.DAYS_NUM + 1
    ROOM_ROW_NUMBER = Constant.DAY_HOURS + 1
    COLOR1 = "#047857"
    COLOR2 = "#b91c1c"
    # Số bước tối đa hiển thị thời khóa biểu chi tiết trong file HTML.
    MAX_STEP_PANELS = 60
    # Ký hiệu viết tắt của 4 tiêu chí kiểm tra ràng buộc:
    #   P = Phòng học   C = Chỗ ngồi
    #   G = Giảng viên  S = Sinh viên
    CRITERIAS = ('P', 'C', 'G', 'S')
    CRITERIA_LABELS = (
        "Phòng không trùng lịch",
        "Đủ số chỗ ngồi",
        "Giảng viên không trùng lịch",
        "Nhóm sinh viên không trùng lịch",
    )
    OK_DESCR = (
        "Phòng học không bị trùng lịch",
        "Phòng học có đủ chỗ ngồi",
        "Giảng viên không bị trùng lịch dạy",
        "Nhóm sinh viên không bị trùng lịch học",
    )
    FAIL_DESCR = (
        "Phòng học bị trùng lịch",
        "Phòng học không đủ chỗ ngồi",
        "Giảng viên bị trùng lịch dạy",
        "Nhóm sinh viên bị trùng lịch học",
    )
    PERIODS = (
        "", "Tiết 1", "Tiết 2", "Tiết 3", "Tiết 4",
        "Tiết 5", "Tiết 6", "Tiết 7", "Tiết 8",
        "Tiết 9", "Tiết 10", "Tiết 11", "Tiết 12"
    )
    PERIOD_TIMES = (
        "", "9:00 – 10:00", "10:00 – 11:00", "11:00 – 12:00", "12:00 – 13:00",
        "13:00 – 14:00", "14:00 – 15:00", "15:00 – 16:00", "16:00 – 17:00",
        "17:00 – 18:00", "18:00 – 19:00", "19:00 – 20:00", "20:00 – 21:00"
    )
    WEEK_DAYS = ("T2", "T3", "T4", "T5", "T6")
    WEEK_DAY_NAMES = ("Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu")

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
            --amber-bg: #fffbeb;
            --shadow-lg: 0 24px 60px -32px rgba(15, 23, 42, .45);
            --shadow-sm: 0 10px 30px -22px rgba(15, 23, 42, .4);
        }

        * { box-sizing: border-box; }

        html { -webkit-text-size-adjust: 100%; }

        body {
            margin: 0;
            min-height: 100vh;
            color: var(--text);
            background:
                radial-gradient(1100px 560px at 8% -8%, #dbeafe 0%, rgba(219, 234, 254, 0) 60%),
                radial-gradient(900px 500px at 100% 0%, #ede9fe 0%, rgba(237, 233, 254, 0) 55%),
                var(--bg);
            font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
            font-size: 15px;
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

        .schedule tbody tr:nth-child(even) td.empty { background: #fbfcfe; }

        .schedule td.filled {
            background: #fff;
            transition: background .15s ease;
        }

        .schedule td.filled.conflict {
            background: #fffafa;
        }

        .schedule tbody tr:hover td.filled { background: #f8fbff; }
        .schedule tbody tr:hover td.empty { background: #f8fafc; }

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

        .tag-group {
            color: #1e40af;
            background: #eff6ff;
            border: 1px solid #dbeafe;
        }

        .tag-duration {
            color: #475569;
            background: #f1f5f9;
            border: 1px solid var(--border);
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
            font-size: 12px;
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

        .step-list {
            display: grid;
            gap: 12px;
            margin-top: 16px;
        }

        .step {
            overflow: hidden;
            background: var(--surface);
            border: 1px solid rgba(226, 232, 240, .95);
            border-radius: 16px;
            box-shadow: var(--shadow-sm);
        }

        .step > summary {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px 14px;
            padding: 14px 18px;
            cursor: pointer;
            list-style: none;
        }

        .step > summary::-webkit-details-marker { display: none; }
        .step > summary::marker { content: ""; }
        .step > summary:hover { background: #f8fbff; }

        .step > summary::after {
            content: "▾";
            margin-left: 4px;
            color: var(--muted);
            font-size: .85rem;
            transition: transform .15s ease;
        }

        .step[open] > summary {
            border-bottom: 1px solid var(--border);
            background: #f8fbff;
        }

        .step[open] > summary::after { transform: rotate(180deg); }

        .step-main {
            display: flex;
            flex: 1 1 220px;
            flex-direction: column;
            min-width: 150px;
            line-height: 1.3;
        }

        .step-title {
            color: var(--text);
            font-size: .9rem;
            font-weight: 700;
        }

        .step-meta {
            margin-top: 1px;
            color: var(--muted);
            font-size: .73rem;
        }

        .step-meter {
            display: inline-block;
            width: 82px;
            height: 6px;
            overflow: hidden;
            border-radius: 999px;
            background: #e2e8f0;
        }

        .step-meter span {
            display: block;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #60a5fa, var(--brand));
        }

        .step-counts {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 5px;
        }

        .step-score {
            color: var(--brand);
            font-size: .76rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }

        .step-body { padding: 16px 18px 18px; }

        .step .rooms {
            gap: 16px;
            margin-top: 0;
        }

        .step .room {
            border-radius: 16px;
            box-shadow: none;
        }

        .step .room-head { padding: 14px 18px; }

        .step .room-head h2 { font-size: 1.1rem; }

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
            .step > summary { padding: 13px 14px; gap: 8px 10px; }
            .step-main { flex-basis: 100%; }
            .step-counts { width: 100%; }
            .step-body { padding: 12px; }
            .step .rooms { gap: 12px; }
            .step .room-head { padding: 12px 14px; }
        }

        @media print {
            body {
                background: #fff;
                font-size: 11px;
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

            .result-section { margin-top: 18px; }
            .result-section .rooms { margin-top: 12px; }
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

    @staticmethod
    def getCriteriaBadges(criterias, ci):
        """Tạo 4 huy hiệu tiêu chí P/C/G/S cho một lớp học."""
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
        sb.append('</div>')
        return "".join(sb)

    @staticmethod
    def getCourseClass(cc, criterias, ci):
        """Tạo nội dung HTML cho một ô lịch (môn học, giảng viên, nhóm, tiêu chí)."""
        sb = [
            '<div class="course">', html.escape(cc.Course.Name), '</div>',
            '<div class="prof">', html.escape(cc.Professor.Name), '</div>',
        ]

        groups = sorted((g.Name for g in cc.Groups), key=str.casefold)
        if groups or cc.Duration > 1:
            sb.append('<div class="tags">')
            for group_name in groups:
                sb.append('<span class="tag tag-group">')
                sb.append(html.escape(group_name))
                sb.append('</span>')
            if cc.Duration > 1:
                sb.append(f'<span class="tag tag-duration">{cc.Duration} tiết</span>')
            sb.append('</div>')

        sb.append(HtmlOutput.getCriteriaBadges(criterias, ci))
        return "".join(sb)

    @staticmethod
    def getContinuedClass(cc, criterias, ci):
        """Phiên bản rút gọn cho các tiết tiếp theo của lớp đang kéo dài."""
        return "".join([
            '<div class="course">', html.escape(cc.Course.Name), '</div>',
            '<div class="prof">', html.escape(cc.Professor.Name), '</div>',
            '<div class="tags"><span class="tag tag-continued">Tiếp tiết</span></div>',
            HtmlOutput.getCriteriaBadges(criterias, ci),
        ])

    @staticmethod
    def generateTimeTable(solution):
        """Dựng lịch theo phòng/ngày/tiết, giữ mọi lớp kể cả khi bị trùng phòng."""
        ci = 0

        entries_by_slot = defaultdict(lambda: defaultdict(list))
        getCourseClass = HtmlOutput.getCourseClass
        getContinuedClass = HtmlOutput.getContinuedClass

        for cc, reservation_index in solution.classes.items():
            reservation = Reservation.parse(reservation_index)

            # toạ độ của ô thời gian - không gian
            dayId = reservation.Day + 1
            startPeriod = reservation.Time + 1
            roomId = reservation.Room
            duration = cc.Duration

            entry = {
                "start": startPeriod,
                "duration": duration,
                "html": getCourseClass(cc, solution.criteria, ci),
                "continued": getContinuedClass(cc, solution.criteria, ci),
            }

            for offset in range(duration):
                periodId = startPeriod + offset
                if periodId >= HtmlOutput.ROOM_ROW_NUMBER:
                    break
                entries_by_slot[(roomId, dayId)][periodId].append(entry)

            ci += len(HtmlOutput.CRITERIAS)

        overlapping_slots = {
            key
            for key, periods in entries_by_slot.items()
            if any(len(entries) > 1 for entries in periods.values())
        }
        return entries_by_slot, overlapping_slots

    @staticmethod
    def getHtmlCell(content, rowspan):
        if content is None:
            return '<td class="slot empty"></td>'

        if rowspan and rowspan > 1:
            return f'<td class="slot filled" rowspan="{int(rowspan)}">{content}</td>'
        return f'<td class="slot filled">{content}</td>'

    @staticmethod
    def getRoomTable(room, roomId, entries_by_slot, overlapping_slots):
        rows = []
        covered = {
            dayId: set()
            for dayId in range(1, HtmlOutput.ROOM_COLUMN_NUMBER)
        }

        for periodId in range(1, HtmlOutput.ROOM_ROW_NUMBER):
            cells = []
            for dayId in range(1, HtmlOutput.ROOM_COLUMN_NUMBER):
                if periodId in covered[dayId]:
                    # Ô đã được phủ bởi rowspan của lớp học ở tiết phía trên.
                    continue

                day_entries = entries_by_slot.get((roomId, dayId), {})
                slot_entries = day_entries.get(periodId, [])
                if not slot_entries:
                    cells.append('<td class="slot empty"></td>')
                    continue

                has_overlap = (roomId, dayId) in overlapping_slots
                if not has_overlap and len(slot_entries) == 1:
                    entry = slot_entries[0]
                    if entry["start"] == periodId:
                        span = min(
                            entry["duration"],
                            HtmlOutput.ROOM_ROW_NUMBER - periodId,
                        )
                        content = f'<div class="course-card">{entry["html"]}</div>'
                        cells.append(HtmlOutput.getHtmlCell(content, span))
                        if span > 1:
                            covered[dayId].update(
                                range(periodId + 1, periodId + span)
                            )
                        continue

                    content = (
                        f'<div class="course-card continued">'
                        f'{entry["continued"]}</div>'
                    )
                    cells.append(f'<td class="slot filled">{content}</td>')
                    continue

                # Trùng phòng: xếp chồng mọi lớp đang diễn ra trong cùng ô.
                cards = []
                if len(slot_entries) > 1:
                    cards.append('<div class="slot-warning">Trùng phòng</div>')
                for entry in slot_entries:
                    if entry["start"] == periodId:
                        cards.append(
                            f'<div class="course-card">{entry["html"]}</div>'
                        )
                    else:
                        cards.append(
                            f'<div class="course-card continued">'
                            f'{entry["continued"]}</div>'
                        )
                content = f'<div class="slot-stack">{"".join(cards)}</div>'
                cells.append(f'<td class="slot filled conflict">{content}</td>')

            rows.append(
                '<tr>'
                f'<th class="period" scope="row">'
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
            '<section class="room">'
            '<div class="room-head">'
            '<div class="room-title">'
            '<span class="room-kicker">Phòng học</span>'
            f'<h2>{html.escape(room.Name)}</h2>'
            '</div>'
            '<div class="room-badges">'
            f'<span class="badge">{room.NumberOfSeats} chỗ ngồi</span>'
            '</div>'
            '</div>'
            '<p class="scroll-hint">Vuốt ngang để xem đủ các ngày '
            '<span aria-hidden="true">→</span></p>'
            '<div class="table-wrap">'
            '<table class="schedule">'
            f'<caption class="sr-only">Thời khóa biểu phòng {html.escape(room.Name)}</caption>'
            '<thead><tr>'
            '<th class="corner" scope="col">Tiết / Ngày</th>'
            f'{day_headers}'
            '</tr></thead>'
            '<tbody>'
            + "".join(rows) +
            '</tbody>'
            '</table>'
            '</div>'
            '</section>'
        )

    @staticmethod
    def getRoomSections(solution):
        """Tạo các bảng thời khóa biểu của một lời giải (phòng học)."""
        configuration = solution.configuration
        nr = configuration.numberOfRooms

        entries_by_slot, overlapping_slots = HtmlOutput.generateTimeTable(solution)
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
                    HtmlOutput.getRoomTable(
                        room,
                        roomId,
                        entries_by_slot,
                        overlapping_slots,
                    )
                )
        return "".join(sections)

    @staticmethod
    def _snapshotSolution(entry):
        """Chuyển một bản ghi lịch sử thành đối tượng đủ trường để vẽ lịch."""
        return SimpleNamespace(
            configuration=entry["configuration"],
            classes=entry["classes"],
            criteria=entry["criteria"],
            fitness=entry["fitness"],
        )

    @staticmethod
    def _criteriaCounts(entry):
        """Trả về (số lớp đạt từng tiêu chí, tổng số lớp) của một bản ghi."""
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
    def selectStepEntries(history, max_steps=None):
        """Chọn các bước tiêu biểu để hiển thị lịch chi tiết.

        Kết quả cuối cùng đã được hiển thị riêng ở đầu trang nên bỏ bản ghi
        cuối; các bản ghi còn lại được lấy đều nếu vượt quá max_steps.
        """
        if not history or len(history) <= 1:
            return []

        if max_steps is None:
            max_steps = HtmlOutput.MAX_STEP_PANELS
        max_steps = max(1, int(max_steps))
        candidates = list(history[:-1])
        if len(candidates) <= max_steps:
            return candidates
        if max_steps == 1:
            return [candidates[-1]]

        indexes = sorted({
            int(round(i * (len(candidates) - 1) / (max_steps - 1)))
            for i in range(max_steps)
        })
        return [candidates[i] for i in indexes]

    @staticmethod
    def getFitnessChart(history):
        """Tạo biểu đồ đường fitness qua các thế hệ bằng SVG nội tuyến."""
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
        axis_decimals = 2 if axis_span < 0.02 else (1 if axis_span < 0.5 else 0)

        width, height = 1000, 340
        left, right, top, bottom = 58, 22, 28, 52
        plot_width = width - left - right
        plot_height = height - top - bottom
        baseline = top + plot_height

        def x_for(index):
            if count <= 1:
                return left + plot_width / 2
            return left + (index / (count - 1)) * plot_width

        def y_for(value):
            return top + (axis_max - value) / axis_span * plot_height

        points = [
            (x_for(index), y_for(value))
            for index, value in enumerate(values)
        ]
        line_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        area_path = (
            f"M {points[0][0]:.2f} {baseline:.2f} "
            + " ".join(f"L {x:.2f} {y:.2f}" for x, y in points)
            + f" L {points[-1][0]:.2f} {baseline:.2f} Z"
        )

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

        dots = ""
        if 1 < count <= 160:
            dots = "".join(
                f'<circle class="chart-dot" cx="{x:.2f}" cy="{y:.2f}" r="2.4">'
                f'<title>Thế hệ {html.escape(str(generations[index]))} · '
                f'Fitness {values[index]:.4f}</title></circle>'
                for index, (x, y) in enumerate(points)
            )

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
        """Tạo biểu đồ đánh giá fitness qua từng thế hệ."""
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
    def getStepsSection(history):
        """Tạo các khối thu gọn chứa thời khóa biểu của các bước trung gian."""
        steps = HtmlOutput.selectStepEntries(history)
        if not steps:
            return ""

        panels = []
        for index, entry in enumerate(steps):
            snapshot = HtmlOutput._snapshotSolution(entry)
            rooms = HtmlOutput.getRoomSections(snapshot)
            counts, total = HtmlOutput._criteriaCounts(entry)
            fitness = float(entry.get("fitness", 0.0))
            percent = max(0.0, min(1.0, fitness)) * 100
            counts_html = "".join(
                '<span class="count-pill {}" title="{}: {}/{} lớp đạt">'
                '<strong>{}</strong> {}/{}</span>'.format(
                    "ok" if count == total else "bad",
                    letter, count, total, letter, count, total,
                )
                for letter, count in zip(HtmlOutput.CRITERIAS, counts)
            )
            open_attr = " open" if index == len(steps) - 1 else ""
            generation = entry.get("generation", index + 1)
            elapsed = float(entry.get("elapsed", 0.0) or 0.0)

            panels.append(
                f'<details class="step" id="step-{generation}"{open_attr}>'
                '<summary>'
                '<span class="step-main">'
                f'<span class="step-title">Thế hệ {generation}</span>'
                f'<span class="step-meta">Fitness {fitness:.4f} · {elapsed:.1f}s</span>'
                '</span>'
                f'<span class="step-meter" aria-hidden="true">'
                f'<span style="width:{percent:.1f}%"></span></span>'
                '<span class="step-counts" aria-label="Số lớp đạt các tiêu chí '
                f'P, C, G, S">{counts_html}</span>'
                f'<span class="step-score">{percent:.1f}%</span>'
                '</summary>'
                '<div class="step-body">'
                f'<div class="rooms">{rooms}</div>'
                '</div>'
                '</details>'
            )

        intermediate_count = max(0, len(history) - 1)
        if intermediate_count > len(steps):
            note = (
                f"Hiển thị {len(steps)}/{intermediate_count} bước tiêu biểu; "
                f"biểu đồ fitness phía trên có đủ {len(history)} thế hệ."
            )
        else:
            note = (
                f"Hiển thị {len(steps)} bước trung gian; "
                "kết quả cuối cùng ở phía trên."
            )

        return (
            '<section class="steps-section" aria-labelledby="steps-title">'
            '<div class="section-head">'
            '<div>'
            '<p class="section-kicker">Diễn biến</p>'
            '<h2 id="steps-title">Thời khóa biểu qua các bước</h2>'
            '</div>'
            f'<p class="section-note">{note}</p>'
            '</div>'
            f'<div class="step-list">{"".join(panels)}</div>'
            '</section>'
        )

    @staticmethod
    def getResult(solution, history=None):
        room_sections = HtmlOutput.getRoomSections(solution)
        return HtmlOutput.getDocument(solution, room_sections, history=history)

    @staticmethod
    def getDocument(solution, room_sections, history=None):
        configuration = solution.configuration
        total_hours = sum(cc.Duration for cc in configuration.courseClasses)

        stats = (
            (len(solution.classes), "lớp học"),
            (configuration.numberOfRooms, "phòng"),
            (configuration.numberOfProfessors, "giảng viên"),
            (configuration.numberOfStudentGroups, "nhóm sinh viên"),
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
            percent = max(0.0, min(1.0, float(fitness))) * 100
            perfect_class = " perfect" if percent >= 99.95 else ""
            score_html = (
                f'<div class="score{perfect_class}">'
                f'<span class="score-value">{percent:.1f}%</span>'
                '<span class="score-label">Độ phù hợp</span>'
                '</div>'
            )

        legend_items = "".join(
            f'<li class="legend-item"><span class="crit">{letter}</span>'
            f'<span>{html.escape(label)}</span></li>'
            for letter, label in zip(HtmlOutput.CRITERIAS, HtmlOutput.CRITERIA_LABELS)
        )

        generated_at = datetime.now().strftime("%H:%M · %d/%m/%Y")
        subtitle = (
            f"Kết quả xếp lịch cho {Constant.DAYS_NUM} ngày làm việc, "
            f"{Constant.DAY_HOURS} tiết mỗi ngày."
        )
        history_html = HtmlOutput.getHistorySection(history)
        steps_html = HtmlOutput.getStepsSection(history)

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
            f'{score_html}\n'
            '</div>\n'
            f'<ul class="stats">{stats_html}</ul>\n'
            '</div>\n'
            '</header>\n'
            '<section class="legend" aria-label="Chú thích tiêu chí">\n'
            '<div class="legend-head">\n'
            '<h2>Chú thích</h2>\n'
            '<p class="legend-note">'
            '<span class="legend-ok">Xanh</span> = đạt · '
            '<span class="legend-bad">Đỏ</span> = vi phạm. '
            'Di chuột hoặc chạm vào ký hiệu để xem chi tiết. '
            'Các lớp trùng phòng được xếp chồng trong cùng một ô.'
            '</p>\n'
            '</div>\n'
            f'<ul class="legend-items">{legend_items}</ul>\n'
            '</section>\n'
            '<section class="result-section" aria-labelledby="result-title">\n'
            '<div class="section-head">\n'
            '<div>\n'
            '<p class="section-kicker">Kết quả cuối</p>\n'
            '<h2 id="result-title">Thời khóa biểu cuối cùng</h2>\n'
            '</div>\n'
            '<p class="section-note">Lời giải tốt nhất sau khi thuật toán kết thúc.</p>\n'
            '</div>\n'
            '<div class="rooms">\n'
            f'{room_sections}\n'
            '</div>\n'
            '</section>\n'
            f'{history_html}\n'
            f'{steps_html}\n'
            '<footer class="footer">\n'
            '<span>Được tạo bởi <strong>GASchedule.py</strong></span>\n'
            f'<span>Cập nhật lúc {generated_at}</span>\n'
            '</footer>\n'
            '</main>\n'
            '</body>\n'
            '</html>\n'
        )
