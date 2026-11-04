# Báo cáo: Áp dụng giải thuật di truyền vào bài toán lập thời khoá biểu

Tài liệu này mô tả **từng bước** cách giải thuật di truyền (Genetic Algorithm — GA) được dùng để
xếp thời khoá biểu trong dự án, kèm **một ví dụ số thật ở mỗi bước**. Toàn bộ số liệu trong báo cáo
được trích ra bằng cách chạy chính bộ mã trong thư mục này trên bộ dữ liệu mẫu `GaSchedule.json`
(không phải số bịa); cách tái tạo từng ví dụ được ghi ở **Phụ lục C**.

| | |
|---|---|
| Mã giải thuật | `algorithm/GeneticAlgorithm.py`, `model/Schedule.py`, `model/Criteria.py` |
| Mã hoá nhiễm sắc thể | `model/Schedule.py` (lớp `Schedule`) |
| Bộ dữ liệu minh hoạ | `GaSchedule.json` — 5 giảng viên · 10 môn · 4 phòng · 48 lớp học phần |
| Tài liệu tham khảo bộ toán tử | Lakshmi, R. et al. *"A New Biological Operator in Genetic Algorithm for Class Scheduling Problem."* International Journal of Computer Applications 60 (2012): 6–11 |

---

## Mục lục

