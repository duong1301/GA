"""Hằng số mô hình thời gian và các hàm quy đổi giữa hai hệ quy chiếu tiết học.

MỘT NGÀY CÓ DAY_HOURS = 13 OFFSET, đánh số 0..12:
    offset 0..5   : 6 tiết sáng, 7:00 → 12:00, mỗi tiết 50 phút, liền nhau
    offset 6      : khung nghỉ trưa 12:00 → 13:00 (KHÔNG phải tiết học)
    offset 7..12  : 6 tiết chiều, 13:00 → 18:00
Một tuần có DAYS_NUM = 5 ngày nên một phòng có TEACHING_HOURS × DAYS_NUM = 60 tiết
dạy thật. Schedule._slots phẳng vẫn giữ 13 offset mỗi ngày (kể cả nghỉ trưa) vì
công thức băm ô nhân thẳng với DAY_HOURS.

HAI HỆ QUY CHIẾU, đừng nhầm:
    offset 0-based  : dùng trong Reservation.Time, Professor.BusySlots, JSON "busy"
                      và mọi vòng lặp tính toán của giải thuật.
    số tiết 1-based : chỉ để hiển thị, do periodNumber() sinh ra. Vì nghỉ trưa không
                      chiếm số tiết, quy đổi KHÔNG đều: sáng offset o → tiết o + 1,
                      chiều offset o → tiết o (buổi chiều đã tự nhảy một bậc).
                      HtmlOutput lại cộng thêm 1 nữa để ra số dòng bảng (1..13,
                      nghỉ trưa ở dòng 7).
"""
class Constant:

    # Số ngày trong một tuần
    DAYS_NUM = 5
    # Giờ bắt đầu làm việc trong ngày (buổi sáng)
    START_HOUR = 7
    # Thời lượng mỗi tiết (phút)
    PERIOD_MINUTES = 50
    # Giờ bắt đầu buổi chiều (sau giờ nghỉ trưa)
    AFTERNOON_START_HOUR = 13
    # Số khung giờ trong một ngày:
    #   buổi sáng  6 tiết  (7:00 - 12:00, liền nhau)  -> chỉ số 0..5
    #   nghỉ trưa  1 khung  (12:00 - 13:00) -> chỉ số LUNCH_PERIOD
    #   buổi chiều 6 tiết  (13:00 - 18:00, liền nhau) -> chỉ số 7..12
    DAY_HOURS = 13
    # Chỉ số (bắt đầu từ 0) của khung giờ nghỉ trưa trong ngày.
    # Xếp lịch vào khung giờ này là vi phạm ràng buộc cứng N.
    LUNCH_PERIOD = 6
    # Số tiết dạy thực sự trong một ngày (không kể khung nghỉ trưa)
    TEACHING_HOURS = DAY_HOURS - 1

    @staticmethod
    def periodNumber(offset):
        """Số thứ tự tiết (bắt đầu từ 1), KHÔNG tính khung nghỉ trưa.

        Buổi sáng: offset 0..LUNCH_PERIOD-1 -> tiết 1..LUNCH_PERIOD.
        Buổi chiều: offset LUNCH_PERIOD+1..DAY_HOURS-1 -> tiết LUNCH_PERIOD+1..DAY_HOURS.
        Trả về None nếu offset là khung nghỉ trưa.
        """
        if offset == Constant.LUNCH_PERIOD:
            return None
        if offset < Constant.LUNCH_PERIOD:
            return offset + 1
        return offset

    @staticmethod
    def periodStart(offset):
        """Trả về số phút bắt đầu (tính từ 0h) của tiết có chỉ số offset (0-based).

        Các tiết trong cùng buổi xếp LIỀN NHAU, mỗi tiết PERIOD_MINUTES phút.
        Buổi sáng bắt đầu START_HOUR, buổi chiều bắt đầu AFTERNOON_START_HOUR.
        """
        if offset <= Constant.LUNCH_PERIOD:
            # buổi sáng: các tiết liền nhau
            return Constant.START_HOUR * 60 + offset * Constant.PERIOD_MINUTES
        # buổi chiều: các tiết liền nhau (bỏ qua khung nghỉ trưa)
        local = offset - Constant.LUNCH_PERIOD - 1
        return Constant.AFTERNOON_START_HOUR * 60 + local * Constant.PERIOD_MINUTES

    @staticmethod
    def formatHM(minutes):
        """Định dạng số phút thành chuỗi 'H:MM' (ví dụ 7:00, 13:50)."""
        return "{}:{:02d}".format(minutes // 60, minutes % 60)

    @staticmethod
    def periodTimeRange(offset, sep=" – "):
        """Chuỗi 'HH:MM<sep>HH:MM' của một tiết (chỉ số offset, 0-based)."""
        start = Constant.periodStart(offset)
        end = start + Constant.PERIOD_MINUTES
        return "{}{}{}".format(Constant.formatHM(start), sep, Constant.formatHM(end))

    @staticmethod
    def lunchRange(sep=" – "):
        """Chuỗi 'HH:MM<sep>HH:MM' của khung nghỉ trưa (giữa buổi sáng và buổi chiều)."""
        morning_end = Constant.periodStart(Constant.LUNCH_PERIOD - 1) + Constant.PERIOD_MINUTES
        afternoon_start = Constant.periodStart(Constant.LUNCH_PERIOD + 1)
        return "{}{}{}".format(Constant.formatHM(morning_end), sep, Constant.formatHM(afternoon_start))
