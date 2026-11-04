# GASchedule.py

Lập thời khóa biểu học bằng thuật toán di truyền với Python

# Giới thiệu

Lập thời khóa biểu là một bài toán NP-khó. Bài toán này có thể được giải bằng thuật toán tìm kiếmheuristic để tìm ra phương án tối ưu, nhưng cách đó chỉ hiệu quả với những trường hợp đơn giản. Với dữ liệu đầu vào và yêu cầu phức tạp hơn, việc tìm ra một phương án tốt có thể mất khá lâu, hoặc thậm chí không thể thực hiện được. Đây là lúc thuật toán di truyền bước vào cuộc. Trong tài liệu này, tôi giả định rằng bạn đã quen thuộc với các khái niệm cơ bản của thuật toán di truyền, nên sẽ không mô tả lại chi tiết, vì điều đó đã được trình bày rất nhiều lần trước đây.

# Bối cảnh

Khi lập thời khóa biểu, bạn phải tính đến nhiều yêu cầu: số lượng giảng viên, lớp học và phòng học, cùng nhiều yếu tố khác. Các yêu cầu này có thể được chia thành vài nhóm theo mức độ quan trọng.

**Ràng buộc cứng** (vi phạm một ràng buộc thì lịch không khả thi):

1. Một lớp học chỉ có thể được xếp vào phòng học còn trống.
2. Không giảng viên nào được có hai lớp học cùng lúc.

**Ràng buộc mềm** (có thể bị vi phạm mà lịch vẫn khả thi), trong mô tả kinh điển của bài
toàn gồm:

1. Thời gian giảng viên muốn dạy.
2. Phòng học giảng viên muốn dùng.
3. Mức độ phân bố (theo thời gian hoặc không gian) của các lớp học dành cho giảng viên.

Ràng buộc cứng và ràng buộc mềm phụ thuộc vào tình huống cụ thể. Bản hiện tại cài đặt ba
ràng buộc cứng `P`, `G`, `N` và **một** ràng buộc mềm `B` — không xếp lớp vào khung giờ
giảng viên báo bận; ba ràng buộc mềm kinh điển còn lại chưa được hiện thực. Ràng buộc
mềm luôn có trọng số phạt **nhỏ hơn** ràng buộc cứng — xem mục "Trọng số tiêu chí".

# Các đối tượng của thời khóa biểu

**Giảng viên (`Professor`)**
Lớp `Professor` có mã và tên của giảng viên. Nó cũng chứa danh sách các lớp mà giảng viên đó phụ trách dạy.

**Phòng học (`Room`)**
Lớp `Room` có mã và tên của phòng học. Mã định danh được sinh ra tự động bên trong.

**Môn học (`Course`)**
Lớp `Course` có mã và tên của môn học.

**Lớp học (`CourseClass`)**
Đối tượng `CourseClass` giữ tham chiếu tới môn học mà lớp thuộc về, tham chiếu tới giảng viên phụ trách dạy và thời lượng của lớp (tính bằng giờ).

**Nhiễm sắc thể (`Chromosome`)**
Việc đầu tiên cần cân nhắc khi làm việc với thuật toán di truyền là cách biểu diễn lời giải sao cho thuận tiện cho các phép toán lai ghép (crossover) và biến dị (mutation). Đồng thời, ta cũng cần biết lời giải đó tốt đến đâu, nói cách khác là phải tính được giá trị độ thích nghi (fitness) của lời giải.

## Cách biểu diễn

Làm thế nào để biểu diễn nhiễm sắc thể cho một thời khóa biểu? Ta cần một ô thời gian - không gian (time-space slot) cho mỗi khung giờ (ta giả thiết thời gian tính theo đơn vị một giờ), cho mỗi phòng học, mỗi ngày. Một ngày có 13 khung giờ từ 7 giờ đến 18 giờ, chia làm hai buổi: buổi sáng 6 tiết (7h–12h) và buổi chiều 6 tiết (13h–18h), mỗi tiết 50 phút; khung 12h–13h là giờ nghỉ trưa, không được xếp lịch (tổng cộng 12 tiết dạy mỗi ngày). Ngày làm việc từ thứ hai đến thứ sáu (tổng cộng 5 ngày). Các tham số này được cấu hình trong `model/Constant.py` qua `START_HOUR`, `DAY_HOURS` (13 khung giờ), `LUNCH_PERIOD` (chỉ số 6 của khung nghỉ trưa) và `TEACHING_HOURS` (12 tiết dạy).

