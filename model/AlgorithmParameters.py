import math


class ParameterError(ValueError):
    """Thông số do người dùng nhập không hợp lệ."""


DEFAULTS = {
    "numberOfChromosomes": 100,
    "trackBest": 5,
    "replaceByGeneration": 8,
    "numberOfCrossoverPoints": 2,
    "mutationSize": 2,
    "crossoverProbability": 80,
    "mutationProbability": 3,
    "maxIterations": 1000,
    "maxStagnation": 100,
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
    if isinstance(raw, bool):
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
    """Chuẩn hoá thông số, điền mặc định và giới hạn các tổ hợp không hợp lệ."""
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
