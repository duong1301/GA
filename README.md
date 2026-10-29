# GASchedule.py

Lập thời khóa biểu học bằng thuật toán di truyền với Python

# Giới thiệu

Lập thời khóa biểu là một bài toán NP-khó. Bài toán này có thể được giải bằng thuật toán tìm kiếmheuristic để tìm ra phương án tối ưu, nhưng cách đó chỉ hiệu quả với những trường hợp đơn giản. Với dữ liệu đầu vào và yêu cầu phức tạp hơn, việc tìm ra một phương án tốt có thể mất khá lâu, hoặc thậm chí không thể thực hiện được. Đây là lúc thuật toán di truyền bước vào cuộc. Trong tài liệu này, tôi giả định rằng bạn đã quen thuộc với các khái niệm cơ bản của thuật toán di truyền, nên sẽ không mô tả lại chi tiết, vì điều đó đã được trình bày rất nhiều lần trước đây.

# Bối cảnh

Khi lập thời khóa biểu, bạn phải tính đến nhiều yêu cầu: số lượng giảng viên, lớp học và phòng học, cùng nhiều yếu tố khác. Các yêu cầu này có thể được chia thành vài nhóm theo mức độ quan trọng.

**Ràng buộc cứng** (vi phạm một ràng buộc thì lịch không khả thi):

1. Một lớp học chỉ có thể được xếp vào phòng học còn trống.
2. Không giảng viên nào được có hai lớp học cùng lúc.

**Ràng buộc mềm** (có thể bị vi phạm mà lịch vẫn khả thi):

1. Thời gian giảng viên muốn dạy.
2. Phòng học giảng viên muốn dùng.
3. Mức độ phân bố (theo thời gian hoặc không gian) của các lớp học dành cho giảng viên.

Rõ ràng, ràng buộc cứng và ràng buộc mềm phụ thuộc vào tình huống cụ thể. Trong ví dụ này, chỉ các ràng buộc cứng được cài đặt. Hãy bắt đầu bằng việc giải thích các đối tượng tạo nên một thời khóa biểu.

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

Làm thế nào để biểu diễn nhiễm sắc thể cho một thời khóa biểu? Ta cần một ô thời gian - không gian (time-space slot) cho mỗi khung giờ (ta giả thiết thời gian tính theo đơn vị một giờ), cho mỗi phòng học, mỗi ngày. Một ngày có 11 khung giờ từ 7 giờ đến 18 giờ, chia làm hai buổi: buổi sáng 5 tiết (7h–12h) và buổi chiều 5 tiết (13h–18h); khung 12h–13h là giờ nghỉ trưa, không được xếp lịch (tổng cộng 10 tiết dạy mỗi ngày). Ngày làm việc từ thứ hai đến thứ sáu (tổng cộng 5 ngày). Các tham số này được cấu hình trong `model/Constant.py` qua `START_HOUR`, `DAY_HOURS` (11 khung giờ), `LUNCH_PERIOD` (chỉ số khung nghỉ trưa) và `TEACHING_HOURS` (10 tiết dạy).

Kết quả sẽ được hiển thị dưới dạng bảng HTML. Chương trình sẽ mở trình duyệt mặc định để trình bày thời khóa biểu một cách rõ ràng.

# Độ thích nghi

Bây giờ cần gán một giá trị độ thích nghi cho nhiễm sắc thể. Như đã nói ở trên, chỉ có các ràng buộc cứng được dùng để tính độ thích nghi. Cách tính như sau:

- Mỗi lớp học có thể nhận từ 0 đến 3 điểm, ứng với các tiêu chí `P`, `G`, `N`.
- Nếu lớp học nằm trong phòng còn trống, tăng điểm của lớp đó.
- Nếu giảng viên không có lớp khác trong thời điểm đó, tăng thêm một điểm cho lớp.
- Nếu lớp học không rơi vào khung giờ nghỉ trưa 12h–13h, tăng thêm một điểm cho lớp.
- Nếu một lớp vi phạm quy tắc, điểm của tiêu chí đó là `1 - trọng số phạt` thay vì `1`. Trọng số phạt nằm trong khoảng 0 đến 1; `0` nghĩa là không phạt, `1` nghĩa là mất trọn điểm của tiêu chí.