Mỗi khung giờ có hai cách gọi cần phân biệt khi đọc mã nguồn:

- **offset** (chỉ số 0-based của khung giờ trong ngày, 0..12, bỏ qua offset 6 là nghỉ trưa) — đây là giá trị lưu trong `Reservation.Time`, trong tập `BusySlots`, và trong các trường `start`/`end` của khối `busy` ở tệp JSON;
- **số tiết** (1..12, do `Constant.periodNumber(offset)` sinh ra) — sáng: offset 0..5 thành tiết 1..6, chiều: offset 7..12 thành tiết 7..12.

Báo cáo HTML và lưới chọn giờ bận luôn hiển thị theo **số tiết**, không phải offset.

Kết quả sẽ được hiển thị dưới dạng bảng HTML. Chương trình sẽ mở trình duyệt mặc định để trình bày thời khóa biểu một cách rõ ràng.

# Độ thích nghi

Bây giờ cần gán một giá trị độ thích nghi cho nhiễm sắc thể. Điểm của một lớp dựa trên
ba ràng buộc cứng, sau đó cả lịch bị trừ thêm phạt của các ràng buộc mềm (nhẹ hơn hẳn
ràng buộc cứng). Cách tính phần cứng như sau:

- Mỗi lớp học có thể nhận từ 0 đến 3 điểm, ứng với các tiêu chí `P`, `G`, `N`.
- Nếu lớp học nằm trong phòng còn trống, tăng điểm của lớp đó.
- Nếu giảng viên không có lớp khác trong thời điểm đó, tăng thêm một điểm cho lớp.
- Nếu lớp học không rơi vào khung giờ nghỉ trưa 12h–13h, tăng thêm một điểm cho lớp.
- Nếu một lớp vi phạm quy tắc, điểm của tiêu chí đó là `1 - trọng số phạt` thay vì `1`. Trọng số phạt nằm trong khoảng 0 đến 1; `0` nghĩa là không phạt, `1` nghĩa là mất trọn điểm của tiêu chí.

Tổng điểm của một thời khóa biểu là tổng số điểm của tất cả các lớp, sau khi trừ phạt của
ràng buộc mềm. Giá trị độ thích nghi được tính bằng `điểm_lịch / điểm_tối_đa`, trong đó
`điểm_lịch = điểm cứng − tổng phạt mềm` và `điểm_tối_đa = số_lớp_học × 3`. Vì mỗi phạt mềm
đều nhỏ hơn 1 điểm nên độ thích nghi vẫn nằm trong khoảng từ 0 đến 1.

> **Lưu ý về cơ chế phạt:** Vì các ràng buộc cứng chỉ bị trừ điểm chứ không bị loại bỏ nhiệm vụ, nên luôn tồn tại một lời giải khả thi. Thuật toán tiến dần đưa giá trị độ thích nghi về gần 1, và dừng lại khi đạt ngưỡng (mặc định là 0,999).

# Lai ghép (Crossover)

Một phép lai ghép kết hợp dữ liệu trong các bản đồ băm (hash map) của hai nhiễm sắc thể cha mẹ, rồi tạo ra một vectơ các ô thời gian - không gian dựa trên nội dung của bản đồ băm mới. Phép lai ghép "chia" bản đồ băm của cả hai cha mẹ thành các phần có kích thước ngẫu nhiên. Số phần được xác định bởi số điểm lai ghép (cộng thêm một) trong các tham số của nhiễm sắc thể. Sau đó, nó lần lượt chép các phần từ cha mẹ sang nhiễm sắc thể mới một cách xen kẽ, và hình thành một danh sách các ô thời gian - không gian mới.

# Biến dị (Mutation)

Một phép biến dị rất đơn giản. Nó chỉ đơn giản là chọn ngẫu nhiên một lớp học và chuyển nó sang một ô thời gian - không gian khác được chọn ngẫu nhiên. Vị trí mới luôn nằm trong các khung giờ dạy hợp lệ (buổi sáng 7h–12h hoặc buổi chiều 13h–18h), không bao giờ rơi vào khung nghỉ trưa 12h–13h. Số lớp học sẽ được chuyển trong một lần thao tác được quy định bởi kích thước biến dị (mutation size) trong các tham số của nhiễm sắc thể.

# Thuật toán

Thuật toán di truyền khá đơn giản. Với mỗi thế hệ, nó thực hiện hai thao tác cơ bản:

