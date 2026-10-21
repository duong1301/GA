# Giải thuật GA trong GASchedule.py — tài liệu chi tiết

> Tài liệu này chỉ trình bày **thuật toán di truyền đơn mục tiêu (Genetic Algorithm — GA)** đang được dùng trong `ConsoleApp.py`, tức lớp `algorithm/GeneticAlgorithm.py` và các phần của `model/Schedule.py`, `model/Criteria.py`, `model/Reservation.py` mà GA gọi tới.
>
> Các thuật toán khác trong thư mục `algorithm/` (NSGA-II, NSGA-III, AMGA2, CSO, FPA, DLBA, GAQPSO, NRGA…) không thuộc phạm vi tài liệu này.

---

## Mục lục

1. [Tổng quan luồng chạy](#1-tổng-quan-luồng-chạy)
2. [Mô hình bài toán và công thức mã hóa](#2-mô-hình-bài-toán-và-công-thức-mã-hóa)
3. [Công thức tính fitness](#3-công-thức-tính-fitness)
4. [Các tham số và cách chuẩn hóa](#4-các-tham-số-và-cách-chuẩn-hóa)
5. [Các bước thực hiện chi tiết](#5-các-bước-thực-hiện-chi-tiết)
6. [Pseudocode đầy đủ](#6-pseudocode-đầy-đủ)
7. [Ví dụ tính tay](#7-ví-dụ-tính-tay)
8. [Độ phức tạp](#8-độ-phức-tạp)
9. [Những điểm cần lưu ý khi đọc code](#9-những-điểm-cần-lưu-ý-khi-đọc-code)
10. [Bảng đối chiếu code](#10-bảng-đối-chiếu-code)
11. [Tóm tắt công thức cốt lõi](#11-tóm-tắt-công-thức-cốt-lõi)
12. [Đọc nhanh trong 10 dòng](#12-đọc-nhanh-trong-10-dòng)

---

## 1. Tổng quan luồng chạy

GA trong project là GA **một mục tiêu**, dùng giá trị `fitness` (một số thực trong khoảng 0..1; với bộ trọng số hiện tại là 0.125..1) để đánh giá và chọn lọc. Luồng tổng quát:

```text
Đọc file JSON
    ↓
Tạo Configuration: giảng viên, môn học, phòng, nhóm SV, lớp học phần
    ↓
Tạo Schedule "prototype" rỗng
    ↓
Khởi tạo quần thể: mỗi cá thể là một thời khóa biểu ngẫu nhiên
    ↓
Lặp từng thế hệ:
    ├─ Lấy cá thể tốt nhất hiện tại
    ├─ Kiểm tra điều kiện dừng
    ├─ Chọn ngẫu nhiên các cặp cha mẹ
    ├─ Lai ghép → tạo con
    ├─ Đột biến con
    ├─ Thay con vào quần thể (trừ nhóm tốt nhất)
    ├─ Cập nhật nhóm cá thể tốt nhất
    └─ Ghi nhận tiến trình
    ↓
Trả về cá thể tốt nhất (alg.result)
```

Các file tham gia:

| File | Vai trò trong GA |
|---|---|
| `algorithm/GeneticAlgorithm.py` | Vòng lặp tiến hóa, chọn cha mẹ, thay thế, nhóm tốt nhất |
| `model/Schedule.py` | Nhiễm sắc thể: khởi tạo, lai ghép, đột biến, tính fitness |
| `model/Criteria.py` | Bốn tiêu chí đánh giá: phòng, chỗ ngồi, giảng viên, nhóm SV |
| `model/Reservation.py` | Công thức mã hóa `(ngày, tiết, phòng)` thành chỉ số ô |
| `model/Constant.py` | `DAYS_NUM = 5`, `DAY_HOURS = 12` |
| `model/AlgorithmParameters.py` | Giá trị mặc định và chuẩn hóa tham số |
| `Trace.py` | In tiến trình, không ảnh hưởng kết quả thuật toán |

---

## 2. Mô hình bài toán và công thức mã hóa

### 2.1. Không gian thời gian — không gian

Gọi:

| Ký hiệu | Ý nghĩa | Giá trị / nguồn |
|---|---|---|
| `D` | Số ngày làm việc | `Constant.DAYS_NUM = 5` |
| `H` | Số tiết mỗi ngày | `Constant.DAY_HOURS = 12` |
| `R` | Số phòng học | `configuration.numberOfRooms` |
| `N` | Số lớp học phần | `configuration.numberOfCourseClasses` |
| `dur(c)` | Thời lượng của lớp `c` | `CourseClass.Duration` |
| `seats(c)` | Số chỗ lớp `c` cần | tổng số SV của các nhóm trong lớp |

Tổng số ô thời gian — không gian:

```text
S = D × H × R
```

Mỗi ô tương ứng với **một tiết** trong **một phòng** vào **một ngày**.

### 2.2. Công thức chỉ số ô

Code dùng công thức trong `Reservation.getHashCode`:

```text
idx(d, t, r) = d × H × R + r × H + t
```

Trong đó:

```text
d ∈ {0, 1, ..., D-1}      # ngày
t ∈ {0, 1, ..., H-1}      # tiết trong ngày
r ∈ {0, 1, ..., R-1}      # phòng
```

Công thức giải mã ngược (`Reservation.parse`):

```text
d = idx // (H × R)
rem = idx %  (H × R)
r = rem // H
t = rem %  H
```

Ví dụ với `D = 5`, `H = 12`, `R = 2`:

```text
idx(3, 4, 1) = 3 × 12 × 2 + 1 × 12 + 4 = 88
```

Giải mã:

```text
d   = 88 // 24 = 3
rem = 88 % 24  = 16
r   = 16 // 12 = 1
t   = 16 % 12  = 4
```

### 2.3. Cách một lớp chiếm ô

Một lớp `c` có thời lượng `dur(c)` được đặt tại `(d, t, r)` sẽ chiếm `dur(c)` ô liên tiếp:

```text
p = idx(d, t, r)
c chiếm các ô: p, p+1, ..., p+dur(c)-1
```

Điều kiện để lớp kết thúc trong ngày:

```text
t + dur(c) ≤ H
⇔ t ∈ {0, 1, ..., H - dur(c) - 1}
```

Code lấy ngẫu nhiên:

```python
time = randrange(DAY_HOURS - dur)
```

tức `t` chạy từ `0` đến `H - dur - 1`. Ví dụ `H = 12`, `dur = 2` thì `t ∈ {0..9}`; lớp chiếm tiết `t` và `t+1`, tiết cuối cùng là 11.

> **Lưu ý:** với lớp 1 tiết, `randrange(12 - 1) = randrange(11)` cho `t ∈ {0..10}`, nên tiết cuối `t = 11` không bao giờ được chọn làm **tiết bắt đầu**. Đây là hệ quả của công thức `H - dur`, không phải lỗi riêng của GA.

### 2.4. Hai cách biểu diễn nhiễm sắc thể

Mỗi `Schedule` lưu **hai cấu trúc song song**:

#### (a) Bảng gen `_classes`

```python
self._classes: dict[CourseClass, int]
```

- Khóa: đối tượng lớp học phần `c`.
- Giá trị: chỉ số ô bắt đầu `p = idx(d, t, r)`.

Đây là phần "gen" thực sự: mỗi lớp có một gen là vị trí bắt đầu.

#### (b) Bảng ô `_slots`

```python
self._slots: list[list[CourseClass]]
```

- Độ dài `S = D × H × R`.
- `slots[p]` chứa danh sách các lớp đang chiếm ô `p`.

Khi lớp `c` ở vị trí `p`:

```text
slots[p], slots[p+1], ..., slots[p+dur(c)-1]  đều chứa c
```

Hai cấu trúc này là hai góc nhìn của cùng một lời giải:

- `_classes` dùng để biết lớp nằm ở đâu, phục vụ di chuyển / sao chép gen.
- `_slots` dùng để kiểm tra trùng phòng, trùng giảng viên, trùng nhóm SV rất nhanh.

**Bất biến quan trọng:** trong một nhiễm sắc thể hợp lệ, mỗi lớp `c` xuất hiện đúng một lần trong `_classes`, và đúng `dur(c)` lần trong `_slots` — mỗi lần ở một ô liên tiếp.

### 2.5. Ví dụ minh họa

Giả sử `D = 5`, `H = 12`, `R = 2`, lớp `c` có `dur(c) = 3`, đặt tại ngày 3, tiết 4, phòng 1:

```text
p = 3×24 + 1×12 + 4 = 88
c chiếm slots[88], slots[89], slots[90]
classes[c] = 88
```

Nếu sau đó đột biến chuyển `c` sang ngày 2, tiết 5, phòng 0:

```text
p' = 2×24 + 0×12 + 5 = 53
```

Code sẽ:

1. Xóa `c` khỏi `slots[88]`, `slots[89]`, `slots[90]`.
2. Thêm `c` vào `slots[53]`, `slots[54]`, `slots[55]`.
3. Gán `classes[c] = 53`.

---

## 3. Công thức tính fitness

### 3.1. Bốn tiêu chí

Với mỗi lớp `c`, định nghĩa bốn biến nhị phân:

| Biến | Tiêu chí | Bằng 1 khi | Bằng 0 khi |
|---|---|---|---|
| `P_c` | Phòng không trùng | Không lớp nào khác chiếm cùng ô phòng/ngày/tiết | Có ít nhất một ô bị lớp khác chiếm |
| `C_c` | Phòng đủ chỗ | `seats(room(c)) ≥ seats(c)` | Phòng nhỏ hơn số SV cần |
| `G_c` | Giảng viên không trùng | Không lớp khác cùng giảng viên trùng giờ | Có lớp khác cùng giảng viên trùng giờ |
| `S_c` | Nhóm SV không trùng | Không lớp khác có nhóm SV giao nhau trùng giờ | Có ít nhất một nhóm SV bị trùng |

Trọng số phạt trong `model/Criteria.py`:

```python
weights = [1.0, 0.5, 1.0, 1.0]
#           P    C    G    S
```

Ý nghĩa:

- `w_i = 0`: vi phạm không bị phạt.
- `w_i = 1`: vi phạm mất trọn 1 điểm của tiêu chí.
- `w_C = 0.5`: vi phạm tiêu chí chỗ ngồi chỉ mất 0.5 điểm.

### 3.2. Công thức điểm và fitness

Với mỗi lớp `c` và tiêu chí `i`:

```text
điểm(c, i) = 1                 nếu tiêu chí đạt
             1 - w_i           nếu tiêu chí vi phạm
```

Tổng điểm:

```text
score = Σ_c Σ_i điểm(c, i)
```

Gọi `V_i` là **số lớp vi phạm tiêu chí `i`**:

```text
V_i = số lớp c mà tiêu chí i của c không đạt
```

Khi đó:

```text
score = Σ_c Σ_i [1 - w_i × (1 - đạt(c,i))]
      = 4N - Σ_i w_i × V_i
```

và fitness:

```text
F = score / (4N)
  = 1 - (w_P×V_P + w_C×V_C + w_G×V_G + w_S×V_S) / (4N)
```

Thay trọng số thực tế:

```text
F = 1 - (V_P + 0.5×V_C + V_G + V_S) / (4N)
```

Trong đó `4N` chính là `len(self._criteria)` vì mỗi lớp có 4 tiêu chí.

**Tính chất:**

```text
0.125 ≤ F ≤ 1        (với bộ trọng số hiện tại [1.0, 0.5, 1.0, 1.0])
F = 1     ⇔  V_P = V_C = V_G = V_S = 0  (lịch hoàn hảo)
F = 0.125 ⇔  mọi lớp đều vi phạm cả 4 tiêu chí
```

Vì tiêu chí `C` chỉ bị trừ `0.5` điểm, mỗi lớp luôn còn ít nhất `0.5` điểm, nên fitness không thể về 0 với bộ trọng số hiện tại. Nếu tất cả trọng số đều bằng `1.0` thì mới có `0 ≤ F ≤ 1`.

### 3.3. Cách code tính fitness

`Schedule.calculateFitness()` làm đúng các bước sau:

```text
1. V = [0, 0, 0, 0]          # V_P, V_C, V_G, V_S
2. score = 0
3. Với từng lớp c trong _classes:
     a. Giải mã vị trí p → (d, t, r)
     b. P = không trùng phòng
     c. C = phòng đủ chỗ
     d. G, S = kiểm tra trùng giảng viên / nhóm SV
     e. Với i = 0..3:
          nếu tiêu chí i đạt: score += 1
          ngược lại:          score += 1 - weights[i]
                              V[i] += 1
4. F = score / (4N)
```

Trong code, `V` chính là `self._objectives`, còn `4N` là `len(self._criteria)`.

### 3.4. Kiểm tra từng tiêu chí trong code

#### (a) Trùng phòng — `P`

`Criteria.isRoomOverlapped(slots, reservation, dur)`:

```python
p = hash(reservation)
for k in range(dur):
    if len(slots[p + k]) > 1:
        return True
return False
```

Công thức:

```text
P_c = 1  ⇔  ∀ k ∈ [0, dur(c)-1]: |slots[p + k]| = 1
```

Nếu một ô có từ 2 lớp trở lên, **cả hai lớp** đều bị `P = 0`, vì mỗi lớp khi kiểm tra đều thấy ô đó có nhiều hơn 1 phần tử.

#### (b) Đủ chỗ — `C`

`Criteria.isSeatEnough(r, cc)`:

```python
return r.NumberOfSeats >= cc.NumberOfSeats
```

với:

```text
seats(c) = Σ_{g ∈ groups(c)} g.NumberOfStudents
```

`NumberOfSeats` được tính trong `CourseClass.__init__` bằng cách cộng số SV của các nhóm trong lớp.

Ví dụ dữ liệu mẫu:

- Lớp có nhóm 1 (19 SV) + nhóm 2 (19 SV) → cần 38 chỗ.
- Phòng 201 có 24 chỗ → `C = 0`.
- Phòng 102 có 60 chỗ → `C = 1`.

#### (c) Trùng giảng viên — `G` và trùng nhóm SV — `S`

`Criteria.isOverlappedProfStudentGrp(slots, cc, numberOfRooms, timeId)`:

```text
timeId = day × (H × R) + time      # ô bắt đầu của phòng 0, đúng ngày và tiết
for mỗi phòng (numberOfRooms lần):
    for j từ timeId đến timeId + dur - 1:
        for từng lớp cc1 trong slots[j]:
            nếu cc1 != cc:
                nếu cc.professorOverlaps(cc1): po = True
                nếu cc.groupsOverlap(cc1):     go = True
    timeId += H                     # nhảy sang phòng kế tiếp
```

Vì `timeId` ban đầu là ô của **phòng 0**, mỗi lần cộng `H = 12` là nhảy sang **phòng kế tiếp** trong cùng ngày. Vì vậy vòng lặp kiểm tra **tất cả các phòng** ở cùng ngày, cùng khung giờ.

Công thức:

```text
G_c = 1  ⇔  không tồn tại c' ≠ c và k, k' sao cho:
             cùng ngày, giờ(c,k) = giờ(c',k'), và professor(c) = professor(c')
```

```text
S_c = 1  ⇔  không tồn tại c' ≠ c và k, k' sao cho:
             cùng ngày, giờ(c,k) = giờ(c',k'), và groups(c) ∩ groups(c') ≠ ∅
```

Trong đó `giờ(c,k)` là tiết thứ `k` của lớp `c`.

`professorOverlaps` so sánh giảng viên theo `Id`; `groupsOverlap` kiểm tra giao của hai tập nhóm SV.

### 3.5. Ví dụ tính fitness

Giả sử `R = 2`, `N = 1`, lớp `c` có `dur = 2`, cần 38 chỗ, đặt ở phòng 0 (24 chỗ), ngày 0, tiết 0. Không có lớp nào khác.

```text
p = 0×24 + 0×12 + 0 = 0
c chiếm slots[0], slots[1]
```

| Tiêu chí | Kết quả | Điểm |
|---|---|---|
| `P` | Mỗi ô chỉ có `c` | 1 |
| `C` | 24 < 38 | 1 - 0.5 = 0.5 |
| `G` | Không có lớp khác | 1 |
| `S` | Không có lớp khác | 1 |

```text
score = 1 + 0.5 + 1 + 1 = 3.5
F = 3.5 / (4×1) = 0.875
```

Theo công thức rút gọn:

```text
V = [V_P, V_C, V_G, V_S] = [0, 1, 0, 0]
F = 1 - (0 + 0.5×1 + 0 + 0) / 4 = 1 - 0.125 = 0.875
```

Nếu thêm lớp `c2` cùng giảng viên, cùng nhóm SV, cùng ngày và tiết nhưng ở phòng 1 (60 chỗ):

| Lớp | P | C | G | S | Điểm |
|---|---|---|---|---|---|
| `c` | 1 | 0 | 0 | 0 | 1 + 0.5 = 1.5 |
| `c2` | 1 | 1 | 0 | 0 | 1 + 1 = 2.0 |

```text
score = 1.5 + 2.0 = 3.5
F = 3.5 / (4×2) = 0.4375
V = [0, 1, 2, 2]
F = 1 - (0 + 0.5 + 2 + 2) / 8 = 1 - 4.5/8 = 0.4375
```

> Nhận xét: một cặp lớp trùng giảng viên làm **cả hai** lớp bị `G = 0`, nên `V_G` tăng 2. Tương tự với `S` và `P`. `V_i` đếm **số lớp vi phạm**, không phải số cặp vi phạm.

### 3.6. Liên hệ với dữ liệu mẫu `GaSchedule.json`

Dữ liệu mẫu có:

```text
N = 27 lớp
R = 2 phòng
D = 5 ngày
H = 12 tiết
4N = 108
```

Vì vậy:

```text
F = 1 - (V_P + 0.5×V_C + V_G + V_S) / 108
```

Mức giảm fitness khi vi phạm:

| Vi phạm | Mức giảm |
|---|---|
| 1 lớp trùng phòng (`P`) | `1/108 ≈ 0.00926` |
| 1 lớp thiếu chỗ (`C`) | `0.5/108 ≈ 0.00463` |
| 1 lớp trùng giảng viên (`G`) | `1/108 ≈ 0.00926` |
| 1 lớp trùng nhóm SV (`S`) | `1/108 ≈ 0.00926` |

Với `N = 27`, điểm cao nhất khi vẫn còn khiếm khuyết (chỉ 1 lỗi `C`) là:

```text
score = 108 - 0.5 = 107.5
F = 107.5 / 108 ≈ 0.99537 < 0.999
```

Do đó ngưỡng dừng mặc định `minFitness = 0.999` chỉ đạt được khi lịch **hoàn hảo** (`F = 1.0`). Đây là lý do với dữ liệu mẫu, GA thường chạy tới khi hết `maxStagnation` hoặc `maxIterations` chứ không dừng sớm vì fitness.

---

## 4. Các tham số và cách chuẩn hóa

### 4.1. Giá trị mặc định

Từ `model/AlgorithmParameters.py` và constructor của `GeneticAlgorithm`:

| Tham số | Ký hiệu | Mặc định | Ý nghĩa |
|---|---:|---:|---|
| `numberOfChromosomes` | `n` | 100 | Số cá thể trong quần thể |
| `trackBest` | `B` | 5 | Số cá thể tốt nhất được giữ lại, không bị thay thế |
| `replaceByGeneration` | `Rgen` | 8 | Số cá thể bị thay bằng con mỗi thế hệ |
| `numberOfCrossoverPoints` | `K` | 2 | Số điểm cắt khi lai ghép |
| `mutationSize` | `M` | 2 | Số lần di chuyển lớp trong một lần đột biến |
| `crossoverProbability` | `Pc` | 80 | Xác suất lai ghép (tham số danh nghĩa) |
| `mutationProbability` | `Pm` | 3 | Xác suất đột biến (tham số danh nghĩa) |
| `maxIterations` | `Gmax` | 1000 | Số thế hệ tối đa |
| `maxStagnation` | `Smax` | 100 | Dừng sau `Smax` thế hệ liên tiếp không cải thiện |
| `minFitness` | — | 0.999 | Ngưỡng fitness để dừng sớm |
| `maxRepeat` | — | 9999 | Tham số của `run()`, dùng cho cơ chế tăng cường khi trì trệ |

### 4.2. Chuẩn hóa trong code

`GeneticAlgorithm.initAlgorithm` và `__init__`:

```text
n    = max(2, int(n))
B    = min(max(1, int(B)), n - 1)
Rgen = max(1, int(Rgen))
nếu Rgen > n - B: Rgen = n - B
Pc   = max(0, min(100, int(Pc)))
Pm   = max(0, min(100, int(Pm)))
K    = max(1, int(K))
M    = max(1, int(M))
Gmax = max(1, int(Gmax))
Smax = max(1, int(Smax))
```

Ý nghĩa:

- `B ≤ n - 1`: luôn chừa ít nhất 1 vị trí cho con.
- `Rgen ≤ n - B`: không thay thế nhiều hơn số cá thể không thuộc nhóm tốt.
- `K`, `M` ít nhất là 1.

`AlgorithmParameters.normalize` còn giới hạn thêm:

```text
K ≤ N   (số lớp học phần)
M ≤ N
```

để tránh chọn điểm cắt hoặc số lần đột biến vượt quá số gen.

### 4.3. Xác suất thực thi thực tế

Đây là điểm rất dễ đọc sai. Trong `Schedule.crossover` và `Schedule.mutation`:

```python
if randrange(100) > probability:
    # bỏ qua
```

`randrange(100)` của NumPy sinh số nguyên `0..99`. Điều kiện bỏ qua là `x > p`, nên **thực thi** khi:

```text
x ≤ p
```

Số giá trị `x` thỏa mãn là `p + 1` (với `p < 100`). Vì vậy xác suất thực thi thực tế là:

```text
P_thực_thi(p) = min(1, (p + 1) / 100)
```

| Tham số danh nghĩa | Xác suất thực thi |
|---:|---:|
| `Pc = 80` | `81/100 = 81%` |
| `Pm = 3` | `4/100 = 4%` |
| `Pc = 0` | `1/100 = 1%` |
| `Pm = 0` | `1/100 = 1%` |
| `Pc = 100` | `100%` |

> Nếu mô tả thuật toán theo ý định thiết kế, ta nói xác suất là `Pc%` và `Pm%`. Nếu mô tả **đúng code hiện tại**, phải dùng `(p+1)%`. Tài liệu này ưu tiên mô tả đúng code.

---

## 5. Các bước thực hiện chi tiết

### Bước 0 — Đọc cấu hình và tạo prototype

**Mục tiêu:** chuyển dữ liệu JSON thành các đối tượng bài toán.

Code:

```python
configuration = Configuration()
configuration.parseFile(file_name)
```

Kết quả:

```text
configuration.numberOfRooms          = R
configuration.numberOfCourseClasses  = N
configuration.courseClasses          = [c0, c1, ..., c(N-1)]
```

Sau đó `GeneticAlgorithm.__init__` tạo:

```python
Schedule(configuration)
```

Đây là **prototype rỗng**: chưa có lớp nào được xếp, dùng làm khuôn để sinh nhiễm sắc thể mới.

---

### Bước 1 — Khởi tạo quần thể

**Công thức:** với mỗi cá thể `k = 1..n`, với mỗi lớp `c`:

```text
d ~ Uniform{0, ..., D-1}
r ~ Uniform{0, ..., R-1}
t ~ Uniform{0, ..., H - dur(c) - 1}

p = d×H×R + r×H + t
slots[p .. p+dur(c)-1] ← slots[...] ∪ {c}
classes[c] = p
```

**Code:** `GeneticAlgorithm.initialize` gọi `prototype.makeNewFromPrototype()` cho từng vị trí quần thể.

`Schedule.makeNewFromPrototype`:

```python
new_chromosome = self.copy(self, True)   # Schedule rỗng
for c in configuration.courseClasses:
    dur = c.Duration
    day  = randrange(D)
    room = randrange(R)
    time = randrange(H - dur)
    reservation = Reservation.getReservation(R, day, time, room)
    p = hash(reservation)
    for i in range(dur - 1, -1, -1):
        new_chromosome_slots[p + i].append(c)
    new_chromosome_classes[c] = p
new_chromosome.calculateFitness()
```

**Đầu ra:** `n` nhiễm sắc thể ngẫu nhiên, mỗi nhiễm sắc thể đã có fitness.

**Lưu ý:**

- Các lớp được xếp **hoàn toàn ngẫu nhiên**, không kiểm tra trùng.
- Vì vậy thế hệ 0 thường có fitness thấp.
- `randrange` ở đây là `numpy.random.randint`, không phải `random.randrange`.
- Trong `initialize` của GA, dòng `addToBest(i)` bị **chú thích**, nên nhóm tốt nhất chưa được nạp từ quần thể ban đầu. Điều này được phân tích ở mục 9.

---

### Bước 2 — Đánh giá fitness

**Công thức:**

```text
F = 1 - (V_P + 0.5×V_C + V_G + V_S) / (4N)
```

**Code:** `Schedule.calculateFitness()` (xem mục 3.3).

**Khi nào được gọi?**

- Cuối `makeNewFromPrototype` — sau khi khởi tạo.
- Cuối `Schedule.crossover` — sau khi ghép gen.
- Cuối `Schedule.mutation` — sau khi di chuyển lớp, nhưng **chỉ khi** đột biến thực sự xảy ra.
- Không gọi lại nếu đột biến bị bỏ qua do xác suất.

---

### Bước 3 — Bắt đầu vòng lặp thế hệ và kiểm tra dừng

**Code:** `GeneticAlgorithm.run`.

Mỗi vòng lặp làm theo thứ tự:

```text
1. best = self.result
2. nếu best.fitness > minFitness: dừng
3. difference = |best.fitness - lastBestFit|
   nếu difference <= 1e-7: repeat += 1
   ngược lại:              repeat = 0
4. nếu repeat >= maxStagnation: dừng
5. nếu repeat > maxRepeat / 100:
       random.seed(time)
       replaceByGeneration = min(3 × replaceByGeneration, n - B)
       crossoverProbability += 1
6. replacement(...)
7. lastBestFit = best.fitness
8. Trace.trace(...)
9. currentGeneration += 1
```

**Giải thích từng điều kiện:**

#### (a) Dừng khi đạt fitness mục tiêu

```python
if best.fitness > minFitness:
    break
```

- Dùng `>` chứ không phải `>=`.
- Mặc định `minFitness = 0.999`.
- Với `N = 27`, chỉ `F = 1.0` mới thỏa `F > 0.999` (vì `107.5/108 ≈ 0.99537`).

#### (b) Đếm số thế hệ trì trệ

```python
difference = abs(best.fitness - lastBestFit)
if difference <= 0.0000001:
    repeat += 1
else:
    repeat = 0
```

- `repeat` là số thế hệ liên tiếp fitness tốt nhất **không thay đổi** (chênh lệch ≤ `1e-7`).
- `lastBestFit` ban đầu bằng `0.0`.
- `best` được lấy **trước** khi thay thế ở thế hệ hiện tại, nên `lastBestFit` là fitness tốt nhất của đầu thế hệ trước.

#### (c) Dừng khi trì trệ quá lâu

```python
if repeat >= maxStagnation:
    break
```

- Mặc định dừng sau 100 thế hệ liên tiếp không cải thiện.
- Đây là điều kiện dừng chính khi `minFitness` quá cao.

#### (d) Tăng cường khi trì trệ rất lâu

```python
if repeat > (maxRepeat / 100):
    random.seed(round(time() * 1000))
    self.set_replace_by_generation(self._replaceByGeneration * 3)
    self._crossoverProbability += 1
```

- `maxRepeat` mặc định `9999`, nên `maxRepeat / 100 = 99.99`.
- Điều kiện `repeat > 99.99` chỉ đúng khi `repeat >= 100`.
- Khi đó:
  - đặt lại seed cho `random` (không ảnh hưởng NumPy);
  - tăng số cá thể bị thay thế lên gấp 3 (sau đó bị chặn bởi `n - B`);
  - tăng `crossoverProbability` thêm 1.

> **Lưu ý:** với `maxStagnation = 100` (mặc định), vòng lặp dừng ở `repeat = 100` **trước khi** nhánh tăng cường chạy. Vì vậy nhánh này chỉ có tác dụng nếu `maxStagnation > 100`.

---

### Bước 4 — Chọn cha mẹ

**Code:** `GeneticAlgorithm.selection`.

```python
def selection(self, population):
    length_chromosomes = len(population)
    return (population[randrange(32768) % length_chromosomes],
            population[randrange(32768) % length_chromosomes])
```

**Công thức:**

```text
i1 = randrange(32768) mod n
i2 = randrange(32768) mod n
parent1 = population[i1]
parent2 = population[i2]
```

**Đặc điểm:**

- Chọn **ngẫu nhiên đều** (uniform random), không dùng tournament, không dùng roulette wheel.
- Có hoàn lại: `i1` có thể bằng `i2`, tức có thể chọn cùng một cá thể làm cả cha và mẹ.
- `randrange` ở đây là `random.randrange` của Python (khác với NumPy trong `Schedule`).
- `32768` không chia hết cho `n` trong nhiều trường hợp, nên có sai lệch modulo rất nhỏ; không đáng kể với `n = 100`.

---

### Bước 5 — Lai ghép (crossover)

**Code:** `Schedule.crossover(parent, numberOfCrossoverPoints, crossoverProbability)`.

#### 5.1. Kiểm tra xác suất

```python
if randrange(100) > crossoverProbability:
    return self.copy(self, False)
```

- Nếu bỏ qua: trả về **bản sao của cha thứ nhất** (`self`), không lai.
- Nếu thực hiện: xác suất thực tế là `(Pc + 1)%` như mục 4.3.

#### 5.2. Chọn điểm cắt

```python
cp = [False] * size
for i in range(numberOfCrossoverPoints, 0, -1):
    while True:
        p = randrange(size)
        if not cp[p]:
            cp[p] = True
            break
```

- Chọn `K` vị trí **phân biệt** trong `0..N-1`.
- Đây là chọn **không hoàn lại** (rejection sampling).
- Nếu `K > N`, vòng `while` sẽ không bao giờ tìm được vị trí chưa chọn → **treo vô hạn**. Code không kiểm tra điều này; `AlgorithmParameters.normalize` giới hạn `K ≤ N`, nhưng nếu gọi constructor trực tiếp với `K > N` thì vẫn có thể treo. `K = N` vẫn hợp lệ (chọn hết tất cả vị trí), nhưng ít dùng.

#### 5.3. Ghép gen

```python
first = randrange(2) == 0
for i in range(size):
    if first:
        c = course_classes[i]
        p = classes[c]
    else:
        c = parent_course_classes[i]
        p = parent.classes[c]

    n_classes[c] = p
    for j in range(c.Duration - 1, -1, -1):
        n_slots[p + j].append(c)

    if cp[i]:
        first = not first
```

**Công thức khối:**

Giả sử `K = 2`, điểm cắt tại `c1 < c2`, cha `A`, mẹ `B`. Nếu bắt đầu bằng `A`:

```text
child = A[0..c1] + B[c1+1..c2] + A[c2+1..N-1]
```

Nếu bắt đầu bằng `B`:

```text
child = B[0..c1] + A[c1+1..c2] + B[c2+1..N-1]
```

Trong đó `A[i]` là **toàn bộ gen của lớp thứ i**, bao gồm:

- vị trí bắt đầu `p`;
- toàn bộ `dur(c)` ô mà lớp chiếm.

**Ví dụ với `N = 6`, `K = 2`, cắt tại 1 và 4, bắt đầu bằng A:**

```text
A = [A0, A1, A2, A3, A4, A5]
B = [B0, B1, B2, B3, B4, B5]

child = [A0, A1, B2, B3, B4, A5]
```

Giải thích:

- `i = 0, 1`: lấy A.
- Sau `i = 1` (điểm cắt), đổi sang B.
- `i = 2, 3, 4`: lấy B.
- Sau `i = 4` (điểm cắt), đổi lại A.
- `i = 5`: lấy A.

#### 5.4. Tính fitness cho con

```python
n.calculateFitness()
return n
```

**Đặc điểm quan trọng:**

- Mỗi lớp được sao chép **nguyên khối**, không bị cắt giữa chừng.
- Vì vậy con luôn có đủ `N` lớp, mỗi lớp đúng `dur(c)` ô liên tiếp.
- Lai ghép **không sửa** xung đột; nó chỉ tạo ra một tổ hợp vị trí mới, rồi fitness đánh giá.
- Trong luồng bình thường, mọi nhiễm sắc thể được sinh từ cùng prototype nên thứ tự khóa trong `_classes` giống nhau; code dựa vào giả định này khi dùng `course_classes[i]` và `parent_course_classes[i]`.

---

### Bước 6 — Đột biến (mutation)

**Code:** `Schedule.mutation(mutationSize, mutationProbability)`.

#### 6.1. Kiểm tra xác suất

```python
if randrange(100) > mutationProbability:
    return
```

- Nếu bỏ qua: không thay đổi gì, fitness giữ nguyên từ bước lai ghép.
- Nếu thực hiện: xác suất thực tế là `(Pm + 1)%`.

#### 6.2. Di chuyển lớp

```python
for i in range(mutationSize, 0, -1):
    mpos = randrange(numberOfClasses)
    c = course_classes[mpos]
    p_old = classes[c]
    self.repair(c, p_old, None)
```

Mỗi lần `repair`:

```text
1. Xóa c khỏi slots[p_old .. p_old + dur(c) - 1]
2. Chọn ngẫu nhiên:
       d ~ Uniform{0..D-1}
       r ~ Uniform{0..R-1}
       t ~ Uniform{0..H - dur(c) - 1}
   p_new = d×H×R + r×H + t
3. Thêm c vào slots[p_new .. p_new + dur(c) - 1]
4. classes[c] = p_new
```

**Công thức vị trí mới:**

```text
p_new = d×H×R + r×H + t
```

với `d`, `r`, `t` chọn đều trong miền hợp lệ.

#### 6.3. Tính fitness

```python
self.calculateFitness()
```

- Chỉ gọi **một lần** sau khi đã di chuyển xong `M` lớp.
- Không kiểm tra xung đột trong lúc di chuyển; đột biến là "mù" (blind), sau đó fitness mới đánh giá.

#### 6.4. Đặc điểm

- `M` lần chọn lớp **có hoàn lại**: một lớp có thể được chọn nhiều lần, nên `M` không có nghĩa là "M lớp khác nhau".
- Nếu `M = N`, vẫn có thể có lớp không được chọn và lớp khác bị chọn nhiều lần.
- Vị trí mới có thể trùng vị trí cũ; khi đó lớp không thay đổi.
- Nếu `M > N`, một lớp có thể bị di chuyển nhiều lần; kết quả cuối là vị trí của lần cuối.

---

### Bước 7 — Thay thế và cập nhật nhóm tốt nhất

**Code:** `GeneticAlgorithm.replacement`.

```python
offspring = replaceByGeneration * [None]
for j in range(replaceByGeneration):
    parent = selection(population)

    offspring[j] = parent[0].crossover(
        parent[1], numberOfCrossoverPoints, crossoverProbability
    )
    offspring[j].mutation(mutationSize, mutationProbability)

    ci = randrange(32768) % length_chromosomes
    while isInBest(ci):
        ci = randrange(32768) % length_chromosomes

    population[ci] = offspring[j]
    self.addToBest(ci)
```

**Công thức chọn vị trí thay thế:**

```text
ci ~ Uniform{0..n-1}
ci phải là cá thể không nằm trong nhóm tốt nhất
```

**Đặc điểm:**

- Mỗi vòng lặp tạo **một** con và thay nó vào **một** vị trí.
- `Rgen` vòng lặp, nhưng có thể chọn trùng `ci`, nên số vị trí **khác nhau** bị thay có thể nhỏ hơn `Rgen`.
- Không thay thế cá thể đang nằm trong nhóm tốt nhất.
- Sau khi thay, gọi `addToBest(ci)` để xét đưa cá thể mới vào nhóm tốt.

#### 7.1. Cơ chế `addToBest`

Nhóm tốt nhất là một mảng `bestChromosomes` kích thước `B`, sắp xếp **giảm dần** theo fitness.

```python
if (group full and fitness[worst] >= fitness[new]) or already_best:
    return

i = current_size
while i > 0:
    pos = best[i - 1]
    if i < B:
        if fitness[pos] > fitness[new]:
            break
        best[i] = pos
    else:
        bestFlags[pos] = False   # loại cá thể tệ nhất
    i -= 1

best[i] = new
bestFlags[new] = True
if current_size < B:
    current_size += 1
```

**Tóm tắt logic:**

```text
- Nếu nhóm đã đầy và cá thể mới không tốt hơn cá thể tệ nhất → bỏ qua.
- Nếu cá thể mới đã ở trong nhóm → bỏ qua.
- Ngược lại:
    + tìm vị trí chèn theo thứ tự giảm dần;
    + nếu nhóm đầy, đẩy cá thể tệ nhất ra;
    + đánh dấu cá thể mới là "best".
```

**Kết quả:**

- `bestChromosomes[0]` là cá thể tốt nhất trong nhóm.
- `result` trả về `population[bestChromosomes[0]]`.
- Các cá thể trong nhóm được bảo vệ: `replacement` không chọn `ci` nếu `isInBest(ci)`.

#### 7.2. Điểm rất quan trọng: nhóm tốt chỉ nhận con lai

Trong `GeneticAlgorithm.initialize`:

```python
for i in range(0, length_chromosomes):
    population[i] = prototype.makeNewFromPrototype()
    # addToBest(i)   ← bị chú thích
```

Vì dòng `addToBest(i)` bị chú thích, **quần thể ban đầu không được nạp vào nhóm tốt**. Nhóm tốt chỉ bắt đầu được nạp từ những con lai đầu tiên trong `replacement`.

Hệ quả:

1. Trước lần thay thế đầu tiên, `result` trả về `population[0]` (vì `bestChromosomes[0] = 0`), không phải cá thể tốt nhất của quần thể ban đầu.
2. Cá thể tốt nhất của thế hệ 0 có thể bị thay thế bởi một con lai kém hơn, và không bao giờ được đưa vào nhóm tốt.
3. `result` là "tốt nhất trong số các con lai đã từng được chấp nhận", không chắc là "tốt nhất tuyệt đối của toàn bộ quần thể".
4. Sau khi nhóm đã có phần tử, fitness của `result` **không giảm** khi thêm cá thể mới (vì nhóm được giữ theo thứ tự và chỉ nhận cá thể tốt hơn cá thể tệ nhất khi đã đầy). Tuy nhiên, lần chuyển từ `population[0]` sang con lai đầu tiên có thể làm `result` giảm.

Đây là chi tiết cài đặt, không phải lỗi cú pháp; cần biết khi đọc kết quả GA.

---

### Bước 8 — Cập nhật trạng thái và lặp

Sau khi thay thế:

```python
lastBestFit = best.fitness
Trace.trace(self, currentGeneration + 1, repeat)
currentGeneration += 1
```

- `best` là cá thể tốt nhất **trước** khi thay thế ở thế hệ này.
- `lastBestFit` được cập nhật bằng fitness đó, phục vụ so sánh trì trệ ở thế hệ sau.
- `Trace.trace` in tiến trình và lưu lịch sử; không ảnh hưởng thuật toán.
- `currentGeneration` tăng 1.

Vòng lặp tiếp tục cho đến khi một trong các điều kiện dừng ở Bước 3 thỏa.

---

### Bước 9 — Trả kết quả

Khi dừng:

```python
@property
def result(self):
    return self._chromosomes[self._bestChromosomes[0]]
```

`ConsoleApp.run_schedule` lấy:

```python
alg.result
```

rồi truyền cho `HtmlOutput.getResult` để hiển thị thời khóa biểu.

---

## 6. Pseudocode đầy đủ

### 6.1. Hàm fitness

```text
function evaluate(chromosome):
    V = [0, 0, 0, 0]
    score = 0

    for each class c in chromosome.classes:
        p = chromosome.classes[c]
        (d, t, r) = decode(p)
        dur = c.duration

        P = true
        for k in 0 .. dur-1:
            if length(chromosome.slots[p+k]) > 1:
                P = false
                break

        C = (room[r].seats >= c.seats)

        G = true
        S = true
        timeId = d * H * R + t
        for m in 1 .. R:
            for j in timeId .. timeId+dur-1:
                for each c1 in chromosome.slots[j]:
                    if c1 != c:
                        if c.professor == c1.professor:
                            G = false
                        if intersection(c.groups, c1.groups) != empty:
                            S = false
            timeId = timeId + H

        for i, ok in enumerate([P, C, G, S]):
            if ok:
                score = score + 1
            else:
                score = score + 1 - weight[i]
                V[i] = V[i] + 1

    F = score / (4 * N)
    return F, V
```

### 6.2. Khởi tạo quần thể

```text
function initialize(n):
    population = []
    for k in 1 .. n:
        chromosome = empty_schedule()
        for each class c:
            d = random(0, D-1)
            r = random(0, R-1)
            t = random(0, H - c.duration - 1)
            p = d*H*R + r*H + t
            place(c, p)
        chromosome.fitness = evaluate(chromosome)
        population.append(chromosome)
    return population
```

### 6.3. Lai ghép

```text
function crossover(parent1, parent2, K, Pc):
    if random(0, 99) > Pc:
        return clone(parent1)

    N = number_of_classes
    cuts = choose K distinct positions from 0 .. N-1

    child = empty_schedule()
    source = parent1 if random(0,1) == 0 else parent2

    for i in 0 .. N-1:
        c = source.class_at(i)
        p = source.start_of(c)
        place(c, p) in child
        if i in cuts:
            source = the other parent

    child.fitness = evaluate(child)
    return child
```

### 6.4. Đột biến

```text
function mutate(chromosome, M, Pm):
    if random(0, 99) > Pm:
        return

    for k in 1 .. M:
        c = random class in chromosome
        p_old = chromosome.classes[c]
        remove c from chromosome.slots[p_old .. p_old+dur(c)-1]

        d = random(0, D-1)
        r = random(0, R-1)
        t = random(0, H - dur(c) - 1)
        p_new = d*H*R + r*H + t
        add c to chromosome.slots[p_new .. p_new+dur(c)-1]
        chromosome.classes[c] = p_new

    chromosome.fitness = evaluate(chromosome)
```

### 6.5. Vòng lặp GA

```text
function GA(config, n, B, Rgen, K, M, Pc, Pm, Gmax, Smax, minFitness):
    population = initialize(n)
    bestGroup = empty list of size B
    lastBestFit = 0
    repeat = 0

    for generation in 0 .. Gmax-1:
        # result = bestGroup[0] nếu có, ngược lại population[0]
        best = bestGroup[0] if bestGroup not empty else population[0]

        if best.fitness > minFitness:
            break

        if abs(best.fitness - lastBestFit) <= 1e-7:
            repeat = repeat + 1
        else:
            repeat = 0

        if repeat >= Smax:
            break

        if repeat > 99.99:
            reseed_random()
            Rgen = min(3 * Rgen, n - B)
            Pc = Pc + 1

        for j in 1 .. Rgen:
            p1 = population[random(0, n-1)]
            p2 = population[random(0, n-1)]

            child = crossover(p1, p2, K, Pc)
            mutate(child, M, Pm)

            repeat:
                ci = random(0, n-1)
            until not bestGroup.contains(ci)

            population[ci] = child
            bestGroup.offer(ci)

        lastBestFit = best.fitness
        trace(generation+1, repeat)

    return bestGroup[0] if bestGroup not empty else population[0]
```

> Ghi chú: pseudocode dùng `bestGroup[0]` cho gọn; trong code thực tế là `population[bestChromosomes[0]]`. Khi nhóm rỗng, `bestChromosomes[0] = 0` nên `result = population[0]`.

---

## 7. Ví dụ tính tay

### 7.1. Ví dụ một thế hệ nhỏ

Giả sử:

```text
n = 4 cá thể: P0, P1, P2, P3
B = 2 (giữ 2 cá thể tốt)
Rgen = 2 (thay 2 cá thể mỗi thế hệ)
```

Fitness ban đầu:

| Cá thể | Fitness |
|---|---:|
| P0 | 0.70 |
| P1 | 0.80 |
| P2 | 0.75 |
| P3 | 0.65 |

**Thế hệ 0:**

- Nhóm tốt rỗng → `result = P0`, fitness `0.70`.
- Tạo 2 con:
  - `O1` fitness `0.78`
  - `O2` fitness `0.82`
- Giả sử chọn thay `P1` và `P3` (đều không nằm trong nhóm tốt vì nhóm đang rỗng):
  - `population[P1] = O1`
  - `population[P3] = O2`
- Cập nhật nhóm tốt:
  - `O1` vào nhóm → `[O1(0.78)]`
  - `O2` vào nhóm, tốt hơn `O1` → `[O2(0.82), O1(0.78)]`
- `result = O2`, fitness `0.82`.

Quần thể sau thế hệ 0:

| Vị trí | Cá thể | Fitness |
|---|---|---:|
| P0 | P0 | 0.70 |
| P1 | O1 | 0.78 |
| P2 | P2 | 0.75 |
| P3 | O2 | 0.82 |

**Nhận xét:**

- `P1` có fitness `0.80` đã bị thay bởi `O1` (`0.78`) — cá thể tốt hơn của quần thể ban đầu bị mất.
- `P2` (`0.75`) vẫn còn trong quần thể nhưng không nằm trong nhóm tốt, nên `result` không thấy.
- Đây là minh họa cho điểm cần lưu ý ở mục 7.2 của phần 5 (Bước 7): nhóm tốt chỉ nhận con lai.

### 7.2. Ví dụ một phép lai ghép

Giả sử `N = 6`, `K = 2`, điểm cắt tại 1 và 4.

Cha A:

```text
A = [A0, A1, A2, A3, A4, A5]
```

Mẹ B:

```text
B = [B0, B1, B2, B3, B4, B5]
```

Nếu bắt đầu bằng A:

```text
child = [A0, A1, B2, B3, B4, A5]
```

Nếu bắt đầu bằng B:

```text
child = [B0, B1, A2, A3, A4, B5]
```

Mỗi `Ai` / `Bi` không chỉ là "tên lớp" mà là **toàn bộ gen**:

```text
Ai = (lớp i, vị trí bắt đầu p_i, dur_i ô)
```

Vì vậy con luôn có đủ 6 lớp, không bị mất lớp hay cắt giữa lớp.

### 7.3. Ví dụ một phép đột biến

Lớp `c` có `dur = 2`, đang ở `p_old = 10`:

```text
slots[10] chứa c
slots[11] chứa c
classes[c] = 10
```

Đột biến chọn vị trí mới:

```text
d = 2, r = 0, t = 5
p_new = 2×24 + 0×12 + 5 = 53
```

Kết quả:

```text
slots[10], slots[11] không còn c
slots[53], slots[54] có c
classes[c] = 53
```

Fitness được tính lại sau khi di chuyển xong tất cả `M` lớp.

---

## 8. Độ phức tạp

Gọi:

- `N`: số lớp học phần.
- `R`: số phòng.
- `dur`: thời lượng trung bình (hoặc tối đa) của một lớp.
- `Occ`: số lớp trung bình trong một ô (thường rất nhỏ).
- `G`: số thế hệ chạy.
- `Rgen`: số cá thể thay mỗi thế hệ.
- `B`: kích thước nhóm tốt.

### 8.1. Tính fitness

Với mỗi lớp:

- Kiểm tra `P`: `O(dur)`.
- Kiểm tra `G`/`S`: duyệt `R` phòng × `dur` tiết × số lớp trong mỗi ô.

Ước lượng:

```text
O(N × R × dur × Occ)
```

Trường hợp xấu nhất `Occ` có thể lớn, nhưng trong dữ liệu thực tế `Occ` nhỏ.

### 8.2. Các phép toán

| Phép toán | Độ phức tạp |
|---|---|
| Khởi tạo một cá thể | `O(N × dur + fitness)` |
| Khởi tạo quần thể | `O(n × (N × dur + fitness))` |
| Lai ghép | `O(N × dur + fitness)` |
| Đột biến | `O(M × dur + fitness)` |
| Chọn cha mẹ | `O(1)` |
| `addToBest` | `O(B)` |
| Một thế hệ | `O(Rgen × (N × dur + M × dur + fitness + B))` |
| Toàn bộ GA | `O(G × Rgen × (N × dur + M × dur + fitness + B))` |

### 8.3. Bộ nhớ

```text
- slots: D × H × R danh sách
- classes: N cặp khóa-giá trị
- criteria: 4N boolean
- objectives: 4 số
- quần thể: n nhiễm sắc thể, mỗi nhiễm sắc thể có slots + classes riêng
```

Với dữ liệu mẫu:

```text
D×H×R = 5×12×2 = 120 ô
N = 27 lớp
n = 100 cá thể
```

Bộ nhớ rất nhỏ; chi phí chủ yếu là tính fitness lặp lại.

---

## 9. Những điểm cần lưu ý khi đọc code

### 9.1. Xác suất bị lệch 1 đơn vị

Như mục 4.3:

```text
P_thực_thi = (p + 1) / 100   với p < 100
```

- `Pc = 80` → thực tế 81%.
- `Pm = 3` → thực tế 4%.
- `p = 0` vẫn có 1% thực thi, không phải 0%.

Nguyên nhân: dùng `>` thay vì `>=`, và `randrange(100)` sinh `0..99`.

### 9.2. Nhóm tốt chỉ nhận con lai

`initialize` không gọi `addToBest`. Vì vậy:

- `result` ban đầu là `population[0]`, không phải cá thể tốt nhất.
- Cá thể tốt nhất của thế hệ 0 có thể bị mất.
- `result` không đảm bảo là cá thể tốt nhất tuyệt đối của toàn bộ quần thể trong vài thế hệ đầu.

Nếu muốn sửa để đúng ý tưởng elitism, có thể bỏ chú thích dòng `addToBest(i)` trong vòng lặp `initialize`, hoặc nạp toàn bộ quần thể ban đầu vào nhóm tốt sau khi khởi tạo xong.

### 9.3. Hai nguồn ngẫu nhiên khác nhau

| Nơi dùng | Module | Bị ảnh hưởng bởi |
|---|---|---|
| `GeneticAlgorithm.selection`; phần chọn chỉ số `ci` trong `replacement` | `random` (Python) | `random.seed(...)` trong `run` |
| `Schedule.makeNewFromPrototype`, `crossover`, `mutation` | `numpy.random` | Không được seed trong GA |

Vì vậy:

- `random.seed(round(time()*1000))` trong `run` **không** làm cho việc khởi tạo, lai ghép, đột biến có thể tái lập.
- Muốn tái lập hoàn toàn, cần seed cả `numpy.random.seed(...)`.

### 9.4. Miền thời gian bắt đầu

```python
time = randrange(DAY_HOURS - dur)
```

- `t ∈ {0, ..., H-dur-1}`.
- Lớp 1 tiết không bao giờ bắt đầu ở tiết cuối `t = 11`.
- Nếu `dur = 12`, `randrange(0)` sẽ lỗi.
- Nếu `dur > 12`, `randrange(âm)` sẽ lỗi.

Dữ liệu hợp lệ cần `1 ≤ dur ≤ H-1`.

### 9.5. `K > N` có thể treo

Trong `Schedule.crossover`:

```python
while not check_point:
    p = randrange(size)
    if not cp[p]:
        cp[p] = check_point = True
```

Nếu `numberOfCrossoverPoints > size`, không còn vị trí chưa chọn → vòng lặp vô hạn.

- `AlgorithmParameters.normalize` giới hạn `K ≤ N`.
- Nếu khởi tạo `GeneticAlgorithm` trực tiếp với `K > N`, có thể treo.
- Tương tự, `K = N` vẫn hợp lệ về mặt chọn điểm (chọn hết các vị trí), nhưng thực tế ít dùng.

### 9.6. Đột biến chọn lớp có hoàn lại

`M` lần chọn lớp là `M` lần lấy ngẫu nhiên **có hoàn lại**. Vì vậy:

- Không đảm bảo `M` lớp khác nhau bị di chuyển.
- Một lớp có thể bị di chuyển nhiều lần.
- Nếu muốn "M lớp khác nhau", cần chọn không hoàn lại (shuffle danh sách lớp rồi lấy `M` phần tử đầu).

### 9.7. Thay thế có thể chọn trùng vị trí

`replacement` chỉ tránh các vị trí trong nhóm tốt, không tránh các vị trí **vừa bị thay trong cùng thế hệ**. Vì vậy:

- Có thể thay cùng một vị trí nhiều lần trong một thế hệ.
- Số vị trí khác nhau bị thay có thể nhỏ hơn `Rgen`.
- Điều này không sai về mặt thuật toán, nhưng cần biết khi phân tích tốc độ hội tụ.

### 9.8. Nhánh tăng cường gần như không chạy với mặc định

```python
if repeat >= maxStagnation:
    break

if repeat > (maxRepeat / 100):
    ...
```

Với `maxStagnation = 100` và `maxRepeat = 9999`:

- `repeat = 100` → dừng ở điều kiện đầu.
- Nhánh sau cần `repeat >= 100`, nhưng không bao giờ tới được.

Chỉ khi `maxStagnation > 100` thì nhánh tăng cường mới có cơ hội chạy.

### 9.9. Ngưỡng `minFitness` và kích thước bài toán

Điều kiện dừng là `best.fitness > minFitness`.

Với `N = 27`, `4N = 108`:

- `F = 107.5/108 ≈ 0.99537` (một lỗi `C`) < `0.999`.
- `F = 108/108 = 1.0` > `0.999`.

Nên chỉ lịch hoàn hảo mới dừng sớm. Với `N` lớn hơn, một vài lỗi nhỏ có thể vẫn cho `F > 0.999`; khi đó GA có thể dừng với lịch còn lỗi. Đây là hành vi của ngưỡng fitness, không phải lỗi.

### 9.10. Cách đếm vi phạm

`V_i` đếm **số lớp vi phạm**, không phải số cặp. Nếu hai lớp trùng giảng viên:

```text
V_G += 2
```

Nếu ba lớp cùng trùng một giảng viên trong cùng khung giờ:

```text
V_G += 3
```

Tương tự với `P` và `S`. Điều này ảnh hưởng đến cách diễn giải fitness: một xung đột giữa 2 lớp làm `V_i` tăng 2, tức mức phạt gấp đôi so với việc chỉ có 1 lớp bị đánh dấu vi phạm.

### 9.11. `result` trước lần thay thế đầu tiên

Vì `bestChromosomes` được khởi tạo toàn số 0 và nhóm tốt rỗng:

```python
result = population[bestChromosomes[0]] = population[0]
```

Không có bước kiểm tra "nhóm rỗng". Đây là lý do `result` không lỗi khi gọi trước `replacement`, nhưng ý nghĩa là "cá thể đầu tiên", không phải "cá thể tốt nhất".

### 9.12. Ghi chú về `Trace`

`Trace.trace` lấy:

```python
population_size = getattr(algorithm, "_populationSize", 0)
```

`GeneticAlgorithm` không có thuộc tính `_populationSize` (chỉ có `_chromosomes`), nên với GA, `Trace` có thể hiển thị `Cá thể: 0`. Đây là vấn đề hiển thị, không ảnh hưởng fitness hay kết quả.

---

## 10. Bảng đối chiếu code

| Bước / khái niệm | Hàm / thuộc tính | File | Dòng (theo bản hiện tại) |
|---|---|---|---|
| Khởi tạo tham số GA | `initAlgorithm`, `__init__` | `algorithm/GeneticAlgorithm.py` | 15–57 |
| Kết quả tốt nhất | `result` | `algorithm/GeneticAlgorithm.py` | 59–62 |
| Giới hạn số thay thế | `set_replace_by_generation` | `algorithm/GeneticAlgorithm.py` | 64–70 |
| Nhóm tốt nhất | `addToBest` | `algorithm/GeneticAlgorithm.py` | 73–108 |
| Kiểm tra thuộc nhóm tốt | `isInBest` | `algorithm/GeneticAlgorithm.py` | 111–112 |
| Xóa nhóm tốt | `clearBest` | `algorithm/GeneticAlgorithm.py` | 115–117 |
| Khởi tạo quần thể | `initialize` | `algorithm/GeneticAlgorithm.py` | 120–128 |
| Chọn cha mẹ | `selection` | `algorithm/GeneticAlgorithm.py` | 130–132 |
| Thay thế | `replacement` | `algorithm/GeneticAlgorithm.py` | 134–162 |
| Vòng lặp chính | `run` | `algorithm/GeneticAlgorithm.py` | 165–209 |
| Tạo cá thể ngẫu nhiên | `makeNewFromPrototype` | `model/Schedule.py` | 55–87 |
| Lai ghép | `crossover` | `model/Schedule.py` | 112–171 |
| Sửa vị trí lớp | `repair` | `model/Schedule.py` | 241–267 |
| Đột biến | `mutation` | `model/Schedule.py` | 270–293 |
| Tính fitness | `calculateFitness` | `model/Schedule.py` | 296–351 |
| Trùng phòng | `isRoomOverlapped` | `model/Criteria.py` | 14–17 |
| Đủ chỗ | `isSeatEnough` | `model/Criteria.py` | 21–22 |
| Trùng GV / nhóm SV | `isOverlappedProfStudentGrp` | `model/Criteria.py` | 26–47 |
| Công thức chỉ số ô | `getHashCode` | `model/Reservation.py` | 27–28 |
| Giải mã chỉ số ô | `parse` | `model/Reservation.py` | 15–24 |
| Hằng số ngày/tiết | `DAYS_NUM`, `DAY_HOURS` | `model/Constant.py` | 3–6 |
| Tham số mặc định | `DEFAULTS` | `model/AlgorithmParameters.py` | 8–19 |
| Chuẩn hóa tham số | `normalize` | `model/AlgorithmParameters.py` | 162–190 |

---

## 11. Tóm tắt công thức cốt lõi

```text
# 1. Chỉ số ô
idx(d, t, r) = d × H × R + r × H + t
d = idx // (H×R)
r = (idx % (H×R)) // H
t = idx % H

# 2. Lớp c chiếm
slots[p .. p+dur(c)-1], với p = idx(d, t, r)

# 3. Vi phạm
V_P = số lớp bị trùng phòng
V_C = số lớp bị thiếu chỗ
V_G = số lớp bị trùng giảng viên
V_S = số lớp bị trùng nhóm SV

# 4. Fitness
F = 1 - (V_P + 0.5×V_C + V_G + V_S) / (4N)

# 5. Xác suất thực thi thực tế
P_thực_thi(p) = min(1, (p + 1) / 100)

# 6. Vị trí mới khi đột biến
p_new = d×H×R + r×H + t
d ~ U{0..D-1}, r ~ U{0..R-1}, t ~ U{0..H-dur-1}
```

---

## 12. Đọc nhanh trong 10 dòng

1. Mỗi lớp học phần là một gen; gen lưu ô bắt đầu trong lưới `5 ngày × 12 tiết × R phòng`.
2. `slots` là lưới ô, `classes` là bảng lớp → vị trí bắt đầu.
3. Fitness = `1 - (V_P + 0.5V_C + V_G + V_S)/(4N)`, càng gần 1 càng tốt.
4. Khởi tạo bằng cách đặt từng lớp vào vị trí ngẫu nhiên.
5. Chọn cha mẹ ngẫu nhiên đều, không tournament.
6. Lai ghép cắt danh sách lớp tại `K` điểm, sao chép nguyên khối gen từ hai cha mẹ.
7. Đột biến di chuyển `M` lớp (có hoàn lại) sang vị trí ngẫu nhiên mới.
8. Con thay vào vị trí ngẫu nhiên không thuộc nhóm `trackBest` cá thể tốt nhất.
9. Nhóm tốt nhất giữ `B` cá thể, sắp giảm dần; `result` là phần tử đầu.
10. Dừng khi fitness > `minFitness`, đủ `maxIterations`, hoặc trì trệ `maxStagnation` thế hệ.

---

*Tài liệu được viết dựa trên code hiện tại của project. Nếu các tham số mặc định hoặc `Criteria.weights` thay đổi, các công thức và ví dụ số cần cập nhật tương ứng.*
