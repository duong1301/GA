import html
import json
import math
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace

from model.AlgorithmParameters import FIELDS, format_value, normalize, summary
from model.Constant import Constant
from model.Reservation import Reservation


class HtmlOutput:
    ROOM_COLUMN_NUMBER = Constant.DAYS_NUM + 1
    ROOM_ROW_NUMBER = Constant.DAY_HOURS + 1
    COLOR1 = "#047857"
    COLOR2 = "#b91c1c"
    # Ký hiệu viết tắt của 3 tiêu chí kiểm tra ràng buộc:
    #   P = Phòng học   G = Giảng viên   N = Nghỉ trưa
    CRITERIAS = ('P', 'G', 'N')
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
    PERIODS = ("",) + tuple(
        "Nghỉ trưa" if period - 1 == Constant.LUNCH_PERIOD
        else f"Tiết {period}"
        for period in range(1, Constant.DAY_HOURS + 1)
    )
    PERIOD_TIMES = ("",) + tuple(
        f"{Constant.START_HOUR + offset}:00 – {Constant.START_HOUR + offset + 1}:00"
        for offset in range(Constant.DAY_HOURS)
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

        .rerun-button:hover {
            background: #eff6ff;
            transform: translateY(-1px);
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

        .result-tab:hover {
            color: var(--brand);
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
        .input-summary:hover { background: #f8fbff; }

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

        .rerun-button--header:hover {
            background: #1e40af;
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
        .settings-toggle:hover { background: #f1f5f9; }

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

        .input-table tbody tr:hover {
            background: #f8fbff;
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

        .step-grid-wrap::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

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

        .step-cell:hover {
            border-color: #bfdbfe;
            transform: translateY(-1px);
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
                setStatus("Đang chạy lại thuật toán…");
                try {
                    const response = await fetch("/rerun", {
                        method: "POST",
                        headers: {
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ parameters }),
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
                    setStatus("Không chạy lại được: " + message, true);
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

        // Chuyển tab giữa lịch theo phòng học và lịch theo giảng viên
        (() => {
            const tabs = Array.from(document.querySelectorAll(".result-tab"));
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
        })();
        // Thời khóa biểu của từng thế hệ: bấm một ô trong lưới để xem ở dưới.
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

            const columns = () => {
                const value = getComputedStyle(grid).gridTemplateColumns;
                const count = value ? value.split(" ").length : 0;
                return count > 0 ? count : 10;
            };

            // Huy hiệu P/G/N của một lớp học ở thế hệ đang xem.
            const criteriaBadges = (bits, offset) => {
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
                return html + "</div>";
            };

            const courseCard = (courseClass, bits, offset, continued) => {
                let html = '<div class="course">' + esc(courseClass.course) +
                    '</div><div class="prof">' + esc(courseClass.prof) + "</div>";
                if (continued) {
                    html += '<div class="tags">' +
                        '<span class="tag tag-continued">Tiếp tiết</span></div>';
                } else if (courseClass.dur > 1) {
                    html += '<div class="tags"><span class="tag tag-duration">' +
                        courseClass.dur + " tiết</span></div>";
                }
                return html + criteriaBadges(bits, offset);
            };

            // Sắp các lớp học vào ô (phòng, ngày, tiết) như phần dựng bảng.
            const collectSlots = step => {
                const slots = new Map();
                step.s.forEach((slot, index) => {
                    const courseClass = data.classes[index];
                    if (!slot || !courseClass) return;
                    const key = slot[0] + "|" + (slot[1] + 1);
                    const startPeriod = slot[2] + 1;
                    for (let offset = 0; offset < courseClass.dur; offset++) {
                        const periodId = startPeriod + offset;
                        if (periodId >= data.rows) break;
                        const bucket = slots.get(key) || {};
                        const list = bucket[periodId] || [];
                        list.push({
                            start: startPeriod,
                            course: courseClass,
                            bits: step.b,
                            offset: index * letters.length,
                        });
                        bucket[periodId] = list;
                        slots.set(key, bucket);
                    }
                });

                const overlaps = new Set();
                slots.forEach((bucket, key) => {
                    for (const period in bucket) {
                        if (bucket[period].length > 1) {
                            overlaps.add(key);
                            break;
                        }
                    }
                });
                return { slots, overlaps };
            };

            const roomTable = (roomId, slots, overlaps) => {
                const roomName = data.rooms[roomId];
                const covered = {};
                let rows = "";

                for (let periodId = 1; periodId < data.rows; periodId++) {
                    let cellsHtml = "";
                    for (let dayId = 1; dayId < data.cols; dayId++) {
                        const dayCovered =
                            covered[dayId] || (covered[dayId] = new Set());
                        if (dayCovered.has(periodId)) continue;

                        const bucket = slots.get(roomId + "|" + dayId) || {};
                        const entries = bucket[periodId] || [];
                        if (!entries.length) {
                            cellsHtml += '<td class="slot empty"></td>';
                            continue;
                        }

                        const hasOverlap = overlaps.has(roomId + "|" + dayId);
                        if (!hasOverlap && entries.length === 1) {
                            const entry = entries[0];
                            if (entry.start === periodId) {
                                const span = Math.min(
                                    entry.course.dur,
                                    data.rows - periodId
                                );
                                cellsHtml += '<td class="slot filled"' +
                                    (span > 1 ? ' rowspan="' + span + '"' : "") +
                                    '><div class="course-card">' +
                                    courseCard(
                                        entry.course, entry.bits, entry.offset, false
                                    ) +
                                    "</div></td>";
                                for (let step = 1; step < span; step++) {
                                    dayCovered.add(periodId + step);
                                }
                            } else {
                                cellsHtml += '<td class="slot filled">' +
                                    '<div class="course-card continued">' +
                                    courseCard(
                                        entry.course, entry.bits, entry.offset, true
                                    ) +
                                    "</div></td>";
                            }
                            continue;
                        }

                        let cards = "";
                        if (entries.length > 1) {
                            cards += '<div class="slot-warning">Trùng phòng</div>';
                        }
                        entries.forEach(entry => {
                            const first = entry.start === periodId;
                            cards += '<div class="course-card' +
                                (first ? "" : " continued") + '">' +
                                courseCard(
                                    entry.course, entry.bits, entry.offset, !first
                                ) +
                                "</div>";
                        });
                        cellsHtml += '<td class="slot filled conflict">' +
                            '<div class="slot-stack">' + cards + "</div></td>";
                    }

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
                        roomTable(roomId, collected.slots, collected.overlaps)
                    ).join("") +
                    "</div>";
                panel.hidden = false;
                if (focus) cells[index].focus();
            };

            cells.forEach((cell, index) => {
                cell.addEventListener("click", () => select(index, false));
            });

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
    def getCriteriaBadges(criterias, ci):
        """Tạo các huy hiệu tiêu chí (P/G/N) cho một lớp học."""
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
        """Tạo nội dung HTML cho một ô lịch (môn học, giảng viên, tiêu chí)."""
        sb = [
            '<div class="course">', html.escape(cc.Course.Name), '</div>',
            '<div class="prof">', html.escape(cc.Professor.Name), '</div>',
        ]

        if cc.Duration > 1:
            sb.append('<div class="tags">')
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
    def getScheduleTable(key, entries_by_slot, overlapping_slots,
                         overlap_label="Trùng phòng", caption=""):
        """Dựng bảng lịch theo ngày (gồm cả khung nghỉ trưa) cho khóa/phòng/GV."""
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

                day_entries = entries_by_slot.get((key, dayId), {})
                slot_entries = day_entries.get(periodId, [])
                if not slot_entries:
                    cells.append('<td class="slot empty"></td>')
                    continue

                has_overlap = (key, dayId) in overlapping_slots
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
                    cards.append(f'<div class="slot-warning">{overlap_label}</div>')
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
    def getRoomTable(room, roomId, entries_by_slot, overlapping_slots):
        """Bảng thời khóa biểu của một phòng học."""
        table = HtmlOutput.getScheduleTable(
            roomId,
            entries_by_slot,
            overlapping_slots,
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
        """Dựng lịch theo giảng viên/ngày/tiết; mỗi ô ghi môn học và phòng."""
        entries_by_slot = defaultdict(lambda: defaultdict(list))

        for cc, reservation_index in solution.classes.items():
            reservation = Reservation.parse(reservation_index)

            dayId = reservation.Day + 1
            startPeriod = reservation.Time + 1
            profId = cc.Professor.Id
            duration = cc.Duration

            room = solution.configuration.getRoomById(reservation.Room)
            room_name = room.Name if room is not None else f"Phòng {reservation.Room}"

            entry = {
                "start": startPeriod,
                "duration": duration,
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
                periodId = startPeriod + offset
                if periodId >= HtmlOutput.ROOM_ROW_NUMBER:
                    break
                entries_by_slot[(profId, dayId)][periodId].append(entry)

        overlapping_slots = {
            key
            for key, periods in entries_by_slot.items()
            if any(len(entries) > 1 for entries in periods.values())
        }
        return entries_by_slot, overlapping_slots

    @staticmethod
    def getProfessorTable(professor, profId, entries_by_slot, overlapping_slots,
                          total_hours, number_of_courses):
        """Bảng thời khóa biểu của một giảng viên."""
        table = HtmlOutput.getScheduleTable(
            profId,
            entries_by_slot,
            overlapping_slots,
            overlap_label="Trùng lịch giảng viên",
            caption=f"Lịch giảng dạy của {professor.Name}",
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
        """Tạo các bảng lịch giảng dạy của từng giảng viên."""
        configuration = solution.configuration
        entries_by_slot, overlapping_slots = HtmlOutput.generateProfessorTimeTable(
            solution
        )
        if not entries_by_slot:
            return (
                '<div class="empty-state">'
                'Chưa có lớp học nào được xếp lịch.'
                '</div>'
            )

        # tổng số tiết và số môn của từng giảng viên trong tuần
        hours = defaultdict(int)
        courses = defaultdict(set)
        for cc in solution.classes:
            hours[cc.Professor.Id] += cc.Duration
            courses[cc.Professor.Id].add(cc.Course.Name)

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
                    overlapping_slots,
                    hours[profId],
                    len(courses[profId]),
                )
            )
        return "".join(sections)

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
    def getStepsData(history):
        """Dữ liệu gọn của từng thế hệ nhúng vào trang.

        Trình duyệt dùng mảng này để tự dựng thời khóa biểu của thế hệ được
        bấm, nhờ đó file HTML chỉ nặng vài trăm KB thay vì hàng chục MB.
        """
        if not history:
            return ""

        # Thứ tự lớp học lấy theo bản ghi đầu tiên; các bản ghi sau được
        # dời về đúng vị trí này (tiêu chí lại được lưu theo thứ tự của nó).
        order = list((history[0].get("classes") or {}).keys())
        position = {course_class: index
                    for index, course_class in enumerate(order)}
        classes = [
            {
                "course": course_class.Course.Name,
                "prof": course_class.Professor.Name,
                "dur": int(course_class.Duration),
            }
            for course_class in order
        ]

        configuration = history[0].get("configuration")
        rooms = []
        if configuration is not None:
            for room_id in range(configuration.numberOfRooms):
                room = configuration.getRoomById(room_id)
                rooms.append(room.Name if room is not None else "Phòng {}".format(room_id))

        step_size = len(HtmlOutput.CRITERIAS)
        steps = []
        for entry in history:
            counts, total = HtmlOutput._criteriaCounts(entry)
            entry_classes = entry.get("classes") or {}
            criteria = entry.get("criteria")

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

            slots = [None] * len(order)
            for course_class, reservation_index in entry_classes.items():
                target = position.get(course_class)
                if target is None:
                    continue
                reservation = Reservation.parse(reservation_index)
                slots[target] = [int(reservation.Room),
                                 int(reservation.Day),
                                 int(reservation.Time)]

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
            })

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
            "classes": classes,
            "steps": steps,
        }
        document = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        return ('<script type="application/json" id="step-data">'
                + document.replace("</", "<\\/")
                + "</script>\n")

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
    def getStepViolations(entry):
        """Trả về (số vi phạm từng tiêu chí, tổng số vi phạm, tổng số lớp)."""
        counts, total = HtmlOutput._criteriaCounts(entry)
        violations = [total - count for count in counts]
        return violations, sum(violations), total

    @staticmethod
    def getStepHeadHtml(entry, index):
        """Phần đầu của khung hiển thị: thông số của thế hệ được chọn."""
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
        """Lưới các thế hệ: mỗi ô chứa fitness và số vi phạm, bấm để xem lịch."""
        if not history:
            return ""

        best_index = max(
            range(len(history)),
            key=lambda index: float(history[index].get("fitness", 0.0)),
        )

        cells = []
        for index, entry in enumerate(history):
            violations, violation_total, total = HtmlOutput.getStepViolations(entry)
            fitness = float(entry.get("fitness", 0.0))
            percent = max(0.0, min(1.0, fitness)) * 100
            generation = entry.get("generation", index + 1)
            elapsed = float(entry.get("elapsed", 0.0) or 0.0)
            population = int(entry.get("populationSize", 0) or 0)
            stagnation = int(entry.get("bestNotEnhance", 0) or 0)

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
    def getInputSection(solution):
        """Hiển thị danh sách giảng viên, môn học và phòng học."""
        configuration = solution.configuration
        classes = list(configuration.courseClasses)

        professors = sorted(configuration._professors.values(), key=lambda item: item.Id)
        professor_rows = []
        for professor in professors:
            courses = sorted(
                {cc.Course.Name for cc in professor.CourseClasses},
                key=str.casefold,
            )
            professor_rows.append([
                professor.Id,
                professor.Name,
                ", ".join(courses) if courses else "—",
            ])

        courses = sorted(configuration._courses.values(), key=lambda item: item.Id)
        course_rows = []
        total_classes = 0
        total_periods = 0
        for course in courses:
            course_classes = [cc for cc in classes if cc.Course.Id == course.Id]
            total_classes += len(course_classes)
            total_periods += sum(cc.Duration for cc in course_classes)
            course_rows.append([
                course.Id,
                course.Name,
                len(course_classes),
                sum(cc.Duration for cc in course_classes),
            ])
        course_footer = ["", "Tổng cộng", total_classes, total_periods]

        capacity = Constant.TEACHING_HOURS * Constant.DAYS_NUM
        rooms = sorted(configuration._rooms.values(), key=lambda item: item.Id)
        room_rows = [
            [room.Id, room.Name, f"{capacity} giờ"]
            for room in rooms
        ]

        cards = [
            HtmlOutput.getInputCard(
                "Giảng viên",
                len(professor_rows),
                HtmlOutput.getInputTable(
                    ["Mã", "Họ tên", "Môn học phụ trách"],
                    professor_rows,
                    ["r", "l", "l"],
                ),
            ),
            HtmlOutput.getInputCard(
                "Môn học",
                len(course_rows),
                HtmlOutput.getInputTable(
                    ["Mã", "Môn học", "Số lớp", "Số tiết/tuần"],
                    course_rows,
                    ["r", "l", "r", "r"],
                    footer=course_footer,
                ),
            ),
            HtmlOutput.getInputCard(
                "Phòng học",
                len(room_rows),
                HtmlOutput.getInputTable(
                    ["Mã", "Phòng học", "Sức chứa/tuần"],
                    room_rows,
                    ["r", "l", "r"],
                ),
            ),
        ]

        summary_counts = (
            f"{len(professor_rows)} giảng viên · {len(course_rows)} môn học · "
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
            f'<div class="input-grid">{"".join(cards)}</div>'
            '</div>'
            '</details>'
        )

    @staticmethod
    def getSettingsSection(parameters=None):
        """Khối điều khiển thông số; nút chạy lại nằm ngoài phần thu gọn."""
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
            '<p class="settings-summary-note">{} · thay đổi áp dụng cho lần chạy lại</p>'
            '</div>'
            '<div class="settings-header-actions">'
            '<button class="rerun-button rerun-button--header" id="rerun-button" '
            'type="button" data-rerun '
            'title="Chạy lại thuật toán với thông số hiện tại">'
            '↻ Chạy lại</button>'
            '<p class="settings-status" id="settings-status" '
            'data-rerun-status role="status" aria-live="polite"></p>'
            '</div>'
            '</div>'
            '<details class="settings-details" open>'
            '<summary class="settings-toggle">Thông số chi tiết</summary>'
            '<div class="settings-body">'
            '<p class="settings-note">Điều chỉnh thông số cho lần chạy kế tiếp, '
            'sau đó bấm <strong>↻ Chạy lại</strong> ở phần đầu khối này.</p>'
            '<form id="ga-parameters" class="settings-form" autocomplete="off">'
            '<div class="settings-grid">{}</div>'
            '</form>'
            '</div>'
            '</details>'
            '</section>'
        ).format(summary(values), "".join(fields))

    @staticmethod
    def getResult(solution, history=None, parameters=None):
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
        configuration = solution.configuration
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
            f"mỗi ngày 2 buổi × {Constant.TEACHING_HOURS // 2} tiết "
            f"(sáng {Constant.START_HOUR}:00–{Constant.START_HOUR + Constant.LUNCH_PERIOD}:00, "
            f"chiều {Constant.START_HOUR + Constant.LUNCH_PERIOD + 1}:00–"
            f"{Constant.START_HOUR + Constant.DAY_HOURS}:00). "
            f"Khung {Constant.START_HOUR + Constant.LUNCH_PERIOD}:00–"
            f"{Constant.START_HOUR + Constant.LUNCH_PERIOD + 1}:00 là giờ nghỉ trưa."
        )
        settings_html = HtmlOutput.getSettingsSection(parameters)
        input_html = HtmlOutput.getInputSection(solution)
        history_html = HtmlOutput.getHistorySection(history)
        steps_html = HtmlOutput.getStepsSection(history)
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
            '<span class="legend-bad">Đỏ</span> = vi phạm. '
            'Di chuột hoặc chạm vào ký hiệu để xem chi tiết. '
            'Các lớp trùng phòng được xếp chồng trong cùng một ô.'
            '</p>\n'
            '</div>\n'
            f'<ul class="legend-items">{legend_items}</ul>\n'
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