1. Ngẫu nhiên chọn N cặp cha mẹ từ quần thể hiện tại và tạo ra N nhiễm sắc thể mới bằng cách thực hiện phép lai ghép trên mỗi cặp.
2. Ngẫu nhiên chọn N nhiễm sắc thể từ quần thể hiện tại và thay thế chúng bằng những cái mới. Thuật toán không chọn những nhiễm sắc thể để thay thế nếu nó nằm trong nhóm những nhiễm sắc thể tốt nhất.

Hai thao tác này được lặp lại cho đến khi nhiễm sắc thể tốt nhất đạt giá trị độ thích nghi bằng 1 (nghĩa là tất cả các lớp trong lịch đều đáp ứng yêu cầu). Như đã đề cập trước đó, thuật toán di truyền theo dõi một nhóm cá thể tốt nhất trong quần thể, và bảo đảm chúng không bị thay thế khi nằm trong nhóm những cái tốt nhất.

# Tệp cấu hình JSON

Các loại đối tượng:

- `prof` - mô tả một giảng viên.
- `course` - mô tả một môn học.
- `room` - mô tả một phòng học.
- `class` - mô tả một lớp học, ràng buộc giảng viên và môn học.

Cấu trúc các khoá:

**prof:**
`id` (số, bắt buộc) - mã của giảng viên.
`name` (chuỗi, bắt buộc) - tên của giảng viên.
`subjects` (danh sách số, tuỳ chọn) - các môn giảng viên dạy được.
`busy` (danh sách, tuỳ chọn) - khung giờ giảng viên bận; mỗi phần tử là
`{"day": 0-4, "start": offset, "end": offset}` với `start`/`end` là **chỉ số khung giờ
0-based** và đều bao gồm (inclusive).

**course:**
`id` (số, bắt buộc) - mã của môn học.
`name` (chuỗi, bắt buộc) - tên của môn học.

**room:**
`name` (chuỗi, bắt buộc) - tên của phòng học.

**class:**
`professor` (số, bắt buộc) - mã của giảng viên; ràng buộc giảng viên vào một lớp học.
`course` (số, bắt buộc) - mã của môn học; ràng buộc môn học vào một lớp học.
`duration` (số, tuỳ chọn) - thời lượng lớp học (tính bằng giờ); nếu không khai báo thì mặc định là 1.

> **Lưu ý:** tiêu chí máy tính (`M`) và khóa `lab` đã được bỏ hoàn toàn khỏi bài toán.
> Tệp cấu hình không cần khai báo `lab` cho phòng hay lớp học; nếu tệp cũ còn khóa này,
> chương trình sẽ bỏ qua. Xem mục "Trọng số tiêu chí" bên dưới.

Lưu ý: các đối tượng giảng viên và môn học phải được định nghĩa trước khi được ràng buộc vào một đối tượng lớp học.

## Ví dụ dữ liệu mẫu

Tệp `GaSchedule.json` đi kèm chứa: 5 giảng viên, 10 môn học, 4 phòng học và 48 lớp học.

```json
[
    { "prof":   { "id": 1, "name": "Nguyễn Văn An",
                  "subjects": [1, 2],
                  "busy": [{ "day": 0, "start": 0, "end": 1 }] } },
    { "course": { "id": 1, "name": "Lập trình hướng đối tượng" } },
    { "room":   { "name": "Phòng 201" } },
    { "class":  { "professor": 1, "course": 1, "duration": 2 } }
]
```

## Trọng số tiêu chí

Tất cả trọng số nằm trong `model/Criteria.py`. **Ràng buộc cứng** tính theo từng lớp,
mỗi tiêu chí tối đa 1 điểm (P, G, N); trọng số là mức phạt khi vi phạm.

| Mã | Tiêu chí (cứng) | Trọng số phạt |
|---|---|---|
| `P` | Phòng học không bị trùng lịch | 1.0 |
| `G` | Giảng viên không bị trùng lịch | 1.0 |
| `N` | Không xếp lịch vào khung nghỉ trưa 12h–13h | 1.0 |

Khi một lớp vi phạm tiêu chí cứng, điểm của tiêu chí đó là `1 - trọng số`, tức mất trọn
1 điểm. Trọng số `0` nghĩa là không phạt, còn `1` là phạt tối đa.

**Ràng buộc mềm** chỉ làm giảm điểm của nhiệm vụ khả thi và **luôn có trọng số nhỏ hơn
một vi phạm cứng**, để thuật toán bao giờ cũng ưu tiên sửa P/G/N trước:

| Mã | Tiêu chí (mềm) | Cách tính | Trọng số phạt |
|---|---|---|---|
| `B` | Không xếp lớp vào khung giờ giảng viên bận | theo từng lớp dính bận | 0.2 |