Tổng điểm của một thời khóa biểu là tổng số điểm của tất cả các lớp. Giá trị độ thích nghi được tính bằng `điểm_lịch / điểm_tối_đa`, trong đó `điểm_tối_đa = số_lớp_học × 3`. Giá trị độ thích nghi nằm trong khoảng từ 0 đến 1.

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

Tệp `GaSchedule.json` đi kèm chứa: 10 giảng viên, 8 môn học, 3 phòng học và 38 lớp học.

```json
[
    { "prof":   { "id": 1, "name": "Nguyễn Văn An" } },
    { "course": { "id": 1, "name": "Lập trình hướng đối tượng" } },
    { "room":   { "name": "Phòng 201" } },
    { "class":  { "professor": 1, "course": 1, "duration": 2 } }
]
```

## Trọng số tiêu chí

Ba tiêu chí được lưu trong `model/Criteria.py`. Trọng số là **mức phạt** khi lớp học vi phạm:

| Mã | Tiêu chí | Trọng số phạt |
|---|---|---|
| `P` | Phòng học không bị trùng lịch | 1.0 |
| `G` | Giảng viên không bị trùng lịch | 1.0 |
| `N` | Không xếp lịch vào khung nghỉ trưa 12h–13h | 1.0 |

Khi một lớp vi phạm tiêu chí, điểm của tiêu chí đó là `1 - trọng số`. Vì vậy `P`, `G` và `N` là các tiêu chí nghiêm: vi phạm sẽ mất trọn 1 điểm. Trọng số `0` nghĩa là không phạt, còn `1` là phạt tối đa.

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
- cập nhật cả trang đang mở và tệp `.htm` trong thư mục tạm.

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
- các khối **Thời khóa biểu qua các bước** cho phép mở từng bước trung gian để xem lịch tương ứng, kèm badge số lớp đạt từng tiêu chí `P/G/N`.

Gọi `Tracer.reset()` trước khi chạy để xóa lịch sử của lần chạy trước. Nếu không truyền `history`, HTML chỉ hiển thị kết quả cuối cùng như trước đây. Mặc định tối đa 60 bước tiêu biểu được vẽ lịch chi tiết; có thể đổi bằng `HtmlOutput.MAX_STEP_PANELS`.

Project hiện chỉ dùng `GeneticAlgorithm`; các thuật toán tối ưu đa mục tiêu và siêu heuristic khác đã được lược bỏ để tập trung vào GA.

# Thư viện yêu cầu

- `numpy >= 1.2.0`

# Giải thích kết quả xuất ra

Kết quả là một tệp HTML hoàn chỉnh (đã nhúng sẵn CSS và JavaScript, không cần mạng) gồm:

- Phần tiêu đề và thống kê độ phù hợp.
- **Thông số thuật toán**: khối nằm trên phần chú thích và dữ liệu đầu vào, mở sẵn để chỉnh kích thước quần thể, lai ghép, đột biến, điều kiện dừng và fitness mục tiêu; nút **↻ Chạy lại** nằm ở phần đầu khối.
- **Chú thích 3 tiêu chí** với ký hiệu `P/G/N`, được giữ cố định khi cuộn trang.
- **Thời khóa biểu cuối cùng**: một bảng cho mỗi phòng học, 11 hàng tương ứng 11 khung giờ (10 tiết dạy từ 7h–12h và 13h–18h, xen giữa là hàng nền kẻ chéo "Nghỉ trưa" 12h–13h) và 5 cột tương ứng từ thứ hai đến thứ sáu.
- **Lịch giảng dạy theo giảng viên**: nằm ngay dưới thời khóa biểu cuối cùng; mỗi giảng viên một bảng 11 khung giờ × 5 ngày (giống bảng phòng, gồm hàng nghỉ trưa), kèm badge số tiết/tuần và số môn trong tuần; mỗi ô ghi môn học cùng tên phòng (nhãn tím). Bấm vào tên giảng viên để thu gọn hoặc mở rộng bảng; nếu vi phạm tiêu chí `G`, ô bị trùng được xếp chồng kèm nhãn `Trùng lịch giảng viên`.
- **Dữ liệu đầu vào**: nằm phía trên kết quả cuối cùng và có thể thu gọn/mở rộng; gồm các bảng giảng viên, môn học và phòng học, kèm số giờ và sức chứa để đối chiếu với kết quả xếp lịch. Bảng giảng viên không hiển thị số lớp học phần mà giảng viên đảm nhận.
- **Fitness qua các thế hệ**: biểu đồ đường ghi lại fitness của thế hệ tốt nhất sau mỗi bước, giúp thấy rõ mức tăng/giảm; trục dọc được thu gọn quanh dải fitness thực tế để biến động dễ nhìn hơn; phía dưới có các chỉ số bắt đầu, cao nhất và cuối cùng.
- **Thời khóa biểu qua các bước**: các khối thu gọn, mở ra để xem lịch của bước trung gian. Kết quả cuối cùng luôn được hiển thị riêng ở phía trên; biểu đồ fitness vẫn có đủ mọi thế hệ đã ghi. Mỗi bước hiển thị badge `P/G/N` với số lớp đạt trên tổng số lớp, màu xanh nếu đạt toàn bộ và đỏ nếu còn vi phạm.

