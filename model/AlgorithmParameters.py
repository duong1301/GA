"""Thông số của giải thuật di truyền: mặc định, khoảng hợp lệ và quy tắc ép buộc.

MỖI THÔNG SỐ ẢNH HƯỞNG GÌ TỚI VÒNG TIẾN HOÁ (xem algorithm/GeneticAlgorithm.py):
  numberOfChromosomes   N — số cá thể mỗi thế hệ; không gian tìm kiếm rộng hơn
                        nhưng mỗi thế hệ chậm hơn và elit chiếm nhiều chỗ hơn.
  trackBest             số cá thểelit được bảo vệ khỏi bị con lai ghi đè.
  replaceByGeneration   số con lai cài vào quần thể mỗi thế hệ = tốc độ thay máu.
  numberOfCrossoverPoints  số điểm cắt trên dãy gen khi lai ghép (cắt nhiều điểm
                        thì con trộn hai cha mẹ mạnh hơn).
  mutationSize          số lớp bị dời trong MỘT lần đột biến được kích hoạt.
  crossoverProbability / mutationProbability  ngưỡng % cho hai phép thử
                        randrange(100) > p, nên xác suất thực sự là (p + 1) / 100:
                        80% -> 81% lai, 3% -> 4% đột biến.
  maxIterations         trần số thế hệ.
  maxStagnation         số thế hệ liên tiếp fitness tốt nhất không đổi (|Δ| <= 1e-7)
                        trước khi bỏ cuộc.
  minFitness            ngưỡng thắng; vòng lặp dừng khi best.fitness LỚN HƠN hẳn
                        giá trị này (nên 1.0 gần như không bao giờ chạm tới, còn
                        0.0 khiến vòng lặp break ngay ở thế hệ 0).

Giá trị mặc định dưới đây là cấu hình dùng cho bộ dữ liệu mẫu 48 lớp:
quần thể 100, giữ 5 elit, thay 8 cá thể mỗi thế hệ, chạy tối đa 1000 thế hệ.
"""
import math


class ParameterError(ValueError):
    """Thông số do người dùng nhập không hợp lệ."""


DEFAULTS = {
    # số cá thể mỗi thế hệ (N)
    "numberOfChromosomes": 100,
    # số cá thểelit không bao giờ bị con lai ghi đè
    "trackBest": 5,
    # số con lai được cài vào quần thể mỗi thế hệ
    "replaceByGeneration": 8,
    # số điểm cắt trên dãy gen khi lai ghép
    "numberOfCrossoverPoints": 2,
    # số lớp bị dời khi một lần đột biến được kích hoạt
    "mutationSize": 2,
    # ngưỡng % cho phép thử lai ghép (xác suất thật = 81%)
    "crossoverProbability": 80,
    # ngưỡng % cho phép thử đột biến (xác suất thật = 4%)
    "mutationProbability": 3,
    # trần số thế hệ của một lần chạy
    "maxIterations": 1000,
    # số thế hệ đứng yên liên tiếp trước khi dừng sớm
    "maxStagnation": 100,
    # dừng sớm khi fitness tốt nhất vượt ngưỡng này (so sánh nghiêm >)
    "minFitness": 0.999,
}



FIELDS = (
    {
        "name": "numberOfChromosomes",
        "label": "Kích thước quần thể",
        "kind": "int",
        "min": 2,
        "max": 1000,
        "step": 1,
        "unit": "cá thể",
        "help": "Số cá thể trong mỗi thế hệ.",
    },
    {
        "name": "trackBest",
        "label": "Giữ lại cá thể tốt",
        "kind": "int",
        "min": 1,
        "max": 1000,
        "step": 1,
        "unit": "cá thể",
        "help": "Số cá thể tốt nhất không bị thay thế.",
    },
    {
        "name": "replaceByGeneration",
        "label": "Thay thế mỗi thế hệ",
        "kind": "int",
        "min": 1,
        "max": 1000,
        "step": 1,
        "unit": "cá thể",
        "help": "Số cá thể được thay bằng con lai mỗi thế hệ.",
    },
    {
        "name": "numberOfCrossoverPoints",
        "label": "Điểm lai ghép",
        "kind": "int",
        "min": 1,
        "max": 50,
        "step": 1,
        "unit": "điểm",
        "help": "Số điểm cắt khi lai ghép; tự giới hạn theo số lớp.",
    },
    {
        "name": "mutationSize",
        "label": "Mức đột biến",
        "kind": "int",
        "min": 1,
        "max": 50,
        "step": 1,
        "unit": "lớp",
        "help": "Số lớp bị thay đổi trong một lần đột biến.",
    },
    {
        "name": "crossoverProbability",
        "label": "Xác suất lai ghép",
        "kind": "int",
        "min": 0,
        "max": 100,
        "step": 1,
        "unit": "%",
        "help": "Tỉ lệ chọn phép lai ghép.",
    },
    {
        "name": "mutationProbability",
        "label": "Xác suất đột biến",
        "kind": "int",
        "min": 0,
        "max": 100,
        "step": 1,
        "unit": "%",
        "help": "Tỉ lệ chọn phép đột biến.",
    },
    {
        "name": "maxIterations",
        "label": "Số thế hệ tối đa",
        "kind": "int",
        "min": 1,
        "max": 100000,
        "step": 1,
        "unit": "thế hệ",
        "help": "Giới hạn số thế hệ của một lần chạy.",
    },
    {
        "name": "maxStagnation",
        "label": "Dừng khi không cải thiện",
        "kind": "int",
        "min": 1,
        "max": 100000,
        "step": 1,
        "unit": "thế hệ",
        "help": "Dừng sau bấy nhiêu thế hệ fitness không tăng.",
    },
    {
        "name": "minFitness",
        "label": "Fitness mục tiêu",
        "kind": "float",
        "min": 0.0,
        "max": 1.0,
        "step": 0.001,
        "unit": "",
        "help": "Dừng sớm khi fitness vượt giá trị này.",
    },
)


