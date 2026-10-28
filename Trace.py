"""Theo dõi từng bước khi thuật toán đang chạy.

In ra console:
  0. Toàn bộ thông tin đầu vào đọc từ tệp cấu hình (gọi thủ công trước khi chạy).
  1. Một dòng tóm tắt cho MỖI thế hệ.
  2. Bảng thời khóa biểu của cá thể tốt nhất, lặp lại mỗi SCHEDULE_EVERY_GENERATION thế hệ.
  3. Chi tiết từng lớp học của cá thể tốt nhất, lặp lại mỗi DETAIL_EVERY_GENERATION thế hệ.
  4. Lưu lịch sử từng thế hệ (fitness, tiêu chí, lịch) để HtmlOutput vẽ bảng
     đánh giá và thời khóa biểu của các bước. Dùng Trace.get_history() để lấy.

Tinh chỉnh:
  - SCHEDULE_EVERY_GENERATION = 1  -> in bảng thời khóa biểu mỗi thế hệ
  - SCHEDULE_EVERY_GENERATION = None -> không in bảng thời khóa biểu
  - MAX_HISTORY = 5000 -> số thế hệ tối đa lưu lại cho biểu đồ fitness/lịch sử HTML
"""
import time

from model.Reservation import Reservation
from model.Constant import Constant

# In bảng thời khóa biểu mỗi N thế hệ (None = không in)
SCHEDULE_EVERY_GENERATION = 10
# In chi tiết từng lớp học của cá thể tốt nhất, mỗi N thế hệ (None = không in)
DETAIL_EVERY_GENERATION = 50
# Độ rộng tối đa của một cột trong bảng (ký tự)
MAX_COLUMN_WIDTH = 30
# Số bản ghi tối đa giữ lại để xuất lịch sử ra HTML
MAX_HISTORY = 5000


class Table:
    """Bộ kẻ bảng dùng ký tự vẽ khung Unicode, tự co giãn cột theo nội dung."""

    TL, TR, BL, BR = "┌", "┐", "└", "┘"
    H, V = "─", "│"
    LT, RT, TT, BT = "├", "┤", "┬", "┴"
    X = "┼"
    BAR, DASH, CHECK, CROSS = "┃", "─", "✓", "✗"

    def __init__(self, headers, aligns=None, maxWidth=MAX_COLUMN_WIDTH):
        self.headers = list(headers)
        # aligns: 'l' trái, 'r' phải, 'c' giữa
        self.aligns = list(aligns) if aligns else ["l"] * len(self.headers)
        self.maxWidth = maxWidth
        self.rows = []
        self.indent = " "

    def add(self, row):
        # Ô có thể chứa nhiều dòng, phân tách bằng "\n"
        self.rows.append(["" if v is None else str(v) for v in row])
        return self

    # ---- đo ----
    def _lines_of(self, cell):
        return cell.split("\n") if cell else [""]

    def _widths(self):
        widths = [len(h) for h in self.headers]
        for row in self.rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    for piece in self._lines_of(cell):
                        widths[i] = max(widths[i], len(piece))
        return [min(w, self.maxWidth) for w in widths]

    def _clip(self, text, width):
        return text if len(text) <= width else text[:width - 1] + "…"

    def _cell(self, text, width, align):
        text = self._clip(text, width).ljust(width)
        if align == "r":
            return text.rjust(width)
        if align == "c":
            return text.center(width)
        return text

    def _rule(self, left, mid, right):
        return left + mid.join(self.H * (w + 2) for w in self._widths()) + right

    # ---- kẻ ----
    def _render_row(self, cells, widths, aligns):
        parts = [" " + self._cell(cells[i] if i < len(cells) else "",
                                  widths[i], aligns[i]) + " "
                 for i in range(len(widths))]
        return self.V + self.V.join(parts) + self.V

    def _render_multiline(self, cells, widths, aligns):
        """Ô chứa nhiều dòng: kẻ thành nhiều dòng vật lý, mỗi dòng một hàng."""
        columns = [self._lines_of(cells[i] if i < len(cells) else "")
                   for i in range(len(widths))]
        height = max((len(c) for c in columns), default=1)
        lines = []
        for h in range(height):
            parts = []
            for i in range(len(widths)):
                lines_of_cell = columns[i]
                text = lines_of_cell[h] if h < len(lines_of_cell) else ""
                parts.append(" " + self._cell(text, widths[i], aligns[i]) + " ")
            lines.append(self.V + self.V.join(parts) + self.V)
        return lines

    def render(self, title=None):
        widths, aligns = self._widths(), self.aligns
        inner = sum(w + 3 for w in widths)          # bề rộng bên trong khung
        lines = []
        if title:
            lines.append(self.indent + self.BAR + " " + title +
                         " " * max(1, inner - len(title) - 1) + self.BAR)
        lines.append(self.indent + self._rule(self.TL, self.TT, self.TR))
        lines.append(self.indent + self._render_row(self.headers, widths, aligns))
        lines.append(self.indent + self._rule(self.LT, self.X, self.RT))
        for row in self.rows:
            lines.extend(self.indent + ln
                         for ln in self._render_multiline(row, widths, aligns))
        lines.append(self.indent + self._rule(self.BL, self.BT, self.BR))
        return "\n".join(lines)

    def show(self, title=None):
        print(self.render(title))
        return self


