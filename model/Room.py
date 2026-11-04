# Lưu trữ dữ liệu về phòng học
class Room:
    """Phòng học; ID do bộ đếm tự tăng, KHÔNG đọc từ tệp.

    ID được gán theo thứ tự xuất hiện của các object `room` trong JSON, nên thêm
    hoặc đảo vị trí phòng làm thay đổi ID và kéo theo toàn bộ tham chiếu phòng
    trong Reservation/slots dịch theo. Mỗi phòng có khả năng chứa
    Constant.TEACHING_HOURS × Constant.DAYS_NUM tiết mỗi tuần.
    """
    # Bộ đếm ID được dùng để gán ID tự động
    _next_room_id = 0


    # Khởi tạo dữ liệu phòng học và gán ID cho phòng
    def __init__(self, name):
        # Trả về ID của phòng - được gán tự động
        self.Id = Room._next_room_id
        Room._next_room_id += 1
        # Trả về tên phòng
        self.Name = name

    def __hash__(self):
        return hash(self.Id)

    # So sánh ID của hai đối tượng đại diện cho phòng học
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
        Room._next_room_id = 0