Fitness = `(điểm cứng − tổng phạt mềm) / (số lớp × 3)`. Vì mỗi phạt mềm đều dưới 1.0,
một vi phạm mềm không bao giờ đắt bằng một vi phạm cứng.

Trên báo cáo HTML, ô lớp bị xếp vào khung giảng viên bận tô **cam** kèm nhãn
`GV bận · tiết 3` (ràng buộc mềm); rê chuột vào nhãn để thấy khung giờ tương ứng
(VD `8:40–9:30`). Các tiết liền nhau của cùng một lớp được gộp thành **một ô
`rowspan`** duy nhất; chỉ khi một lớp khác trùng vào giữa chuỗi, các tiết còn lại mới
tách ra và mang thẻ **Tiếp tiết**. Ô trống
có sọc cam trong lịch của một giảng viên là tiết giảng viên đó báo bận. Phân biệt
với **đỏ** của ràng buộc cứng; mỗi giảng viên có badge số lớp dính bận ở đầu bảng
lịch. Giao diện không dùng hiệu ứng `:hover`, mọi trạng thái đều hiển thị sẵn.

Số tiết bận lấy từ `BusySlots` (tập hợp `(ngày, chỉ số khung giờ)` đã được
`Configuration` bung từ các khối `busy` trong tệp JSON), nên cột **Lịch bận** và lưới
chọn giờ bận dùng chung một cách đếm tiết với các dòng của bảng thời khóa biểu.

# Hiệu năng

Thời gian chạy phụ thuộc vào dữ liệu đầu vào, kích thước quần thể và số thế hệ. Chạy `python ConsoleApp.py` để đo thời gian thực tế; có thể tăng `maxStagnation` hoặc `maxIterations` trong khối **Thông số thuật toán** trên báo cáo HTML nếu muốn thuật toán tìm kiếm lâu hơn.

# Cách chạy

## Chạy từ dòng lệnh

```powershell
python -m pip install -r requirements.txt
python ConsoleApp.py                    # dùng tệp GaSchedule.json mặc định
python ConsoleApp.py du_lieu_rieng.json # dùng tệp cấu hình khác
python ConsoleApp.py --no-serve         # chỉ tạo tệp HTML tĩnh
```

Chương trình in tiến trình tối ưu hoá ra màn hình, sau khi hoàn thành sẽ tạo tệp kết quả `.htm` trong thư mục tạm của hệ điều hành và mở bằng trình duyệt mặc định. Báo cáo được phục vụ qua một máy chủ nhỏ trên `127.0.0.1` để nút **Chạy lại** hoạt động.

`ConsoleApp.py` hiện dùng `GeneticAlgorithm` với mặc định tối đa 1000 thế hệ, dừng khi fitness vượt `0.999` hoặc sau 100 thế hệ liên tiếp không cải thiện. Các thông số này có thể chỉnh trực tiếp trên báo cáo HTML; xem mục **Thông số thuật toán trên giao diện** bên dưới.

## Chạy lại từ trang HTML

Khi chạy ở chế độ mặc định, nút **↻ Chạy lại** nằm ở phần đầu khối **Thông số thuật toán** phía trên báo cáo. Bấm nút này để:

- chạy lại thuật toán với đúng tệp cấu hình đang dùng;
- đọc lại tệp JSON nếu bạn vừa sửa dữ liệu;
- lưu lịch bận đã chọn trên lưới giờ bận của giảng viên trở lại tệp cấu hình;
- cập nhật cả trang đang mở và tệp `.htm` trong thư mục tạm.

Quy tắc liên kết (binding) của lưới chọn giờ bận, để dữ liệu trên trang và dữ liệu
trong tệp luôn là một:

- mỗi ô của lưới mang `data-prof` (ID giảng viên), `data-day` và `data-time` là
  **chỉ số khung giờ 0-based** — cùng hệ toạ độ với `Reservation.Time` và `BusySlots`;
- khi bấm **Chạy lại**, trang gửi nguyên trạng thái lưới: mọi giảng viên đều có mặt
  trong payload, giảng viên đã bỏ hết ô bận gửi danh sách rỗng `[]`;
- máy chủ chỉ ghi tệp khi yêu cầu có khoá `busy`. Danh sách rỗng xoá sạch khung bận
  của giảng viên đó; giảng viên vắng mặt trong payload được giữ nguyên dữ liệu cũ;
