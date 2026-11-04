# Lưu trữ dữ liệu về môn học
class Course:
    """Một môn học trong danh mục; ID lấy thẳng từ tệp cấu hình.

    Môn học không chứa giảng viên hay lịch: quan hệ "ai dạy được môn này" do
    Professor.Subjects và tra cứu trong Configuration đảm nhiệm, còn số tiết mỗi
    tuần nằm ở các CourseClass trỏ về môn.
    """
    # Khởi tạo môn học
    def __init__(self, id, name):
        # Trả về ID của môn học
        self.Id = id
        # Trả về tên của môn học
        self.Name = name