def _kv_table(pairs, keyWidth=34):
    """Bảng hai cột Nhãn : Giá trị cho phần thống kê."""
    t = Table(["", ""], ["l", "l"])
    t.indent = "  "
    for k, v in pairs:
        t.add([k, v])
    return t


class Trace:
    WEEK_DAYS = ("T2", "T3", "T4", "T5", "T6")
    PERIODS = tuple(
        f"Tiết {period:<2} {Constant.START_HOUR + period - 1}-"
        f"{Constant.START_HOUR + period}"
        for period in range(1, Constant.DAY_HOURS + 1)
    )
    CRITERIA_NAMES = ("P", "G")
    CRITERIA_MEAN = ("Phòng", "GV")
    _start_time = time.time()
    # Lịch sử từng thế hệ để xuất biểu đồ fitness và thời khóa biểu của các bước ra HTML.
    _history = []

    @staticmethod
    def reset():
        """Đặt lại mốc thời gian và xóa lịch sử, gọi một lần trước khi chạy."""
        Trace._start_time = time.time()
        Trace._history = []

    @staticmethod
    def elapsed() -> float:
        """Số giây đã trôi qua kể từ lần gọi reset() gần nhất."""
        return time.time() - Trace._start_time

    @staticmethod
    def get_history():
        """Trả về danh sách ảnh chụp kết quả của từng thế hệ đã chạy."""
        return list(Trace._history)

    @staticmethod
    def _record(solution, generation: int, populationSize: int, bestNotEnhance: int):
        """Lưu lại kết quả của một thế hệ mà không làm chậm đáng kể thuật toán."""
        if len(Trace._history) >= MAX_HISTORY:
            return

        criteria = solution.criteria
        step = len(Trace.CRITERIA_NAMES)
        total = len(criteria) // step
        counts = tuple(
            sum(1 for j in range(total) if criteria[j * step + i])
            for i in range(step)
        )
        Trace._history.append({
            "generation": int(generation),
            "fitness": float(solution.fitness),
            "criteria": criteria.copy(),
            "classes": dict(solution.classes),
            "configuration": solution.configuration,
            "counts": counts,
            "total": total,
            "populationSize": int(populationSize or 0),
            "bestNotEnhance": int(bestNotEnhance or 0),
            "elapsed": Trace.elapsed(),
        })

    # ==================== THÔNG TIN ĐẦU VÀO ====================

    @staticmethod
    def input(configuration, fileName: str = None):
        """In toàn bộ thông tin đầu vào đọc từ tệp cấu hình."""
        print()
        print("═" * 96)
        print("  THÔNG TIN ĐẦU VÀO".ljust(96))
        print("═" * 96)
        if fileName:
            print("  Tệp cấu hình : {}".format(fileName))
        print("  Quy mô       : {} giảng viên · {} môn học · {} phòng học · "
              "{} lớp học"
              .format(configuration.numberOfProfessors, configuration.numberOfCourses,
                      configuration.numberOfRooms,
                      configuration.numberOfCourseClasses))
        print()

        Trace._professors(configuration)
        Trace._courses(configuration)
        Trace._rooms(configuration)
        Trace._classes(configuration)
        Trace._statistics(configuration)
        print()

    @staticmethod
    def _professors(configuration):
        t = Table(["Mã", "Họ tên giảng viên", "Môn học phụ trách"],
                  ["r", "l", "l"])
        for prof in configuration._professors.values():
            courses = sorted({cc.Course.Name for cc in prof.CourseClasses})
            t.add([prof.Id, prof.Name, ", ".join(courses) if courses else "(chưa có lớp)"])
        t.show("GIẢNG VIÊN")

    @staticmethod
    def _courses(configuration):
        t = Table(["Mã", "Tên môn học", "Số lớp", "Số giờ / tuần"],
                  ["r", "l", "r", "r"])
        for course in configuration._courses.values():
            classes = [cc for cc in configuration.courseClasses if cc.Course == course]
            t.add([course.Id, course.Name, len(classes),
                   sum(cc.Duration for cc in classes)])
        t.show("MÔN HỌC")

    @staticmethod
    def _rooms(configuration):
        t = Table(["Mã", "Tên phòng", "Sức chứa / tuần"],
                  ["r", "l", "r"])
        capacity = Constant.DAY_HOURS * Constant.DAYS_NUM
        for room in configuration._rooms.values():
            t.add([room.Id, room.Name,
                   "{} giờ".format(capacity)])
        t.show("PHÒNG HỌC")

    @staticmethod
    def _classes(configuration):
        t = Table(["Mã", "Môn học", "Giảng viên", "Thời lượng"],
                  ["r", "l", "l", "c"])
        for index, cc in enumerate(configuration.courseClasses):
            t.add([index, cc.Course.Name, cc.Professor.Name,
                   "{} tiết".format(cc.Duration)])
        t.show("LỚP HỌC")

    @staticmethod
    def _statistics(configuration):
        classes = configuration.courseClasses
        totalHours = sum(cc.Duration for cc in classes)
        capacity = Constant.DAY_HOURS * Constant.DAYS_NUM * configuration.numberOfRooms

        pairs = [
            ("Tổng số giờ học trong tuần",
             "{} giờ  ({} lớp · trung bình {:.1f} giờ/lớp)"
             .format(totalHours, len(classes), totalHours / len(classes))),
            ("Sức chứa của hệ thống phòng",
             "{} tiết/ngày × {} ngày × {} phòng = {} giờ"
             .format(Constant.DAY_HOURS, Constant.DAYS_NUM,
                     configuration.numberOfRooms, capacity)),
            ("Tỉ lệ sử dụng phòng", "{:.1f} %".format(totalHours / capacity * 100)),
        ]

        t = Table(["Chỉ số", "Giá trị"], ["l", "l"], maxWidth=64)
        t.indent = "  "
        for k, v in pairs:
            t.add([k, v])
        t.show("THỐNG KÊ")

    # ==================== TIẾN TRÌNH THUẬT TOÁN ====================

    @staticmethod
    def trace(algorithm, generation: int, bestNotEnhance: int = None):
        """Điểm vào duy nhất mà mỗi thuật toán gọi ở cuối mỗi thế hệ.

        bestNotEnhance là số thế hệ liên tiếp không cải thiện được độ phù hợp tốt nhất;
        các thuật toán đặt biến này ở phạm vi cục bộ nên thuật toán truyền vào.
        """
        try:
            best = algorithm.result
            population_size = getattr(algorithm, "_populationSize", 0)
            stagnation = 0 if bestNotEnhance is None else bestNotEnhance
            try:
                Trace._record(best, generation, population_size, stagnation)
            except Exception:
                # Việc lưu lịch sử không được làm gián đoạn phần in console.
                pass

            Trace.generation(generation, best, population_size, stagnation)

            if SCHEDULE_EVERY_GENERATION and generation % SCHEDULE_EVERY_GENERATION == 0:
                Trace.schedule(best, generation)
            if DETAIL_EVERY_GENERATION and generation % DETAIL_EVERY_GENERATION == 0:
                Trace.detail(best, generation)
        except Exception as error:
            # Theo dõi không bao giờ được làm hỏng cuộc chạy của thuật toán
            print("  [Trace] Bỏ qua do lỗi: {}: {}".format(type(error).__name__, error))

    @staticmethod
    def generation(generation: int, best, populationSize: int, bestNotEnhance: int = 0):
        """In một dòng tóm tắt cho thế hệ hiện tại, kèm bảng 4 tiêu chí."""
        criteria = best.criteria
        step = len(Trace.CRITERIA_NAMES)
        total = len(criteria) // step

        print("\n" + "─" * 96)
        print("  THẾ HỆ {:<6} │ Độ phù hợp: {:.6f} │ Cá thể: {:<4} │ "
              "Không cải thiện: {:<4} │ {:6.2f}s"
              .format(generation, best.fitness, populationSize,
                      bestNotEnhance, Trace.elapsed()))

        meanings = ("Phòng học không bị trùng",
                    "Giảng viên không trùng lịch")
        t = Table(["Mã", "Ràng buộc", "Đạt / tổng", "Kết quả"],
                  ["c", "l", "r", "c"])
        t.indent = "    "
        for i in range(step):
            ok = sum(1 for j in range(total) if criteria[j * step + i])
            t.add([Trace.CRITERIA_NAMES[i], meanings[i], "{}/{}".format(ok, total),
                   Table.CHECK if ok == total else Table.CROSS])
        t.show()

    @staticmethod
    def detail(solution, generation: int):
        """In chi tiết từng lớp học của cá thể tốt nhất kèm 4 cờ tiêu chí."""
        configuration = solution.configuration
        codes = Trace.CRITERIA_NAMES

        t = Table(["Mã", "Môn học", "Giảng viên", "Ngày",
                   "Tiết", "Phòng"] + list(codes),
                  ["r", "l", "l", "c", "c", "l"] + ["c"] * len(codes),
                  maxWidth=22)

        criteria = solution.criteria
        for index, (cc, reservation_index) in enumerate(solution.classes.items()):
            res = Reservation.parse(reservation_index)
            room = configuration.getRoomById(res.Room)
            row = [index, cc.Course.Name, cc.Professor.Name,
                   Trace.WEEK_DAYS[res.Day],
                   "{} ({}h)".format(res.Time + 1, cc.Duration),
                   room.Name if room else res.Room]
            for i in range(len(codes)):
                ok = criteria[index * len(codes) + i]
                row.append(Table.CHECK if ok else Table.CROSS)
            t.add(row)

        t.show("CHI TIẾT TỪNG LỚP HỌC — thế hệ {}".format(generation))

    @staticmethod
    def schedule(solution, generation: int):
        """In bảng thời khóa biểu đầy đủ, mỗi phòng một bảng."""
        configuration = solution.configuration
        print("\n" + "═" * 96)
        print("  THỜI KHÓA BIỂU TỐI ƯU  —  thế hệ {}  │  độ phù hợp {:.6f}"
              .format(generation, solution.fitness))
        print("═" * 96)

        # cover[(phòng, ngày, tiết)] = (nhãn, có_phải_tiết_đầu, thời_lượng)
        cover = {}
        for cc, reservation_index in solution.classes.items():
            res = Reservation.parse(reservation_index)
            label = "{} · {}".format(cc.Course.Name, cc.Professor.Name)
            for offset in range(cc.Duration):
                cover[(res.Room, res.Day, res.Time + offset)] = (
                    label, offset == 0, cc.Duration)

        for room_id in range(configuration.numberOfRooms):
            room = configuration.getRoomById(room_id)

            headers = ["Tiết"] + list(Trace.WEEK_DAYS)
            rows = []
            cellWidth = 18
            for period in range(Constant.DAY_HOURS):
                row = [Trace.PERIODS[period]]
                for day in range(Constant.DAYS_NUM):
                    entry = cover.get((room_id, day, period))
                    if entry is None:
                        row.append("")
                        continue
                    label, isFirst, dur = entry
                    if not isFirst:
                        row.append("↳")          # tiết tiếp của cùng lớp
                        continue
                    # Dòng trên: tên môn. Dòng dưới: giảng viên kèm thời lượng.
                    course, professor = label.split(" · ")
                    suffix = " ({}h)".format(dur) if dur > 1 else ""
                    row.append("{}\n{}".format(course, professor + suffix))
                rows.append(row)

            t = Table(headers, ["l"] * len(headers), maxWidth=cellWidth)
            for row in rows:
                t.add(row)
            t.show("PHÒNG {}".format(room.Name))
            print()