- lịch bận của từng thế hệ trên lưới **Thời khóa biểu qua các bước** tra theo **ID**
  giảng viên (`data.busy` và `data.profNames` trong mảng JSON nhúng), không tra theo
  tên hiển thị, nên hai giảng viên trùng tên không dính khung bận của nhau.

Cần giữ cửa sổ dòng lệnh mở trong lúc dùng nút; nhấn `Ctrl+C` để dừng máy chủ. Nếu chạy với `--no-serve` hoặc mở trực tiếp tệp `.htm`, nút sẽ nhắc chạy `ConsoleApp.py` để bật máy chủ cục bộ.

## Thông số thuật toán trên giao diện

Khối **Thông số thuật toán** nằm trên phần chú thích và dữ liệu đầu vào, mặc định mở sẵn để chỉnh ngay. Nút **↻ Chạy lại** nằm ở phần đầu khối, bên ngoài phần thông số chi tiết; bấm nút này sau khi chỉnh các giá trị dùng cho lần chạy kế tiếp.

| Thông số | Mặc định | Ý nghĩa |
|---|---:|---|
| Kích thước quần thể | 100 | Số cá thể trong mỗi thế hệ. |
| Giữ lại cá thể tốt | 5 | Số cá thể tốt nhất không bị thay thế. |
| Thay thế mỗi thế hệ | 8 | Số cá thể được thay bằng con lai mỗi thế hệ. |
| Điểm lai ghép | 2 | Số điểm cắt khi lai ghép; tự giới hạn theo số lớp. |
| Mức đột biến | 2 | Số lớp bị thay đổi trong một lần đột biến. |
| Xác suất lai ghép | 80% | Tỉ lệ chọn phép lai ghép. |
| Xác suất đột biến | 3% | Tỉ lệ chọn phép đột biến. |
| Số thế hệ tối đa | 1000 | Giới hạn số thế hệ của một lần chạy. |
| Dừng khi không cải thiện | 100 | Dừng sau bấy nhiêu thế hệ fitness không tăng. |
| Fitness mục tiêu | 0.999 | Dừng sớm khi fitness vượt giá trị này. |

Các giá trị được kiểm tra ở cả trình duyệt và máy chủ. Nếu một tổ hợp không hợp lệ (ví dụ giữ lại quá nhiều cá thể so với kích thước quần thể), chương trình sẽ tự giới hạn lại và hiển thị giá trị thực tế sau khi chạy. Thông số chỉ ảnh hưởng đến lần chạy, không được ghi vào tệp JSON cấu hình.

## Cách dùng như một thư viện

```python
import pathlib
import time

from model.Configuration import Configuration
from algorithm.GeneticAlgorithm import GeneticAlgorithm
from HtmlOutput import HtmlOutput
from Trace import Trace as Tracer

file_name = "/GaSchedule.json"
start_time = int(round(time.time() * 1000))

configuration = Configuration()
target_file = str(pathlib.Path().absolute()) + file_name
configuration.parseFile(target_file)

Tracer.reset()
alg = GeneticAlgorithm(configuration)
alg.run()
html_result = HtmlOutput.getResult(alg.result, history=Tracer.get_history())
```

`HtmlOutput.getResult()` trả về một tài liệu HTML hoàn chỉnh (có `<!DOCTYPE html>`), có thể ghi trực tiếp ra tệp `.html` rồi mở bằng trình duyệt. Khi dùng theo cách này, trang là tĩnh; nút **Chạy lại** chỉ hoạt động khi báo cáo được phục vụ qua máy chủ cục bộ của `ConsoleApp.py`.

Nếu truyền thêm `history=Tracer.get_history()`, tài liệu HTML sẽ có:
- biểu đồ đường **Fitness qua các thế hệ** thể hiện mức tăng/giảm của fitness qua mọi thế hệ đã chạy, kèm các chỉ số bắt đầu, cao nhất và cuối cùng;
- lưới **Thời khóa biểu qua các bước**: mỗi thế hệ là một ô (10 ô mỗi hàng) hiển thị fitness và số vi phạm `P/G/N`, bấm vào ô để xem thời khóa biểu của thế hệ đó ở khung bên dưới.

Gọi `Tracer.reset()` trước khi chạy để xóa lịch sử của lần chạy trước. Nếu không truyền `history`, HTML chỉ hiển thị kết quả cuối cùng như trước đây. Mọi thế hệ đã ghi đều được vẽ thành một ô trong lưới 10 cột; thời khóa biểu của từng thế hệ được trình duyệt dựng lại từ dữ liệu gọn nhúng trong trang nên số thế hệ lớn cũng không làm file nặng.