def format_value(value):
    """Hiển thị số thực gọn, không có .0 thừa."""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _parse_value(field, raw):
    """Ép một giá trị thô (từ form HTML hoặc JSON) về kiểu và khoảng của field.

    Số nguyên không nhận phần thập phân, float phải hữu hạn, và mọi giá trị nằm
    ngoài [min, max] của FIELDS bị từ chối bằng ParameterError thay vì âm thầm cắt.
    """
    if isinstance(raw, bool):
        # bool là int ở Python nhưng không phải thông số có nghĩa ở đây
        raise ParameterError("{} phải là một số.".format(field["label"]))

    try:
        if field["kind"] == "int":
            if isinstance(raw, float) and not raw.is_integer():
                raise ValueError
            value = int(raw)
        else:
            value = float(raw)
    except (TypeError, ValueError, OverflowError):
        raise ParameterError("{} phải là một số hợp lệ.".format(field["label"]))

    if field["kind"] == "float" and not math.isfinite(value):
        raise ParameterError("{} phải là một số hữu hạn.".format(field["label"]))

    if value < field["min"] or value > field["max"]:
        raise ParameterError(
            "{} phải nằm trong khoảng {}–{}.".format(
                field["label"],
                format_value(field["min"]),
                format_value(field["max"]),
            )
        )

    return value


def normalize(values=None, numberOfClasses=None):
    """Chuẩn hoá thông số, điền mặc định và giới hạn các tổ hợp không hợp lệ.

    Ba bất biến ép buộc, khớp với những gì GeneticAlgorithm giả định:
        2 <= numberOfChromosomes
        1 <= trackBest <= numberOfChromosomes - 1
        1 <= replaceByGeneration <= numberOfChromosomes - trackBest
    Hai ràng buộc cuối bảo đảm quần thể còn ít nhất một chỗ không bị elit chiếm
    cho con lai; nếu người dùng nhập vượt, giá trị bị hạ xuống chứ không báo lỗi.

    numberOfClasses (số lớp thực tế của bộ dữ liệu) còn chặn thêm:
        numberOfCrossoverPoints <= số lớp   (điểm cắt rút không hoàn lại; vượt quá
                                            sẽ khiến vòng chọn điểm cắt lặp vô hạn)
        mutationSize <= số lớp               (dời nhiều hơn số lớp là vô nghĩa)
    """
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ParameterError("Thông số thuật toán không hợp lệ.")

    result = {}
    for field in FIELDS:
        name = field["name"]
        result[name] = _parse_value(field, values.get(name, DEFAULTS[name]))

    # Nhóm cá thể tốt phải nhỏ hơn quần thể để còn chỗ cho con lai.
    population = result["numberOfChromosomes"]
    result["trackBest"] = min(result["trackBest"], population - 1)
    result["replaceByGeneration"] = min(
        result["replaceByGeneration"],
        population - result["trackBest"],
    )

    # Các toán tử không nên vượt quá số lớp thực tế.
    if numberOfClasses is not None and int(numberOfClasses) > 0:
        class_count = int(numberOfClasses)
        result["numberOfCrossoverPoints"] = min(
            result["numberOfCrossoverPoints"], class_count
        )
        result["mutationSize"] = min(result["mutationSize"], class_count)

    return result


def summary(values=None):
    """Chuỗi tóm tắt ngắn để hiển thị trên phần thu gọn."""
    values = normalize(values)
    return "{} cá thể · {} thế hệ · dừng sau {} thế hệ".format(
        values["numberOfChromosomes"],
        values["maxIterations"],
        values["maxStagnation"],
    )