Giao diện dùng thẻ (card) cho từng phòng và từng nhóm dữ liệu đầu vào, bảng có viền gọn, màu trạng thái và tự co giãn trên màn hình nhỏ; phần thông số thuật toán nằm trên cùng và mở sẵn, còn dữ liệu đầu vào nằm trên kết quả cuối và mặc định thu gọn để không chiếm chỗ. Khi in chỉ giữ lại phần kết quả (thời khóa biểu phòng và lịch giảng dạy của giảng viên). Phần chú thích được giữ cố định ở đầu trang khi cuộn để luôn đối chiếu được các ký hiệu. Mỗi ô chứa thông tin của lớp học:

- Tên môn học, tên giảng viên và nhãn thời lượng (ví dụ `2 tiết`).
- Nếu nhiều lớp cùng được xếp vào một phòng, cùng ngày và cùng tiết (vi phạm tiêu chí `P`), tất cả vẫn được hiển thị: các thẻ lớp học xếp chồng trong ô kèm nhãn `Trùng phòng`; những tiết tiếp theo của lớp kéo dài được đánh dấu `Tiếp tiết`.
- Hai ký hiệu nhỏ mô tả trạng thái kiểm tra ràng buộc, **xanh lá là đạt, đỏ là vi phạm** (đưa chuột vào sẽ hiện giải thích):

| Ký hiệu | Ý nghĩa |
|---|---|
| `P` | Phòng học không bị trùng lịch |
| `G` | Giảng viên không bị trùng lịch dạy |
| `N` | Lớp không bị xếp vào khung nghỉ trưa 12h–13h |

# Theo dõi từng bước khi chạy

Tệp `Trace.py` in ra console thông tin đầu vào, tiến trình tối ưu hoá và lịch giảng dạy của từng giảng viên sau khi có kết quả. Đồng thời, mỗi thế hệ được lưu vào bộ nhớ để `HtmlOutput` vẽ biểu đồ fitness và thời khóa biểu của các bước (xem mục "Giải thích kết quả xuất ra").

**0. Thông tin đầu vào** — in ra trước khi thuật toán bắt đầu chạy

Gồm 5 bảng: giảng viên, môn học, phòng học, toàn bộ danh sách lớp học, và thống kê tổng thể.

```
THÔNG TIN ĐẦU VÀO
Tệp cấu hình : /GaSchedule.json
Quy mô       : 10 giảng viên · 8 môn học · 3 phòng học · 38 lớp học

  GIẢNG VIÊN
  Mã    Họ tên                     Danh sách môn dạy
  1     Nguyễn Văn An               Cơ sở dữ liệu, Cấu trúc dữ liệu...
  ...

  LỚP HỌC
  Mã    Môn học                    Giảng viên      Thời lượng
  0     Lập trình hướng đối tượng  Nguyễn Văn An   3 tiết
  2     Lập trình hướng đối tượng  Lê Quốc Cường   3 tiết
  ...

  THỐNG KÊ
  Tổng số giờ học trong tuần : 80 giờ (38 lớp, trung bình 2.1 giờ/lớp)
  Sức chứa của hệ thống phòng: 10 tiết/ngày x 5 ngày x 3 phòng = 150 giờ
  Tỉ lệ sử dụng phòng       : 53.3%
```