Project hiện chỉ dùng `GeneticAlgorithm`; các thuật toán tối ưu đa mục tiêu và siêu heuristic khác đã được lược bỏ để tập trung vào GA.

# Thư viện yêu cầu

- `numpy >= 1.2.0`

# Giải thích kết quả xuất ra

Kết quả là một tệp HTML hoàn chỉnh (đã nhúng sẵn CSS và JavaScript, không cần mạng) gồm:

- Phần tiêu đề và thống kê độ phù hợp.
- **Thông số thuật toán**: khối nằm trên phần chú thích và dữ liệu đầu vào, mở sẵn để chỉnh kích thước quần thể, lai ghép, đột biến, điều kiện dừng và fitness mục tiêu; nút **↻ Chạy lại** nằm ở phần đầu khối.
- **Chú thích ràng buộc** với ba ký hiệu cứng `P/G/N` và ký hiệu mềm `B` (kèm trọng số phạt của từng loại), được giữ cố định khi cuộn trang.
- **Thời khóa biểu cuối cùng**: một bảng cho mỗi phòng học, 13 hàng tương ứng 13 khung giờ (12 tiết dạy, sáng 6 tiết từ 7h–12h và chiều 6 tiết từ 13h–18h, xen giữa là hàng nền kẻ chéo "Nghỉ trưa" 12h–13h) và 5 cột tương ứng từ thứ hai đến thứ sáu.
- **Lịch giảng dạy theo giảng viên**: nằm ngay dưới thời khóa biểu cuối cùng; mỗi giảng viên một bảng 13 khung giờ × 5 ngày (giống bảng phòng, gồm hàng nghỉ trưa), kèm badge số tiết/tuần và số môn trong tuần; mỗi ô ghi môn học cùng tên phòng (nhãn tím). Bấm vào tên giảng viên để thu gọn hoặc mở rộng bảng; nếu vi phạm tiêu chí `G`, ô bị trùng được xếp chồng kèm nhãn `Trùng lịch giảng viên`.
- **Dữ liệu đầu vào**: nằm phía trên kết quả cuối cùng và có thể thu gọn/mở rộng; gồm các bảng giảng viên, môn học và phòng học, kèm số giờ và sức chứa để đối chiếu với kết quả xếp lịch. Bảng giảng viên không hiển thị số lớp học phần mà giảng viên đảm nhận.
- **Fitness qua các thế hệ**: biểu đồ đường ghi lại fitness của thế hệ tốt nhất sau mỗi bước, giúp thấy rõ mức tăng/giảm; trục dọc được thu gọn quanh dải fitness thực tế để biến động dễ nhìn hơn; phía dưới có các chỉ số bắt đầu, cao nhất và cuối cùng.
- **Thời khóa biểu qua các bước**: lưới 10 cột, mỗi ô là một thế hệ với fitness (phần trăm), tổng số vi phạm và số vi phạm từng tiêu chí `P/G/N`; ô nền xanh là thế hệ không có vi phạm, ô có viền vàng là thế hệ fitness cao nhất. Bấm vào một ô (hoặc di chuyển bằng phím mũi tên) thì thời khóa biểu của thế hệ đó hiện ra ở khung ngay dưới lưới, gồm cả phần đầu ghi fitness, số vi phạm, thời gian và quy mô quần thể. Khung lưới giới hạn chiều cao (mặc định 430px, chỉnh bằng biến CSS `--step-grid-height`) và cuộn ngay trong khung nên trang không bị dài khi số thế hệ lớn.

Giao diện dùng thẻ (card) cho từng phòng và từng nhóm dữ liệu đầu vào, bảng có viền gọn, màu trạng thái và tự co giãn trên màn hình nhỏ; phần thông số thuật toán nằm trên cùng và mở sẵn, còn dữ liệu đầu vào nằm trên kết quả cuối và mặc định thu gọn để không chiếm chỗ. Khi in chỉ giữ lại phần kết quả (thời khóa biểu phòng và lịch giảng dạy của giảng viên). Phần chú thích được giữ cố định ở đầu trang khi cuộn để luôn đối chiếu được các ký hiệu. Mỗi ô chứa thông tin của lớp học:

