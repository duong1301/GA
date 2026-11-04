class CourseClass:
    """Một lớp học phần = một môn + số tiết liền nhau mỗi tuần.

    Đây là đơn vị mà GA xếp lịch: mỗi CourseClass tương ứng MỘT gen vị trí
    (ngày, phòng, tiết) và MỘT gen giảng viên trong nhiễm sắc thể. Tổng số lớp
    quyết định độ dài nhiễm sắc thể, số ô cờ tiêu chí (3 cờ mỗi lớp) và mẫu số
    của công thức fitness.
    """
    # Bộ đếm ID được dùng để gán ID tự động
    _next_class_id = 0

    # Khởi tạo đối tượng lớp học phần
    # Giảng viên KHÔNG còn thuộc lớp học phần: do nhiễm sắc thể (GA) gán khi xếp lịch.
    def __init__(self, course, duration):
        # ID tự tăng theo thứ tự đọc tệp; Schedule dùng thứ tự này làm thứ tự gen
        self.Id = CourseClass._next_class_id
        CourseClass._next_class_id += 1
        # Trả về con trỏ tới môn học mà lớp học phần này thuộc về
        self.Course = course
        # Số tiết liền nhau trong một buổi (bộ dữ liệu mẫu dùng 2-4, trung bình
        # 160/48 ≈ 3.3 tiết/lớp). Khối tiết không được chồng khung nghỉ trưa và
        # không tràn khỏi ngày 13 offset.
        self.Duration = duration


    def __hash__(self):
        return hash(self.Id)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return hash(self) == hash(other)

    def __ne__(self, other):
        # Không thực sự cần thiết, nhưng để tránh việc x==y và x!=y
        # cùng trả về True
        return not (self == other)

    # Khởi động lại việc gán ID
    @staticmethod
    def restartIDs() -> None:
        CourseClass._next_class_id = 0