Phần thống kê cuối giúp kiểm tra nhanh quy mô dữ liệu và sức chứa phòng trước khi chạy thuật toán.

**1. Dòng tóm tắt cho mỗi thế hệ**

```
THẾ HỆ 10     │ Độ phù hợp: 0.862963 │ Cá thể: 100  │ Không cải thiện: 6     │ 3.73s
    ┌────┬────────────────────────────────────┬──────────┬────────┐
    │ Mã │ Ràng buộc                          │ Đạt/tổng │ Kết quả│
    ├────┼────────────────────────────────────┼──────────┼────────┤
    │ P  │ Phòng học không bị trùng           │   38/38  │   ✓    │
    │ G  │ Giảng viên không trùng lịch        │   36/38  │   ✗    │
    │ N  │ Không xếp vào khung nghỉ trưa ...  │   38/38  │   ✓    │
    └────┴────────────────────────────────────┴──────────┴────────┘
```

**2. Bảng thời khóa biểu đầy đủ** của cá thể tốt nhất, in lặp lại mỗi 10 thế hệ. Ta có thể quan sát lịch được sắp xếp lại dần như thế nào. Dấu `^` nghĩa là tiết tiếp theo của cùng một lớp đang kéo dài:

```
  +-- PHÒNG Phòng 201 ----------------------------------------------------
  +------------------------------------------------------------------------------------
  | Tiết              | T2                        | T3                        | ...
  +------------------------------------------------------------------------------------
  | Tiết 2 (8-9)      |                           | Lập trình hướng đối tượng / Trần Thị | ...
  | Tiết 3 (9-10)     | An toàn thông tin        | ^                         | ...
  | Tiết 4 (10-11)    |                           | ^                         | ...
  | Nghỉ trưa 12-13   |                           |                           | ...
  | Tiết 7 (13-14)    |                           |                           | ...
  +------------------------------------------------------------------------------------
```

**3. Chi tiết từng lớp học** kèm 3 cờ tiêu chí, in mỗi 50 thế hệ. `-` là đạt, `X` là vi phạm:

```
  Mã   Môn học                      Giảng viên           Ngày  Tiết        Phòng     P G N
  0    Lập trình hướng đối tượng    Nguyễn Văn An        T6    tiết 8 (3h)   Phòng 102  ---
  4    Lập trình hướng đối tượng    Vũ Anh Đức           T4    tiết 9 (2h)   Phòng 102  -X-
```

**4. Lịch giảng dạy theo giảng viên** — in ra một lần, sau khi thuật toán chạy xong

Mỗi lớp học là một dòng, sắp xếp theo giảng viên rồi theo ngày và tiết, giúp xem nhanh một giảng viên dạy môn nào, ngày nào, tiết mấy, phòng nào:

```
  LỊCH GIẢNG DẠY THEO GIẢNG VIÊN
  Giảng viên        Môn học                 Ngày  Tiết      Thời lượng  Phòng
  Nguyễn Văn An     Cơ sở dữ liệu           T2    7 (2h)     2 tiết      Phòng 201
  Nguyễn Văn An     Cấu trúc dữ liệu...     T4    3 (3h)     3 tiết      Phòng 102
  ...
```

## Tinh chỉnh mức độ chi tiết

Điều chỉnh các hằng số ở đầu tệp `Trace.py`:

| Hằng số | Mặc định | Ý nghĩa |
|---|---|---|
| `SCHEDULE_EVERY_GENERATION` | `10` | In bảng thời khóa biểu mỗi N thế hệ. Đặt `1` để in mỗi thế hệ, `None` để tắt hẳn |
| `DETAIL_EVERY_GENERATION` | `50` | In chi tiết từng lớp mỗi N thế hệ. `None` để tắt |
| `MAX_COLUMN_WIDTH` | `30` | Độ rộng tối đa của một cột trong bảng console |
| `MAX_HISTORY` | `5000` | Số thế hệ tối đa được lưu để xuất biểu đồ fitness và lịch sử bước ra HTML |

Lịch sử cho HTML được lưu độc lập với việc in bảng ra console. Muốn giới hạn số bước có lịch chi tiết trong HTML, đổi `HtmlOutput.MAX_STEP_PANELS` (mặc định `60`).

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