- Tên môn học, tên giảng viên và nhãn thời lượng (ví dụ `2 tiết`).
- Các tiết liền nhau của cùng một lớp trong cùng một cột ngày được **gộp thành một ô `rowspan`** cao bằng số tiết; ô đó mang nhãn thời lượng (ví dụ `3 tiết`) và, nếu lớp dính khung bận, một nhãn `GV bận · tiết 1-2` liệt kê đúng các tiết bận trong khoảng gộp.
- Nếu nhiều lớp cùng được xếp vào một phòng, cùng ngày và cùng tiết (vi phạm tiêu chí `P`), tất cả vẫn được hiển thị: các thẻ lớp học xếp chồng trong ô kèm nhãn `Trùng phòng`, và chuỗi tiết bị cắt tại đúng ô trùng — các tiết còn lại của lớp kéo dài mang dấu `Tiếp tiết`.
- Ba ký hiệu nhỏ mô tả trạng thái ràng buộc cứng, **xanh lá là đạt, đỏ là vi phạm** (đưa chuột vào sẽ hiện giải thích), kèm một ký hiệu mềm màu cam chỉ xuất hiện khi lớp dính khung bận:

| Ký hiệu | Ý nghĩa |
|---|---|
| `P` | Phòng học không bị trùng lịch |
| `G` | Giảng viên không bị trùng lịch dạy |
| `N` | Lớp không bị xếp vào khung nghỉ trưa 12h–13h |
| `B` | (cam, tuỳ chọn) lớp không rơi vào khung giờ giảng viên bận — ràng buộc mềm |

# Theo dõi từng bước khi chạy