1. [Bài toán và dữ liệu](#1-bài-toán-và-dữ-liệu)
2. [Bước 1 — Mã hoá nhiễm sắc thể](#2-bước-1--mã-hoá-nhiễm-sắc-thể)
3. [Bước 2 — Hàm fitness](#3-bước-2--hàm-fitness)
4. [Bước 3 — Khởi tạo quần thể](#4-bước-3--khởi-tạo-quần-thể)
5. [Bước 4 — Lựa chọn cha mẹ](#5-bước-4--lựa-chọn-cha-mẹ)
6. [Bước 5 — Lai ghép nhiều điểm](#6-bước-5--lai-ghép-nhiều-điểm-multi-point-crossover)
7. [Bước 6 — Đột biến](#7-bước-6--đột-biến)
8. [Bước 7 — Thay thế và elitism](#8-bước-7--thay-thế-và-elitism)
9. [Bước 8 — Điều kiện dừng](#9-bước-8--điều-kiện-dừng)
10. [Bước 9 — Đọc kết quả](#10-bước-9--đọc-kết-quả)
11. [Nhận xét: điểm mạnh, hạn chế, hướng cải tiến](#11-nhận-xét-điểm-mạnh-hạn-chế-hướng-cải-tiến)
12. [Phụ lục A — Tham số mặc định](#phụ-lục-a--tham-số-mặc-định)
13. [Phụ lục B — Cách chạy](#phụ-lục-b--cách-chạy)
14. [Phụ lục C — Tái tạo các ví dụ](#phụ-lục-c--tái-tạo-các-ví-dụ)
15. [Phụ lục D — Ánh xạ khái niệm → mã nguồn](#phụ-lục-d--ánh-xạ-khái-niệm--mã-nguồn)

---

## 0. Đọc nhanh: 9 bước của giải thuật

| Bước | Việc thực hiện | Mã nguồn | Ví dụ trong báo cáo |
|---|---|---|---|
| 1 | Mã hoá một phương án xếp lịch thành nhiễm sắc thể | `model/Schedule.py` | §2.3 — 10 gen đầu |
| 2 | Chấm điểm (fitness) theo ràng buộc cứng P, G, N và ràng buộc mềm B | `Schedule.calculateFitness` | §3.3 — 0,504167 |
| 3 | Sinh quần thể 100 cá thể ngẫu nhiên | `Schedule.makeNewFromPrototype` | §4.2 — phân phối fitness |
| 4 | Chọn ngẫu nhiên đều 2 cá thể làm cha mẹ | `GeneticAlgorithm.selection` | §5 |
| 5 | Lai ghép nhiều điểm theo thứ tự lớp → 1 con | `Schedule.crossover` | §6.2 — con 0,611111 vượt cả bố lẫn mẹ |
| 6 | Đột biến: dời tối đa `mutationSize` lớp + gán lại giảng viên | `Schedule.mutation` | §7.2 — 0,643056 → 0,656944 |
| 7 | Cài con lai vào chỗ **không phải elit** | `GeneticAlgorithm.replacement` | §8 |
| 8 | Kiểm tra 3 điều kiện dừng (đích / hết thế hệ / đứng yên) | `GeneticAlgorithm.run` | §9.2 — hai lần chạy thật |
| 9 | Lưu ảnh chụp từng thế hệ, in bảng và xuất HTML | `Trace.py`, `HtmlOutput.py` | §10 |

---

## 1. Bài toán và dữ liệu

### 1.1 Đầu vào và đầu ra

**Đầu vào** (đọc từ `GaSchedule.json` bởi `model/Configuration.py`):

* Danh sách giảng viên, mỗi người kèm **các môn dạy được** (`subjects`) và **các khung đã bận** (`busy`).
* Danh sách môn học.
* Danh sách phòng học.
* Danh sách **lớp học phần** (`CourseClass`): một môn + số tiết liền nhau trong một buổi.

**Đầu ra**: với **mỗi lớp học phần**, GA phải quyết định 4 đại lượng

```
lớp  →  (ngày trong tuần, phòng học, tiết bắt đầu, giảng viên được giao)
```

sao cho không vi phạm ràng buộc cứng và hạn chế tối đa ràng buộc mềm.

### 1.2 Mô hình thời gian

Một tuần có **5 ngày** (T2–T6). Một ngày được chia thành **13 offset**, đánh số `0..12`
(`model/Constant.py`: `DAY_HOURS = 13`, `LUNCH_PERIOD = 6`, `PERIOD_MINUTES = 50`):

| offset | Tiết hiển thị | Khung giờ |
|---:|---:|---|
| 0 | Tiết 1 | 7:00 – 7:50 |
| 1 | Tiết 2 | 7:50 – 8:40 |
| 2 | Tiết 3 | 8:40 – 9:30 |
| 3 | Tiết 4 | 9:30 – 10:20 |
| 4 | Tiết 5 | 10:20 – 11:10 |
| 5 | Tiết 6 | 11:10 – 12:00 |
| **6** | **—** | **12:00 – 13:00 (nghỉ trưa)** |
| 7 | Tiết 7 | 13:00 – 13:50 |
| 8 | Tiết 8 | 13:50 – 14:40 |
| 9 | Tiết 9 | 14:40 – 15:30 |
| 10 | Tiết 10 | 15:30 – 16:20 |
| 11 | Tiết 11 | 16:20 – 17:10 |
| 12 | Tiết 12 | 17:10 – 18:00 |

Có **hai hệ quy chiếu** và báo cáo này dùng hệ **offset 0-based** (hệ mà giải thuật thao tác nội bộ):
buổi sáng `offset o → tiết o + 1`, buổi chiều `offset o → tiết o` — hai hệ **lệch nhau 1 đơn vị từ buổi chiều**.
Toàn bộ mã của GA (`Reservation.Time`, `Professor.BusySlots`, trường `busy` trong JSON) dùng offset.

> **Số liệu mẫu:** 48 lớp với tổng **160 tiết/tuần**. Sức chứa phòng học =
> 4 phòng × 5 ngày × 12 tiết thật = **240 tiết**, tức nhu cầu chiếm **66,7 %** — về mặt tổng lượng,
> bài toán **không** bị quá tải; mọi vi phạm còn lại đều do GA kẹt ở cực trị địa phương (xem §11).

### 1.3 Bộ dữ liệu mẫu `GaSchedule.json`

**Phòng học** (ID do `Room` tự tăng theo thứ tự đọc tệp):

| ID | Tên |
|---:|---|
| 0 | Phòng 201 |
| 1 | Phòng 102 |
| 2 | Phòng 303 |
| 3 | Phòng 401 |

**Giảng viên** — `Subjects` là môn dạy được (ID môn), `Busy` là tập ô `(ngày, offset)` đã bận:

| ID | Họ tên | Môn dạy được | Số ô bận | Khung bận `(ngày, offset)` |
|---:|---|---|---:|---|
| 1 | Nguyễn Văn An | 1, 2, 4, 6, 9 | 10 | cả 5 ngày, offset 0–1 (2 tiết đầu mỗi sáng) |
| 2 | Trần Thị Bình | 1, 2, 3, 5, 10 | 4 | (0,1) (0,2) (0,7) (0,8) |
| 3 | Lê Quốc Cường | 1, 2, 3, 4, 8 | 6 | (0,1) (0,2) (0,7) (0,8) (0,9) (0,10) |
| 4 | Phạm Thị Dung | 1, 3, 6, 7, 9 | 2 | (0,9) (0,10) |
| 5 | Vũ Anh Đức | 1, 2, 4, 5, 7 | 4 | (0,1) (0,2) (0,7) (0,8) |

**Lớp học phần** — ID lớp chính là thứ tự trong tệp, và cũng là **thứ tự gen** của nhiễm sắc thể:

| Lớp | Môn | Số tiết |
|---:|---|---:|
| 0–5 | Lập trình hướng đối tượng (môn 1) | 3 |
| 6–9 | Cấu trúc dữ liệu và giải thuật (môn 2) | 4 |
| … | … | … |

Phân bố số tiết của 48 lớp: **6 lớp 2 tiết · 20 lớp 3 tiết · 22 lớp 4 tiết** (trung bình 3,33 tiết/lớp).

### 1.4 Các ràng buộc

| Ký hiệu | Loại | Nội dung | Cách kiểm tra | Trọng số / mức phạt |
|---|---|---|---|---|
| **P** | cứng | Phòng học không bị hai lớp chiếm cùng một ô | `Criteria.isRoomOverlapped` | `weights[0] = 1.0` |
| **G** | cứng | Một giảng viên không dạy hai lớp cùng (ngày, offset) | `Criteria.isOverlappedProf` | `weights[1] = 1.0` |
| **N** | cứng | Khối tiết của lớp không chồng offset nghỉ trưa (6) | `Criteria.isInLunchBreak` | `weights[2] = 1.0` |
| **B** | **mềm** | Lớp không rơi vào khung đã bận của chính giảng viên được gán | `Professor.isBusyAt` | `busyPenalty = 0.2` / **lớp** |

Hai điểm cần nhớ:

* Phạt B tính **một lần cho mỗi lớp** dù lớp dài mấy tiết (`break` ngay sau ô bận đầu tiên).
* Vì `weights = [1, 1, 1]` và `busyPenalty = 0.2`, **một vi phạm cứng luôn đắt hơn mọi vi phạm mềm** —
  thiết kế này giữ cho GA không "đổi chỗ vi phạm cứng lấy vi phạm mềm".

### 1.5 Vì sao phải dùng GA

Không gian tìm kiếm của **một lớp** (sau khi `randomTime` đã loại các offset chồng nghỉ trưa):

| Số tiết | Offset hợp lệ | Phương án vị trí (5 ngày × 4 phòng × offset) |
|---:|---|---:|
| 2 | 10 → `0,1,2,3,4,7,8,9,10,11` | 5 × 4 × 10 = **200** |
| 3 | 8 → `0,1,2,3,7,8,9,10` | 5 × 4 × 8 = **160** |
| 4 | 6 → `0,1,2,7,8,9` | 5 × 4 × 6 = **120** |

Nhân với số giảng viên dạy được môn của lớp (1 đến 5 người, tuỳ môn) rồi nhân chéo **48 lớp**, ta được

```
log10(không gian tìm kiếm) ≈ 122,4   →   ≈ 10^122 phương án
```

Duyệt exhaustive là bất khả thi, và bài toán lại **có nhiều cực trị địa phương** (dời một lớp làm
thay đổivi phạm của các lớp khác). Đó chính là lý do cần một phương pháp tiến hoá theo quần thể.

---

## 2. Bước 1 — Mã hoá nhiễm sắc thể

### 2.1 Cấu trúc gen

Một **cá thể** (nhiễm sắc thể) là một phương án xếp lịch **hoàn chỉnh** cho cả 48 lớp, được biểu diễn
bằng 5 trường trong `model/Schedule.py`:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `_slots` | mảng phẳng độ dài `5 × 13 × sốPhòng` = **260** (với 4 phòng) | Mỗi ô là **danh sách** lớp đang chiếm ô; ô có ≥ 2 phần tử ⇔ **trùng phòng** |
| `_classes` | `lớp → chỉ số ô mở đầu` | **Gen vị trí** — 48 gen |
| `_professors` | `lớp → giảng viên` | **Gen giảng viên** — 48 gen |
| `_criteria` | mảng bool độ dài `3 × 48 = 144` | Cờ đạt P/G/N, sắp **class-major**: lớp `k`, tiêu chí `i` ở chỉ số `k*3 + i` |
| `_fitness` | float | Điểm chuẩn hoá của cá thể |

Như vậy nhiễm sắc thể có **96 gen** (48 gen vị trí + 48 gen giảng viên), và độ dài mảng cờ
**144 = 3 × 48** chính là mẫu số của công thức fitness.

### 2.2 Công thức quy đổi ô ⇄ toạ độ

`model/Reservation.py` — với `NR` = số phòng, `DH = DAY_HOURS = 13`:

```
index = (ngày × NR + phòng) × 13 + offset         (mã hoá)

ngày   = index // (13 × NR)
phòng  = (index % (13 × NR)) // 13
offset = index % 13                                (giải mã)
```

Đi hết một ngày là nhảy `13 × NR = 52` chỉ số; tiến một `offset` là `+1`; tiến một **phòng**
(nhưng vẫn cùng ngày, cùng offset) là `+13`.

### 2.3 Ví dụ minh hoạ — 10 gen đầu của một cá thể khởi tạo

Cá thể đầu tiên của quần thể sinh với `numpy.random.seed(7)` (xem Phụ lục C):

| Lớp | Môn | Số tiết | `index` ô mở đầu | Giải mã (ngày, phòng, offset) | Các ô bị chiếm | GV được gán |
|---:|---|---:|---:|---|---|---|
| 0 | Lập trình hướng đối tượng | 3 | 230 | (4, 1 → Phòng 102, 9) | 230, 231, 232 | Phạm Thị Dung (4) |
| 1 | Lập trình hướng đối tượng | 3 | 205 | (3, 3 → Phòng 401, 10) | 205, 206, 207 | Vũ Anh Đức (5) |
| 2 | Lập trình hướng đối tượng | 3 | 88 | (1, 2 → Phòng 303, 10) | 88, 89, 90 | Nguyễn Văn An (1) |
| 3 | Lập trình hướng đối tượng | 3 | 80 | (1, 2 → Phòng 303, 2) | 80, 81, 82 | Lê Quốc Cường (3) |
| 4 | Lập trình hướng đối tượng | 3 | 48 | (0, 3 → Phòng 401, 9) | 48, 49, 50 | Vũ Anh Đức (5) |
| 5 | Lập trình hướng đối tượng | 3 | 49 | (0, 3 → Phòng 401, 10) | 49, 50, 51 | Vũ Anh Đức (5) |
| 6 | Cấu trúc dữ liệu & giải thuật | 4 | 41 | (0, 3 → Phòng 401, 2) | 41, 42, 43, 44 | Lê Quốc Cường (3) |
| 7 | Cấu trúc dữ liệu & giải thuật | 4 | 164 | (3, 0 → Phòng 201, 8) | 164–167 | Vũ Anh Đức (5) |
| 8 | Cấu trúc dữ liệu & giải thuật | 4 | 9 | (0, 0 → Phòng 201, 9) | 9–12 | Nguyễn Văn An (1) |
| 9 | Cấu trúc dữ liệu & giải thuật | 4 | 169 | (3, 1 → Phòng 102, 0) | 169–172 | Lê Quốc Cường (3) |

**Kiểm tra lại phép mã hoá** bằng tay cho lớp 0: ngày 4, phòng 1, offset 9

```
index = (4 × 4 + 1) × 13 + 9 = 17 × 13 + 9 = 221 + 9 = 230  ✔
```

và giải mã ngược: `230 // 52 = 4` (ngày), `(230 % 52) // 13 = 42 // 13 = 3`… —  *để ý*: `230 % 52 = 22`,
`22 // 13 = 1` (phòng 1), `230 % 13 = 9` (offset) ✔.

Hai điểm dễ thấy ngay trong bảng, và sẽ được §3 chấm thành điểm:

* **Lớp 4 và lớp 5 cùng phòng 401, ngày 0**: khối ô `48,49,50` và `49,50,51` chồng nhau tại ô 49, 50 → **vi phạm P**.
* Hai lớp đó còn do **cùng một giảng viên** (Vũ Anh Đức) dạy, trùng offset 10–11 → **vi phạm G**.

### 2.4 Vì sao gen là "cả khối ô" chứ không phải một ô

Một lớp `dur` tiết chiếm `dur` ô **liền nhau** và `index` lưu trong `_classes` chỉ là ô **mở đầu**.
Nhờ `randomTime(dur)` (§4) luôn chọn offset sao cho khối `[offset, offset + dur)` nằm gọn trong ngày,
phép `index + i` không bao giờ tràn sang phòng/ngày kế tiếp — đây là **bất biến** mà mọi hàm đếm ô khác
(`isRoomOverlapped`, phạt B, vẽ bảng) đều dựa vào.

---

## 3. Bước 2 — Hàm fitness

### 3.1 Công thức

`Schedule.calculateFitness()` duyệt 48 lớp, với mỗi lớp tính 3 cờ và cộng điểm:

```
điểm = Σ_{lớp k} Σ_{i ∈ {P,G,N}} ( 1                 nếu cờ i của lớp k ĐẠT
                                 | 1 - weights[i]      nếu cờ i VI PHẠM )
         − ( số lớp dính khung bận của GV được gán ) × busyPenalty

fitness = điểm / len(_criteria) = điểm / (3 × số lớp) = điểm / 144
```

Với `weights = [1.0, 1.0, 1.0]` và `busyPenalty = 0.2`, công thức gọn lại thành:

```
điểm = (số cờ ĐẠT trong 144 cờ) − 0.2 × (số lớp bị phạt B)
fitness = điểm / 144                    ∈ [0, 1]
```

| Đại lượng | Giá trị | Ý nghĩa |
|---|---:|---|
| Tổng số cờ | 144 | điểm tối đa |
| Một vi phạm cứng | −1 điểm ≈ −0,00694 fitness | mất trọn 1/144 |
| Một lớp bị phạt B | −0,2 điểm ≈ −0,00139 fitness | rẻ hơn 5 lần so với vi phạm cứng |
| fitness = 1.0 | 144/144 | lịch hoàn hảo: **0** vi phạm cứng **và** 0 lớp dính bận |

### 3.2 Ví dụ tính tay — chính cá thể ở §2.3

Chấm cá thể `seed 7` bằng ba hàm kiểm tra độc lập rồi đối chiếu với `_fitness` của chương trình:

| Thành phần | Kết quả đo được |
|---|---|
| Lớp vi phạm **P** | 33 lớp → 33 cờ P sai |
| Lớp vi phạm **G** | 37 lớp → 37 cờ G sai |
| Lớp vi phạm **N** | 0 lớp → 48/48 cờ N đúng |
| **Tổng cờ SAI** | 33 + 37 + 0 = **70** |
| **Tổng cờ ĐẠT** | 144 − 70 = **74** |
| Số ô phòng bị trùng | 33 ô |
| Số cặp giảng viên trùng lịch | 35 cặp |
| Số lớp bị phạt **B** | **7** → 7 × 0,2 = **1,4** điểm |

```
điểm    = 74 − 1,4 = 72,6
fitness = 72,6 / 144 = 0,504166666…
```

`Schedule.fitness` của cá thể này: **0.50416667** — khớp tuyệt đối ✔.

### 3.3 Ví dụ từng loại vi phạm, đọc từ chính cá thể trên

**P — trùng phòng (ô 49 và 50).** Lớp 4 chiếm `48,49,50`; lớp 5 chiếm `49,50,51`; cả hai ở
Phòng 401, ngày 0 (T2). Ô 49 = `(0×4 + 3)×13 + 10` chứa `[lớp 4, lớp 5]` ⇒ `len > 1` ⇒ cả hai mất cờ P.

Một ô trầm trọng hơn: ô `9` (ngày 0, Phòng 201, offset 9) chứa **3 lớp** `[8, 13, 23]`.

**G — giảng viên trùng lịch (không dính trùng phòng).** Lớp 0 (Phòng 102, ngày 4, offset 9–11) và
lớp 14 (Phòng 201, ngày 4, offset 7–9) **được giao cùng cho Phạm Thị Dung**. Hai phòng khác nhau nên
P không bị ảnh hưởng, nhưng `Criteria.isOverlappedProf` quét **mọi phòng** tại cùng `(ngày, offset)`:

```
timeId = ngày × (13 × NR) + offset          → ô của phòng đầu tiên
timeId += 13                                → nhảy sang CÙNG (ngày, offset) của phòng kế
lặp NR lần                                 → phủ hết mọi phòng
```

⇒ offset chung là `9` ⇒ cả hai lớp mất cờ G. Đây là ví dụ sạch để thấy G và P là hai ràng buộc độc lập.

**N — nghỉ trưa.** Cá thể này (và mọi cá thể trong dự án) có **0 vi phạm N**, vì `randomTime(dur)`
(§4.1) đã loại offset chồng nghỉ trưa **ngay khi sinh gen**, và `repair()` khi đột biến cũng dùng lại
chính hàm đó. Cờ N vì thế hoạt động như một **lưới an toàn** hơn là một tiêu chí thật sự cạnh tranh
(ghi chú này được nhắc lại ở §11.2).

**B — khung bận của giảng viên.** Lớp 12 được gán Lê Quốc Cường và mang gen
`(ngày 0, phòng 3 → Phòng 401, offset 0)` với `dur = 3`, tức chiếm các offset `0, 1, 2`.
GV Cường bận `(0,1)` và `(0,2)` ⇒ khối này chạm **hai** ô bận, nhưng vòng phạt có `break` ngay sau ô
bận đầu tiên nên lớp chỉ mất **một lần** `0,2` điểm — phạt tính **theo lớp**, không theo ô. Đó là lý do
mức phạt mềm của cả cá thể này là `7 × 0,2 = 1,4` chứ không lớn hơn. Danh sách 7 lớp bị phạt:

| Lớp | GV | Gen (ngày, phòng, offset) | Ô bận bị chạm | Vị trí trong khối |
|---:|---|---|---|---:|
| 6 | Lê Quốc Cường | (0, 3, 2) | (0, 2) | tiết đầu |
| 10 | Lê Quốc Cường | (0, 1, 8) | (0, 8) | tiết đầu |
| 12 | Lê Quốc Cường | (0, 3, 0) | (0, 1) | tiết thứ 2 |
| 13 | Lê Quốc Cường | (0, 0, 9) | (0, 9) | tiết đầu |
| 23 | Vũ Anh Đức | (0, 0, 8) | (0, 8) | tiết đầu |
| 26 | Nguyễn Văn An | (3, 3, 0) | (3, 0) | tiết đầu |
| 34 | Nguyễn Văn An | (1, 1, 0) | (1, 0) | tiết đầu |

---

## 4. Bước 3 — Khởi tạo quần thể

### 4.1 Cách sinh một cá thể ngẫu nhiên

`GeneticAlgorithm.initialize()` gọi `Schedule.makeNewFromPrototype()` **N lần**. Mỗi lần, với **từng** lớp
theo đúng thứ tự trong `configuration.courseClasses`:

```python
day  = randrange(DAYS_NUM)          # 0..4, đều
room = randrange(numberOfRooms)     # 0..3, đều
time = Schedule.randomTime(dur)     # offset hợp lệ, không chồng nghỉ trưa
professors[lop] = _randomProfessorFor(lop)   # đều trong GV dạy được môn đó
```

`randomTime(dur)` là bước **lọc không gian mẫu**:

```python
times = [t for t in range(DAY_HOURS - dur + 1) if not (t <= LUNCH_PERIOD < t + dur)]
```

Ví dụ với `dur = 3`: `range(11)` cho `0..10`, loại `t ∈ {4,5,6}` (vì `t ≤ 6 < t+3`) ⇒ còn
`[0,1,2,3,7,8,9,10]` — 8 ứng viên, đúng bằng bảng §1.5.

**Không gen nào được đảm nhận từ dữ liệu đầu vào**: giảng viên do GA tự gán (mô hình cũ cài sẵn GV
cho lớp đã được bỏ), nên `_randomProfessorFor` rút đều trong `Configuration._professorsByCourse[môn]`.
Nếu một môn không có GV nào dạy được, lớp đó nhận `None` — và khi đó **không phát sinh vi phạm G
cũng không phát sinh phạt B** (cả hai hàm đều `continue`/bỏ qua khi `prof is None`).

### 4.2 Ví dụ — phân phối fitness của quần thể khởi tạo

Quần thể 100 cá thể, `numpy.random.seed(7)` (cá thể số 0 chính là cá thể đã chấm ở §3.2):

| Thống kê | Fitness |
|---|---:|
| Thấp nhất | 0,504167 |
| Tứ phân vị 25 % | 0,551389 |
| Trung vị | 0,576389 |
| Tứ phân vị 75 % | 0,601389 |
| Cao nhất | 0,669444 |
| Trung bình | 0,578736 |

Phân bố theo khoảng: **71 cá thể trong [0,50 – 0,60) · 29 cá thể trong [0,60 – 0,70) · 0 cá thể ≥ 0,70.**

Nhận xét quan trọng cho phần tinh chỉnh tham số: quần thể khởi tạo **đã tập trung hẹp** quanh 0,58.
Đó là hệ quả tổ hợp của hai việc — (a) không có ràng buộc nào bị vi phạm *nặng* ngay từ đầu vì mỗi
phòng chỉ chứa trung bình 160/260 ≈ 0,6 lớp, và (b) N đã bị chặn bằng `randomTime`. GA không tiến hoá
từ "con số 0" mà từ "đã khá tốt", nên tín hiệu chọn lọc (**chênh lệch fitness giữa các cá thể**) nhỏ.

### 4.3 Ghi chú cài đặt

* `initialize()` **không** nạp elitelist. Các chỉ số `_bestChromosomes` chỉ được nạp dần trong
  `replacement()` của thế hệ đầu, nên trước lần `addToBest` đầu tiên `result` trả về cá thể ngẫu nhiên
  ở chỉ số 0.
* `_criteria` được cấp phát bằng `np.zeros(..., dtype=bool)`, nên một cá thể chưa chấm điểm có
  "tất cả cờ = sai" — vì thế `makeNewFromPrototype` luôn gọi `calculateFitness()` trước khi trả cá thể.

---

## 5. Bước 4 — Lựa chọn cha mẹ

`GeneticAlgorithm.selection(population)`:

```python
return (population[randrange(32768) % N], population[randrange(32768) % N])
```

Đây là **uniform random pairing**, không phải roulette wheel, không phải tournament:

* Mỗi cá thể có xác suất `1/N` như nhau, **bất kể fitness**.
* Hai vị trí được rút **có hoàn lại** ⇒ cha và mẹ có thể **chính là một cá thể** (xác suất 1/100 = 1 %
  với quần thể 100). Khi đó con lai chỉ là bản sao của bố mẹ.
* Áp lực chọn lọc **không** đến từ bước này, mà đến từ bước 7 (elit được bảo vệ) và từ việc con lai
  phải tự chứng minh bằng fitness.

**Ví dụ với quần thể 100 ở §4.2**: xác suất một cá thể cụ thể được chọn làm cha (hoặc mẹ) trong một
lượt sinh sản là 1 %. Với `replaceByGeneration = 8`, mỗi thế hệ có **8 cặp** ⇒ **16 lượt rút**;
xác suất một cá thể *không* bao giờ được rút trong thế hệ đó ≈ `(1 − 0,01)^16 ≈ 85 %`.

> Chi tiết kỹ thuật: `randrange(32768) % N` lấy số ngẫu nhiên từ **Python `random`**, còn toàn bộ phần
> sinh gen/lai ghép/đột biến trong `Schedule` dùng **`numpy.random`**. Hai dòng RNG độc lập — hệ quả
> được bàn ở §9.3 và Phụ lục C.

---

## 6. Bước 5 — Lai ghép nhiều điểm (multi-point crossover)

### 6.1 Cơ chế

`Schedule.crossover(parent, k, p)` — `self` là **cha**, đối số `parent` là **mẹ**, trả về **một con duy nhất**:

1. **Cổng xác suất**: `if randrange(100) > p: return copy(cha)` — không lai, chỉ sao chép cha.
   Vì `randrange(100)` cho `0..99`, điều kiện sai khi `r ≤ p`, tức **xác suất lai thật sự = (p + 1)/100**.
   Với `p = 80` mặc định ⇒ **81 %**, không phải 80 %.
2. **Chọn điểm cắt**: `k` vị trí trong dãy gen được rút **không hoàn lại** trên toàn bộ `size` lớp.
   Vì vậy `k ≤ số lớp`; `AlgorithmParameters.normalize` ép điều này, nếu không vòng `while` chọn
   điểm cắt sẽ **lặp vô hạn**. Mặc định `k = 2` ⇒ 3 đoạn.
3. **Nguồn khởi đầu**: `first = (randrange(2) == 0)` — đoạn đầu lấy từ cha hay mẹ là ngẫu nhiên.
4. **Sao chép theo đoạn**: với mỗi lớp `i`, nếu `first` thì **copy nguyên khối** từ cha
   (`_classes[lop]` + `dur` ô + giảng viên), ngược lại copy từ mẹ. `if cp[i]: first = not first`.

Hai tính chất đáng chú ý:

* Vì mỗi lớp lấy **nguyên** `(vị trí, giảng viên)` của **một** cha mẹ, con luôn có đúng một vị trí cho
  mỗi lớp ⇒ **không cần repair sau lai ghép**.
* Gen **giảng viên di truyền cùng gen vị trí** của cùng một lớp, không bao giờ bị trộn chéo giữa hai
  cha mẹ. Đây là lựa chọn thiết kế: cặp (lớp ở đâu, ai dạy) được coi là một "allele" thống nhất.

### 6.2 Ví dụ minh hoạ — con vượt cả hai cha mẹ

Hai cá thể khởi tạo (`numpy.random.seed(1)`), ép lai ghép bằng `crossoverProbability = 100`
(⇒ cổng luôn cho qua), `k = 2`:

| Cá thể | Fitness | Sai P | Sai G | Sai N | Lớp bị phạt B | Kiểm tra công thức |
|---|---:|---:|---:|---:|---:|---|
| Cha (P₁) | 0,543056 | 35 | 29 | 0 | 9 | (144 − 64 − 1,8)/144 = **0,543056** ✔ |
| Mẹ (P₂) | 0,583333 | 32 | 27 | 0 | 5 | (144 − 59 − 1,0)/144 = **0,583333** ✔ |
| **Con** | **0,611111** | 27 | 28 | 0 | 5 | (144 − 55 − 1,0)/144 = **0,611111** ✔ |

Hai điểm cắt rơi **sau lớp 13** và **sau lớp 36**, nguồn khởi đầu là **mẹ**, nên cấu trúc nhiễm sắc thể con:

```
lớp  0 … 13  →  từ MẸ     (14 lớp)
lớp 14 … 36  →  từ CHA     (23 lớp)
lớp 37 … 47  →  từ MẸ      (11 lớp)
-------------------------------------------
             tổng: mẹ 25 gen, cha 23 gen  (đếm bằng cách so sánh từng gen với hai cha mẹ)
```

Vài dòng cụ thể (cột *gen* là `[index, ngày, phòng, offset]`):

| Lớp | Gen cha | Gen mẹ | **Gen con** | GV cha | GV mẹ | **GV con** | Nguồn |
|---:|---|---|---|---:|---:|---:|---|
| 0 | `[156,3,0,0]` | `[256,4,3,9]` | **`[256,4,3,9]`** | 2 | 1 | **1** | mẹ |
| 1 | `[179,3,1,10]` | `[195,3,3,0]` | **`[195,3,3,0]`** | 1 | 4 | **4** | mẹ |
| 2 | `[20,0,1,7]` | `[88,1,2,10]` | **`[88,1,2,10]`** | 5 | 5 | **5** | mẹ |
| 14 | *(đoạn cha)* | | | | | | cha |
| 26 | `[223,4,1,2]` | `[118,2,1,1]` | **`[223,4,1,2]`** | 1 | 1 | **1** | cha |
| 27 | `[176,3,1,7]` | `[2,0,0,2]` | **`[176,3,1,7]`** | 4 | 1 | **4** | cha |
| 44 | `[234,4,2,0]` | `[34,0,2,8]` | **`[34,0,2,8]`** | 4 | 1 | **1** | mẹ |
| 47 | `[86,1,2,8]` | `[195,3,3,0]` | **`[195,3,3,0]`** | 4 | 5 | **5** | mẹ |

**Vì sao con lại tốt hơn cả hai cha mẹ?** Số lớp vi phạm P giảm từ 32/35 xuống **27**: mỗi đoạn gen
mang theo *cách xếp của cả một nhóm lớp*, nên khi ghép đoạn "mẹ 0–13" với đoạn "cha 14–36", hai nhóm
lớp vốn không cạnh tranh nhau trong cha/mẹ giờ được đặt vào **các phòng khác nhau** và số ô trùng
giảm. Đây đúng là cơ chế mà GA mong đợi: **tái tổ hợp** tạo ra cá thể nằm ngoài "hộp lồi" của cha mẹ.

Lưu ý ngược lại: điểm G của con (28 sai) **xấu hơn mẹ** (27 sai) — tái tổ hợp cũng có thể phá vỡ một
lịch đã tốt. Vì vậy fitness phải được **tính lại từ đầu** sau lai ghép (`n.calculateFitness()`), và con
vẫn phải cạnh tranh ở bước 7.

---

## 7. Bước 6 — Đột biến

### 7.1 Cơ chế

`Schedule.mutation(mutationSize, mutationProbability)` — áp dụng **trên chính con lai** sau bước 5:

```python
if randrange(100) > mutationProbability:      # xác suất ĐỘT BIẾN thật = (p + 1)/100
    return                                    # mặc định p = 3  ⇒  4 %
for i in range(mutationSize, 0, -1):
    mpos = randrange(numberOfClasses)         # rút CÓ hoàn lại ⇒ có thể dời 2 lần cùng một lớp
    repair(lop, ô_cũ, reservation2=None)      # gỡ khỏi dur ô cũ, đặt vào (ngày, phòng, offset) ngẫu nhiên
    professors[lop] = _randomProfessorFor(lop) # gán lại GV trong set dạy được môn
calculateFitness()                             # chỉ chấm MỘT lần sau toàn bộ các lần dời
```

* Đột biến đổi **cả hai khối gen** (vị trí *và* giảng viên) để thoát cực trị địa phương mà lai ghép
  một mình không vượt được.
* `repair(..., reservation2=None)` tái dùng đúng phân phối của bước sinh khởi tạo (`randomTime`),
  nên **sau đột biến vẫn không bao giờ sinh vi phạm N**.
* Với mặc định `mutationProbability = 3`, chỉ **4 %** số con lai bị đột biến — đây là toán tử *hiếm*,
  đóng vai trò "đánh thức" quần thể chứ không phải nguồn thay đổi chính.

### 7.2 Ví dụ minh hoạ — hai lớp bị dời, một lần chấm điểm

Lấy một cá thể ngẫu nhiên (`numpy.random.seed(101)`), rồi gọi `mutation(2, 100)` (ép chắc chắn xảy ra,
dời đúng 2 lớp). Kết quả đo:

| | Fitness | Sai P | Sai G | Lớp bị phạt B | Kiểm tra |
|---|---:|---:|---:|---:|---|
| **Trước** | 0,643056 | 26 | 24 | 7 | (144 − 50 − 1,4)/144 = **0,643056** ✔ |
| **Sau** | **0,656944** | 26 | 22 | 7 | (144 − 48 − 1,4)/144 = **0,656944** ✔ |

Hai gen thay đổi:

| Lớp | Môn | Tiết | **Trước** | **Sau** | GV trước → sau |
|---:|---|---:|---|---|---|
| 14 | Cơ sở dữ liệu | 3 | `index 55` → (ngày 1, Phòng 201, offset 3), ô 55–57 | `index 140` → (ngày 2, Phòng 303, offset 10), ô 140–142 | Cường (3) → **Dung (4)** |
| 43 | An toàn thông tin | 4 | `index 216` → (ngày 4, Phòng 201, offset 8), ô 216–219 | `index 61` → (ngày 1, Phòng 201, offset 9), ô 61–64 | Cường (3) → Cường (3) *(rút trúng cùng người)* |

Kiểm tra mã hoá của gen mới lớp 14: `(2 × 4 + 2) × 13 + 10 = 10 × 13 + 10 = 140` ✔.

**Ba quan sát rất quan trọng để hiểu cách fitness vận hành:**

1. **Lớp 43 hết vi phạm G** — nó được dời khỏi trùng lịch với các lớp khác của GV Cường. Hợp lý.
2. **Lớp 31 cũng hết vi phạm G**, dù **không bị đụng tới**. Đây là *hiệu ứng lan truyền*: cờ G của lớp
   31 được tính bằng cách quét các lớp **khác** của cùng giảng viên; khi lớp 43 rời khỏi ô đó, lớp 31
   tự động sạch. ⇒ **fitness là hàm toàn cục, không separable theo lớp**; một đột biến nhỏ đổi điểm của
   nhiều lớp.
3. **Số vi phạm P không giảm** dù đã dời 2 lớp: danh sách lớp sai P **bớt lớp 12** nhưng **thêm lớp 40**
   (một lớp khác giờ đè vào ô mới của lớp 14 hoặc 43). Net = 0, nên toàn bộ mức cải thiện
   (0,643056 → 0,656944) đến từ ràng buộc G.

---

## 8. Bước 7 — Thay thế và elitism

`GeneticAlgorithm.replacement(population, replaceByGeneration)` chạy `replaceByGeneration` vòng;
mỗi vòng làm trọn chuỗi **chọn → lai → đột biến → cài**:

```python
for j in range(replaceByGeneration):          # mặc định 8
    parent = selection(population)             # bước 4
    child  = parent[0].crossover(parent[1], k, p_crossover)   # bước 5
    child.mutation(mutationSize, p_mutation)                  # bước 6
    ci = randrange(32768) % N
    while isInBest(ci):                        # ⚠ bỏ qua mọi chỗ đang bị elit chiếm
        ci = randrange(32768) % N
    population[ci] = child
    addToBest(ci)                              # nạp con vào elitelist nếu đủ tốt
```

**Elitelist** là `_bestChromosomes` (độ dài `trackBest`, mặc định 5) cùng `_bestFlags`, với bất biến:

> các chỉ số trong `_bestChromosomes` được sắp theo **fitness GIẢM DẦN**, nên
> `_bestChromosomes[0]` luôn là cá thể tốt nhất toàn quần thể — đó chính là `GeneticAlgorithm.result`.

`addToBest(ci)` bỏ qua ngay trong hai trường hợp: (a) nhóm đã đầy **và** cá thể mới không tốt hơn
phần tử cuối nhóm; (b) cá thể đã nằm trong nhóm. Khi nhóm đầy, phần tử cuối (kém nhất) bị rút
`_bestFlags` để nhường chỗ ⇒ **cá thể elit không bao giờ bị con lai ghi đè** (elitism cổ điển).

**Ví dụ đếm theo tham số mặc định** (`N = 100`, `trackBest = 5`, `replaceByGeneration = 8`):

| Đại lượng | Giá trị |
|---|---:|
| Chỗ bị elit chiếm (không bao giờ bị thay) | 5 |
| Chỗ con lai có thể đứng | 95 |
| Số con lai mỗi thế hệ | 8 |
| Tỷ lệ quần thể bị "trẻ hoá" mỗi thế hệ | 8/100 = **8 %** |
| Số cá thể giữ nguyên qua một thế hệ | 92 (90 không elit + 5 elit) |
| Tổng số phép `crossover` cho 100 thế hệ | 800 |

Clamp bảo đảm cấu hình luôn hợp lệ (`initAlgorithm` + `set_replace_by_generation`):

```
N        ≥ 2
1 ≤ trackBest ≤ N − 1                     (phải chừa ít nhất 1 chỗ cho con)
1 ≤ replaceByGeneration ≤ N − trackBest   (số chỗ không bị elit chiếm)
```

---

## 9. Bước 8 — Điều kiện dừng

### 9.1 Ba điều kiện, kiểm tra ở **đầu** mỗi thế hệ

```python
while currentGeneration < maxIterations:
    best = self.result
    if best.fitness > minFitness:          # ① đạt đích — so sánh NGHIÊM
        break
    difference = abs(best.fitness - lastBestFit)
    if difference <= 0.0000001:            # ② stagnation: fitness đứng yên
        repeat += 1
    else:
        repeat = 0
    if repeat >= maxStagnation:
        break
    ... replacement ... Trace.trace(self, currentGeneration + 1, repeat)
```

| # | Điều kiện | Mặc định | Hệ quả của cách viết |
|---|---|---|---|
| ① | `best.fitness > minFitness` | `minFitness = 0.999` | So sánh **nghiêm**: `minFitness = 1.0` **không bao giờ** thoả (cần lịch hoàn hảo tuyệt đối); `minFitness = 0.0` dừng ngay ở thế hệ 0 |
| ② | `repeat >= maxStagnation` | `maxStagnation = 100` | Ngưỡng "đứng yên" là `|Δ| ≤ 1e-7` |
| ③ | `currentGeneration >= maxIterations` | `maxIterations = 1000` | Ngân sách thế hệ |

Vì `best` được đọc ở **đầu** vòng, `Trace` lại chụp **sau** khi cài con lai, nên dòng thế hệ in ra
phản ánh quần thể **mới**, còn phép so sánh `minFitness`/stagnation dùng kết quả của thế hệ **trước**.
Đây là lý do `Trace` ghi thế hệ 1-based (`currentGeneration + 1`) trong khi bộ đếm vòng lặp là 0-based.

### 9.2 Ví dụ minh hoạ — cùng một dữ liệu, hai số phận

**Chạy A — tham số mặc định** (`N = 100`, `maxIterations = 1000`, `maxStagnation = 100`,
`replaceByGeneration = 8`, `crossover 80 %`, `mutation 3 %`), `numpy.random.seed(2026)`:

| Thế hệ | Fitness | P đạt | G đạt | N đạt | Thế hệ không cải thiện | elapsed |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0,619444 | 19/48 | 24/48 | 48/48 | 0 | 0,10 s |
| 2 | 0,625000 | 22/48 | 22/48 | 48/48 | 0 | 0,10 s |
| 10 | 0,651389 | 27/48 | 20/48 | 48/48 | 2 | 0,13 s |
| 25 | 0,679167 | 21/48 | 30/48 | 48/48 | 2 | 0,18 s |
| 50 | 0,687500 | 19/48 | 33/48 | 48/48 | 3 | 0,27 s |
| 75 | 0,705556 | 21/48 | 34/48 | 48/48 | 0 | 0,37 s |
| 100 | 0,705556 | 21/48 | 34/48 | 48/48 | 25 | 0,47 s |
| 125 | 0,705556 | 27/48 | 28/48 | 48/48 | 50 | 0,57 s |
| 150 | 0,705556 | 21/48 | 34/48 | 48/48 | 75 | 0,67 s |
| **174** | **0,705556** | 21/48 | 34/48 | 48/48 | **99** | **0,79 s** |

Vòng lặp **dừng ở thế hệ 174** (điều kiện ②): `Trace` ghi `repeat = 99` ở thế hệ 174, và ở đầu vòng
kế tiếp `repeat` thành 100 ⇒ `repeat >= maxStagnation` ⇒ `break`. **Chưa dùng hết 1000 thế hệ.**

Dòng thế hệ 125 là một minh hoạ đắt giá: `P đạt 27, G đạt 28` **khác hoàn toàn** thế hệ 100
(`21 + 34`) nhưng **tổng vẫn 55** ⇒ cùng fitness 0,705556. Hàm stagnation chỉ nhìn **tổng điểm**,
nên quần thể vẫn đang tiến hoá mạnh về *chất* mà bộ đếm vẫn tính là "đứng yên".

**Chạy B — ép chạy tiếp** (`maxIterations = 400`, `maxStagnation = 400`, mọi thứ còn lại giữ nguyên,
cùng seed quần thể):

| Thế hệ | Fitness | P đạt | G đạt | N đạt | Thế hệ không cải thiện | elapsed |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0,629167 | 22/48 | 23/48 | 48/48 | 0 | 0,11 s |
| 7 | 0,677778 | 21/48 | 30/48 | 48/48 | 0 | 0,14 s |
| 21 | 0,706944 | 23/48 | 33/48 | 48/48 | 3 | 0,19 s |
| 51 | 0,706944 | 23/48 | 33/48 | 48/48 | 33 | 0,30 s |
| 101 | 0,706944 | 23/48 | 33/48 | 48/48 | 83 | 0,52 s |
| **151** | **0,787500** | 29/48 | 38/48 | 48/48 | 0 | 1,87 s |
| 201 | 0,852778 | 37/48 | 39/48 | 48/48 | 32 | 4,05 s |
| 251 | 0,859722 | 36/48 | 41/48 | 48/48 | 43 | 6,19 s |
| 301 | 0,881944 | 39/48 | 41/48 | 48/48 | 5 | 8,26 s |
| 351 | 0,888889 | 40/48 | 41/48 | 48/48 | 13 | 10,38 s |
| **400** | **0,904167** | 42/48 | 41/48 | 48/48 | 11 | **12,41 s** |

Bài học thực nghiệm rõ ràng: chạy A **dừng ở 0,705556 sau 0,79 s**; chạy B **vượt bình nguyên**
(quanh thế hệ ~130–150) rồi đạt **0,904167**. Nếu giữ nguyên `maxStagnation = 100`, dự án **mất luôn**
cơ hội cải thiện này — bình nguyên 100 thế hệ là **rất bình thường** với bài toán 48 lớp.

### 9.3 Nhánh "mồi nổ" và tính tái lập

* **Nhánh thích ứng** (`if repeat > maxRepeat / 100`) tăng gấp 3 số con lai mỗi thế hệ và +1 % xác suất
  lai ghép. Với `maxRepeat = 9999` mặc định, điều kiện chỉ thành từ `repeat = 100` — **đúng lúc**
  `repeat >= maxStagnation` (100) đã `break` ở ngay phía trên ⇒ **nhánh này không bao giờ chạy với
  tham số mặc định**. Phải hạ `maxRepeat` xuống dưới `100 × maxStagnation` (ví dụ 5000 ⇒ bật từ
  `repeat = 51`) nó mới có tác dụng.
* `run()` gọi `random.seed(round(time() * 1000))` ⇒ chỉ **Python RNG** (dùng ở `selection`/`replacement`)
  được mồi theo đồng hồ; **Schedule dùng `numpy.random`** và không chịu ảnh hưởng. Hai lần chạy vì thế
  cho hai kết quả khác nhau, kể cả khi mồi lại RNG — đây là lý do các bảng ở §9.2 là **một lần chạy thật**
  và cần được đọc như "phân phối điển hình", không phải kết quả tái lập từng chữ số.

---

## 10. Bước 9 — Đọc kết quả

### 10.1 Cá thể tốt nhất của chạy B: `fitness = 0,904167`

| Thành phần | Giá trị |
|---|---:|
| Cờ ĐẠT | 131 / 144 (sai: 6 P + 7 G + 0 N = 13) |
| Lớp bị phạt B | 4 ⇒ 0,8 điểm |
| `điểm = 131 − 0,8` | 130,2 |
| **fitness** | 130,2 / 144 = **0,90416667** ✔ (khớp `Schedule.fitness`) |
| Ô phòng còn trùng | 6 ô (3 cặp lớp) |
| Cặp giảng viên còn trùng | 5 cặp |
| Thời gian tiến hoá | 12,41 s / 400 thế hệ (≈ 31 ms/thế hệ, 3200 phép lai) |

**Ba cặp vi phạm P còn lại** — mỗi cặp nằm ở cùng phòng, cùng ngày, chồng nhau về offset:

| Cặp lớp | Ngày | Phòng | Offset chung |
|---|---:|---|---|
| 10 & 23 | 1 (T3) | Phòng 401 | 2 |
| 18 & 30 | 2 (T4) | Phòng 201 | 7, 8, 9 |
| 0 & 17 | 4 (T6) | Phòng 401 | 9, 10 |

**Các cặp vi phạm G còn lại** (cùng giảng viên, cùng ngày, trùng offset — phòng khác nhau):

| Giảng viên | Cặp lớp | Ngày | Offset chung |
|---|---|---:|---|
| Lê Quốc Cường | 7 & 33 | 4 (T6) | 1, 2, 3 |
| Lê Quốc Cường | 31 & 32 | 2 (T4) | 1, 2, 3, 4 |
| Nguyễn Văn An | 8 & 17 | 4 (T6) | 7, 8, 9, 10 |
| Nguyễn Văn An | 8 & 38 | 4 (T6) | 7, 8, 9, 10 |

**Bốn lớp còn dính phạt B**: lớp 13 (Cường, chạm `(0,2)`), lớp 19 (Cường, `(0,8)`),
lớp 26 (Dung, `(0,9)`), lớp 35 (An, `(0,0)`).

### 10.2 Đầu ra dạng bảng — ngày 0 (Thứ hai) của cá thể 0,904167

9 lớp được xếp trong 4 phòng, **không lớp nào chồng nghỉ trưa**:

| Phòng | offset → | Tiết | Môn | Lớp | GV |
|---|---|---|---|---:|---|
| Phòng 201 | 0–1 | 1–2 | Kỹ thuật phần mềm | 35 | Nguyễn Văn An ⚠ |
| Phòng 201 | 3–5 | 4–6 | Lập trình hướng đối tượng | 2 | Phạm Thị Dung |
| Phòng 201 | 9–12 | 9–12 | Công nghệ Web | 26 | Phạm Thị Dung ⚠ |
| Phòng 102 | 2–4 | 3–5 | Cơ sở dữ liệu | 13 | Lê Quốc Cường ⚠ |
| Phòng 102 | 8–11 | 8–11 | Mạng máy tính | 19 | Lê Quốc Cường ⚠ |
| Phòng 303 | 3–5 | 4–6 | Hệ điều hành | 46 | Vũ Anh Đức |
| Phòng 303 | 10–12 | 10–12 | Hệ điều hành | 24 | Nguyễn Văn An |
| Phòng 401 | 2–5 | 3–6 | Mạng máy tính | 20 | Lê Quốc Cường |
| Phòng 401 | 7–10 | 7–10 | Cấu trúc dữ liệu và giải thuật | 9 | Nguyễn Văn An |

⚠ = lớp đang bị phạt mềm B (xếp vào khung bận của chính giảng viên được gán).

### 10.3 Kết quả được trình bày ở đâu

Mỗi thế hệ, `Trace.trace()` chụp một ảnh vào `Trace._history` (`generation`, `fitness`, `criteria`,
`classes`, `professors`, `counts`, `elapsed`) rồi in ra console:

* **Console**: một dòng tóm tắt thế hệ + bảng `Đạt / tổng` cho P, G, N và một bảng riêng cho B.
* **HTML** (`HtmlOutput.py`): biểu đồ fitness theo thế hệ, lưới "qua các bước" (điều hướng bằng phím
  mũi tên), bảng thời khoá biểu theo phòng với các ô liền nhau được gộp bằng `rowspan`, badge tiêu chí,
  và ô bị phạt B được tô riêng.

---

## 11. Nhận xét: điểm mạnh, hạn chế, hướng cải tiến

### 11.1 Điểm mạnh của cách áp dụng GA ở đây

1. **Mã hoá "một lớp = một gen khối"** tránh được các nhiễm sắc thể *không hợp lệ về cấu trúc*: mỗi lớp
   luôn có đúng một vị trí, không cần sửa (repair) sau lai ghép.
2. **Tách rõ ràng giữa "gen" và "điểm"**: `Schedule` chỉ chứa gen + cờ + fitness; mọi chính sách tiến hoá
   (chọn, thay, elit, dừng) nằm trong `GeneticAlgorithm`. Đổi thuật toán không đụng tới mã hoá.
3. **`_slots` dạng mảng ô cho phép đếm trùng phòng trong O(1)** mỗi lớp; `Reservation.parse` dùng bảng nhớ
   tạm theo `numberOfRooms` để giải mã không phải chia lấy dư lặp lại.
4. **Elitism + thay thế một phần** bảo đảm `result` **đơn điệu không giảm** theo thế hệ — tính chất mà
   bảng §9.2 và §10 đều thấy rõ.
5. **Ràng buộc mềm B rẻ hơn ràng buộc cứng** (0,2 < 1,0) ⇒ GA luôn "ưu tiên hết sạch trùng lịch rồi mới
   tối ưu sự thoải mái của giảng viên", đúng thứ tự mong muốn về mặt nghiệp vụ.

### 11.2 Hạn chế (đo được, không phải suy đoán)

1. **Tiêu chí N hầu như không cạnh tranh.** `randomTime()` và `repair()` loại offset chồng nghỉ trưa
   *ngay khi sinh gen*, và `crossover` chỉcopy nguyên khối từ cha mẹ (cũng đã hợp lệ), nên trong mọi
   quần thể được khảo sát, **N luôn 48/48**. 1/3 mẫu số fitness (48 cờ trên 144) do đó **luôn là hằng số**
   và chỉ có tác dụng kéo giá trị fitness về 1,0. §9.2/§10 đều hiển thị cột này bằng 48.
2. **`maxStagnation = 100` cắt ngắn cuộc chạy một cách lãng phí.** Run A dừng ở 0,705556 sau 0,79 s
   trong khi run B — cùng quần thể khởi tạo — đạt 0,904167. Bình nguyên 100 thế hệ là chuyện bình
   thường với 48 lớp (xem các plateau 21→101 ở run B, dài 80 thế hệ mà chưa tới ngưỡng).
3. **Nhánh thích ứng ở §9.3 là mã chết** với tham số mặc định: `maxRepeat = 9999` khiến điều kiện bật
   *sau* `break` của stagnation.
4. **Fitness chỉ nhìn tổng điểm.** Ví dụ thế hệ 100 vs 125 của run A (21+34 và 27+28 đều = 55 sai):
   hai cá thể rất khác nhau về *bản chất* vi phạm nhưng không phân biệt được. Điều này làm nhiễu cả
   elitelist lẫn bộ đếm stagnation.
5. **Chọn cha mẹ hoàn toàn ngẫu nhiên** ⇒ tín hiệu chọn lọc yếu (chỉelit + cạnh tranh con-cha mới tạo
   áp lực). Đây là nguyên nhân chính của các plateau dài ở §9.2.
6. **Không có tiêu chí về tải giảng viên.** GA không penalise việc một người phải dạy quá nhiều tiết,
   dù tổng 160 tiết chia cho 5 người; lịch "0 vi phạm" vẫn có thể không dùng được trên thực tế.
7. **Lệch hệ quy chiếu khi đọc console.** Cột "Tiết" trong `Trace.detail`/`Trace.professors` in
   `res.Time + 1`, tức **số dòng bảng** (1–13, nghỉ trưa ở dòng 7), còn `PERIODS` và báo cáo HTML in
   **số tiết** (1–12, không đếm nghỉ trưa). Với một lớp chiều offset 7, console ghi "Tiết 8" trong khi
   HTML ghi "Tiết 7 — 13:00". Số liệu trong tài liệu này dùng **offset** để tránh nhầm.

### 11.3 Hướng cải tiến đề xuất

| Ưu tiên | Việc | Kỳ vọng |
|---|---|---|
| Cao | Tăng `maxStagnation` (500–2000) hoặc đổi stagnation thành "không cải thiện **số vi phạm cứng**" | Tránh cắt ngang plateau như run A |
| Cao | Đổi `selection` sang **tournament** (k = 3) hoặc roulette theo `fitness − min(fitness)` | Tăng áp lực chọn lọc, rút ngắn plateau |
| Trung bình | Bỏ cờ N khỏi `_criteria` **hoặc** cho `randomTime` sinh cả offset chồng trưa để N thực sự cạnh tranh | Mẫu số 96 thay vì 144, gradient "thật" hơn |
| Trung bình | Kích hoạt nhánh thích ứng bằng `maxRepeat` hợp lý (ví dụ 5000) hoặc thay bằng **restart** khi stagnation | Thoát bình nguyên |
| Trung bình | Thêm tiêu chí mềm: cân bằng số tiết giữa các giảng viên, phân tán lớp của một môn trong tuần | Lịch khả thi về nghiệp vụ |
| Thấp | Sửa cột "Tiết" trong console dùng `Constant.periodNumber()` | Đồng nhất với HTML |

---

## Phụ lục A — Tham số mặc định

Nguồn: `model/AlgorithmParameters.py` (`DEFAULTS` + `FIELDS`), `algorithm/GeneticAlgorithm.py`
và giá trị thực đo ở §9–§10.

| Tham số | Mặc định | Khoảng nhập | Ý nghĩa | Xác suất / hiệu lực **thật** |
|---|---:|---|---|---|
| `numberOfChromosomes` | 100 | 2–1000 | Kích thước quần thể `N` | — |
| `trackBest` | 5 | 1…`N−1` | Số cá thể elit không bao giờ bị ghi đè | — |
| `replaceByGeneration` | 8 | 1…`N−trackBest` | Số con lai cài vào quần thể mỗi thế hệ | 8 % quần thể trẻ hoá/thế hệ |
| `numberOfCrossoverPoints` | 2 | 1…min(50, số lớp) | Số điểm cắt ⇒ 3 đoạn gen | — |
| `mutationSize` | 2 | 1…số lớp | Số lớp bị dời khi đột biến kích hoạt | — |
| `crossoverProbability` | 80 | 0–100 | Ngưỡng cổng lai ghép | **(80+1)/100 = 81 %** |
| `mutationProbability` | 3 | 0–100 | Ngưỡng cổng đột biến | **(3+1)/100 = 4 %** |
| `maxIterations` | 1000 | 1–100000 | Trần số thế hệ | — |
| `maxStagnation` | 100 | 1–100000 | Số thế hệ fitness không đổi thì dừng | `|Δ| ≤ 1e-7` |
| `minFitness` | 0.999 | 0.0–1.0 | Đích dừng sớm | so sánh **nghiêm** `>` |
| `maxRepeat` | 9999 | *(đối số `run()`)* | Ngưỡng bật nhánh thích ứng | `repeat > maxRepeat/100` ⇒ **mã chết** mặc định |

Trọng số chấm điểm: `Criteria.weights = [1.0, 1.0, 1.0]` cho (P, G, N), `Criteria.busyPenalty = 0.2` cho B.

Ba bất biến được `normalize()` ép buộc: `N ≥ 2`; `1 ≤ trackBest ≤ N − 1`;
`1 ≤ replaceByGeneration ≤ N − trackBest`; ngoài ra `numberOfCrossoverPoints ≤ số lớp`
(nếu vượt, vòng chọn điểm cắt lặp vô hạn) và `mutationSize ≤ số lớp`.

---

## Phụ lục B — Cách chạy

```bash
# Chạy một lần, in console + xuất báo cáo HTML tĩnh
python ConsoleApp.py GaSchedule.json --no-serve

# Chạy kèm máy chủ /rerun để chỉnh tham số ngay trên báo cáo
python ConsoleApp.py GaSchedule.json
```

Quy trình bên trong `ConsoleApp.run_schedule`:

```
Trace.reset()  →  Configuration().parseFile(json)  →  Trace.input(...)
   →  GeneticAlgorithm(configuration, **tham_số)  →  alg.run()
   →  Trace.get_history()  →  HtmlOutput(...).getDocument()  →  ghi tệp .htm
```

`Trace.reset()` **phải** đứng trước `alg.run()` vì mọi cột giây trong bảng thế hệ và trục thời gian của
biểu đồ fitness tính từ mốc này.

---

## Phụ lục C — Tái tạo các ví dụ

Kết quả của **vòng tiến hoá** phụ thuộc RNG mồi theo đồng hồ (§9.3), nên các bảng §9–§10 là *một lần
chạy thật*. Ngược lại, **mọi ví dụ về một cá thể / một phép toán** dưới đây tái lập được 100 % vì
`Schedule` dùng `numpy.random` và ta mồi trước khi gọi:

```python
import sys, os, numpy as np, random
sys.path.insert(0, os.getcwd())          # chạy từ thư mục GA
import numpy as np
from model.Configuration import Configuration
from model.Schedule import Schedule

conf = Configuration(); conf.parseFile("GaSchedule.json")
proto = Schedule(conf)

# §2.3 + §3.2 + §3.3 + §4.2 — cá thể đầu và quần thể khởi tạo
np.random.seed(7); random.seed(7)
pop = [proto.makeNewFromPrototype() for _ in range(100)]
ch0 = pop[0]
print(ch0.fitness, ch0.classes[conf.courseClasses[0]])      # 0.5041666…, 230

# §6.2 — lai ghép
np.random.seed(1)
dad = proto.makeNewFromPrototype(); mom = proto.makeNewFromPrototype()
kid = dad.crossover(mom, 2, 100)        # p = 100 ⇒ cổng luôn cho qua
print(dad.fitness, mom.fitness, kid.fitness)                 # 0.543056 / 0.583333 / 0.611111

# §7.2 — đột biến
np.random.seed(101); m = proto.makeNewFromPrototype()
before = dict(m.classes), dict(m.professors), m.fitness
np.random.seed(102); m.mutation(2, 100)
print(before[2], m.fitness)                                   # 0.643056 → 0.656944
```

| Ví dụ | Seed quần thể/gen | Seed toán tử | Ghi chú |
|---|---|---|---|
| §2.3, §3.2–3.3, §4.2 | `np.random.seed(7)` | — | `random.seed(7)` chỉ ảnh hưởng `selection`/`replacement` |
| §6.2 | `np.random.seed(1)` | cùng seed (cùng dòng RNG) | `crossoverProbability = 100` để chắc chắn lai |
| §7.2 | `np.random.seed(101)` | `np.random.seed(102)` | `mutationProbability = 100` để chắc chắn đột biến |
| §9.2 run A | `np.random.seed(2026)` | đồng hồ | `alg.run()` dùng mặc định |
| §9.2 run B, §10 | `np.random.seed(2026)` | đồng hồ | `maxIterations = 400`, `maxStagnation = 400` |

---

## Phụ lục D — Ánh xạ khái niệm → mã nguồn

| Khái niệm GA kinh điển | Trong dự án này | Vị trí |
|---|---|---|
| Nhiễm sắc thể | `Schedule` (một phương án xếp lịch đầy đủ) | `model/Schedule.py` |
| Gen vị trí | `Schedule._classes[lop] = index ô mở đầu` | `model/Schedule.py` |
| Gen giảng viên | `Schedule._professors[lop]` | `model/Schedule.py` |
| Giải mã gen ⇄ toạ độ | `Reservation.getHashCode` / `Reservation.parse` | `model/Reservation.py` |
| Hàm mục tiêu | `Schedule.calculateFitness` | `model/Schedule.py` |
| Ràng buộc | `Criteria.isRoomOverlapped` / `isOverlappedProf` / `isInLunchBreak` | `model/Criteria.py` |
| Khởi tạo quần thể | `GeneticAlgorithm.initialize` | `algorithm/GeneticAlgorithm.py` |
| Chọn cha mẹ | `GeneticAlgorithm.selection` (uniform random pairing) | `algorithm/GeneticAlgorithm.py` |
| Lai ghép | `Schedule.crossover` (multi-point theo thứ tự lớp) | `model/Schedule.py` |
| Đột biến | `Schedule.mutation` + `Schedule.repair` | `model/Schedule.py` |
| Thay thế + elitism | `GeneticAlgorithm.replacement` + `addToBest` / `isInBest` | `algorithm/GeneticAlgorithm.py` |
| Vòng tiến hoá & dừng | `GeneticAlgorithm.run` | `algorithm/GeneticAlgorithm.py` |
| Theo dõi & báo cáo | `Trace` (console + `_history`), `HtmlOutput` (biểu đồ, lưới bước, TKB) | `Trace.py`, `HtmlOutput.py` |
| Tham số | `AlgorithmParameters.DEFAULTS` / `FIELDS` / `normalize` | `model/AlgorithmParameters.py` |

*Tài liệu được cập nhật cùng bộ mã chú thích giải thuật (docstring + công thức) trong các tệp
`algorithm/GeneticAlgorithm.py`, `model/Schedule.py`, `model/Criteria.py`, `model/Reservation.py`,
`model/Constant.py` và `model/AlgorithmParameters.py`.*
