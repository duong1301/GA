"""Ô thời gian - không gian (ngày, tiết, phòng) và phép ánh xạ sang chỉ số mảng.

Mọi gen vị trí trong Schedule đều là một chỉ số nguyên vào mảng _slots phẳng:

    index = (ngày × NR + phòng) × DAY_HOURS + tiết      (getHashCode)

với NR = số phòng, DAY_HOURS = 13 offset mỗi ngày (0..12, offset 6 là nghỉ trưa).
index // DAY_HOURS cho biết ô thuộc khối (ngày, phòng) nào, index % DAY_HOURS là
offset trong ngày.

    ngày  = index // (DAY_HOURS × NR)                    (parse)
    phòng = (index % (DAY_HOURS × NR)) // DAY_HOURS
    tiết  = (index % (DAY_HOURS × NR)) % DAY_HOURS

Vì công thức phụ thuộc NR, Reservation giữ NR và bảng nhớ tạm ở cấp lớp: đổi số
phòng phải dựng lại bảng, nếu không các chỉ số cũ sẽ giải mã sai. getReservation
làm việc đó hộ caller (kênh duy nhất để có NR mới là nr != NR và nr > 0).
"""
from .Constant import Constant


class Reservation:
    # Số phòng đang dùng cho công thức băm; -1 = chưa cấu hình
    NR = -1
    # Bảng nhớ tạm hashCode -> đối tượng, để hash(reservation) trả về đúng chỉ số
    # ô và hai ô giống nhau so sánh được mà không cần dựng đối tượng mới
    _reservationPool = {}


    def __init__(self, day: int, time: int, room: int):
        self.Day = day
        self.Time = time
        self.Room = room

    @staticmethod
    def parse(hashCode):
        """Giải mã chỉ số ô thành (ngày, phòng, tiết) và nhớ lại kết quả.

        Đây là phép nghịch đảo của getHashCode; nhờ bảng nhớ tạm, Schedule có thể
        gọi parse cho mỗi lần chấm điểm mà không phân bổ đối tượng mới.
        """
        reservation = Reservation._reservationPool.get(hashCode)
        if reservation is None:
            day = hashCode // (Constant.DAY_HOURS * Reservation.NR)
            hashCode2 = hashCode - (day * Constant.DAY_HOURS * Reservation.NR)
            room = hashCode2 // Constant.DAY_HOURS
            time = hashCode2 % Constant.DAY_HOURS
            reservation = Reservation(day, time, room)
            Reservation._reservationPool[hashCode] = reservation
        return reservation

    @staticmethod
    def getHashCode(day: int, time: int, room: int) -> int:
        """Ép (ngày, phòng, tiết) về chỉ số ô phẳng; tiết là offset 0-based."""
        return day * Reservation.NR * Constant.DAY_HOURS + room * Constant.DAY_HOURS + time

    @staticmethod
    def getReservation(nr: int, day: int, time: int, room: int):
        """Lấy ô tương ứng với số phòng `nr`, đồng thời đổi công thức băm nếu nr đổi.

        Khi bộ cấu hình có số phòng khác với NR đang dùng (thường xảy ra giữa hai
        lần chạy trong cùng tiến trình), bảng nhớ tạm bị xóa vì mọi chỉ số cũ đã
        được tính theo độ rộng ngày của số phòng cũ.
        """
        if nr != Reservation.NR and nr > 0:
            Reservation.NR = nr
            Reservation._reservationPool.clear()

        hashCode = Reservation.getHashCode(day, time, room)
        reservation = Reservation.parse(hashCode)

        if reservation is None:
            reservation = Reservation(day, time, room)
            Reservation._reservationPool[hashCode] = reservation
        return reservation

    def __hash__(self) -> int:
        # Trả về thẳng chỉ số ô trong Schedule._slots, nên hash() dùng làm index
        return Reservation.getHashCode(self.Day, self.Time, self.Room)


    def __eq__(self, other):
        # Hai ô bằng nhau khi cùng (ngày, phòng, tiết) vì băm đã ép về một số
        if not isinstance(other, self.__class__):
            return False
        return hash(self) == hash(other)
            
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __str__(self):
        return "Day: " + str(self.Day) + ", " + "Room: " + str(self.Room) + ", Time: " + str(self.Time)