Tệp `Trace.py` in ra console thông tin đầu vào, tiến trình tối ưu hoá và lịch giảng dạy
của từng giảng viên sau khi có kết quả. Đồng thời, mỗi thế hệ được lưu vào bộ nhớ để
`HtmlOutput` vẽ biểu đồ fitness và thời khóa biểu của các bước (xem mục "Giải thích kết quả
xuất ra"). Các bảng console dùng ký tự khung `┃ ┌ ─ ┐` và rút gọn cột dài bằng `…`.

**0. Thông tin đầu vào** — in ra trước khi thuật toán bắt đầu chạy

Gồm 5 bảng: giảng viên, môn học, phòng học, toàn bộ danh sách lớp học, và thống kê tổng thể.

```text
  THÔNG TIN ĐẦU VÀO
  Tệp cấu hình : GaSchedule.json
  Quy mô       : 5 giảng viên · 10 môn học · 4 phòng học · 48 lớp học

 ┃ GIẢNG VIÊN                                               ┃
 │ 1  │ Nguyễn Văn An     │ Công nghệ Web, Cấu trúc dữ li… │
 │ 2  │ Trần Thị Bình     │ Cơ sở dữ liệu, Cấu trúc dữ li… │
 ...

 ┃ MÔN HỌC                                                        ┃
 │ 1  │ Lập trình hướng đối tượng      │ 6      │ 18             │
 ...
 │    │ Tổng cộng                      │ 48     │ 160            │

 ┃ PHÒNG HỌC                         ┃
 │ 0  │ Phòng 201 │ 60 giờ          │
 │ 1  │ Phòng 102 │ 60 giờ          │
 │ 2  │ Phòng 303 │ 60 giờ          │
 │ 3  │ Phòng 401 │ 60 giờ          │

  ┃ THỐNG KÊ                                                                  ┃
  │ Tổng số giờ học trong tuần  │ 160 giờ  (48 lớp · trung bình 3.3 giờ/lớp) │
  │ Sức chứa của hệ thống phòng │ 12 tiết/ngày × 5 ngày × 4 phòng = 240 giờ  │
  │ Tỉ lệ sử dụng phòng         │ 66.7 %                                     │
```

Phần thống kê cuối giúp kiểm tra nhanh quy mô dữ liệu và sức chứa phòng trước khi chạy
thuật toán.

**1. Dòng tóm tắt cho mỗi thế hệ**, kèm hai bảng nhỏ: ràng buộc cứng `P/G/N` (đạt trên tổng
số lớp) và ràng buộc mềm `B` (số lớp dính bận cùng trọng số phạt).

```text
  THẾ HỆ 10     │ Độ phù hợp: 0.637500 │ Cá thể: 60   │ Không cải thiện: 4    │   0.17s
    │ P  │ Phòng học không bị trùng       │ 21/48      │ ✗       │
    │ G  │ Giảng viên không trùng lịch    │ 25/48      │ ✗       │
    │ N  │ Không xếp vào khung nghỉ trưa… │ 48/48      │ ✓       │
    │ B  │ Tránh khung giờ bận của GV │ 11 lớp dính bận │ ×0.2 │
```

**2. Bảng thời khóa biểu đầy đủ** của cá thể tốt nhất, in lặp lại mỗi 10 thế hệ, một bảng
cho mỗi phòng. Ta có thể quan sát lịch được sắp xếp lại dần như thế nào. Dấu `↳` nghĩa là
tiết tiếp theo của cùng một lớp đang kéo dài:

```text
  THỜI KHÓA BIỂU TỐI ƯU  —  thế hệ 10  │  độ phù hợp 0.637500
 ┃ PHÒNG Phòng 201
 │ Tiết              │ T2                 │ T3                 │ ...
 │ Tiết 1  7:00-7:50  │ Cấu trúc dữ liệu … │                    │ ...
 │                    │ Nguyễn Văn An (4h) │                    │ ...
 │ Tiết 2  7:50-8:40  │ An toàn thông tin  │                    │ ...
 │ Tiết 3  8:40-9:30  │ An toàn thông tin  │                    │ ...
 │ Tiết 4  9:30-10:20 │ ↳                  │                    │ ...
 │ Nghỉ trưa    12:0… │                    │                    │ ...
```

**3. Chi tiết từng lớp học** kèm ba cờ tiêu chí cứng, in mỗi 50 thế hệ. `✓` là đạt, `✗` là
vi phạm:

```text
 ┃ CHI TIẾT TỪNG LỚP HỌC — thế hệ 1
 │ Mã │ Môn học                │ Giảng viên    │ Ngày │ Tiết    │ Phòng     │ P │ G │ N │
 │ 0  │ Lập trình hướng đối t… │ Phạm Thị Dung │ T4   │ 11 (3h) │ Phòng 401 │ ✗ │ ✗ │ ✓ │
 │ 1  │ Lập trình hướng đối t… │ Phạm Thị Dung │ T6   │ 8 (3h)  │ Phòng 102 │ ✓ │ ✓ │ ✓ │
```

**4. Lịch giảng dạy theo giảng viên** — in ra một lần, sau khi thuật toán chạy xong

Mỗi lớp học là một dòng, sắp xếp theo giảng viên rồi theo ngày và tiết, giúp xem nhanh một
giảng viên dạy môn nào, ngày nào, tiết mấy, phòng nào:

```text
 ┃ LỊCH GIẢNG DẠY THEO GIẢNG VIÊN
 │ Giảng viên    │ Môn học                  │ Ngày │ Tiết    │ Thời lượng │ Phòng     │
 │ Trần Thị Bình │ Hệ điều hành             │ T3   │ 1 (3h)  │ 3 tiết     │ Phòng 201 │
 │ Lê Quốc Cường │ Mạng máy tính            │ T2   │ 2 (4h)  │ 4 tiết     │ Phòng 102 │
```
## Tinh chỉnh mức độ chi tiết

Điều chỉnh các hằng số ở đầu tệp `Trace.py`:

| Hằng số | Mặc định | Ý nghĩa |
|---|---|---|
| `SCHEDULE_EVERY_GENERATION` | `10` | In bảng thời khóa biểu mỗi N thế hệ. Đặt `1` để in mỗi thế hệ, `None` để tắt hẳn |
| `DETAIL_EVERY_GENERATION` | `50` | In chi tiết từng lớp mỗi N thế hệ. `None` để tắt |
| `MAX_COLUMN_WIDTH` | `30` | Độ rộng tối đa của một cột trong bảng console |
| `MAX_HISTORY` | `5000` | Số thế hệ tối đa được lưu để xuất biểu đồ fitness và lịch sử bước ra HTML |

Lịch sử cho HTML được lưu độc lập với việc in bảng ra console. Mọi thế hệ được ghi (tối đa `MAX_HISTORY`) đều xuất hiện trong lưới các bước, mỗi thế hệ chiếm một ô; dữ liệu thời khóa biểu của từng thế hệ được nén thành một mảng JSON trong trang thay vì dựng sẵn toàn bộ bảng.

Ví dụ muốn xem lịch thay đổi ở **từng** thế hệ:

```python
# Trace.py
SCHEDULE_EVERY_GENERATION = 1
DETAIL_EVERY_GENERATION = None
```

Muốn chạy nhanh và gọn như bản gốc:

```python
SCHEDULE_EVERY_GENERATION = None
DETAIL_EVERY_GENERATION = None
```

Dòng tóm tắt mỗi thế hệ thì luôn được in. Nếu chạy thuật toán ngoài `ConsoleApp.py`, nhớ gọi `Trace.reset()` một lần trước khi chạy để mốc thời gian và lịch sử HTML bắt đầu từ đúng.

# Giấy phép

MIT