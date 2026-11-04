# Các bước của giải thuật di truyền và cách biểu diễn dữ liệu thành cấu trúc dữ liệu

Đây là **bản thứ hai** của tài liệu về giải thuật. Nếu bản thứ nhất
(`BAO_CAO_GA_THOI_KHOA_BIEU.md`) nặng về **số đo thực nghiệm trên bộ dữ liệu 48 lớp**, thì bản này nặng về
**cấu trúc**: dữ liệu đi từ tệp vào như thế nào, được biến đổi qua mấy tầng, mỗi tầng giữ gì và bỏ gì,
rồi từng bước của GA thao tác lên đúng những cấu trúc đó ra sao.

Để người đọc **tự lần tay được trên giấy**, xuyên suốt tài liệu dùng một **bộ dữ liệu mini 6 lớp**
(§1.1) thay vì 48 lớp; bộ 48 lớp chỉ được dùng để đối chiếu kích thước. Toàn bộ kết quả in ra trong tài
liệu là **kết quả chạy thật của mã trong repo** — code tái lập ở Phụ lục A.

---

## Mục lục

1. [Bốn tầng biểu diễn: toàn cảnh pipeline](#1-bốn-tầng-biểu-diễn-toàn-cảnh-pipeline)
2. [Tầng 1 — Từ tệp JSON sang đối tượng miền](#2-tầng-1--từ-tệp-json-sang-đối-tượng-miền)
3. [Tầng 2 — Từ đối tượng miền sang không gian chỉ số](#3-tầng-2--từ-đối-tượng-miền-sang-không-gian-chỉ-số)
4. [Tầng 3 — Nhiễm sắc thể: bốn khối gen và một khối cờ](#4-tầng-3--nhiễm-sắc-thể-bốn-khối-gen-và-một-khối-cờ)
5. [Tầng 4 — Từ quần thể sang báo cáo](#5-tầng-4--từ-quần-thể-sang-báo-cáo)
6. [Chín bước của GA thao tác trên các cấu trúc đó](#6-chín-bước-của-ga-thao-tác-trên-các-cấu-trúc-đó)
7. [Điều mô hình biểu diễn được và không biểu diễn được](#7-điều-mô-hình-biểu-diễn-được-và-không-biểu-diễn-được)
8. [Bảng ánh xạ nghiệp vụ → cấu trúc → mã](#8-bảng-ánh-xạ-nghiệp-vụ--cấu-trúc--mã)
9. [Phụ lục A — Bộ mini và code tái lập](#phụ-lục-a--bộ-mini-và-code-tái-lập)

---

## 1. Bốn tầng biểu diễn: toàn cảnh pipeline

```
TỆP JSON                     ĐỐI TƯỢNG MIỀN                KHÔNG GIAN CHỈ SỐ            NHIỄM SẮC THỂ            BÁO CÁO
GaSchedule.json      ──1──▶  Configuration        ──2──▶   Reservation + _slots  ──3──▶ Schedule            ──4──▶ Trace._history
[{"prof": {...}},            ._professors: dict             index = (ngày·NR              ._classes  (gen vị trí)     → console
 {"course":...},             ._courses: dict                   + phòng)·13 + offset        ._professors (gen GV)       → HtmlOutput
 {"room":...},               ._rooms: dict            5 × 13 × sốPhòng ô                  ._criteria  (18/144 cờ)
 {"class":...}]              ._courseClasses: list            phẳng, mỗi ô là             ._fitness                   → tệp .htm
                             ._professorsByCourse             MỘT DANH SÁCH lớp
```

| Tầng | Cấu trúc chủ đạo | Vai trò trong giải thuật | Ai tạo ra |
|---|---|---|---|
| 0 | văn bản JSON | nguồn dữ liệu, người dùng soạn | bên ngoài |
| 1 | `Professor` / `Course` / `Room` / `CourseClass` | **từ điển** của bài toán: ai dạy được môn nào, phòng nào, lớp mấy tiết | `Configuration.parseFile` |
| 2 | mảng `_slots` 130 hoặc 260 ô | **sân chơi**: mọi truy vấn "ô này còn trống không" trả lời O(1) | `Schedule.__init__` |
| 3 | `_classes` + `_professors` + `_criteria` + `_fitness` | **đối tượng tiến hoá**: đây mới là nhiễm sắc thể | các bước ở §6 |
| 4 | `Trace._history` (list dict) | **vết tiến hoá** để vẽ biểu đồ và bảng bước | `Trace._record` |

Điểm cần nắm ngay: **tầng 1 là dữ liệu tĩnh, tầng 3 mới là gen**. Lớp học phần ở tầng 1 *không chứa*
ngày/giờ/phòng/giảng viên — bốn thứ đó là thứ GA *sinh ra* và *tiến hoá*, không phải thứ đọc từ tệp.

---

## 2. Tầng 1 — Từ tệp JSON sang đối tượng miền

### 2.1 Tệp đầu vào có dạng một danh sách các object một key

`GaSchedule.json` **không** phải là một object có bốn mục `professors / courses / rooms / classes`; nó là
**một list 67 phần tử**, mỗi phần tử bọc đúng một bản ghi:

```json
[
  { "prof":   { "id": 1, "name": "Nguyễn Văn An",
                "subjects": [1, 2, 4, 6, 9],
                "busy": [ {"day": 0, "start": 0, "end": 1}, ... ] }},
  { "course": { "id": 1, "name": "Lập trình hướng đối tượng" }},
  { "room":   { "name": "Phòng 201" }},
  { "class":  { "course": 1, "duration": 3 }}
]
```

Vòng lặp trong `Configuration.parseFile` (`model/Configuration.py:211`) chỉ làm một việc: nhìn key
(`prof` / `course` / `room` / `class`) rồi gọi hàm parse tương ứng và nhét kết quả vào đúng bình chứa.

**Bộ mini dùng suốt tài liệu này** (12 dòng, lưu tạm thành `mini5.json`):

```json
[
  { "prof":   { "id": 1, "name": "Cô A", "subjects": [1, 2],
                "busy": [{"day": 0, "start": 1, "end": 2}] }},
  { "prof":   { "id": 2, "name": "Thầy B", "subjects": [1] }},
  { "course": { "id": 1, "name": "Toán" }},
  { "course": { "id": 2, "name": "Lý" }},
  { "room":   { "name": "P1" }},
  { "room":   { "name": "P2" }},
  { "class":  { "course": 1, "duration": 2 }},
  { "class":  { "course": 2, "duration": 2 }},
  { "class":  { "course": 1, "duration": 2 }},
  { "class":  { "course": 2, "duration": 2 }},
  { "class":  { "course": 1, "duration": 2 }},
  { "class":  { "course": 1, "duration": 2 }}
]
```

Kết quả parse: **2 phòng · 2 môn · 2 giảng viên · 6 lớp**, mỗi lớp 2 tiết.

### 2.2 Bảng ánh xạ key → thuộc tính → nơi tiêu thụ

| Trong tệp | Thành | Thuộc tính Python | Kiểu | Ai đọc nó trong giải thuật |
|---|---|---|---|---|
| `prof.id` | `Professor` | `Id` | int | khoá trong `_professors`, dùng cho `getProfessorById` |
| `prof.name` | `Professor` | `Name` | str | chỉ để hiển thị (console, HTML) |
| `prof.subjects` | `Professor` | `Subjects` | **set** int | **không gian gen giảng viên** (§2.4) |
| `prof.busy` | `Professor` | `BusySlots` | **set** `(ngày, offset)` | **đầu vào duy nhất của ràng buộc mềm B** |
| `course.id` | `Course` | `Id` | int | khoá nối `class.course` ↔ giảng viên |
| `course.name` | `Course` | `Name` | str | hiển thị |
| `room.name` | `Room` | `Id`, `Name` | int, str | `Id` là **gen phòng**; `Name` hiển thị |
| `class.course` | `CourseClass` | `Course` (con trỏ) | `Course` | tra giảng viên dạy được môn này |
| `class.duration` | `CourseClass` | `Duration` | int | **số ô liền nhau** mà lớp chiếm |

`CourseClass` **chỉ có hai nội dung**: môn học và số tiết. Không có giảng viên cài sẵn, không có ngày/giờ.
Đó là lý do nó đủ nhỏ để GA tự do xếp.

### 2.3 ID: hai quy tắc khác nhau, và thứ tự đọc có ý nghĩa

| Đối tượng | ID lấy từ đâu | Hệ quả |
|---|---|---|
| `Professor`, `Course` | **lấy từ tệp** (`id`) | người soạn kiểm soát; `id = 0` hoặc thiếu tên ⇒ bản ghi bị loại |
| `Room` | **tự tăng** theo thứ tự xuất hiện (`Room._next_room_id`) | phòng đầu trong tệp = ID 0, phòng thứ hai = ID 1 |
| `CourseClass` | **tự tăng** theo thứ tự xuất hiện (`CourseClass._next_class_id`) | **ID lớp == chỉ số lớp trong danh sách == thứ tự gen** |

`parseFile` gọi `Room.restartIDs()` và `CourseClass.restartIDs()` trước khi đọc, nên mỗi lần nạp lại một
bộ dữ liệu mới trong cùng tiến trình, ID được đánh lại từ 0 — nếu không, phòng của bộ thứ hai sẽ nhận
ID 4, 5, 6 và mọi chỉ số ô tính theo `numberOfRooms` sẽ lệch.

**Thứ tự trong tệp là một yêu cầu, không phải sở thích**: `class` được xử lý ngay khi gặp và tra môn bằng
`getCourseById(cid)` (`Configuration.py:179`), nên **mọi object `course` phải đứng trước object `class`
mà nó tham chiếu**. Với `prof` thì không ràng buộc, vì lớp không còn giữ giảng viên cài sẵn.

### 2.4 Hai cấu trúc tra cứu được *dựng thêm*, không có trong tệp

**(a) `_professorsByCourse`: môn → danh sách giảng viên dạy được**

```python
for professor in self._professors.values():
    for courseId in professor.Subjects:
        self._professorsByCourse.setdefault(courseId, []).append(professor)
```

Với bộ mini: `{1: [Cô A, Thầy B], 2: [Cô A]}` — Nghĩa là **môn Lý chỉ một người dạy được**.
Đây là *toàn bộ* không gian mà gen giảng viên được phép rút: `Schedule._randomProfessorFor` gọi
`getProfessorsByCourse(lop.Course.Id)` rồi `randrange` trong danh sách đó. Nếu một môn không có ai dạy,
danh sách rỗng ⇒ lớp nhận `None` ⇒ **không sinh vi phạm G và không sinh phạt B** (cả hai hàm đều bỏ qua
`prof is None`) — tức là im lặng chấp nhận, không báo lỗi.

**(b) `BusySlots`: dải → tập ô rời rạc**

Trong tệp, một khung bận viết theo **dải khép kín hai đầu** `{day, start, end}`. Khi parse, dải bị *bung*
thành từng ô:

```python
for t in range(int(start), int(end) + 1):      # bao gồm cả end
    busy.append((int(day), t))
```

| Trong tệp | Sau parse | Số ô |
|---|---|---:|
| `{"day":0,"start":1,"end":2}` | `{(0,1), (0,2)}` | 2 |
| Nguyễn Văn An: 5 dải `start 0 end 1`, mỗi ngày 0..4 | 10 ô | 10 |

**Dạng dải không còn tồn tại sau bước này.** Mọi kiểm tra về sau (`Professor.isBusyAt(day, time)`,
phạt B, lưới tô màu trong HTML) đều làm việc trên **tập ô rời rạc**, tra O(1). Đây là một ví dụ điển hình
về *biểu diễn phục vụ truy vấn*: đổi biểu diễn một lần khi đọc để mọi truy vấn sau này rẻ.

### 2.5 Ba hệ quy chiếu thời gian — nguồn hiểu lầm số một

| Hệ | Miền giá trị | Dùng ở đâu |
|---|---|---|
| **offset 0-based** | `0..12`, `6` = nghỉ trưa | `Reservation.Time`, `Professor.BusySlots`, trường `busy` trong JSON, **mọi vòng lặp của giải thuật** |
| **số tiết hiển thị** | `1..12`, không có số cho nghỉ trưa | `Constant.periodNumber(offset)`; nhãn `Tiết n` trong HTML |
| **số dòng bảng** | `1..13`, nghỉ trưa ở dòng 7 | `HtmlOutput` (rowspan, `ROOM_ROW_NUMBER = 14`) |

Quy tắc chuyển: sáng `offset o → tiết o+1`; chiều `offset o → tiết o`; `offset 6 → None`.
Vì `randomTime` chặn offset 6 và `isInLunchBreak` dùng chính offset, **giải thuật không bao giờ phải đổi hệ**.

### 2.6 Ba điểm gãy đã kiểm chứng khi dữ liệu đầu vào không sạch

Những hành vi sau đây được **đo bằng cách chạy thật**, không phải suy đoán:

| Dữ liệu | Chuyện xảy ra | Thời điểm phát hiện |
|---|---|---|
| `{ "class": { "course": 99 }}` (môn không tồn tại) | `__parseCourseClass` trả `None`, và `parseFile` **âm thầm append `None`** vào `_courseClasses`; `numberOfCourseClasses` đếm cả nó | Crash **muộn và khó đoán**: khi sinh quần thể → `AttributeError: 'NoneType' object has no attribute 'Duration'` |
| `{ "prof": { "id": 0, "name": "" }}` | `__parseProfessor` trả `None`, nhưng `parseFile` ghi `self._professors[prof.Id]` ngay | Crash **tức thì**: `AttributeError: 'NoneType' object has no attribute 'Id'` |
| `{ "class": { "course": 1, "duration": 7 }}` | `randomTime(7)` sinh danh sách offset rỗng (mọi `t ∈ 0..6` đều chồng nghỉ trưa), gọi `randrange(0)` | Crash khi khởi tạo: `ValueError: high <= 0` |

Hàm `__parseCourseClass` còn có mặc định `dur = 3` khi thiếu key `duration` — tức một lớp viết thiếu
số tiết **không báo lỗi**, mà âm thầm thành lớp 3 tiết.

---

## 3. Tầng 2 — Từ đối tượng miền sang không gian chỉ số

### 3.1 Ô "thời gian–không gian" và phép băm

Mọi gen vị trí **không phải** một tuple `(ngày, phòng, tiết)` mà là **một số nguyên chỉ số vào mảng phẳng**.
`model/Reservation.py`:

```
index = (ngày × NR + phòng) × 13 + offset              (mã hoá — getHashCode)

ngày   = index // (13 × NR)                            (giải mã — parse)
phòng  = (index % (13 × NR)) // 13
offset = (index % (13 × NR)) % 13
```

`NR = numberOfRooms`. Với bộ mini (`NR = 2`), lưới có `5 × 13 × 2 = 130` ô; với `GaSchedule.json`
(`NR = 4`), `5 × 13 × 4 = 260` ô. `ngày` là chỉ số `0..4`, hiển thị thành `T2..T6`
(`Trace.WEEK_DAYS` / `HtmlOutput.WEEK_DAYS`) — ngày 0 = T2, ngày 3 = T5.

**Bảng tra thật, in từ `Reservation.parse` trên bộ mini** — nhìn để thấy cấu trúc của mảng:

| `index` | ngày | phòng | offset | Nhận xét |
|---:|---:|---:|---:|---|
| 0 | 0 | 0 | 0 | đầu mảng: T2, phòng P1, tiết 1 |
| 13 | 0 | 1 | 0 | **+13 = sang phòng kế, cùng ngày cùng offset** |
| 26 | 1 | 0 | 0 | **+26 = sang ngày kế** (độ rộng một ngày = `13 × NR`) |
| 39 | 1 | 1 | 0 | |
| 52 | 2 | 0 | 0 | |
| 65 | 2 | 1 | 0 | |
| 77 | 2 | 1 | 12 | cuối ngày T4 |

Ba hằng số bước nhảy cần nhớ: `+1` = thêm một tiết trong cùng phòng, `+13` = nhảy sang cùng tiết của
**phòng kế tiếp**, `+26` (= `13 × NR`) = nhảy sang cùng tiết của **ngày kế tiếp**.

### 3.2 `_slots`: mảng mà mỗi phần tử là một **danh sách lớp**

```python
self._slots = [[] for _ in range(DAYS_NUM * DAY_HOURS * numberOfRooms)]
```

Mỗi ô giữ **danh sách** những lớp đang chiếm nó, không phải một lớp. Đây là lựa chọn biểu diễn then chốt:

| Truy vấn | Nhờ biểu diễn này |
|---|---|
| "Ô này có bị trùng phòng không?" | `len(ô) > 1` — **O(1)**, không cần quét toàn lịch |
| "Ô này có những lớp nào?" | đọc thẳng list |
| "Lớp này chiếm ô nào?" | `_classes[lop] + i` cho `i = 0..dur-1` — `dur` ô **liền nhau**, chỉ cần một số nguyên |
| "Lớp này ở (ngày, phòng, offset) nào?" | `Reservation.parse(index)` — có bảng nhớ tạm, không cấp phát lại |

Vì sao một ô có thể chứa **nhiều hơn một** lớp? Vì cá thể khởi tạo xếp mỗi lớp vào một ô **ngẫu nhiên,
không kiểm tra va chạm** (§6.1). Trùng phòng là **chuyện bình thường** ở quần thể ban đầu, và chính
mảng-danh-sách biến nó thành thứ đếm được tức thời để phạt.

**Kiểm chứng bằng bộ mini**: cá thể `seed 7` (đoạn tái lập riêng ở Phụ lục A) đặt lớp 0 ở `index 125` và
lớp 2 ở `index 126`, cả hai cùng ngày 4 – cùng phòng P2:

```
ô 126 = [lớp 0, lớp 2]     ← len == 2  ⇒  cả hai mất cờ P
```

Không cần quét 130 ô để phát hiện: chỉ cần nhìn đúng ô 126 mà hai lớp đó chiếm.

### 3.3 Cái giá của biểu diễn chỉ số

| Đánh đổi | Hệ quả thực tế |
|---|---|
| Mảng phẳng nhân thẳng với `DAY_HOURS = 13` | phải **giữ cả offset nghỉ trưa** trong lưới dù không ai dạy giờ đó (ô 6, 19, 32… luôn rỗng); `TEACHING_HOURS = 12` chỉ dùng khi tính sức chứa/hiển thị |
| Công thức băm phụ thuộc `NR` | `Reservation.NR` và `_reservationPool` là **trạng thái toàn cục theo lớp**; đổi bộ dữ liệu có số phòng khác ⇒ `getReservation` tự xoá bảng nhớ tạm. Nếu gọi `parse` trên chỉ số cũ sau khi `NR` đổi, kết quả **giải mã sai** |
| `index` là số nguyên trần | đọc log/debug phải tự chia lấy dư; đó là lý do `Trace` luôn in kèm `(ngày, phòng, offset)` đã giải mã |

---

## 4. Tầng 3 — Nhiễm sắc thể: bốn khối gen và một khối cờ

### 4.1 Sơ đồ và kích thước

```
Schedule
├── _configuration ──▶ (tầng 1, dùng chung, KHÔNG thuộc gen)
├── _slots        : list 130 (mini) / 260 (thật)   ← PHẢN CHIẾU của hai khối dưới
├── _classes      : dict  6 / 48   lop → index ô MỞ ĐẦU     ← gen vị trí
├── _professors   : dict  6 / 48   lop → Professor          ← gen giảng viên
├── _criteria     : np.bool  18 / 144 = 3 × số lớp          ← cờ, class-major
└── _fitness      : float                                    = Σcờ / (3 × số lớp) − phạt
```

`_slots` **không chứa thông tin mới**: nó được dựng từ `_classes` và được cập nhật song song mỗi khi một
lớp bị dời. Nó tồn tại chỉ để biến các truy vấn "có ai chiếm ô này không" thành O(1). Có thể coi nó là
**chỉ mục phụ (index)** trong ngữ điệu cơ sở dữ liệu — và vì là chỉ mục phụ, nó **dễ vỡ nếu đồng bộ thiếu**.

### 4.2 Layout của `_criteria` — chỗ hay đọc sai nhất

`3` cờ cho một lớp, xếp **class-major** (lớp trước, tiêu chí sau):

```
chỉ số = k × 3 + i        với  k = chỉ số lớp,  i = 0:P  1:G  2:N
```

Bộ mini, 6 lớp ⇒ chuỗi 18 cờ đọc theo nhóm ba:

```
index : 0 1 2 | 3 4 5 | 6 7 8 | 9 10 11 | 12 13 14 | 15 16 17
lớp   :   0   |   1   |   2   |    3    |     4    |     5
          P G N   P G N   P G N   P G N     P G N      P G N
```

Nếu nhầm sang layout **criterion-major** (tất cả cờ P trước, rồi G, rồi N), mọi con số trong §6 sẽ sai vị trí.

### 4.3 Một cá thể cụ thể, in nguyên vẹn từ chương trình

Bộ mini, `numpy.random.seed(2)`, cá thể đầu tiên của quần thể:

| Lớp `k` | Môn | `Duration` | `_classes[k]` | Giải mã (ngày, phòng, offset) | Chiếm các ô | `_professors[k]` |
|---:|---|---:|---:|---|---|---|
| 0 | Toán | 2 | 23 | (0, 1 → P2, 10) | 23, 24 | Cô A (1) |
| 1 | Lý | 2 | 88 | (3, 0 → P1, 10) | 88, 89 | Cô A (1) |
| 2 | Toán | 2 | 72 | (2, 1 → P2, 7) | 72, 73 | Thầy B (2) |
| 3 | Lý | 2 | 56 | (2, 0 → P1, 4) | 56, 57 | Cô A (1) |
| 4 | Toán | 2 | 82 | (3, 0 → P1, 4) | 82, 83 | Cô A (1) |
| 5 | Toán | 2 | 100 | (3, 1 → P2, 9) | 100, 101 | Cô A (1) |

Kiểm tra lại hai phép mã hoá: `23 = (0×2 + 1)×13 + 10` ✔ và `100 = (3×2 + 1)×13 + 9 = 91 + 9` ✔.

Chuỗi cờ in ra: `111101111111111101`, tách nhóm ba →

| Lớp | P | G | N | Diễn giải |
|---:|:-:|:-:|:-:|---|
| 0 | ✔ | ✔ | ✔ | ổn |
| 1 | ✔ | ✗ | ✔ | **Cô A** dạy lớp 1 (ngày 3 = T5, offset 10–11) **và** lớp 5 (ngày 3 = T5, offset 9–10) — trùng offset 10, **hai phòng khác nhau** |
| 2 | ✔ | ✔ | ✔ | ổn |
| 3 | ✔ | ✔ | ✔ | ổn |
| 4 | ✔ | ✔ | ✔ | ổn |
| 5 | ✔ | ✗ | ✔ | cùng cặp vi phạm với lớp 1 |

```
cờ đạt = 16 / 18 ;  phạt mềm = 0  (lớp 1 và 5 ở ngày 3, Cô A chỉ bận ngày 0)
fitness = 16 / 18 = 0,888889        ✔ khớp Schedule.fitness
```

Lớp 0 không có cờ P sai dù `index 23` cạnh lớp khác: các ô `23,24` chỉ có một mình nó.

**Cá thể thứ hai cùng `seed 2`** (để đối chiếu sau): chuỗi cờ `111111111011011111`, tức **lớp 3 và lớp 4
mất cờ P** — cả hai nằm ngày 4, cùng phòng P1, ô trùng là `106`:

```
lớp 3: index 106 → (4, 0, 2)  chiếm 106, 107   GV Cô A
lớp 4: index 105 → (4, 0, 1)  chiếm 105, 106   GV Thầy B
        ⇒ ô 106 = [lớp 3, lớp 4]  ⇒ len > 1 ⇒ mất P cả hai
        ⇒ G không sao vì hai giảng viên khác nhau
fitness = 16 / 18 = 0,888889
```

Hai cá thể này minh hoạ đúng hai loại ràng buộc cứng **tách rời**: một cái chỉ G, một cái chỉ P.

### 4.4 Đối chiếu kích thước với bộ thật

| Đại lượng | Bộ mini | `GaSchedule.json` |
|---|---:|---:|
| Phòng | 2 | 4 |
| Lớp học phần | 6 | 48 |
| Tổng tiết dạy | 12 | 160 |
| Sức chứa (`phòng × 5 × 12`) | 120 (10 %) | 240 (66,7 %) |
| `_slots` | 130 ô | 260 ô |
| Gen vị trí + gen giảng viên | 12 | 96 |
| `_criteria` | 18 | 144 |
| Không gian tìm kiếm | ≈ 10^13,2 | ≈ 10^122,4 |

---

## 5. Tầng 4 — Từ quần thể sang báo cáo

Mỗi cuối thế hệ, `Trace._record()` dựng một dict trong `Trace._history`:

| Khoá | Nội dung | Ai dùng |
|---|---|---|
| `generation` | số thế hệ **1-based** | bảng bước, tiêu đề |
| `fitness` | `float` cá thể elit tốt nhất | biểu đồ fitness |
| `criteria` | bản sao mảng 18/144 cờ | ô "qua các bước" tô đỏ/xanh |
| `classes`, `professors` | bản sao **hai dict gen** | vẽ lại đúng lịch của thế hệ đó |
| `configuration` | tham chiếu tầng 1 | giải mã tên phòng/môn/GV |
| `counts` | `(P đạt, G đạt, N đạt)` — đếm theo công thức `criteria[j*3+i]` | bảng `Đạt / tổng` |
| `total` | `len(criteria) // 3` = số lớp | mẫu số trong bảng |
| `populationSize`, `bestNotEnhance` | `N` và bộ đếm stagnation | dòng console |
| `elapsed` | giây kể từ `Trace.reset()` | trục thời gian |

Hai ghi chú thiết kế:

* `MAX_HISTORY = 5000` chặn số ảnh được lưu, để chạy `maxIterations` lớn không nổ bộ nhớ.
* `_record` **được bọc trong `try/except` riêng** trong `Trace.trace`: việc lưu lịch sử không bao giờ
  được làm hỏng cuộc chạy của giải thuật. Nói cách khác, tầng 4 là *quan sát*, cố ý tách khỏi *thực thi*.

---

## 6. Chín bước của GA thao tác trên các cấu trúc đó

Mỗi bước dưới đây liệt kê **cấu trúc nào đọc, cấu trúc nào ghi**, rồi ví dụ mini chạy thật.

### Bước 1 — Khởi tạo quần thể: tầng 1 ⇒ tầng 3

`GeneticAlgorithm.initialize` gọi `Schedule.makeNewFromPrototype()` `N` lần. Với **từng lớp theo thứ tự
tệp**, rút độc lập, **không kiểm tra va chạm**:

```python
day  = randrange(5)                       # đều
room = randrange(NR)                      # đều
time = randomTime(cc.Duration)            # lọc offset chồng nghỉ trưa
prof = _randomProfessorFor(cc)            # đều trong _professorsByCourse[môn]
for i in range(dur - 1, -1, -1):
    _slots[index + i].append(lop)         # ghi chỉ mục phụ
_classes[lop] = index
_professors[lop] = prof
calculateFitness()                         # rồi mới có _fitness
```

`randomTime` là **điểm duy nhất kiến thức nghiệp vụ "nghỉ trưa" lọt vào biểu diễn gen**:

```python
times = [t for t in range(DAY_HOURS - dur + 1) if not (t <= 6 < t + dur)]
```

Với `dur = 2` (bộ mini): `range(12)` = `0..11`, loại `t ∈ {5,6}` ⇒ **10 offset hợp lệ**
`[0,1,2,3,4,7,8,9,10,11]`. Không gian mỗi lớp mini = `5 ngày × 2 phòng × 10 offset × số GV dạy được môn`
= **200** (Toán, 2 GV) hoặc **100** (Lý, 1 GV).

Ví dụ: cá thể `seed 2` ở §4.3 là kết quả của đúng phép này — sáu dòng trong bảng đó chính là sáu lần rút.

> **Gen không bao giờ "hỏng về mặt cấu trúc".** Nhờ mọi offset hợp lệ đều làm khối `dur` ô nằm gọn trong
> một `(ngày, phòng)`, chỉ mục phụ `_slots` không bao giờ có ô vượt biên. Đây là lý do bảng `Đạt/tổng`
> của tiêu chí N luôn đầy (§6.2).

### Bước 2 — Chấm điểm: `_slots` + `_classes` + `_professors` ⇒ `_criteria` ⇒ `_fitness`

`Schedule.calculateFitness` duyệt `_classes.items()` **một lượt**, mỗi lớp làm ba việc:

| Tiêu chí | Truy vấn trên cấu trúc | Chi phí |
|---|---|---|
| P | cắt `dur` ô liên tiếp từ `index`, hỏi `len(ô) > 1` | `O(dur)` |
| G | `timeId = ngày × (13 × NR) + offset`, rồi `dur` ô × `NR` phòng qua `timeId += 13`; so giảng viên của từng lớp tìm thấy | `O(dur × NR)` |
| N | `timeId <= 6 < timeId + dur` — chỉ cần offset và `dur` | O(1) |
| B | `dur` lần `Professor.isBusyAt(ngày, offset + i)` trên `BusySlots` (tập ô), **dừng ở ô đầu tiên dính** | `O(dur)` |

```python
điểm = Σ (1 nếu cờ đạt, else 1 - weights[i])  −  0,2 × (số lớp dính bận)
fitness = điểm / len(_criteria)
```

**Ví dụ mini (cá thể §4.3)**: 16/18 cờ đạt, 0 lớp bận ⇒ `0,888889`.
**Ví dụ mini khác** — cá thể `seed 3` trong §6.4 dưới: 14/18 cờ đạt và **2** lớp dính bận Cô A
⇒ `(14 − 0,4) / 18 = 0,755556`.

### Bước 3 — Lựa chọn cha mẹ: chỉ đọc `_chromosomes`, không sửa gì

```python
(population[randrange(32768) % N], population[randrange(32768) % N])
```

Rút **có hoàn lại** từ quần thể ⇒ cha và mẹ có thể là cùng một cá thể. Xác suất một cá thể cụ thể được
rút trong một lượt sinh sản: `1/N`; với `N = 40` (mini) là **2,5 %**, với `N = 100` (thật) là **1 %**.
Fitness **không** tham gia bước này — toàn bộ áp lực tiến hoá nằm ở Bước 6 và 7.

### Bước 4 — Lai ghép: `_classes`/`_professors` của hai cha mẹ ⇒ của một con

Cắt theo **thứ tự lớp**, không theo ô:

```python
if randrange(100) > p: return copy(cha)          # xác suất lai THẬT = (p+1)/100
cp = [False]*size
for i in range(k, 0, -1):                          # k điểm cắt, rút KHÔNG hoàn lại
    while True:
        j = randrange(size)
        if not cp[j]: cp[j] = True; break
first = randrange(2) == 0                          # đoạn đầu lấy cha hay mẹ
for i in range(size):
    lấy nguyên (index, dur ô, giảng viên) của lớp i từ (cha if first else mẹ)
    if cp[i]: first = not first
n.calculateFitness()                               # bắt buộc chấm lại
```

Vì một lớp **đi cả cụm** (vị trí + giảng viên), con luôn hợp lệ về cấu trúc, không cần sửa.

**Ví dụ thật, bộ mini, `seed 3`, `k = 2`, `p = 100`** (⇒ chắc chắn lai):

| | Fitness | Chuỗi cờ | Gen vị trí (lớp 0..5) |
|---|---:|---|---|
| Cha | 0,755556 | `111001111111111001` | `63, 0, 89, 74, 9, 1` |
| Mẹ | 0,988889 | `111111111111111111` | `53, 75, 49, 14, 91, 105` |
| **Con** | **0,866667** | `111111111101111101` | `63, 75, 49, 14, 91, 1` |

Đọc từng cột:

```
lớp        0     1     2     3     4     5
con        63    75    49    14    91     1
nguồn     CHA   MẸ    MẸ    MẸ    MẸ   CHA      ← cắt sau lớp 0 và sau lớp 4
```

* Cha (0,755556) sai 4 cờ: lớp 1 và lớp 5 **vừa trùng phòng vừa trùng Cô A** ở ngày 0 (lớp 1 chiếm ô `0,1`;
  lớp 5 chiếm ô `1,2`; ô `1` có `[lớp 1, lớp 5]`). Cha còn 2 lớp dính bận Cô A ⇒ `(14 − 0,4)/18`.
* Mẹ hoàn hảo về cứng (18/18) nhưng 1 lớp dính bận ⇒ `(18 − 0,2)/18 = 0,988889`.
* Con: bốn lớp giữa lấy từ mẹ nên **sạch vi phạm phòng**; cặp phòng–GV hỏng của cha bị tách, nhưng
  lớp 5 lấy từ cha (ngày 0, P1, offset 1–2) lại rơi đúng khung mà lớp 3 lấy từ mẹ đang chiếm
  (ngày 0, P2, offset 1–2) — **cả hai đều của Cô A** ⇒ một cặp G mới, **mất 2 cờ**.
  Kèm 2 lớp dính bận Cô A (lớp 3 từ mẹ, lớp 5 từ cha) ⇒ `(16 − 0,4)/18 = 0,866667`.

Bài học của ví dụ: **con không chắc tốt hơn cha mẹ tốt nhất** (0,867 < 0,989). Đây chính là lý do cần
Bước 7 — con chỉ *được* vào quần thể, còn elit thì không bao giờ bị mất.

### Bước 5 — Đột biến: sửa `_classes`, `_professors` và chỉ mục phụ `_slots`

```python
if randrange(100) > p: return                 # xác suất thật = (p+1)/100
for _ in range(mutationSize):
    mpos = randrange(số lớp)                  # rút CÓ hoàn lại
    repair(lop, ô_cũ, reservation2=None)       # gỡ dur ô cũ, ghi dur ô mới
    _professors[lop] = _randomProfessorFor(lop) # gán lại GV
calculateFitness()                              # CHẤM MỘT LẦN ở cuối
```

`repair` là chỗ duy nhất đụng tới `_slots`:

```python
for j in range(dur):  while lop in slots[ô_cũ + j]: slots[ô_cũ + j].remove(lop)   # gỡ
for j in range(dur):  slots[ô_mới + j].append(lop)                                 # đặt
self._classes[lop] = ô_mới
```

**Ví dụ thật, bộ mini**: vẫn cá thể `seed 2` của §4.3 (0,888889), gọi `mutation(1, 100)` với
`numpy.random.seed(2)` — dời đúng **một** lớp:

| | Trước | Sau |
|---|---|---|
| Lớp bị dời | lớp 5: `index 100` → (ngày 3, P2, offset 9), GV **Cô A** | `index 2` → (ngày 0, P1, offset 2), GV **Thầy B** |
| Các lớp khác | không đổi | không đổi |
| Chuỗi cờ | `111101111111111101` | `111111111111111111` |
| Fitness | 0,888889 | **1,000000** |

Điều đáng học nằm ở chỗ **chỉ một lớp bị đụng mà hai cờ cùng được sửa**:

```
cờ G của lớp 1 (không bị dời) cũng chuyển từ ✗ thành ✔
→ vì lớp 1 bị ✗ là DO lớp 5; lớp 5 rời khỏi (ngày 3, offset 10) thì lớp 1 sạch.
cờ G của chính lớp 5 cũng ✔ — nó sang ngày 0, nơi Thầy B chưa có lớp nào.
và nó KHÔNG dính phạt B: Thầy B có BusySlots rỗng.
```

⇒ **Fitness không tách theo lớp.** Hệ quả thực hành: không thể "sửa cục bộ rồi tính incremental" một cách
đơn giản, và dự án chọn cách **tính lại toàn bộ sau mỗi lần đột biến** (đúng một lần, ở cuối).
Ô đích cũng giải mã đúng theo công thức §3.1: `2 = (0×2 + 0)×13 + 2` ⇒ ngày 0, phòng `0` (P1), offset `2`.

### Bước 6 — Thay thế và elitism: đổi chỗ trong `_chromosomes`, duy trì `_bestChromosomes`

```python
for j in range(replaceByGeneration):          # mặc định 8
    parent = selection(pop)                    # bước 3
    child  = parent[0].crossover(parent[1], k, p_c)      # bước 4
    child.mutation(size, p_m)                              # bước 5
    ci = randrange(32768) % N
    while isInBest(ci):  ci = randrange(32768) % N        # KHÔNG bao giờ đè elit
    population[ci] = child
    addToBest(ci)
```

Trạng thái cần nhớ: `_bestChromosomes` là mảng `trackBest` chỉ số **sắp theo fitness GIẢM DẦN**, nên
`_bestChromosomes[0]` luôn là cá thể tốt nhất — đó chính là `GeneticAlgorithm.result` mà `run` và `Trace`
đọc. `addToBest` bỏ qua nếu nhóm đã đầy mà con không tốt hơn phần tử cuối, hoặc con đã ở trong nhóm;
khi nhóm đầy, phần tử cuối bị rút cờ `_bestFlags` để nhường chỗ.

| Cấu hình mini | N = 40, `trackBest = 3`, `replaceByGeneration = 4` |
|---|---|
| Chỗ elit, bất khả xâm phạm | 3 |
| Chỗ con lai có thể đứng | 37 |
| Tỷ lệ trẻ hoá mỗi thế hệ | 4/40 = **10 %** |

Ba clamp bảo đảm cấu hình hợp lệ (`initAlgorithm` + `set_replace_by_generation`): `N ≥ 2`;
`1 ≤ trackBest ≤ N − 1`; `1 ≤ replaceByGeneration ≤ N − trackBest`.

### Bước 7 — Điều kiện dừng: đọc `result.fitness` ở **đầu** vòng

```python
if best.fitness > minFitness: break                    # ① đích, so sánh NGHIÊM
if abs(best.fitness - lastBestFit) <= 1e-7: repeat += 1
else: repeat = 0                                       # ② stagnation
if repeat >= maxStagnation: break
# ③ hết maxIterations (điều kiện của while)
```

**Ví dụ mini, điều kiện ① kích hoạt rất nhanh.** Chạy GA trên bộ mini với
`N = 40, trackBest = 3, replaceByGeneration = 4, k = 2, mutationSize = 1, p_c = 80, p_m = 30,
maxIterations = 80, maxStagnation = 80`, `numpy.random.seed(2)`:

```
số thế hệ được ghi vào Trace._history : 1
fitness tốt nhất                      : 1,000000
đếm theo tiêu chí (counts)             : (6, 6, 6) / 6 lớp   ← P, G, N đều đủ
cờ của cá thể thắng                    : 111111111111111111
```

Bài học từ chính ví dụ này: với bài toán **nhẹ** (6 lớp, sức chứa dùng 10 %), GA chạm lịch hoàn hảo sau
**một** thế hệ rồi dừng ngay ở đầu thế hệ thứ hai vì `1,0 > 0,999`. Bộ 48 lớp thì ngược lại — cùng cấu
trúc vòng lặp nhưng đi hàng trăm thế hệ (bảng hội tụ thực đo ở bản 1, §9.2).

Cũng từ ví dụ này thấy rõ **cột N luôn đầy** trên mọi bộ dữ liệu, vì `randomTime` loại offset nghỉ trưa
ngay khi sinh gen, `repair` dùng lại chính `randomTime`, và `crossover` chỉ nguyên khối đã hợp lệ của cha
mẹ. Cờ N tồn tại như **lưới an toàn**, không như một tiêu chí cạnh tranh.

### Bước 8 — Ghi ảnh chụp thế hệ

`run()` gọi `Trace.trace(self, currentGeneration + 1, repeat)` ở **cuối** mỗi vòng. Vì `best` được đọc ở
**đầu** vòng còn `Trace` đọc lại `result` sau khi cài con lai, dòng console in ra là trạng thái **quần thể
mới**, nhưng phép thử `①` và `②` lại dùng kết quả của thế hệ **trước**. Đây là nguồn lệch một thế hệ dễ gây
bối khi đối chiếu bảng bước với log.

### Bước 9 — Render: `_history` ⇒ console + HTML

`HtmlOutput` đọc `Trace.get_history()` (bản sao, để không sửa lịch sử đang dùng) và dựng: biểu đồ fitness,
lưới "qua các bước" (điều hướng bằng phím mũi tên), bảng thời khoá biểu theo phòng (các tiết liền nhau
cùng môn được gộp `rowspan`, **không bao giờ gộp qua dòng nghỉ trưa 7**), badge tiêu chí và ô bị phạt B.

---

## 7. Điều mô hình biểu diễn được và không biểu diễn được

**Biểu diễn được** (và GA tối ưu trực tiếp): trùng phòng (P), trùng lịch giảng viên (G), tránh nghỉ trưa
(N), tránh khung bận của giảng viên (B).

**Không biểu diễn được** — cần nói rõ vì đây là giới hạn *của cấu trúc*, không phải của giải thuật:

| Nhu cầu thực tế | Vì sao cấu trúc hiện tại không nói được |
|---|---|
| Sức chứa phòng theo số sinh viên | `Room` chỉ có `Id`, `Name`; không có sức chứa; một ô chỉ hỏi "rỗng hay chưa", không hỏi "chứa đủ X SV không" |
| Một môn học phải chia thành nhiều buổi trong tuần | `CourseClass` **là** một buổi `dur` tiết liền; "môn có 5 lớp" biểu diễn bằng 5 object `class` riêng, không có quan hệ nhóm |
| Sinh viên cùng nhóm không được xếp trùng hai môn | không có khái niệm nhóm SV trong mô hình (ràng buộc nhóm SV từng tồn tại và đã bị bỏ) |
| Cân bằng số tiết giữa các giảng viên | không có tiêu chí nào nhìn **tổng** tiết của một `Professor`; gen GV chỉ bị phạt khi *xếp chồng* hoặc *dính bận* |
| Phòng nào phù hợp môn nào (thực hành/lý thuyết) | `CourseClass` không mang loại phòng; mọi phòng ngang nhau với mọi lớp |
| Nhiều tuần / luân phiên | mô hình là **một tuần lặp lại**, `DAYS_NUM = 5` và không có trục tuần |

Và ba giới hạn *kỹ thuật* của chính biểu diễn đã kiểm chứng ở §2.6 (durations ≥ 7 crash, class trỏ môn
lỗi thành `None` lặng lẽ, prof lỗi crash tức thì).

---

## 8. Bảng ánh xạ nghiệp vụ → cấu trúc → mã

| Khái niệm nghiệp vụ | Cấu trúc dữ liệu | Thuộc tính / chỉ số | Hàm xử lý |
|---|---|---|---|
| "Một lớp cần xếp" | `CourseClass` | `Id` = thứ tự gen, `Duration` | `Configuration.__parseCourseClass` |
| "Lớp này đặt lúc nào, ở đâu" | gen vị trí | `Schedule._classes[lop] = index` | `Reservation.getHashCode` / `parse` |
| "Ai dạy lớp này" | gen giảng viên | `Schedule._professors[lop]` | `Schedule._randomProfessorFor` |
| "Chỗ này đã bị ai chiếm" | chỉ mục phụ | `Schedule._slots[index] : list` | ghi trong `makeNewFromPrototype` / `repair` |
| "Phòng có trùng không" | cờ P | `_criteria[k*3 + 0]` | `Criteria.isRoomOverlapped` |
| "Thầy/cô có trùng lịch không" | cờ G | `_criteria[k*3 + 1]` | `Criteria.isOverlappedProf` |
| "Có đè giờ trưa không" | cờ N | `_criteria[k*3 + 2]` | `Criteria.isInLunchBreak` |
| "Thầy/cô đang bận giờ đó" | ràng buộc mềm | `Professor.BusySlots : set` | `Professor.isBusyAt` + vòng phạt ở `calculateFitness` |
| "Phương án này tốt cỡ nào" | scalar | `Schedule._fitness` | `Schedule.calculateFitness` |
| "Ai là cha/mẹ, ai sống sót" | quần thể + elit | `_chromosomes`, `_bestChromosomes`, `_bestFlags` | `selection`, `replacement`, `addToBest` |
| "Tiến trình ra sao" | vết thế hệ | `Trace._history` | `Trace._record` → `HtmlOutput` |

---

## Phụ lục A — Bộ mini và code tái lập

Toàn bộ con số trong §4, §6 tái lập bằng lệnh sau, **chạy từ thư mục `GA`**:

```python
import sys, os, json, tempfile, random, io, contextlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console Windows cần dòng này
sys.path.insert(0, os.getcwd())
import numpy as np
from model.Configuration import Configuration
from model.Reservation import Reservation
from model.Schedule import Schedule
from algorithm.GeneticAlgorithm import GeneticAlgorithm
from Trace import Trace

MINI = [
    {"prof": {"id": 1, "name": "Cô A", "subjects": [1, 2],
              "busy": [{"day": 0, "start": 1, "end": 2}]}},
    {"prof": {"id": 2, "name": "Thầy B", "subjects": [1]}},
    {"course": {"id": 1, "name": "Toán"}}, {"course": {"id": 2, "name": "Lý"}},
    {"room": {"name": "P1"}}, {"room": {"name": "P2"}},
    {"class": {"course": 1, "duration": 2}}, {"class": {"course": 2, "duration": 2}},
    {"class": {"course": 1, "duration": 2}}, {"class": {"course": 2, "duration": 2}},
    {"class": {"course": 1, "duration": 2}}, {"class": {"course": 1, "duration": 2}},
]
path = os.path.join(tempfile.gettempdir(), "mini5.json")
json.dump(MINI, open(path, "w", encoding="utf-8"))

conf = Configuration(); conf.parseFile(path)
proto = Schedule(conf); CL = conf.courseClasses

def show(tag, ch):
    print(tag, round(ch.fitness, 6),
          "".join("1" if bool(x) else "0" for x in ch.criteria),
          [int(ch.classes[cc]) for cc in CL],
          [ch.professors.get(cc).Id for cc in CL])

# §4.3 — hai cá thể đầu của quần thể seed 2
np.random.seed(2)
show("cha ", proto.makeNewFromPrototype())      # 0.888889 111101111111111101 [23,88,72,56,82,100]
show("me  ", proto.makeNewFromPrototype())      # 0.888889 111111111011011111 [68,8,93,106,105,11]

# §3.2 — một cá thể CÓ trùng phòng: ô 126 chứa hai lớp
np.random.seed(7)
y = proto.makeNewFromPrototype()
print("seed7", round(y.fitness, 6), [int(y.classes[cc]) for cc in CL],
      [cc.Id for cc in y.slots[126]])          # [125, 100, 126, 36, 113, 22] và ô 126 = [0, 2]

# §6.4 — lai ghép 2 điểm, chắc chắn xảy ra (p = 100)
np.random.seed(3)
d = proto.makeNewFromPrototype(); m = proto.makeNewFromPrototype()
show("con ", d.crossover(m, 2, 100))            # 0.866667 111111111101111101 [63,75,49,14,91,1]

# §6.5 — đột biến dời 1 lớp: 0.888889 -> 1.000000
np.random.seed(2); x = proto.makeNewFromPrototype()
np.random.seed(2); x.mutation(1, 100)
show("sau ", x)                                 # 1.0 111111111111111111 [23,88,72,56,82,2]

# §6.7 — chạy GA trên mini
Trace.reset(); np.random.seed(2); random.seed(2)
alg = GeneticAlgorithm(conf, numberOfChromosomes=40, trackBest=3, replaceByGeneration=4,
                       numberOfCrossoverPoints=2, mutationSize=1, crossoverProbability=80,
                       mutationProbability=30, maxIterations=80, maxStagnation=80)
with contextlib.redirect_stdout(io.StringIO()):
    alg.run()
print(len(Trace.get_history()), round(alg.result.fitness, 6))     # 1 1.0
```

Kết quả in ra là **đúng các con số đã dùng trong tài liệu**. Lưu ý: `Schedule` dùng `numpy.random`, còn
`selection`/`replacement` dùng Python `random` — vì `run()` mồi lại Python RNG theo đồng hồ, phần *vòng
tiến hoá* không tái lập từng chữ số giữa các lần chạy; các ví dụ **một cá thể / một phép toán** ở trên thì
có, vì chúng chỉ dùng `numpy.random` và được mồi tường minh.

**Bảng quy chiếu nhanh bộ mini ↔ bộ thật**

| | Mini | `GaSchedule.json` |
|---|---:|---:|
| `_slots` | 130 | 260 |
| `len(_criteria)` | 18 | 144 |
| `+1` khi nhảy tiết | 1 ô | 1 ô |
| `+13` khi nhảy phòng | phòng kế, cùng ngày/tiết | như nhau |
| `+26` / `+52` khi nhảy ngày | `13 × NR` của mini | `13 × NR` của bộ thật |
| Ô hợp lệ cao nhất | 129 | 259 |
